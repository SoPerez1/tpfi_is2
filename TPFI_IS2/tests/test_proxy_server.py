"""Tests for ProxyApplicationServer (in-memory backend, no AWS)."""

from __future__ import annotations

import json
import socket
import threading
import time
from collections.abc import Generator
from typing import Any

import pytest

from tpfi_is2.http_transport import open_response, send_post
from tpfi_is2.observer_client import ObserverClient
from tpfi_is2.proxy import CorporateDataProxy
from tpfi_is2.proxy_server import ProxyApplicationServer
from tpfi_is2.singleton_client import SingletonClient
from tpfi_is2.storage import MemoryCorporateDataGateway, MemoryCorporateLogGateway


def send_request(host: str, port: int, payload: dict[str, Any]) -> Any:
    return SingletonClient(host, port).send(payload)


@pytest.fixture
def memory_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[str, int], None, None]:

    monkeypatch.setenv("TPFI_USE_MEMORY", "1")

    MemoryCorporateDataGateway.reset()
    MemoryCorporateLogGateway.reset()

    data = MemoryCorporateDataGateway.instance()
    log = MemoryCorporateLogGateway.instance()

    proxy = CorporateDataProxy(data=data, log=log)

    server = ProxyApplicationServer(
        host="127.0.0.1",
        port=0,
        proxy=proxy,
        log_gateway=log,
    )

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )

    thread.start()
    time.sleep(0.05)

    yield "127.0.0.1", server.port

    server.shutdown()
    thread.join(timeout=2)


def test_get_set_list_happy_path(memory_backend: tuple[str, int]) -> None:
    # Verifica las operaciones get, set y list
    host, port = memory_backend

    meta = {
        "UUID": "cpu-1",
        "SESSION_ID": "sess-1",
    }

    missing = send_request(
        host,
        port,
        {**meta, "ACTION": "get", "ID": "UADER-FCYT-IS2"},
    )

    assert missing == {"Error": "Record not found: UADER-FCYT-IS2"}

    created = send_request(
        host,
        port,
        {
            **meta,
            "ACTION": "set",
            "ID": "UADER-FCYT-IS2",
            "domicilio": "25 de Mayo 385-1P",
            "localidad": "Concepción del Uruguay",
        },
    )

    assert created["id"] == "UADER-FCYT-IS2"
    assert created["domicilio"] == "25 de Mayo 385-1P"

    fetched = send_request(
        host,
        port,
        {**meta, "ACTION": "get", "ID": "UADER-FCYT-IS2"},
    )

    assert fetched["domicilio"] == "25 de Mayo 385-1P"

    listed = send_request(
        host,
        port,
        {**meta, "ACTION": "list"},
    )

    assert isinstance(listed, list)
    assert len(listed) == 1

    log = MemoryCorporateLogGateway.instance()
    actions = [entry["action"] for entry in log.entries]

    assert actions.count("get") >= 2
    assert "set" in actions
    assert "list" in actions


def test_set_requires_corporate_fields(
    memory_backend: tuple[str, int],
) -> None:
    # Verifica que set requiera campos para modificar
    host, port = memory_backend

    response = send_request(
        host,
        port,
        {
            "UUID": "1",
            "SESSION_ID": "2",
            "ACTION": "set",
            "ID": "X",
        },
    )

    assert "Error" in response


def test_port_already_in_use(
    memory_backend: tuple[str, int],
) -> None:
    # Verifica que no se pueda utilizar un puerto ocupado
    _host, port = memory_backend

    second = ProxyApplicationServer(
        host="127.0.0.1",
        port=port,
    )

    with pytest.raises(SystemExit, match="cannot bind"):
        second.serve_forever()


def test_observer_notified_on_set(
    memory_backend: tuple[str, int],
) -> None:
    # Verifica las notificaciones utilizando ObserverClient
    host, port = memory_backend
    received: list[dict[str, Any]] = []

    client = ObserverClient(host=host, port=port)

    def custom_notify(notification: dict[str, Any]) -> None:
        received.append(notification)

    client.notify = custom_notify  # type: ignore[assignment]
    client.running = True

    assert client.connect()
    assert client.subscribe()

    listen_thread = threading.Thread(
        target=client.listen,
        daemon=True,
    )

    listen_thread.start()

    send_request(
        host,
        port,
        {
            "UUID": "cpu-2",
            "SESSION_ID": "sess-2",
            "ACTION": "set",
            "ID": "NEW-ID",
            "sede": "FCyT",
        },
    )

    deadline = time.time() + 2

    while time.time() < deadline and len(received) < 1:
        time.sleep(0.05)

    client.stop()
    listen_thread.join(timeout=1)

    assert len(received) >= 1
    assert received[-1]["sede"] == "FCyT"


