"""Unit tests for the SingletonClient module."""

import json
import socket
import sys
import threading
import time
import uuid
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from tpfi_is2.singleton_client import SingletonClient, main


@pytest.fixture
def server() -> Generator[tuple[str, int], None, None]:
    """Mock server that answers {"status": "OK", "received": <request>}."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(5)

    def serve() -> None:
        while True:
            try:
                conn, _ = srv.accept()
            except OSError:
                return  # socket closed by the fixture
            with conn:
                data = b""
                while chunk := conn.recv(4096):
                    data += chunk
                reply = {"status": "OK", "received": json.loads(data)}
                conn.sendall(json.dumps(reply).encode("utf-8"))

    threading.Thread(target=serve, daemon=True).start()
    host, port = srv.getsockname()
    yield host, port
    srv.close()


@pytest.fixture
def closed_port() -> int:
    """Return a local port where nobody is listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def run_main(monkeypatch: pytest.MonkeyPatch, *args: str) -> None:
    """Call main() with the given command line arguments."""
    monkeypatch.setattr(sys, "argv", ["singletonclient.py", *args])
    main()


def make_input(tmp_path: Path, data: Any) -> Path:
    """Write data as JSON in tmp_path/input.json."""
    path = tmp_path / "input.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_build_request_adds_uuid_and_session() -> None:
    request = SingletonClient().build_request({"ACTION": "get", "ID": "1"})
    assert request["UUID"] == str(uuid.getnode())
    assert uuid.UUID(request["SESSION_ID"]).version == 4


def test_build_request_list_discards_id() -> None:
    request = SingletonClient().build_request({"ACTION": "list", "ID": "1"})
    assert "ID" not in request


@pytest.mark.parametrize("data", [{}, {"ACTION": "delete"}, [1, 2]])
def test_build_request_invalid(data: Any) -> None:
    with pytest.raises(ValueError):
        SingletonClient().build_request(data)


@pytest.mark.parametrize("action", ["get", "set"])
def test_build_request_requires_id(action: str) -> None:
    with pytest.raises(ValueError, match="requires an ID"):
        SingletonClient().build_request({"ACTION": action})


def test_build_request_set_requires_corporate_field() -> None:
    with pytest.raises(ValueError, match="CorporateData field"):
        SingletonClient().build_request({"ACTION": "set", "ID": "1"})


def test_build_request_set_keeps_corporate_fields() -> None:
    request = SingletonClient().build_request({"ACTION": "set", "ID": "1", "sede": "FCyT"})
    assert request["sede"] == "FCyT"


def test_send_happy_path(server: tuple[str, int]) -> None:
    request = {"ACTION": "get", "ID": "UADER"}
    answer = SingletonClient(*server).send(request)
    assert answer == {"status": "OK", "received": request}


def test_send_server_down(closed_port: int) -> None:
    with pytest.raises(ConnectionError, match="Could not connect"):
        SingletonClient("127.0.0.1", closed_port).send({"ACTION": "list"})


def test_send_empty_response() -> None:
    host = "127.0.0.1"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.bind((host, 0))
        port = int(srv.getsockname()[1])
        srv.listen(1)

        def serve_empty() -> None:
            conn, _ = srv.accept()
            with conn:
                assert conn.recv(4096)
                conn.shutdown(socket.SHUT_WR)

        threading.Thread(target=serve_empty, daemon=True).start()
        time.sleep(0.05)
        with pytest.raises(ValueError, match="Empty response"):
            SingletonClient(host, port).send({"ACTION": "list"})


def test_send_invalid_json_response(closed_port: int) -> None:
    host = "127.0.0.1"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.bind((host, 0))
        port = int(srv.getsockname()[1])
        srv.listen(1)

        def respond_garbage() -> None:
            conn, _ = srv.accept()
            with conn:
                conn.recv(4096)
                conn.sendall(b"not-json")
            srv.close()

        threading.Thread(target=respond_garbage, daemon=True).start()
        time.sleep(0.05)
        with pytest.raises(ValueError, match="Invalid JSON"):
            SingletonClient(host, port).send({"ACTION": "list"})


def test_main_writes_output_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, server: tuple[str, int]) -> None:
    out = tmp_path / "out.json"
    inp = make_input(tmp_path, {"ACTION": "get", "ID": "1"})
    run_main(
        monkeypatch,
        "-i",
        str(inp),
        "-o",
        str(out),
        "-s",
        server[0],
        "-p",
        str(server[1]),
    )
    assert json.loads(out.read_text(encoding="utf-8"))["status"] == "OK"


def test_main_prints_to_stdout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    server: tuple[str, int],
    capsys: pytest.CaptureFixture[str],
) -> None:
    inp = make_input(tmp_path, {"ACTION": "list"})
    run_main(monkeypatch, f"-i={inp}", "-s", server[0], f"-p={server[1]}")
    assert json.loads(capsys.readouterr().out)["status"] == "OK"


def test_main_verbose(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    server: tuple[str, int],
    capsys: pytest.CaptureFixture[str],
) -> None:
    inp = make_input(tmp_path, {"ACTION": "list"})
    run_main(monkeypatch, "-v", "-i", str(inp), "-s", server[0], "-p", str(server[1]))
    assert "Sending to" in capsys.readouterr().out


def test_main_server_down(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, closed_port: int) -> None:
    inp = make_input(tmp_path, {"ACTION": "list"})
    with pytest.raises(SystemExit, match="Could not connect"):
        run_main(monkeypatch, "-i", str(inp), "-s", "127.0.0.1", "-p", str(closed_port))


def test_main_missing_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    inp = make_input(tmp_path, {"ACTION": "get"})
    with pytest.raises(SystemExit, match="requires an ID"):
        run_main(monkeypatch, "-i", str(inp))


def test_main_missing_input_file(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SystemExit, match="Error"):
        run_main(monkeypatch, "-i", "does_not_exist.json")


@pytest.mark.parametrize("args", [[], ["-o", "x.json"], ["-i", "x.json", "-p", "abc"]])
def test_main_malformed_arguments(monkeypatch: pytest.MonkeyPatch, args: list[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        run_main(monkeypatch, *args)
    assert excinfo.value.code == 2
