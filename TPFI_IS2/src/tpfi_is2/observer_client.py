"""ObserverClient module: subscribes to CorporateData updates via TCP socket.

Operates as a subscriber to SingleProxyObserverTPFI, maintaining an open TCP socket,
logging notifications to stdout and an optional output file, and reconnecting every
30 seconds upon socket disconnection.
"""

from __future__ import annotations

import argparse
import json
import logging
import socket
import sys
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any


class ObserverClient:
    """Subscriber client for CorporateData updates."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        output_file: str | Path | None = None,
        verbose: bool = False,
        reconnect_delay: float = 30.0,
    ) -> None:
        """Initialize ObserverClient.

        Args:
            host: Server hostname or IP address.
            port: Server TCP port.
            output_file: Optional file path to record received JSON notifications.
            verbose: Enable debug logging on stdout if True.
            reconnect_delay: Delay in seconds before attempting to reconnect (default 30.0).
        """
        self.host = host
        self.port = port
        self.output_file = Path(output_file) if output_file else None
        self.verbose = verbose
        self.reconnect_delay = reconnect_delay
        self.logger = logging.getLogger(self.__class__.__name__)
        self._configure_logging()

    def _configure_logging(self) -> None:
        """Configure logging level for client."""
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
            force=True,
        )
        self.logger.setLevel(level)

    def get_system_uuid(self) -> str:
        """Retrieve hardware node MAC-based CPU unique identifier.

        Returns:
            String representation of CPU UUID.
        """
        return str(uuid.getnode())

    def get_session_id(self) -> str:
        """Generate unique UUID4 session identifier.

        Returns:
            Session UUID string.
        """
        return str(uuid.uuid4())

    def build_subscribe_request(self) -> dict[str, Any]:
        """Generate subscription request JSON payload.

        Returns:
            Dictionary payload with ACTION='subscribe', CPU UUID and SESSION_ID.
        """
        return {
            "UUID": self.get_system_uuid(),
            "SESSION_ID": self.get_session_id(),
            "ACTION": "subscribe",
        }

    def write_output(self, formatted_json: str) -> None:
        """Write formatted JSON string to configured output file if informed.

        Args:
            formatted_json: Pretty-printed JSON string to write.
        """
        if self.output_file:
            try:
                self.output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.output_file, "w", encoding="utf-8") as file:
                    file.write(formatted_json + "\n")
                self.logger.debug("Wrote update to %s", self.output_file)
            except OSError as exc:
                self.logger.error(
                    "Failed to write to output file %s: %s", self.output_file, exc
                )

    def handle_incoming_message(self, message: dict[str, Any]) -> None:
        """Process and display received JSON notification.

        Args:
            message: Parsed JSON message received from the server.
        """
        formatted = json.dumps(message, indent=2, ensure_ascii=False)
        print(formatted)
        self.write_output(formatted)

    def run_connection(
        self,
        stop_event: threading.Event | None = None,
        max_messages: int | None = None,
        on_message: Callable[[dict[str, Any]], None] | None = None,
    ) -> int:
        """Establish TCP connection, subscribe, and receive stream of notifications.

        Args:
            stop_event: Optional event to signal termination.
            max_messages: Optional max number of notifications to receive before returning.
            on_message: Optional callback executed on each received message.

        Returns:
            Number of notifications received during this session.

        Raises:
            ConnectionError: If connection cannot be established or is interrupted.
        """
        self.logger.debug("Connecting to server at %s:%d", self.host, self.port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10.0)
        try:
            sock.connect((self.host, self.port))
        except OSError as exc:
            sock.close()
            raise ConnectionError(
                f"Cannot connect to {self.host}:{self.port}: {exc}"
            ) from exc

        messages_received = 0
        try:
            # Send subscribe payload
            payload = self.build_subscribe_request()
            request_bytes = (json.dumps(payload, ensure_ascii=False) + "\n").encode(
                "utf-8"
            )
            sock.sendall(request_bytes)
            self.logger.info(
                "Subscription sent to %s:%d with UUID=%s",
                self.host,
                self.port,
                payload["UUID"],
            )

            buffer = ""
            sock.settimeout(
                1.0
            )  # Short timeout to allow responsive checking of stop_event

            while True:
                if stop_event and stop_event.is_set():
                    self.logger.debug("Stop event received, closing connection.")
                    break

                try:
                    chunk = sock.recv(4096)
                except TimeoutError:
                    continue
                except OSError as exc:
                    raise ConnectionError(f"Socket connection error: {exc}") from exc

                if not chunk:
                    # Server closed connection
                    raise ConnectionError("Server closed TCP connection.")

                buffer += chunk.decode("utf-8")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        message = json.loads(line_str)
                    except json.JSONDecodeError as exc:
                        self.logger.warning(
                            "Received invalid JSON line: %r (%s)", line_str, exc
                        )
                        continue

                    # Server subscription acknowledgment or data notification
                    self.logger.debug("Received payload: %s", message)
                    if message.get("status") == "subscribed":
                        self.logger.info(
                            "Successfully subscribed to server notifications."
                        )
                    else:
                        messages_received += 1
                        self.handle_incoming_message(message)
                        if on_message:
                            on_message(message)

                        if (
                            max_messages is not None
                            and messages_received >= max_messages
                        ):
                            return messages_received

        finally:
            try:
                sock.close()
            except OSError:
                pass

        return messages_received

    def start(
        self,
        stop_event: threading.Event | None = None,
        max_messages: int | None = None,
        max_reconnects: int | None = None,
        on_message: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        """Start observer client loop with periodic reconnection upon disconnection.

        Args:
            stop_event: Optional threading event to signal loop termination.
            max_messages: Optional max messages to receive before exiting.
            max_reconnects: Optional maximum number of reconnect attempts.
            on_message: Optional callback for received messages.
        """
        reconnect_attempts = 0
        total_messages = 0

        self.logger.info(
            "Starting ObserverClient (target=%s:%d, reconnect_delay=%.1fs)",
            self.host,
            self.port,
            self.reconnect_delay,
        )

        while True:
            if stop_event and stop_event.is_set():
                self.logger.info("ObserverClient stopped by signal.")
                break

            try:
                remaining_messages = None
                if max_messages is not None:
                    remaining_messages = max_messages - total_messages
                    if remaining_messages <= 0:
                        break

                count = self.run_connection(
                    stop_event=stop_event,
                    max_messages=remaining_messages,
                    on_message=on_message,
                )
                total_messages += count
                reconnect_attempts = 0  # Reset counter on successful session

                if max_messages is not None and total_messages >= max_messages:
                    break

            except ConnectionError as exc:
                self.logger.warning(
                    "Connection lost (%s). Reconnecting in %.1fs...",
                    exc,
                    self.reconnect_delay,
                )
                reconnect_attempts += 1
                if max_reconnects is not None and reconnect_attempts >= max_reconnects:
                    self.logger.error(
                        "Reached maximum reconnect attempts (%d). Exiting.",
                        max_reconnects,
                    )
                    break

                # Wait before reconnecting, respecting stop_event if provided
                if stop_event:
                    if stop_event.wait(timeout=self.reconnect_delay):
                        break
                else:
                    try:
                        time.sleep(self.reconnect_delay)
                    except KeyboardInterrupt:
                        self.logger.info("Cancelled by user.")
                        raise

            except KeyboardInterrupt:
                self.logger.info("Cancelled by user.")
                raise
            except Exception:
                self.logger.exception(
                    "Unexpected exception occurred in ObserverClient:"
                )
                raise


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for observerclient.

    Format: python observerclient.py {-s=hostname} {-p=port} {-o=output.json}{-v}
    """
    parser = argparse.ArgumentParser(
        description="ObserverClient: Subscribe to CorporateData updates via TCP socket."
    )
    parser.add_argument(
        "-s",
        "--server",
        "--hostname",
        dest="hostname",
        default="localhost",
        help="Server hostname or IP (default: localhost)",
    )
    parser.add_argument(
        "-p",
        "--port",
        dest="port",
        type=int,
        default=8080,
        help="Server TCP port (default: 8080)",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output",
        default=None,
        help="Path to output JSON file (optional)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        help="Enable verbose debug logging to stdout",
    )
    parser.add_argument(
        "--reconnect-delay",
        dest="reconnect_delay",
        type=float,
        default=30.0,
        help="Seconds to wait before reconnecting after connection loss (default: 30.0)",
    )

    parsed = parser.parse_args(args)
    if parsed.port <= 0 or parsed.port > 65535:
        parser.error(
            f"Invalid port number: {parsed.port}. Must be between 1 and 65535."
        )
    return parsed


def main(args: list[str] | None = None) -> None:
    """CLI entry point for observerclient."""
    parsed = parse_args(args)
    client = ObserverClient(
        host=parsed.hostname,
        port=parsed.port,
        output_file=parsed.output,
        verbose=parsed.verbose,
        reconnect_delay=parsed.reconnect_delay,
    )
    try:
        client.start()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
