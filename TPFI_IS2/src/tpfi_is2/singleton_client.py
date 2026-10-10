"""SingletonClient: sends get, set and list requests to the application server."""

import argparse
import json
import logging
import socket
import sys
import uuid
from typing import Any

from tpfi_is2.corporate_fields import has_corporate_updates


class SingletonClient:
    """Client that sends one JSON request to the server over TCP."""

    def __init__(self, host: str = "localhost", port: int = 8080) -> None:
        self.host = host
        self.port = port

    def build_request(self, data: Any) -> dict[str, Any]:
        """Validate input and add UUID (CPU) and session id."""
        if not isinstance(data, dict):
            raise ValueError("Input must be a JSON object")
        action = data.get("ACTION")
        if action not in ("get", "set", "list"):
            raise ValueError("ACTION must be 'get', 'set' or 'list'")

        payload = dict(data)
        if action == "list":
            payload.pop("ID", None)
        elif not payload.get("ID"):
            raise ValueError(f"ACTION '{action}' requires an ID")
        if action == "set" and not has_corporate_updates(payload):
            raise ValueError("ACTION 'set' requires at least one CorporateData field")

        payload["UUID"] = str(uuid.getnode())
        payload["SESSION_ID"] = str(uuid.uuid4())
        return payload

    def send(self, request: dict[str, Any]) -> Any:
        """Send the request and return the server JSON response."""
        logging.debug("Sending to %s:%s -> %s", self.host, self.port, request)
        try:
            with socket.create_connection((self.host, self.port), timeout=10) as sock:
                sock.sendall(json.dumps(request).encode("utf-8"))
                sock.shutdown(socket.SHUT_WR)
                answer = b""
                while chunk := sock.recv(4096):
                    answer += chunk
        except OSError as exc:
            raise ConnectionError(f"Could not connect to server {self.host}:{self.port}") from exc

        logging.debug("Received <- %s", answer)
        if not answer:
            raise ValueError("Empty response from server")
        try:
            return json.loads(answer)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON response from server") from exc


def main() -> None:
    """CLI: read input JSON, call the server, print or save the response."""
    parser = argparse.ArgumentParser(description="Query or update CorporateData.")
    parser.add_argument("-i", "--input", required=True, help="input JSON file")
    parser.add_argument("-o", "--output", help="output JSON file (default: stdout)")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug output")
    parser.add_argument("-s", "--server", default="localhost", help="server host")
    parser.add_argument("-p", "--port", type=int, default=8080, help="server port")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, stream=sys.stdout, force=True)

    client = SingletonClient(args.server, args.port)
    try:
        with open(args.input, encoding="utf-8") as file:
            request = client.build_request(json.load(file))
        response = client.send(request)
        answer = json.dumps(response, indent=2, ensure_ascii=False)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        sys.exit(f"Error: {exc}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as file:
            file.write(answer + "\n")
    else:
        print(answer)


if __name__ == "__main__":
    main()
