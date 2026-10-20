"""Exchange HTTP POST requests and JSON responses over TCP sockets."""

import json
import socket
from http import HTTPStatus
from http.client import HTTPResponse, parse_headers
from typing import Any

MAX_BODY = 1024 * 1024


class HTTPRequestError(ValueError):
    """Describe a rejected HTTP request and its response status."""

    def __init__(self, status: int, message: str) -> None:
        """Store the HTTP status and diagnostic message."""
        super().__init__(message)
        self.status = status


def read_request(sock: socket.socket) -> dict[str, Any]:
    """Read one bounded POST / request containing a JSON object."""
    with sock.makefile("rb") as stream:
        line = stream.readline(8193)
        parts = line.decode("ascii").strip().split()
        if len(parts) != 3 or parts[2] not in ("HTTP/1.0", "HTTP/1.1"):
            raise HTTPRequestError(400, "Invalid HTTP request line")
        method, path, _ = parts
        headers = parse_headers(stream)
        if method != "POST":
            raise HTTPRequestError(405, "Use HTTP POST")
        if path != "/":
            raise HTTPRequestError(404, "Unknown endpoint")
        if headers.get("Transfer-Encoding"):
            raise HTTPRequestError(400, "Request Transfer-Encoding is unsupported; use Content-Length")
        lengths = headers.get_all("Content-Length", [])
        if len(lengths) != 1:
            raise HTTPRequestError(411, "One Content-Length header is required")
        try:
            length = int(lengths[0])
        except ValueError as exc:
            raise HTTPRequestError(400, "Invalid Content-Length") from exc
        if length < 0 or length > MAX_BODY:
            raise HTTPRequestError(413, "Request body exceeds the allowed size")
        if headers.get_content_type() != "application/json":
            raise HTTPRequestError(415, "Use Content-Type: application/json")
        body = stream.read(length)
        if len(body) != length:
            raise HTTPRequestError(400, "Incomplete request body")
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise HTTPRequestError(400, "JSON body must be an object")
    return payload


def send_post(sock: socket.socket, payload: dict[str, Any], host: str, port: int) -> None:
    """Send one HTTP/1.1 POST with a UTF-8 JSON body and its byte length."""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = (
        f"POST / HTTP/1.1\r\nHost: {host}:{port}\r\n"
        f"Content-Type: application/json\r\nContent-Length: {len(body)}\r\n"
        "Connection: close\r\n\r\n"
    )
    sock.sendall(headers.encode("ascii") + body)


def write_response(sock: socket.socket, payload: Any, status: int | None = None) -> None:
    """Send a finite HTTP JSON response with an explicit Content-Length."""
    if status is None:
        status = 400 if isinstance(payload, dict) and "Error" in payload else 200
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = (
        f"HTTP/1.1 {status} {HTTPStatus(status).phrase}\r\n"
        f"Content-Type: application/json; charset=utf-8\r\nContent-Length: {len(body)}\r\n"
        "Connection: close\r\n\r\n"
    )
    if status == 405:
        headers = headers.replace("Connection: close", "Allow: POST\r\nConnection: close")
    sock.sendall(headers.encode("ascii") + body)


def start_stream(sock: socket.socket) -> None:
    """Start a close-delimited HTTP response containing newline-delimited JSON."""
    sock.sendall(
        b"HTTP/1.1 200 OK\r\nContent-Type: application/x-ndjson; charset=utf-8\r\n"
        b"Cache-Control: no-store\r\nConnection: close\r\n\r\n"
        b'{"status":"subscribed"}\n'
    )


def open_response(sock: socket.socket) -> HTTPResponse:
    """Parse the response headers while retaining any buffered body bytes."""
    response = HTTPResponse(sock)
    response.begin()
    return response
