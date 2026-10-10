"""JSON helpers for DynamoDB values and TCP payloads."""

import json
import socket
from decimal import Decimal
from typing import Any


def dynamodb_to_json(value: Any) -> Any:
    """Convert DynamoDB types to JSON-serializable values."""
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    if isinstance(value, dict):
        return {k: dynamodb_to_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [dynamodb_to_json(v) for v in value]
    return value


def read_tcp_json(sock) -> dict[str, Any]:
    """Read one JSON object sent by a client (until peer shuts down write side)."""
    chunks: list[bytes] = []
    while True:
        part = sock.recv(4096)
        if not part:
            break
        chunks.append(part)
    if not chunks:
        raise ValueError("Empty request")
    return json.loads(b"".join(chunks).decode("utf-8"))


def write_tcp_json(sock, payload: Any) -> None:
    """Send one JSON response and half-close the write side."""
    sock.sendall(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    sock.shutdown(socket.SHUT_WR)
