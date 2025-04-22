#roymeoded2512@gmail.com 
import time
import socket

SERVER = 'localhost'
PORT = 65432
BUFFER_SIZE = 1024

"""
 This file implements the client-that sends messages to the server,uses sliding window,
 handles acknowledgments(ACK),and ensures retransmissions in case of timeouts.
 """

class SlidingWindowClient:
    def __init__(self, server, port, buffer_size):

        """Initialize the client with the server details,port,and buffer size."""

        self.server = server
        self.port = port
        self.buffer_size = buffer_size
        self.segments = []
        self.acknowledged = []
        self.base = 0
        self.client_socket = None


    def connect_to_server(self):

        """Connect to the server and establishes a TCP connection."""

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.server, self.port))
        print("[Client] Connected to server.")

    def prepare_segments(self, message, max_msg_size):

        """Splits a message into segments based on the server's maximum message size setting.
        Adds a sequence number to each segment."""

        self.segments = []
        sequence_number = 0

        if message.startswith("message:"):
            message = message.replace("message:", "", 1).strip()

        message = f'"{message}"'

        for i in range(0, len(message), max_msg_size):
            segment_data = message[i:i + max_msg_size]
            self.segments.append((sequence_number, segment_data))
            sequence_number += 1

        self.acknowledged = [False] * len(self.segments)
        print(f"[Client] Segments prepared: {self.segments}")

    def send_and_receive(self, window_size, timeout):

        """Send message according to a sliding window and waits for acknowledgments(ACK) from the
        server.Handles retransmission in case of a timeout."""

        total_segments = len(self.segments)

        while self.base < total_segments:
            self.send_window(window_size)
            self.wait_for_ack(timeout)

            if all(self.acknowledged):
                print("[Client] All segments acknowledged. Stopping transmission.")
                break

    def send_window(self, window_size):

        """Send all segments in the current window.
        Ensures retransmission if the timeout period has expired."""

        if not hasattr(self, 'sent_segments'):
            self.sent_segments = []
        if not hasattr(self, 'last_sent'):
            self.last_sent = {}

        window_end = min(self.base + window_size, len(self.segments))
        current_time = time.time()

        for i in range(self.base, window_end):
            if not self.acknowledged[i]:
                if i not in self.sent_segments or (current_time - self.last_sent.get(i, 0) >= self.timeout):
                    seq_num, segment_data = self.segments[i]
                    message = f"M{seq_num}:{segment_data}\n"
                    print(f"[Client] Sending segment: {message.strip()}")
                    self.client_socket.send(message.encode())
                    if i not in self.sent_segments:
                        self.sent_segments.append(i)
                    self.last_sent[i] = current_time

    def wait_for_ack(self, timeout):

        """Wait for acknowledgments(ACK) from the server and updates the status of the message window."""

        self.client_socket.settimeout(timeout)
        try:
            ack_data = self.client_socket.recv(self.buffer_size).decode()
            acks = ack_data.split('\n')

            for ack in acks:
                if ack.strip() and ack.startswith("ACK") and ack[3:].isdigit():
                    print(f"[Client] ACK received: {ack.strip()}")
                    self.handle_ack(ack.strip())
        except socket.timeout:
            print("[Client] Timeout occurred. Resending unacknowledged segments.")
            self.send_window(window_size)

    def handle_ack(self, ack):

        """Handle a single received acknowledgment(ACK) and updates  which messages have been confirmed."""

        try:
            seq_num = int(ack.replace("ACK", "").strip())
            if 0 <= seq_num < len(self.segments):
                if not self.acknowledged[seq_num]:
                    self.acknowledged[seq_num] = True
                    print(f"[Client] The segment ACK{seq_num} confirm.")
                    if seq_num in self.sent_segments:
                        self.sent_segments.remove(seq_num)
                    if seq_num == self.base:
                        print(f"[Client] Sliding window forward. Base now at {self.base + 1}.")
                        self.base += 1
                        self.send_window(self.window_size)
            else:
                print(f"[Client] {ack} out of range.")
        except ValueError:
            print(f"[Client] Invalid ACK received: {ack}")

    def start(self, input_type, message, max_msg_size, window_size, timeout):

        """Starts the communication process with the server,including segment preparation,
        sliding window transmission, and acknowledgment handling."""

        self.connect_to_server()

        # Initialize attributes
        self.sent_segments = []  # Tracks sent segments
        self.last_sent = {}  # Tracks the last time each segment was sent
        self.timeout = timeout
        self.window_size = window_size

        # Send input type to server
        self.client_socket.send(input_type.encode())

        if input_type == "file":
            file_path = input("[Client] Enter the file path: ").strip()
            try:
                with open(file_path, 'r') as file:
                    lines = file.readlines()
                    window_size = int(lines[2].split("window_size:", 1)[1].strip())
                    timeout = int(lines[3].split("timeout:", 1)[1].strip())
                    print(f"[Client] Window size: {window_size}, Timeout: {timeout}")
            except (IndexError, ValueError, FileNotFoundError) as e:
                print(f"[Client] Error reading file: {e}")
                return

        else:
            # Receive the maximum message size from the server
            server_msg_size = int(self.client_socket.recv(self.buffer_size).decode())
            max_msg_size = server_msg_size
            print(f"[Client] Server maximum message size: {max_msg_size}")

            # Ask for window size and timeout after receiving the max message size

            window_size = int(input("Enter the window size: ").strip())

            timeout = int(input("Enter the timeout: ").strip())

            self.window_size=window_size
            self.timeout=timeout

        self.prepare_segments(message, max_msg_size)
        self.send_and_receive(window_size, timeout)

        self.client_socket.close()
        print("[Client] Connection to server closed.")


def read_input():

    """Read input from a file or manual user input."""

    choice = input("Enter 'file' to read from a file or 'input' for manual input: ").strip().lower()
    if choice == 'file':
        file_path = input("Enter the file path: ").strip()
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
                message = lines[0].split("message:", 1)[1].strip().strip('"')
                max_msg_size = int(lines[1].split("maximum_msg_size:", 1)[1].strip())
                window_size = int(lines[2].split("window_size:", 1)[1].strip())
                timeout = int(lines[3].split("timeout:", 1)[1].strip())
                return "file", message, max_msg_size, window_size, timeout
        except (IndexError, ValueError, FileNotFoundError) as e:
            print(f"[Client] Error reading file: {e}")
            return read_input()  # Retry in case of an error


    elif choice == 'input':
        message = input("Enter the message: ").strip()

        return "input", message, None, None, None

    else:
        print("[Client] Invalid choice. Please enter 'file' or 'input'.")
        return read_input()


if __name__ == "__main__":
    input_type, message, max_msg_size, window_size, timeout = read_input()

    client = SlidingWindowClient(SERVER, PORT, BUFFER_SIZE)
    client.start(input_type, message, max_msg_size, window_size, timeout)
