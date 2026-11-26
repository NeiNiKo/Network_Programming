import pytest
import LB4_Server
from unittest.mock import Mock, MagicMock
import struct
import json

def test_validate_filename_valid():
    LB4_Server.validate_filename("example.txt")

def test_validate_filename_invalid():
    with pytest.raises(ValueError):
        LB4_Server.validate_filename("../secret.txt")

@pytest.mark.parametrize("filename",["",".","..","../secret.txt","folder/file.txt",r"folder\file.txt","file:name.txt","file\x00name.txt"])
def test_validate_filename_invalid_cases(filename):
    with pytest.raises(ValueError):
        LB4_Server.validate_filename(filename)

def test_get_unique_path_new_file(tmp_path, monkeypatch):
    monkeypatch.setattr(LB4_Server, "SAVE_DIR", tmp_path)
    result = LB4_Server.get_unique_path("example.txt")
    assert result == tmp_path / "example.txt"

def test_get_unique_path_existing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(LB4_Server, "SAVE_DIR", tmp_path)
    (tmp_path / "example.txt").write_text("Test data")
    result = LB4_Server.get_unique_path("example.txt")
    assert result == tmp_path / "example_1.txt"

def test_get_unique_path_multiple_duplicates(tmp_path, monkeypatch):
    monkeypatch.setattr(LB4_Server, "SAVE_DIR", tmp_path)
    (tmp_path / "example.txt").touch()
    (tmp_path / "example_1.txt").touch()
    (tmp_path / "example_2.txt").touch()
    result = LB4_Server.get_unique_path("example.txt")
    assert result == tmp_path / "example_3.txt"

def test_recv_exact_success():
    connection = Mock()
    connection.recv.return_value = b"Hello"
    result = LB4_Server.recv_exact(connection, 5)
    assert result == b"Hello"
    connection.recv.assert_called_once_with(5)

def test_recv_exact_multiple_chunks():
    connection = Mock()
    connection.recv.side_effect = [b"He", b"llo"]
    result = LB4_Server.recv_exact(connection, 5)
    assert result == b"Hello"
    assert connection.recv.call_count == 2

def test_recv_exact_connection_closed():
    connection = Mock()
    connection.recv.return_value = b""
    with pytest.raises(ConnectionError):
        LB4_Server.recv_exact(connection, 5)

def test_send_response_success():
    connection = Mock()
    data = b"OK"
    LB4_Server.send_response(connection, 1, data)
    expected_header = struct.pack("!BQ", 1, 2)
    assert connection.sendall.call_count == 2
    connection.sendall.assert_any_call(expected_header)
    connection.sendall.assert_any_call(b"OK")

def test_send_response_error():
    connection = Mock()
    data = b"File not found"
    LB4_Server.send_response(connection, 0, data)
    expected_header = struct.pack("!BQ", 0, len(data))
    assert connection.sendall.call_count == 2
    connection.sendall.assert_any_call(expected_header)
    connection.sendall.assert_any_call(data)

def test_send_response_empty_data():
    connection = Mock()
    LB4_Server.send_response(connection, 1, b"")
    expected_header = struct.pack("!BQ", 1, 0)
    assert connection.sendall.call_count == 2
    connection.sendall.assert_any_call(expected_header)
    connection.sendall.assert_any_call(b"")

