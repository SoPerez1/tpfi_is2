"""Unit tests for SingletonClient module."""

import json
import socket
import threading
from typing import Generator
import pytest
from tpfi_is2.singleton_client import SingletonClient


@pytest.fixture
def mock_server() -> Generator[tuple[str, int], None, None]:
    """Start a temporary mock TCP server for testing socket communications."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("localhost", 0))
    host, port = server_socket.getsockname()
    server_socket.listen(1)

    running = True

    def handle_client() -> None:
        server_socket.settimeout(2.0)
        try:
            conn, _ = server_socket.accept()
            with conn:
                data = conn.recv(4096)
                if data:
                    request = json.loads(data.decode("utf-8"))
                    # Echo mock response
                    response = {"status": "OK", "received_action": request.get("ACTION"), "data": request}
                    conn.sendall(json.dumps(response).encode("utf-8"))
        except socket.timeout:
            pass
        finally:
            server_socket.close()

    thread = threading.Thread(target=handle_client, daemon=True)
    thread.start()

    yield host, port

    running = False
    try:
        server_socket.close()
    except OSError:
        pass


def test_process_request_get_action() -> None:
    """Test payload processing for a 'get' action."""
    client = SingletonClient()
    input_data = {"ACTION": "get", "ID": "123"}
    payload = client.process_request(input_data)

    assert payload["ACTION"] == "get"
    assert payload["ID"] == "123"
    assert "UUID" in payload
    assert "SESSION_ID" in payload


def test_process_request_invalid_action() -> None:
    """Test payload processing fails on missing or invalid action."""
    client = SingletonClient()
    with pytest.raises(ValueError, match="Invalid or missing ACTION"):
        client.process_request({"ACTION": "invalid_action"})


def test_send_request_to_mock_server(mock_server: tuple[str, int]) -> None:
    """Test full TCP socket request/response cycle against a mock server."""
    host, port = mock_server
    client = SingletonClient(host=host, port=port, verbose=True)
    payload = {"ACTION": "get", "ID": "UADER-1", "UUID": "test-uuid", "SESSION_ID": "test-session"}

    response = client.send_request(payload)
    assert response["status"] == "OK"
    assert response["received_action"] == "get"
    assert response["data"]["ID"] == "UADER-1"


def test_execute_from_file(tmp_path: pytest.TempPathFactory, mock_server: tuple[str, int]) -> None:
    """Test reading from input JSON file and writing to output JSON file."""
    host, port = mock_server

    input_file = tmp_path.mktemp("test") / "input.json"
    output_file = tmp_path.mktemp("test") / "output.json"

    input_file.write_text(json.dumps({"ACTION": "list"}), encoding="utf-8")

    client = SingletonClient(host=host, port=port)
    res = client.execute(input_path=input_file, output_path=output_file)

    assert res["status"] == "OK"
    assert res["received_action"] == "list"
    assert output_file.exists()

    saved_output = json.loads(output_file.read_text(encoding="utf-8"))
    assert saved_output["status"] == "OK"


def test_send_request_connection_refused() -> None:
    """Test error handling when server is unreachable."""
    client = SingletonClient(host="localhost", port=59999)
    with pytest.raises(ConnectionError, match="Could not connect to server"):
        client.send_request({"ACTION": "get"})
