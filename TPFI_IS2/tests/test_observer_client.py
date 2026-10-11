"""Unit tests for ObserverClient module."""

from __future__ import annotations

import json
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from tpfi_is2.observer_client import ObserverClient, main, parse_args


def test_build_subscribe_request() -> None:
    """Test subscribe request structure and required fields."""
    client = ObserverClient()
    req = client.build_subscribe_request()

    assert req["ACTION"] == "subscribe"
    assert "UUID" in req
    assert "SESSION_ID" in req
    assert len(req["UUID"]) > 0
    assert len(req["SESSION_ID"]) > 0


def test_parse_args_defaults() -> None:
    """Test CLI argument defaults."""
    args = parse_args([])
    assert args.hostname == "localhost"
    assert args.port == 8080
    assert args.output is None
    assert args.verbose is False
    assert args.reconnect_delay == 30.0


def test_parse_args_custom() -> None:
    """Test CLI arguments with custom values."""
    cli_args = [
        "-s",
        "remote-host",
        "-p",
        "9090",
        "-o",
        "result.json",
        "-v",
        "--reconnect-delay",
        "15.5",
    ]
    args = parse_args(cli_args)
    assert args.hostname == "remote-host"
    assert args.port == 9090
    assert args.output == "result.json"
    assert args.verbose is True
    assert args.reconnect_delay == 15.5


@pytest.mark.parametrize("invalid_port", ["-1", "0", "70000", "abc"])
def test_parse_args_invalid_port(invalid_port: str) -> None:
    """Test argument validation with malformed or out-of-range port numbers."""
    with pytest.raises(SystemExit):
        parse_args(["-p", invalid_port])


def test_write_output(tmp_path: Path) -> None:
    """Test writing notifications to specified output file."""
    output_file = tmp_path / "subfolder" / "output.json"
    client = ObserverClient(output_file=output_file)

    test_payload = json.dumps({"test": "data"}, indent=2)
    client.write_output(test_payload)

    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8").strip()
    assert content == test_payload


def test_handle_incoming_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test processing incoming message writes to output file and stdout."""
    output_file = tmp_path / "out.json"
    client = ObserverClient(output_file=output_file)

    msg = {"id": "UADER-1", "sede": "FCyT"}
    client.handle_incoming_message(msg)

    captured = capsys.readouterr()
    assert "UADER-1" in captured.out
    assert "FCyT" in captured.out
    assert output_file.exists()
    assert "UADER-1" in output_file.read_text(encoding="utf-8")


def test_run_connection_happy_path(tmp_path: Path) -> None:
    """Test connecting, subscribing, and receiving notification from a mock TCP server."""
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(("127.0.0.1", 0))
    host, port = server_sock.getsockname()
    server_sock.listen(1)

    received_from_client: list[dict[str, Any]] = []

    def server_thread() -> None:
        conn, _ = server_sock.accept()
        with conn:
            buffer = ""
            while "\n" not in buffer:
                chunk = conn.recv(1024)
                if not chunk:
                    break
                buffer += chunk.decode("utf-8")
            line, _ = buffer.split("\n", 1)
            received_from_client.append(json.loads(line))

            # Send acknowledgment and one data notification
            conn.sendall(b'{"status": "subscribed"}\n')
            time.sleep(0.05)
            conn.sendall(b'{"id": "UADER-FCYT", "telefono": "03442 43-1442"}\n')
            # Keep open briefly
            time.sleep(0.5)

    th = threading.Thread(target=server_thread, daemon=True)
    th.start()

    out_file = tmp_path / "obs_out.json"
    client = ObserverClient(host=host, port=port, output_file=out_file, verbose=True)

    received_notifications: list[dict[str, Any]] = []
    count = client.run_connection(
        max_messages=1,
        on_message=lambda msg: received_notifications.append(msg),
    )

    server_sock.close()
    th.join(timeout=1.0)

    assert count == 1
    assert len(received_from_client) == 1
    assert received_from_client[0]["ACTION"] == "subscribe"
    assert len(received_notifications) == 1
    assert received_notifications[0]["id"] == "UADER-FCYT"


def test_run_connection_server_down() -> None:
    """Test error handling when server is unreachable."""
    client = ObserverClient(host="127.0.0.1", port=59998)
    with pytest.raises(ConnectionError, match="Cannot connect to"):
        client.run_connection()


def test_reconnect_loop_recovers_after_server_restart() -> None:
    """Test that start() retries periodically and recovers when server reappears."""
    server_port_box: list[int] = []
    server_ready = threading.Event()
    stop_event = threading.Event()
    received_msgs: list[dict[str, Any]] = []

    def start_delayed_server() -> None:
        # Wait before starting the server so the client experiences an initial disconnection
        time.sleep(0.1)
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        server_port_box.append(srv.getsockname()[1])
        srv.listen(1)
        server_ready.set()

        conn, _ = srv.accept()
        with conn:
            conn.sendall(b'{"status": "subscribed"}\n')
            time.sleep(0.05)
            conn.sendall(b'{"id": "RECOVERED", "status": "ok"}\n')
            time.sleep(0.2)
        srv.close()

    server_thread = threading.Thread(target=start_delayed_server, daemon=True)
    server_thread.start()

    assert server_ready.wait(timeout=2.0)
    port = server_port_box[0]

    client = ObserverClient(host="127.0.0.1", port=port, reconnect_delay=0.1)
    client.start(
        stop_event=stop_event,
        max_messages=1,
        on_message=lambda msg: received_msgs.append(msg),
    )

    assert len(received_msgs) == 1
    assert received_msgs[0]["id"] == "RECOVERED"


def test_main_cli_execution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test CLI main() execution with mock server."""
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(("127.0.0.1", 0))
    host, port = server_sock.getsockname()
    server_sock.listen(1)

    def srv() -> None:
        conn, _ = server_sock.accept()
        with conn:
            conn.sendall(b'{"status": "subscribed"}\n')
            conn.sendall(b'{"id": "CLI_TEST"}\n')
            time.sleep(0.1)

    th = threading.Thread(target=srv, daemon=True)
    th.start()

    out_file = tmp_path / "cli_out.json"

    # Monkeypatch sys.argv
    cli_args = [
        "observerclient",
        "-s",
        host,
        "-p",
        str(port),
        "-o",
        str(out_file),
        "--reconnect-delay",
        "0.1",
    ]
    monkeypatch.setattr(sys, "argv", cli_args)

    # Run main() with KeyboardInterrupt simulation after a short interval
    def raise_interrupt() -> None:
        time.sleep(0.3)
        # Simulate Ctrl+C in main thread
        import _thread

        _thread.interrupt_main()

    timer_th = threading.Thread(target=raise_interrupt, daemon=True)
    timer_th.start()

    with pytest.raises(SystemExit) as exc:
        main()

    server_sock.close()
    th.join(timeout=1.0)
    assert exc.value.code == 0
    assert out_file.exists()
    assert "CLI_TEST" in out_file.read_text(encoding="utf-8")
