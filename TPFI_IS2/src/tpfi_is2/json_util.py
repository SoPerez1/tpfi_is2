"""JSON helpers for DynamoDB values and TCP payloads."""

import json
import socket
from decimal import Decimal
from typing import Any


def dynamodb_to_json(value: Any) -> Any:
    # Convierte valores de DynamoDB a formatos compatibles con JSON
    """Convert DynamoDB decimal values into JSON-compatible values."""
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)

    if isinstance(value, dict):
        return {k: dynamodb_to_json(v) for k, v in value.items()}

    if isinstance(value, list):
        return [dynamodb_to_json(v) for v in value]

    return value


def read_tcp_json(sock: socket.socket) -> dict[str, Any]:
    # Recibe un mensaje JSON por TCP
    """Read a JSON request from a TCP connection."""
    buffer = ""

    while True:
        part = sock.recv(4096)

        if not part:
            break

        buffer += part.decode("utf-8")

        # Procesa mensajes terminados en salto de línea
        if "\n" in buffer:
            line = buffer.split("\n", 1)[0]

            if line.strip():
                return json.loads(line)

        # También acepta un JSON completo sin salto de línea
        try:
            return json.loads(buffer)
        except json.JSONDecodeError:
            continue

    if not buffer.strip():
        raise ValueError("Empty request")

    return json.loads(buffer)


def write_tcp_json(sock: socket.socket, payload: Any) -> None:
    # Envía una respuesta JSON por TCP
    """Send a JSON response and finish writing to the connection."""
    message = json.dumps(payload, ensure_ascii=False) + "\n"
    sock.sendall(message.encode("utf-8"))

    try:
        sock.shutdown(socket.SHUT_WR)
    except OSError:
        pass
