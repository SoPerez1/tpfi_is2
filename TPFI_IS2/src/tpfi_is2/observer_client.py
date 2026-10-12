"""ObserverClient: Subscribes to ProxyApplicationServer and listens for live updates."""

import argparse
import json
import logging
import socket
import sys
import time
import uuid
from pathlib import Path
from typing import Any


class ObserverClient:
    """TCP client that subscribes to CorporateData change notifications."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        output_file: str | Path | None = None,
        retry_interval: float = 30.0,
        verbose: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.output_file = Path(output_file) if output_file else None
        self.retry_interval = retry_interval
        self.verbose = verbose
        self.socket: socket.socket | None = None
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
        if self.socket is not None:
            try:
                self.socket.close()
            except OSError:
                pass
            self.socket = None
            logging.info("Disconnected from server")

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
            message = json.dumps(request, ensure_ascii=False) + "\n"
            self.socket.sendall(message.encode("utf-8"))
            logging.info("Subscription request sent for UUID=%s", self.uuid)
            return True
        except OSError as error:
            logging.error("Failed to send subscription: %s", error)
            self.disconnect()
            return False

    def listen(self) -> bool:
        """Listen for incoming JSON notifications from the server."""
        if self.socket is None:
            return False

        buffer = ""
        try:
            while self.running:
                data = self.socket.recv(4096)
                if not data:
                    logging.info("Server closed connection")
                    return False

                buffer += data.decode("utf-8")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line.strip():
                        continue
                    try:
                        notification = json.loads(line)
                        self.notify(notification)
                    except json.JSONDecodeError:
                        logging.warning("Received invalid JSON line: %r", line)

        except (OSError, UnicodeDecodeError) as error:
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