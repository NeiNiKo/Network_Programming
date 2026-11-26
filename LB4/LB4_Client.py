import socket
import struct
import json
import os
from pathlib import Path

HOST = "127.0.0.1"
PORT = 9000
BUFFER_SIZE = 4096
MAX_FILE_SIZE = 10 * 1024 * 1024
CMD_UPLOAD = 1
CMD_DOWNLOAD = 2
CMD_LIST = 3

def get_downloads_folder():
    if os.name == "nt":
        import winreg
        try:
            registry_path = r"Software\Microsoft\Windows\CurrentVersion" r"\Explorer\User Shell Folders"
            downloads_id = "{374DE290-123F-4565-9164-39C4925E467B}"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as key: folder, _ = winreg.QueryValueEx(key, downloads_id)
            return Path(os.path.expandvars(folder))
        except OSError:
            pass
    return Path.home() / "Downloads"

def recv_exact(connection, size):
    data = bytearray()
    while len(data) < size:
        chunk = connection.recv(size - len(data))
        if not chunk:
            raise ConnectionError("Connection closed unexpectedly")
        data.extend(chunk)
    return bytes(data)

def receive_response(connection):
    header = recv_exact(connection, 9)
    status, data_size = struct.unpack("!BQ", header)
    if data_size > 1024 * 1024:
        raise ValueError("Server response is too large")
    data = recv_exact(connection, data_size)
    return status, data

def get_unique_path(folder, filename):
    path = folder / filename
    counter = 1
    while path.exists():
        original = Path(filename)
        path = folder / f"{original.stem}_{counter}{original.suffix}"
        counter += 1
    return path

def upload_file():
    file_path = input("Enter file path: ").strip().strip('"')
    path = Path(file_path)
    if not path.is_file():
        print("File not found")
        return
    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        print("File is too large")
        return
    filename = path.name.encode("utf-8")
    if not 1 <= len(filename) <= 255:
        print("Invalid filename length")
        return
    header = struct.pack("!BIQ", CMD_UPLOAD, len(filename), file_size)
    try:
        with socket.create_connection((HOST, PORT), timeout=10) as client:
            client.settimeout(30)
            client.sendall(header)
            client.sendall(filename)
            with open(path, "rb") as file:
                while True:
                    chunk = file.read(BUFFER_SIZE)
                    if not chunk:
                        break
                    client.sendall(chunk)
            status, response = receive_response(client)
            message = response.decode("utf-8")
            if status == 1:
                print(f"Upload successful: {message}")
            else:
                print(f"Upload failed: {message}")
    except (OSError, ValueError, UnicodeError) as error:
        print(f"Upload error: {error}")

def list_server_files():
    try:
        with socket.create_connection((HOST, PORT), timeout=10) as client:
            client.settimeout(30)
            client.sendall(bytes([CMD_LIST]))
            status, response = receive_response(client)
            if status != 1:
                print(f"Server error: {response.decode('utf-8')}")
                return None
            files = json.loads(response.decode("utf-8"))
            print("\n(´｡• ω •｡) SERVER FILES ⊙_⊙")
            if not files:
                print("No files available")
                return []
            for index, file in enumerate(files, start=1):
                print(
                    f"{index}. {file['name']} "
                    f"({file['size']} bytes)"
                )
            return files
    except (OSError, ValueError, UnicodeError) as error:
        print(f"List error: {error}")
        return None

def download_file():
    files = list_server_files()
    if files is None or not files:
        return
    choice = input("\nSelect file number (0 to cancel): ").strip()
    if not choice.isdigit():
        print("Invalid file number")
        return
    index = int(choice)
    if index == 0:
        print("Download cancelled")
        return
    if not 1 <= index <= len(files):
        print("Invalid file number")
        return
    filename = files[index - 1]["name"]
    name_bytes = filename.encode("utf-8")
    if not 1 <= len(name_bytes) <= 255:
        print("Invalid filename length")
        return
    if filename in (".", "..") or any(char in filename for char in ("/", "\\", ":", "\x00")):
        print("Invalid filename")
        return
    request_header = struct.pack("!BI", CMD_DOWNLOAD, len(name_bytes))
    downloads_folder = get_downloads_folder()
    try:
        with socket.create_connection((HOST, PORT), timeout=10) as client:
            client.settimeout(30)
            client.sendall(request_header)
            client.sendall(name_bytes)
            header = recv_exact(client, 9)
            status, data_size = struct.unpack("!BQ", header)
            if status != 1:
                if data_size > 1024 * 1024:
                    raise ValueError("Error response is too large")
                error_message = recv_exact(client, data_size).decode("utf-8")
                print(f"Download failed: {error_message}")
                return
            if data_size > MAX_FILE_SIZE:
                raise ValueError("File is too large")
            downloads_folder.mkdir(parents=True, exist_ok=True)
            save_path = get_unique_path(downloads_folder, filename)
            remaining = data_size
            created = False
            try:
                with open(save_path, "xb") as file:
                    created = True
                    while remaining > 0:
                        chunk = client.recv(min(BUFFER_SIZE, remaining))
                        if not chunk:
                            raise ConnectionError("Download interrupted")
                        file.write(chunk)
                        remaining -= len(chunk)
            except Exception:
                if created:
                    save_path.unlink(missing_ok=True)
                raise
            print("Download successful")
            print(f"Saved to: {save_path}")
    except (OSError, ValueError, UnicodeError) as error:
        print(f"Download error: {error}")

def main():
    while True:
        print("\n(☞ﾟヮﾟ)☞ TCP FILE CLIENT (=^ェ^=)")
        print("1. Upload file to server")
        print("2. Download file from server")
        print("3. List server files")
        print("0. Exit")
        choice = input("Select option: ").strip()
        if choice == "1":
            upload_file()
        elif choice == "2":
            download_file()
        elif choice == "3":
            list_server_files()
        elif choice == "0":
            print("Exiting client...")
            break
        else:
            print("Invalid option")

if __name__ == "__main__":
    main()