import json
import socket
import sys
import threading
from pathlib import Path

import pytest

from tpfi_is2.observer_client import ObserverClient, main


def test_initialization():
    client = ObserverClient()

    assert client.host == "localhost"
    assert client.port == 8080
    assert client.socket is None
    assert client.retry_interval == 30.0


def test_connection_and_disconnection():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)

    port = server.getsockname()[1]

    def accept_connection():
        connection, _ = server.accept()
        connection.close()

    thread = threading.Thread(target=accept_connection)
    thread.start()

    client = ObserverClient(host="127.0.0.1", port=port)

    assert client.connect() is True
    assert client.socket is not None

    client.disconnect()

    assert client.socket is None

    thread.join(timeout=2)
    server.close()


def test_subscribe():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)

    port = server.getsockname()[1]
    messages = []

    def receive_subscription():
        connection, _ = server.accept()
        data = connection.recv(4096)
        messages.append(json.loads(data.decode("utf-8")))
        connection.close()

    thread = threading.Thread(target=receive_subscription)
    thread.start()

    client = ObserverClient(host="127.0.0.1", port=port)

    assert client.connect() is True
    assert client.subscribe() is True

    thread.join(timeout=2)

    assert len(messages) == 1
    assert messages[0]["ACTION"] == "subscribe"
    assert messages[0]["UUID"] == client.uuid
    assert messages[0]["SESSION_ID"] == client.session_id

    client.disconnect()
    server.close()


def test_notify(capsys, tmp_path: Path):
    out_file = tmp_path / "notifications.json"
    client = ObserverClient(output_file=out_file)

    notification = {"EVENT": "data_updated", "ID": "UADER-FCYT-IS2"}

    client.notify(notification)

    output = capsys.readouterr().out

    assert "Notificación recibida" in output
    assert "data_updated" in output

    written = out_file.read_text(encoding="utf-8")
    assert "UADER-FCYT-IS2" in written


def test_main_cli_arguments(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    out_file = tmp_path / "out.json"

    def dummy_run(self):
        self.running = False

    monkeypatch.setattr(ObserverClient, "run", dummy_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "observerclient.py",
            "-s",
            "127.0.0.1",
            "-p",
            "9090",
            "-o",
            str(out_file),
            "-v",
            "--retry-interval",
            "15",
        ],
    )

    main()