def test_list_files_with_files(tmp_path, monkeypatch):
    monkeypatch.setattr(LB4_Server, "SAVE_DIR", tmp_path)
    (tmp_path / "example.txt").write_text("Hello", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("Python", encoding="utf-8")
    connection = Mock()
    LB4_Server.list_files(connection)
    assert connection.sendall.call_count == 2
    header = connection.sendall.call_args_list[0].args[0]
    data = connection.sendall.call_args_list[1].args[0]
    status, data_size = struct.unpack("!BQ", header)
    assert status == 1
    assert data_size == len(data)
    files = json.loads(data.decode("utf-8"))
    assert files == [
        {"name": "example.txt", "size": 5},
        {"name": "notes.txt", "size": 6}
    ]

def test_list_files_empty_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(LB4_Server, "SAVE_DIR", tmp_path)
    connection = Mock()
    LB4_Server.list_files(connection)
    header = connection.sendall.call_args_list[0].args[0]
    data = connection.sendall.call_args_list[1].args[0]
    status, data_size = struct.unpack("!BQ", header)
    assert status == 1
    assert data_size == 2
    assert json.loads(data.decode("utf-8")) == []

def test_receive_file_success(tmp_path, monkeypatch):
    monkeypatch.setattr(LB4_Server, "SAVE_DIR", tmp_path)
    filename = "example.txt"
    content = b"Hello TCP"
    header = struct.pack("!IQ", len(filename), len(content))
    connection = Mock()
    connection.recv.side_effect = [header, filename.encode("utf-8"), content]
    file_path, file_size = LB4_Server.receive_file(connection)
    assert file_path == tmp_path / filename
    assert file_size == len(content)
    assert file_path.read_bytes() == content
    response_header = connection.sendall.call_args_list[0].args[0]
    status, _ = struct.unpack("!BQ", response_header)
    assert status == 1

def test_receive_file_interrupted(tmp_path, monkeypatch):
    monkeypatch.setattr(LB4_Server, "SAVE_DIR", tmp_path)
    filename = "example.txt"
    header = struct.pack("!IQ", len(filename), 10)
    connection = Mock()
    connection.recv.side_effect = [header, filename.encode("utf-8"), b"Hello", b""]
    with pytest.raises(ConnectionError):
        LB4_Server.receive_file(connection)
    assert not (tmp_path / filename).exists()

def test_send_files_success(tmp_path, monkeypatch):
    monkeypatch.setattr(LB4_Server, "SAVE_DIR", tmp_path)
    filename = "example.txt"
    content = b"Hello TCP"
    (tmp_path / filename).write_bytes(content)
    name_bytes = filename.encode("utf-8")
    name_header = struct.pack("!I", len(name_bytes))
    connection = Mock()
    connection.recv.side_effect = [name_header, name_bytes]
    LB4_Server.send_files(connection)
    expected_header = struct.pack("!BQ", 1, len(content))
    assert connection.sendall.call_count == 2
    assert connection.sendall.call_args_list[0].args[0] == expected_header
    assert connection.sendall.call_args_list[1].args[0] == content

def test_send_files_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(LB4_Server, "SAVE_DIR", tmp_path)
    filename = "missing.txt"
    name_bytes = filename.encode("utf-8")
    connection = Mock()
    connection.recv.side_effect = [struct.pack("!I", len(name_bytes)), name_bytes]
    with pytest.raises(FileNotFoundError):
        LB4_Server.send_files(connection)
    connection.sendall.assert_not_called()

def test_send_files_too_large(tmp_path, monkeypatch):
    monkeypatch.setattr(LB4_Server, "SAVE_DIR", tmp_path)
    monkeypatch.setattr(LB4_Server, "MAX_FILE_SIZE", 5)
    filename = "large.txt"
    (tmp_path / filename).write_bytes(b"1234567890")
    name_bytes = filename.encode("utf-8")
    connection = Mock()
    connection.recv.side_effect = [struct.pack("!I", len(name_bytes)), name_bytes]
    with pytest.raises(ValueError, match="File too large"):
        LB4_Server.send_files(connection)
    connection.sendall.assert_not_called()

@pytest.mark.parametrize(
    "command, handler_name",[(LB4_Server.CMD_UPLOAD, "receive_file"), (LB4_Server.CMD_DOWNLOAD, "send_files"), (LB4_Server.CMD_LIST, "list_files")])
def test_handle_client_valid_commands(
    monkeypatch, command, handler_name):
    connection = Mock()
    connection.recv.return_value = bytes([command])
    handler = Mock()
    monkeypatch.setattr(LB4_Server, handler_name, handler)
    LB4_Server.handle_client(connection, ("127.0.0.1", 50000))
    handler.assert_called_once_with(connection)

def test_handle_client_invalid_command():
    connection = Mock()
    connection.recv.return_value = b"\xFF"
    LB4_Server.handle_client(connection, ("127.0.0.1", 50000))
    assert connection.sendall.call_count == 2
    header = connection.sendall.call_args_list[0].args[0]
    data = connection.sendall.call_args_list[1].args[0]
    status, data_size = struct.unpack("!BQ", header)
    assert status == 0
    assert data_size == len(data)
    assert b"Invalid command" in data

def test_handle_client_handler_error(monkeypatch):
    connection = Mock()
    connection.recv.return_value = bytes([LB4_Server.CMD_LIST])
    handler = Mock(side_effect=ValueError("Test error"))
    monkeypatch.setattr(LB4_Server, "list_files", handler)
    LB4_Server.handle_client(connection, ("127.0.0.1", 50000))
    handler.assert_called_once_with(connection)
    header = connection.sendall.call_args_list[0].args[0]
    data = connection.sendall.call_args_list[1].args[0]
    status, data_size = struct.unpack("!BQ", header)
    assert status == 0
    assert data_size == len(data)
    assert data == b"Test error"

def test_receive_file_invalid_name_length():
    connection = Mock()
    connection.recv.return_value = struct.pack("!IQ", 0, 10)
    with pytest.raises(ValueError, match="Invalid name length"):
        LB4_Server.receive_file(connection)
    connection.sendall.assert_not_called()

def test_receive_file_too_large():
    connection = Mock()
    oversized = LB4_Server.MAX_FILE_SIZE + 1
    connection.recv.return_value = struct.pack("!IQ", 8, oversized)
    with pytest.raises(ValueError, match="File too large"):
        LB4_Server.receive_file(connection)
    connection.sendall.assert_not_called()

def test_send_files_invalid_name_length():
    connection = Mock()
    connection.recv.return_value = struct.pack("!I", 0)
    with pytest.raises(ValueError, match="Invalid filename length"):
        LB4_Server.send_files(connection)
    connection.sendall.assert_not_called()

def test_handle_client_response_connection_error():
    connection = Mock()
    connection.recv.return_value = b"\xFF"
    connection.sendall.side_effect = OSError("Connection closed")
    LB4_Server.handle_client(connection, ("127.0.0.1", 50000))
    assert connection.sendall.call_count == 1

def test_main_server_initialization(tmp_path, monkeypatch):
    monkeypatch.setattr(LB4_Server, "SAVE_DIR", tmp_path)
    server = MagicMock()
    server.__enter__.return_value = server
    server.accept.side_effect = KeyboardInterrupt()
    socket_mock = Mock(return_value=server)
    monkeypatch.setattr(LB4_Server.socket, "socket", socket_mock)
    with pytest.raises(KeyboardInterrupt):
        LB4_Server.main()
    assert tmp_path.is_dir()
    socket_mock.assert_called_once_with(LB4_Server.socket.AF_INET, LB4_Server.socket.SOCK_STREAM)
    server.bind.assert_called_once_with((LB4_Server.HOST, LB4_Server.PORT))
    server.listen.assert_called_once()
    server.accept.assert_called_once()

def test_main_client_connection(tmp_path, monkeypatch):
    monkeypatch.setattr(LB4_Server, "SAVE_DIR", tmp_path)
    connection = MagicMock()
    connection.__enter__.return_value = connection
    address = ("127.0.0.1", 50000)
    server = MagicMock()
    server.__enter__.return_value = server
    server.accept.side_effect = [(connection, address), KeyboardInterrupt()]
    socket_mock = Mock(return_value=server)
    monkeypatch.setattr(LB4_Server.socket, "socket", socket_mock)
    handler_mock = Mock()
    monkeypatch.setattr(LB4_Server, "handle_client", handler_mock)
    with pytest.raises(KeyboardInterrupt):
        LB4_Server.main()
    connection.settimeout.assert_called_once_with(30)
    handler_mock.assert_called_once_with(connection, address)
    assert server.accept.call_count == 2

def test_main_bind_error(tmp_path, monkeypatch):
    monkeypatch.setattr(LB4_Server, "SAVE_DIR", tmp_path)
    server = MagicMock()
    server.__enter__.return_value = server
    server.bind.side_effect = OSError("Address already in use")
    socket_mock = Mock(return_value=server)
    monkeypatch.setattr(LB4_Server.socket, "socket", socket_mock)
    with pytest.raises(OSError, match="Address already in use"):
        LB4_Server.main()
    server.listen.assert_not_called()
    server.accept.assert_not_called()
    server.__exit__.assert_called_once()