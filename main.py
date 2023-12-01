import re
import threading
from socket import socket, AF_INET, SOCK_STREAM


def main():
    http_proxy = HttpProxy(12345, 4096)
    http_proxy.run()


class HttpProxy:
    def __init__(self, port: int, buffer_size: int):
        self.port: int = port
        self.buffer_size: int = buffer_size

    def run(self):
        # Create socket, bind it and listen for incoming connections
        server_socket = socket(AF_INET, SOCK_STREAM)
        server_socket.bind(('localhost', self.port))
        server_socket.listen()
        print(f'Listening on port {self.port}...')

        while True:
            # Handle request
            client_socket, client_address = server_socket.accept()
            print(f'Client connected with address {client_address}')

            handler_thread = threading.Thread(
                target=self._handle_request,
                args=(client_socket, client_address)
            )
            handler_thread.start()

    def _handle_request(self, client_socket, client_address):
        try:
            request_str, host, port, request_method = self._parse_request(client_socket)
            if request_method == 'CONNECT':
                self._send_https_request(client_socket, host, port)
            else:
                self._send_http_request(client_socket, request_str, host, port)
        finally:
            # Close client socket
            print(f'Closing connection with client with address {client_address}')
            client_socket.close()

    def _parse_request(self, client_socket):
        # Receive request
        request = client_socket.recv(self.buffer_size)

        # Decode request to string
        request_str = request.decode()

        # Find host from request
        match = re.search('\r\nHost: (?P<host>[a-zA-Z0-9.]+)(:(?P<port>\\d+))?\r\n', request_str)
        host, port = match.group('host', 'port')
        if not port:
            port = 80
        else:
            port = int(port)

        # Check if request method is CONNECT
        request_method = request_str.split()[0]

        return request_str, host, port, request_method

    def _send_http_request(self, client_socket, request_str, host, port):
        print(f'Sending request to destination {host}:{port}')

        # Remove scheme and domain from request
        request_str = re.sub('[^/ ]+://[^/ ]+', '', request_str)
        request = request_str.encode()

        # Create destination socket
        destination_socket = socket(AF_INET, SOCK_STREAM)
        destination_socket.connect((host, port))

        try:
            # Send request to destination
            destination_socket.sendall(request)

            # Receive response from destination
            response = destination_socket.recv(self.buffer_size)

            # Send response to client
            client_socket.sendall(response)
        finally:
            # Close destination socket
            destination_socket.close()

    def _send_https_request(self, client_socket, host, port):
        print(f'Connecting to destination {host}:{port}')

        # Create destination socket
        destination_socket = socket(AF_INET, SOCK_STREAM)
        destination_socket.connect((host, port))

        try:
            # Send response to client
            client_socket.sendall('HTTP/1.1 200 Connection established\r\n\r\n'.encode())

            # Create, run and wait for sender and receiver threads
            sender_thread = threading.Thread(
                target=self._relay_traffic,
                args=(client_socket, destination_socket)
            )
            receiver_thread = threading.Thread(
                target=self._relay_traffic,
                args=(destination_socket, client_socket)
            )
            sender_thread.start()
            receiver_thread.start()
            sender_thread.join()
            receiver_thread.join()
        finally:
            print(f'Closing connection to destination {host}:{port}')
            destination_socket.close()

    def _relay_traffic(self, source_socket: socket, dest_socket: socket):
        while True:
            data = source_socket.recv(self.buffer_size)
            if not data:
                break

            dest_socket.sendall(data)


if __name__ == '__main__':
    main()
