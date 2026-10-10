"""SingletonClient against ProxyApplicationServer (in-memory)."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Generator

import pytest

from tpfi_is2.proxy import CorporateDataProxy
from tpfi_is2.proxy_server import ProxyApplicationServer
from tpfi_is2.singleton_client import SingletonClient
from tpfi_is2.storage import MemoryCorporateDataGateway, MemoryCorporateLogGateway


@pytest.fixture
def live_server(monkeypatch: pytest.MonkeyPatch) -> Generator[tuple[str, int], None, None]:
    monkeypatch.setenv("TPFI_USE_MEMORY", "1")
    MemoryCorporateDataGateway.reset()
    MemoryCorporateLogGateway.reset()
    data = MemoryCorporateDataGateway.instance()
    log = MemoryCorporateLogGateway.instance()
    server = ProxyApplicationServer(
        host="127.0.0.1",
        port=0,
        proxy=CorporateDataProxy(data=data, log=log),
        log_gateway=log,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    yield "127.0.0.1", server.port
    server.shutdown()
    thread.join(timeout=2)


def test_client_set_and_get_via_server(live_server: tuple[str, int], tmp_path) -> None:
    host, port = live_server
    client = SingletonClient(host, port)
    inp = tmp_path / "in.json"
    inp.write_text(
        '{"ACTION": "set", "ID": "UADER-FCYT-IS2", "domicilio": "25 de Mayo", "sede": "FCyT"}',
        encoding="utf-8",
    )
    payload = client.build_request(json.loads(inp.read_text(encoding="utf-8")))
    created = client.send(payload)
    assert created["domicilio"] == "25 de Mayo"

    payload = client.build_request({"ACTION": "get", "ID": "UADER-FCYT-IS2"})
    fetched = client.send(payload)
    assert fetched["sede"] == "FCyT"
