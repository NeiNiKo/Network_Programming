import socket
import struct
import json
from pathlib import Path

HOST = "127.0.0.1"
PORT = 9000
BUFFER_SIZE = 4096
MAX_FILE_SIZE = 10 * 1024 * 1024
CMD_UPLOAD = 1
CMD_DOWNLOAD = 2
CMD_LIST = 3
SAVE_DIR = Path(__file__).resolve().parent / "received_files"

def recv_exact(connection, size):
    data = bytearray()
    while len(data) < size:
        chunk = connection.recv(size - len(data))
        if not chunk:
            raise ConnectionError("Connection closed during transfer")
        data.extend(chunk)
    return bytes(data)

def send_response(connection, status, data):
    header = struct.pack("!BQ", status, len(data))
    connection.sendall(header)
    connection.sendall(data)

def validate_filename(filename):
    if not filename or filename in (".", "..") or any(char in filename for char in ("/", "\\", ":", "\x00")):
        raise ValueError("Invalid filename")

def get_unique_path(filename):
    path = SAVE_DIR / filename
    counter = 1
    while path.exists():
        original = Path(filename)
        path = SAVE_DIR / f"{original.stem}_{counter}{original.suffix}"
        counter += 1
    return path

def receive_file(connection):
    header = recv_exact(connection, 12)
    name_length, file_size = struct.unpack("!IQ", header)
    if not 1 <= name_length <= 255:
        raise ValueError("Invalid name length")
    if file_size > MAX_FILE_SIZE:
        raise ValueError("File too large")
    filename = recv_exact(connection, name_length).decode("utf-8")
    validate_filename(filename)
    file_path = get_unique_path(filename)
    remaining = file_size
    created = False
    try:
        with open(file_path, "xb") as file:
            created = True
            while remaining > 0:
                chunk = connection.recv(min(BUFFER_SIZE, remaining))
                if not chunk:
                    raise ConnectionError("File transfer interrupted")
                file.write(chunk)
                remaining -= len(chunk)
    except Exception:
        if created:
            file_path.unlink(missing_ok=True)
        raise
    print(f"Received: {file_path.name} ({file_size} bytes)")
    send_response(connection, 1, f"File saved as {file_path.name}".encode("utf-8"))
    return file_path, file_size

def list_files(connection):
    files = []
    for path in sorted(SAVE_DIR.iterdir()):
        if path.is_file() and not path.is_symlink():
            files.append({"name": path.name, "size": path.stat().st_size})
    data = json.dumps(files, ensure_ascii=False).encode("utf-8")
    send_response(connection, 1, data)
    print(f"File list sent ({len(files)} files)")

def send_files(connection):
    name_length = struct.unpack("!I", recv_exact(connection, 4))[0]
    if not 1 <= name_length <= 255:
        raise ValueError("Invalid filename length")
    filename = recv_exact(connection, name_length).decode("utf-8")
    validate_filename(filename)
    file_path = SAVE_DIR / filename
    if not file_path.is_file() or file_path.is_symlink():
        raise FileNotFoundError(f"File {file_path.name} not found")
    file_size = file_path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        raise ValueError("File too large")
    connection.sendall(struct.pack("!BQ", 1, file_size))
    with open(file_path, "rb") as file:
        while True:
            chunk = file.read(BUFFER_SIZE)
            if not chunk:
                break
            connection.sendall(chunk)
    print(f"File {filename} sent ({file_size} bytes)")

def handle_client(connection, address):
    print(f"Client connected {address}")
    try:
        command = recv_exact(connection, 1)[0]
        if command == CMD_UPLOAD:
            receive_file(connection)
        elif command == CMD_DOWNLOAD:
            send_files(connection)
        elif command == CMD_LIST:
            list_files(connection)
        else:
            raise ValueError(f"Invalid command")
    except (OSError, ValueError, UnicodeError, struct.error) as error:
        print(f"client error: {error}")
        try:
            send_response(connection, 0, str(error).encode("utf-8"))
        except OSError:
            pass

def main():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print(f"TCP server listening on {HOST}:{PORT}")
        while True:
            connection, address = server.accept()
            with connection:
                connection.settimeout(30)
                handle_client(connection, address)

if __name__ == "__main__":
    main()



