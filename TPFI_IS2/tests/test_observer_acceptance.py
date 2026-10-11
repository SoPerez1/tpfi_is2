"""Acceptance tests for ObserverClient with ProxyApplicationServer.

Validates:
- Happy path: subscription, CorporateLog audit entry, receiving update notification on CorporateData set.
- Writing received notifications to output file.
- Client reconnection after server outage.
- Argument error handling on malformed CLI options.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from tpfi_is2.observer_client import ObserverClient, parse_args
from tpfi_is2.proxy import CorporateDataProxy
from tpfi_is2.proxy_server import ProxyApplicationServer
from tpfi_is2.singleton_client import SingletonClient
from tpfi_is2.storage import MemoryCorporateDataGateway, MemoryCorporateLogGateway


@pytest.fixture
def running_server(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[ProxyApplicationServer, str, int], None, None]:
    """Start an in-memory ProxyApplicationServer instance."""
    monkeypatch.setenv("TPFI_USE_MEMORY", "1")
    MemoryCorporateDataGateway.reset()
    MemoryCorporateLogGateway.reset()
    data = MemoryCorporateDataGateway.instance()
    log = MemoryCorporateLogGateway.instance()
    proxy = CorporateDataProxy(data=data, log=log)

    server = ProxyApplicationServer(
        host="127.0.0.1", port=0, proxy=proxy, log_gateway=log
    )
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    time.sleep(0.05)

    yield server, "127.0.0.1", server.port

    server.shutdown()
    th.join(timeout=2.0)


def test_acceptance_observer_happy_path(
    running_server: tuple[ProxyApplicationServer, str, int],
    tmp_path: Path,
) -> None:
    """Acceptance: Observer subscribes, verifies CorporateLog audit, receives notification on set."""
    _server, host, port = running_server
    output_file = tmp_path / "observer_acceptance_output.json"

    client = ObserverClient(
        host=host,
        port=port,
        output_file=output_file,
        verbose=True,
        reconnect_delay=0.1,
    )

    received_updates: list[dict[str, Any]] = []
    stop_event = threading.Event()

    # Run observer client in a background thread
    client_thread = threading.Thread(
        target=client.start,
        kwargs={
            "stop_event": stop_event,
            "max_messages": 1,
            "on_message": lambda msg: received_updates.append(msg),
        },
        daemon=True,
    )
    client_thread.start()

    # Wait for subscription to be registered
    deadline = time.time() + 2.0
    while time.time() < deadline:
        with _server._observer._lock:
            if len(_server._observer._subscribers) >= 1:
                break
        time.sleep(0.05)

    # Verify CorporateLog contains audit entry for subscribe action
    log = MemoryCorporateLogGateway.instance()
    subscribe_entries = [e for e in log.entries if e.get("action") == "subscribe"]
    assert (
        len(subscribe_entries) >= 1
    ), "Audit entry for subscribe was not logged in CorporateLog"
    assert subscribe_entries[0]["CPUid"] == client.get_system_uuid()

    # Now make an update using SingletonClient
    singleton = SingletonClient(host=host, port=port)
    set_req = singleton.build_request(
        {
            "ACTION": "set",
            "ID": "UADER-ACCEPTANCE",
            "domicilio": "Urquiza 500",
            "telefono": "03442 42-5555",
            "sede": "FCyT Central",
        }
    )
    singleton.send(set_req)

    # Wait for observer to receive the notification
    client_thread.join(timeout=3.0)
    stop_event.set()

    assert (
        len(received_updates) == 1
    ), "ObserverClient did not receive the update notification"
    notification = received_updates[0]
    assert notification["id"] == "UADER-ACCEPTANCE"
    assert notification["domicilio"] == "Urquiza 500"
    assert notification["sede"] == "FCyT Central"

    # Verify output file was written and contains the update
    assert output_file.exists()
    file_data = json.loads(output_file.read_text(encoding="utf-8"))
    assert file_data["id"] == "UADER-ACCEPTANCE"
    assert file_data["domicilio"] == "Urquiza 500"


def test_acceptance_observer_handles_server_outage_and_reconnects(
    tmp_path: Path,
) -> None:
    """Acceptance: Observer handles temporary server crash and reconnects when server restarts."""
    MemoryCorporateDataGateway.reset()
    MemoryCorporateLogGateway.reset()
    data = MemoryCorporateDataGateway.instance()
    log = MemoryCorporateLogGateway.instance()

    # Start initial server on specific fixed port
    srv1 = ProxyApplicationServer(
        host="127.0.0.1",
        port=0,
        proxy=CorporateDataProxy(data=data, log=log),
        log_gateway=log,
    )
    t1 = threading.Thread(target=srv1.serve_forever, daemon=True)
    t1.start()
    time.sleep(0.05)
    port = srv1.port

    output_file = tmp_path / "reconnect_output.json"
    client = ObserverClient(
        host="127.0.0.1",
        port=port,
        output_file=output_file,
        verbose=True,
        reconnect_delay=0.1,  # Short reconnect for fast testing
    )

    received_updates: list[dict[str, Any]] = []
    stop_event = threading.Event()

    client_thread = threading.Thread(
        target=client.start,
        kwargs={
            "stop_event": stop_event,
            "max_messages": 1,
            "on_message": lambda msg: received_updates.append(msg),
        },
        daemon=True,
    )
    client_thread.start()
    time.sleep(0.1)

    # Simulate server crash by shutting down srv1
    srv1.shutdown()
    t1.join(timeout=1.0)
    time.sleep(0.2)

    # Restart server on the same port
    srv2 = ProxyApplicationServer(
        host="127.0.0.1",
        port=port,
        proxy=CorporateDataProxy(data=data, log=log),
        log_gateway=log,
    )
    t2 = threading.Thread(target=srv2.serve_forever, daemon=True)
    t2.start()

    # Wait until ObserverClient reconnects and re-subscribes
    deadline = time.time() + 3.0
    while time.time() < deadline:
        with srv2._observer._lock:
            if len(srv2._observer._subscribers) >= 1:
                break
        time.sleep(0.05)

    # Send update through SingletonClient on re-established server
    singleton = SingletonClient(host="127.0.0.1", port=port)
    set_req = singleton.build_request(
        {
            "ACTION": "set",
            "ID": "AFTER-CRASH",
            "sede": "FCyT Sede 2",
        }
    )
    singleton.send(set_req)

    client_thread.join(timeout=4.0)
    stop_event.set()
    srv2.shutdown()
    t2.join(timeout=1.0)

    assert len(received_updates) == 1
    assert received_updates[0]["id"] == "AFTER-CRASH"


def test_acceptance_malformed_arguments() -> None:
    """Acceptance: ObserverClient rejects invalid CLI arguments."""
    with pytest.raises(SystemExit):
        parse_args(["-p", "999999"])

    with pytest.raises(SystemExit):
        parse_args(["-p", "invalid_port"])
