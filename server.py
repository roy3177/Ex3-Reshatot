import socket
import time
MAX_MSG_SIZE = 10000
PORT = 65432
BUFFER_SIZE = 1024

"""
 This file implements the server-that listens to the client, handle incoming messages,
 stores them, and sends acknowledgments(ACK) back to the client.
 """

class SlidingWindowServer:
    def __init__(self, port, buffer_size, max_msg_size):

        """Initialize the server with the given parameters: port number, buffer size, and maximum message size."""

        self.port = port
        self.buffer_size = buffer_size
        self.max_msg_size = max_msg_size
        self.received_messages = {}
        self.next_expected = 0
        self.delay=0

    def start_server(self):

        """Start the server and listen for a client, handles steps like reading the maximum message size
        from the keyboard or a file, and sending this value to the client."""

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('localhost', self.port))
        server_socket.listen(1)
        print("[Server] Waiting for connection...")

        conn, addr = server_socket.accept()
        print(f"[Server] Connected to {addr}")

        # Receive input type from client
        input_type = conn.recv(self.buffer_size).decode()

        if input_type == "file":
            file_path = input("[Server] Enter the file path: ").strip()
            try:
                with open(file_path, 'r') as file:
                    lines = file.readlines()
                    max_msg_size = int(lines[1].split("maximum_msg_size:", 1)[1].strip())
                    self.max_msg_size = max_msg_size
                    print(f"[Server] Maximum message size from file: {self.max_msg_size}")
            except (IndexError, ValueError, FileNotFoundError) as e:
                print(f"[Server] Error reading file: {e}")
                self.max_msg_size = MAX_MSG_SIZE  #


        elif input_type == "input":
            # Request maximum message size from user
            user_defined = input("[Server] Enter maximum message size (default is 1024): ").strip()
            if user_defined.isdigit():
                self.max_msg_size = int(user_defined)
            else:
                self.max_msg_size = MAX_MSG_SIZE  # Default value if invalid
            print(f"[Server] Maximum message size from user input: {self.max_msg_size}")



        # Ask about edge cases
        while True:
            print("[Server] Do you want to simulate edge cases? (yes/no)")
            choice = input().strip().lower()
            if choice in ["yes", "no"]:
                break
            print("[Server] Invalid choice. Please enter 'yes' or 'no'.")

        if choice == "yes":
            delay_value= (int(input("[Server] Enter delay in seconds for each ACK: ").strip()))
            time.sleep(delay_value)
            self.delay=delay_value
        else:
            time.sleep(self.delay)
            print("[Server] Running without delays.")

         # Send the maximum message size back to the client
        conn.send(str(self.max_msg_size).encode())
        print(f"[Server] Sent maximum message size to client.")

        try:
            self.handle_client(conn)
        except Exception as e:
            print(f"[Server] Error: {e}")
        finally:
            conn.close()
            print("[Server] Connection closed.")

    def handle_client(self, conn):

        """Manages communication with the client,reads incoming messages,pares sequence numbers,and sends
        acknowledgments(ACK) to the client."""

        while True:
            try:
                # Receive data from the client
                data = conn.recv(self.buffer_size).decode()
                if not data:
                    break

                # Split received data into individual messages
                messages = [msg.strip() for msg in data.split('\n') if msg.strip()]
                for message in messages:
                    print(f"[Server] Raw data received: {message}")
                    seq_num = self.parse_sequence_number(message)

                    if seq_num is not None:
                        self.store_message(seq_num, message)  # Store the segment
                        self.manage_sliding_window(conn)  # Manage sliding window
                    else:
                        print("[Server] Invalid message format, skipping...")
            except Exception as e:
                print(f"[Server] Error in client handling: {e}")
                break

    def parse_sequence_number(self, data):

        """Extracts the sequence number from an incoming message,if the format is invalid-ignores the message"""

        try:
            if not data.startswith("M") or ':' not in data:
                raise ValueError(f"Invalid message format: {data}")
            seq_num = int(data.split(':')[0][1:])
            return seq_num
        except (ValueError, IndexError):
            print(f"[Server] Error parsing sequence number: {data}")
            return None

    def store_message(self, seq_num, data):

        """Store the message if it hasn't been received already,messages are stored based on their sequence number."""

        if seq_num not in self.received_messages:
            try:
                content = data.split(":", 1)[1].strip()
                self.received_messages[seq_num] = content
                print(f"[Server] Stored message {seq_num}. Current messages: {sorted(self.received_messages.keys())}")
            except IndexError:
                print(f"[Server] Failed to store message {seq_num}: {data}")

    def update_next_expected(self):

        """Update the next expected sequence number the server expects,based on messages already received."""

        while self.next_expected in self.received_messages:
            self.next_expected += 1
        return self.next_expected

    def manage_sliding_window(self, conn):

        """Sends an acknowledgment(ACK) to the client for the last message received in order.
        Slides the message window forward if additional messages are received."""

        if self.next_expected in self.received_messages:
            print(f"[Server] Expected segment {self.next_expected} received. Sliding window forward.")
            self.next_expected = self.update_next_expected()
        self.send_ack(conn, self.next_expected - 1)

    def send_ack(self, conn, seq_num):

        """Send an acknowledgment(ACK) to the client with the highest sequence number recieved in order."""

        ack = f"ACK{seq_num}\n"
        time.sleep(self.delay)
        try:
            conn.sendall(ack.encode())
            print(f"[Server] Sent ACK for sequence up to {seq_num}")
        except Exception as e:
            print(f"[Server] Failed to sent ACK:{e}")

    def print_all_messages(self):

        """Print the full message only when all segments are received."""

        try:
            if len(self.received_messages) == max(self.received_messages.keys()) + 1:
                full_message = self.received_messages[0]
                for i in range(1, len(self.received_messages)):
                    current_segment = self.received_messages[i]
                    if not full_message.endswith(" ") and not current_segment.startswith(" "):
                        full_message += " "
                    full_message += current_segment
                print(f'[Server] Full message received: {full_message}')
            else:
                print("[Server] Waiting for more segments. Current messages: ", sorted(self.received_messages.keys()))
        except ValueError as e:
            print(f"[Server] Error assembling full message: {e}")

if __name__ == "__main__":
    # Create an instance of SlidingWindowServer and start it
    server = SlidingWindowServer(PORT, BUFFER_SIZE, MAX_MSG_SIZE)
    server.start_server()