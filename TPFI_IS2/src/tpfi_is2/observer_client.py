"""ObserverClient: Subscribes to ProxyApplicationServer and listens for live updates."""

import argparse
import json
import logging
import socket
import sys
import threading
import time
import uuid
from http.client import HTTPException, HTTPResponse
from pathlib import Path
from typing import Any

from tpfi_is2.http_transport import open_response, send_post
from tpfi_is2.version import VERSION_BUILD


class ObserverClient:
    """HTTP client that subscribes to a persistent NDJSON response."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        output_file: str | Path | None = None,
        retry_interval: float = 30.0,
        verbose: bool = False,
    ) -> None:
        """Initialize the component and its dependencies."""
        self.host = host
        self.port = port
        self.output_file = Path(output_file) if output_file else None
        self.retry_interval = retry_interval
        self.verbose = verbose
        self.socket: socket.socket | None = None
        self._response: HTTPResponse | None = None
        self._disconnect_lock = threading.Lock()
        self._response_lock = threading.Lock()
        self.uuid = str(uuid.getnode())
        self.session_id = str(uuid.uuid4())
        self.running = False
        self._configure_logging()

    def _configure_logging(self) -> None:
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(level=level, stream=sys.stdout, force=True)

    def connect(self) -> bool:
        """Establish TCP socket connection with the application server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            logging.info("Connected to server at %s:%s", self.host, self.port)
            return True
        except OSError as error:
            logging.error("Connection error to %s:%s - %s", self.host, self.port, error)
            self.disconnect()
            return False

    def disconnect(self) -> None:
        """Close TCP socket connection."""
        with self._disconnect_lock:
            sock, self.socket = self.socket, None
            response, self._response = self._response, None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
            logging.info("Disconnected from server")
        if response is not None:
            with self._response_lock:
                response.close()

    def subscribe(self) -> bool:
        """Send subscription JSON request to the server."""
        if self.socket is None:
            logging.error("No active socket connection to subscribe")
            return False

        request = {
            "ACTION": "subscribe",
            "UUID": self.uuid,
            "SESSION_ID": self.session_id,
        }

        try:
            self.socket.settimeout(10)
            send_post(self.socket, request, self.host, self.port)
            self._response = open_response(self.socket)
            if self._response.status != 200 or self._response.headers.get_content_type() != "application/x-ndjson":
                raise ValueError("Server rejected the notification stream")
            if json.loads(self._response.readline()) != {"status": "subscribed"}:
                raise ValueError("Missing subscription confirmation")
            self.socket.settimeout(None)
            logging.info("Subscription request sent for UUID=%s", self.uuid)
            return True
        except (OSError, HTTPException, ValueError) as error:
            logging.error("Failed to send subscription: %s", error)
            self.disconnect()
            return False

    def listen(self) -> bool:
        """Listen for incoming JSON notifications from the server."""
        response = self._response
        if response is None:
            return False
        try:
            while self.running:
                with self._response_lock:
                    line = response.readline()
                if not line:
                    logging.info("Server closed connection")
                    return False
                try:
                    notification = json.loads(line)
                    self.notify(notification)
                except (ValueError, UnicodeDecodeError):
                    logging.warning("Received invalid JSON line: %r", line)
        except (OSError, HTTPException, ValueError) as error:
            logging.error("Error receiving notifications: %s", error)
            return False
        return True

    def notify(self, notification: dict[str, Any]) -> None:
        """Display notification on stdout and append to output file if configured."""
        formatted = json.dumps(notification, indent=2, ensure_ascii=False)
        print(f"Notificación recibida:\n{formatted}")

        if self.output_file:
            try:
                self.output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.output_file, "a", encoding="utf-8") as file:
                    file.write(json.dumps(notification, ensure_ascii=False) + "\n")
            except OSError as error:
                logging.error("Failed writing notification to %s: %s", self.output_file, error)

    def run(self) -> None:
        """Continuously connect, subscribe, listen, and retry upon disconnection."""
        self.running = True
        while self.running:
            if self.connect():
                if self.subscribe():
                    self.listen()
                self.disconnect()

            if self.running:
                logging.info("Reconnecting in %s seconds...", self.retry_interval)
                time.sleep(self.retry_interval)

    def stop(self) -> None:
        """Stop running loop and disconnect."""
        self.running = False
        self.disconnect()


def main() -> None:
    """CLI entry point for ObserverClient."""
    parser = argparse.ArgumentParser(
        description="ObserverClient: Subscribe and receive CorporateData updates over TCP socket."
    )
    parser.add_argument("-s", "--server", default="localhost", help="Server hostname (default: localhost)")
    parser.add_argument("-p", "--port", type=int, default=8080, help="Server port (default: 8080)")
    parser.add_argument("-o", "--output", help="Optional output JSON file to record notifications")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")
    parser.add_argument(
        "--retry-interval",
        type=float,
        default=30.0,
        help="Reconnection retry interval in seconds (default: 30)",
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION_BUILD}")
    args = parser.parse_args()

    client = ObserverClient(
        host=args.server,
        port=args.port,
        output_file=args.output,
        retry_interval=args.retry_interval,
        verbose=args.verbose,
    )

    try:
        client.run()
    except KeyboardInterrupt:
        print("\nObserverClient stopped by user.")
        client.stop()


if __name__ == "__main__":
    main()