def test_observer_notified_with_socket(
    memory_backend: tuple[str, int],
) -> None:
    # Verifica las notificaciones utilizando sockets directamente
    host, port = memory_backend
    received: list[dict[str, Any]] = []
    subscribed = threading.Event()

    def subscriber() -> None:
        with socket.create_connection((host, port), timeout=5) as sock:
            sock.settimeout(0.5)

            send_post(sock, {"UUID": "obs-1", "SESSION_ID": "s-obs", "ACTION": "subscribe"}, host, port)
            with open_response(sock) as response:
                assert response.status == 200
                assert response.headers.get_content_type() == "application/x-ndjson"
                received.append(json.loads(response.readline()))
                subscribed.set()
                received.append(json.loads(response.readline()))

    threading.Thread(
        target=subscriber,
        daemon=True,
    ).start()

    assert subscribed.wait(timeout=3)

    send_request(
        host,
        port,
        {
            "UUID": "cpu-2",
            "SESSION_ID": "sess-2",
            "ACTION": "set",
            "ID": "NEW-ID",
            "sede": "FCyT",
        },
    )

    deadline = time.time() + 3

    while time.time() < deadline and len(received) < 2:
        time.sleep(0.05)

    assert len(received) >= 2
    assert received[-1]["sede"] == "FCyT"


def test_standard_http_client_and_multiple_notifications(memory_backend: tuple[str, int]) -> None:
    """Use the standard HTTP parser to verify finite and streamed response framing."""
    from http.client import HTTPConnection

    host, port = memory_backend
    observer = HTTPConnection(host, port, timeout=3)
    observer.request(
        "POST",
        "/",
        json.dumps({"ACTION": "subscribe", "UUID": "http", "SESSION_ID": "s"}),
        {"Content-Type": "application/json"},
    )
    stream = observer.getresponse()
    assert stream.status == 200
    assert stream.headers.get_content_type() == "application/x-ndjson"
    assert json.loads(stream.readline()) == {"status": "subscribed"}
    try:
        for name in ("Concepción del Uruguay", "Paraná"):
            client = HTTPConnection(host, port, timeout=3)
            client.request(
                "POST",
                "/",
                json.dumps({"ACTION": "set", "ID": "HTTP", "localidad": name}),
                {"Content-Type": "application/json"},
            )
            response = client.getresponse()
            body = response.read()
            assert response.status == 200
            assert int(response.headers["Content-Length"]) == len(body)
            assert json.loads(body)["localidad"] == name
            assert json.loads(stream.readline()) == json.loads(body)
            client.close()
    finally:
        stream.close()
        observer.close()


@pytest.mark.parametrize(
    ("http_request", "status"),
    [
        (b"garbage\r\n\r\n", 400),
        (b"GET / HTTP/1.1\r\n\r\n", 405),
        (b"POST /missing HTTP/1.1\r\n\r\n", 404),
        (b"POST / HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n", 400),
        (b"POST / HTTP/1.1\r\n\r\n", 411),
        (b"POST / HTTP/1.1\r\nContent-Length: x\r\n\r\n", 400),
        (b"POST / HTTP/1.1\r\nContent-Length: -1\r\n\r\n", 413),
        (b"POST / HTTP/1.1\r\nContent-Length: 1048577\r\n\r\n", 413),
        (b"POST / HTTP/1.1\r\nContent-Length: 2\r\nContent-Type: text/plain\r\n\r\n{}", 415),
        (b"POST / HTTP/1.1\r\nContent-Length: 4\r\nContent-Type: application/json\r\n\r\n{}", 400),
        (b"POST / HTTP/1.1\r\nContent-Length: 2\r\nContent-Type: application/json\r\n\r\n[]", 400),
        (b"POST / HTTP/1.1\r\nContent-Length: 1\r\nContent-Type: application/json\r\n\r\n{", 400),
    ],
)
def test_http_rejects_invalid_requests(memory_backend: tuple[str, int], http_request: bytes, status: int) -> None:
    """Reject invalid HTTP envelopes and JSON bodies with structured errors."""
    with socket.create_connection(memory_backend, timeout=3) as sock:
        sock.sendall(http_request)
        sock.shutdown(socket.SHUT_WR)
        with open_response(sock) as response:
            assert response.status == status
            assert "Error" in json.loads(response.read())
