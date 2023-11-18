import socket
import re
import threading


class HttpProxy:

    def __init__(self, port: int):
        self.port = port

    def run(self):
        # Create socket, bind it and listen for incoming connection
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('localhost', self.port))
        server_socket.listen(1)
        print(f'Listening on port {self.port}...')

        while True:
            # Handle request
            client_socket, client_address = server_socket.accept()
            print(f'Client connected with address {client_address}')

            handler_thread = threading.Thread(
                target=self.handle_request,
                args=(client_socket, client_address)
            )
            handler_thread.start()

    def handle_request(self, client_socket, client_address):
        destination_socket = None
        try:
            # Receive request
            request = client_socket.recv(4096)

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
            if request_method == 'CONNECT':
                print(f'Connecting to destination {host}:{port}')

                # Send request to destination
                destination_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                destination_socket.connect((host, port))

                # Send response to client
                client_socket.sendall('HTTP /1.1 200 Connection established'.encode())

                # Create, run and wait for sender and receiver threads
                sender_thread = threading.Thread(
                    target=self.relay_traffic,
                    args=(client_socket, destination_socket)
                )
                receiver_thread = threading.Thread(
                    target=self.relay_traffic,
                    args=(destination_socket, client_socket)
                )
                sender_thread.start()
                receiver_thread.start()
                sender_thread.join()
                receiver_thread.join()

                print(f'Closing connection to destination {host}:{port}')
            else:
                print(f'Sending request to destination {host}:{port}')

                # Remove scheme and domain from request
                request_str = re.sub('[^/ ]+://[^/ ]+', '', request_str)
                request = request_str.encode()

                # Send request to destination
                destination_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                destination_socket.connect((host, port))
                destination_socket.sendall(request)

                # Receive response from destination
                response = destination_socket.recv(4096)

                # Send response to client
                client_socket.sendall(response)
        finally:
            # Close sockets
            if destination_socket is not None:
                destination_socket.close()
            client_socket.close()

    def relay_traffic(self, source_socket: socket.socket, dest_socket: socket.socket):
        while True:
            data = source_socket.recv(4096)
            if not data:
                break
            print(f'received data {data.decode()}')
            dest_socket.sendall(data)


def main():
    http_proxy = HttpProxy(8888)
    http_proxy.run()


if __name__ == '__main__':
    main()
