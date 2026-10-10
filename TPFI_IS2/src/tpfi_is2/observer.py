"""Observer pattern: notify subscribed TCP clients on CorporateData updates."""

from __future__ import annotations

import json
import logging
import socket
import threading
from typing import Any


class CorporateDataObserver:
    """Keeps subscriber sockets and pushes JSON notifications on data changes."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: list[tuple[socket.socket, str]] = []

    def subscribe(self, conn: socket.socket, client_uuid: str) -> None:
        with self._lock:
            self._subscribers.append((conn, client_uuid))
        logging.debug("Observer subscribe UUID=%s (total=%s)", client_uuid, len(self._subscribers))

    def unsubscribe(self, conn: socket.socket) -> None:
        with self._lock:
            self._subscribers = [(c, uid) for c, uid in self._subscribers if c is not conn]

    def notify(self, message: dict[str, Any]) -> None:
        payload = json.dumps(message, ensure_ascii=False).encode("utf-8") + b"\n"
        dead: list[socket.socket] = []
        with self._lock:
            targets = list(self._subscribers)
        for conn, client_uuid in targets:
            try:
                conn.sendall(payload)
                logging.debug("Observer notify UUID=%s", client_uuid)
            except OSError:
                dead.append(conn)
        for conn in dead:
            self.unsubscribe(conn)
