"""Tests for ProxyApplicationServer (in-memory backend, no AWS)."""

from __future__ import annotations

import json
import socket
import threading
import time
from collections.abc import Generator
from typing import Any

import pytest

from tpfi_is2.observer_client import ObserverClient
from tpfi_is2.proxy import CorporateDataProxy
from tpfi_is2.proxy_server import ProxyApplicationServer
from tpfi_is2.storage import MemoryCorporateDataGateway, MemoryCorporateLogGateway


def send_request(host: str, port: int, payload: dict[str, Any]) -> Any:
    with socket.create_connection((host, port), timeout=5) as sock:
        sock.sendall(json.dumps(payload).encode("utf-8"))
        sock.shutdown(socket.SHUT_WR)
        data = b""
        while chunk := sock.recv(4096):
            data += chunk
    return json.loads(data.decode("utf-8"))


@pytest.fixture
def memory_backend(monkeypatch: pytest.MonkeyPatch) -> Generator[tuple[str, int], None, None]:
    monkeypatch.setenv("TPFI_USE_MEMORY", "1")
    MemoryCorporateDataGateway.reset()
    MemoryCorporateLogGateway.reset()
    data = MemoryCorporateDataGateway.instance()
    log = MemoryCorporateLogGateway.instance()
    proxy = CorporateDataProxy(data=data, log=log)
    server = ProxyApplicationServer(host="127.0.0.1", port=0, proxy=proxy, log_gateway=log)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    yield "127.0.0.1", server.port
    server.shutdown()
    thread.join(timeout=2)


def test_get_set_list_happy_path(memory_backend: tuple[str, int]) -> None:
    host, port = memory_backend
    meta = {"UUID": "cpu-1", "SESSION_ID": "sess-1"}

    missing = send_request(host, port, {**meta, "ACTION": "get", "ID": "UADER-FCYT-IS2"})
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

    fetched = send_request(host, port, {**meta, "ACTION": "get", "ID": "UADER-FCYT-IS2"})
    assert fetched["domicilio"] == "25 de Mayo 385-1P"

    listed = send_request(host, port, {**meta, "ACTION": "list"})
    assert isinstance(listed, list)
    assert len(listed) == 1

    log = MemoryCorporateLogGateway.instance()
    actions = [entry["action"] for entry in log.entries]
    assert actions.count("get") >= 2
    assert "set" in actions
    assert "list" in actions


def test_set_requires_corporate_fields(memory_backend: tuple[str, int]) -> None:
    host, port = memory_backend
    response = send_request(
        host,
        port,
        {"UUID": "1", "SESSION_ID": "2", "ACTION": "set", "ID": "X"},
    )
    assert "Error" in response


def test_port_already_in_use(memory_backend: tuple[str, int]) -> None:
    _host, port = memory_backend
    second = ProxyApplicationServer(host="127.0.0.1", port=port)
    with pytest.raises(SystemExit, match="cannot bind"):
        second.serve_forever()


def test_observer_notified_on_set(memory_backend: tuple[str, int]) -> None:
    host, port = memory_backend
    received: list[dict[str, Any]] = []

    client = ObserverClient(host=host, port=port)

    def custom_notify(notification: dict[str, Any]) -> None:
        received.append(notification)

    client.notify = custom_notify  # type: ignore[assignment]
    client.running = True

    assert client.connect()
    assert client.subscribe()

    listen_thread = threading.Thread(target=client.listen, daemon=True)
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
