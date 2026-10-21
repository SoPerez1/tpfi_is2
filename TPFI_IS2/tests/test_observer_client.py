import socket
import sys
import threading
from pathlib import Path

import pytest

from tpfi_is2.http_transport import read_request, start_stream
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
        messages.append(read_request(connection))
        start_stream(connection)
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


def test_stream_disconnect_reconnect_and_fragmented_utf8() -> None:
    """Resubscribe after EOF and decode Unicode events split across TCP writes."""
    import json
    import time

    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        server.settimeout(3)
        requests = []
        events = []
        done = threading.Event()
        client = ObserverClient("127.0.0.1", server.getsockname()[1], retry_interval=0.01)

        def serve():
            for index in range(2):
                conn, _ = server.accept()
                with conn:
                    requests.append(read_request(conn))
                    start_stream(conn)
                    body = (json.dumps({"localidad": "Paraná", "index": index}, ensure_ascii=False) + "\n").encode()
                    split = body.index("á".encode()) + 1
                    conn.sendall(body[:split])
                    time.sleep(0.01)
                    conn.sendall(body[split:])

        def notify(event):
            events.append(event)
            if len(events) == 2:
                client.running = False
                done.set()

        client.notify = notify
        producer = threading.Thread(target=serve, daemon=True)
        consumer = threading.Thread(target=client.run, daemon=True)
        producer.start()
        consumer.start()
        try:
            assert done.wait(5)
        finally:
            client.stop()
            producer.join(1)
            consumer.join(1)
        assert [event["index"] for event in events] == [0, 1]
        assert all(event["localidad"] == "Paraná" for event in events)
        assert len(requests) == 2
        assert all(req["ACTION"] == "subscribe" for req in requests)
