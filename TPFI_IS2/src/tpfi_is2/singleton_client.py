# ES: Módulo SingletonClient para TPFI_IS2.
# ES: Permite consultar y modificar CorporateData mediante comunicación TCP con el servidor.
"""SingletonClient module for TPFI_IS2.

This module provides the SingletonClient class and CLI interface for querying
and modifying CorporateData via TCP socket communication with the application server.
"""

import argparse
import json
import logging
import socket
import sys
import uuid
from pathlib import Path
from typing import Any


# ES: Cliente que envía solicitudes get, set y list al servidor central de aplicaciones.
class SingletonClient:
    """Client for issuing get, set, and list requests to the central application server."""

    # ES: Inicializa el cliente. host es el nombre o IP del servidor; port, el puerto TCP;
    # ES: verbose activa los registros de depuración.
    def __init__(self, host: str = "localhost", port: int = 8080, verbose: bool = False) -> None:
        """Initialize SingletonClient with target server host and port.

        Args:
            host: Server hostname or IP address.
            port: Server TCP port number.
            verbose: Enable debug logging if True.
        """
        self.host = host
        self.port = port
        self.verbose = verbose
        self.logger = logging.getLogger(self.__class__.__name__)
        self._configure_logging()

    # ES: Configura el nivel y el formato de los registros según la opción de detalle.
    def _configure_logging(self) -> None:
        """Configure logging level and formatting based on verbosity flag."""
        log_level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )
        self.logger.setLevel(log_level)

    # ES: Devuelve como texto el identificador único del sistema basado en la dirección MAC.
    def get_system_uuid(self) -> str:
        """Retrieve hardware node MAC-based unique identifier.

        Returns:
            String representation of the unique system CPU/Node ID.
        """
        return str(uuid.getnode())

    # ES: Devuelve un identificador de sesión aleatorio en formato UUID4.
    def get_session_id(self) -> str:
        """Generate a unique random session identifier.

        Returns:
            UUID4 session string.
        """
        return str(uuid.uuid4())

    # ES: input_data es el contenido de la solicitud; devuelve el payload validado y completo.
    # ES: Lanza ValueError si falta ACTION o su valor no es válido.
    def process_request(self, input_data: dict[str, Any]) -> Any:
        """Process and validate request payload before transmission.

        Args:
            input_data: Dictionary containing input payload.

        Returns:
            Validated payload dictionary ready to be sent to server.

        Raises:
            ValueError: If mandatory fields like ACTION are missing or invalid.
        """
        action = input_data.get("ACTION")
        if not action or action not in ("get", "set", "list"):
            raise ValueError(f"Invalid or missing ACTION: '{action}'. Must be 'get', 'set', or 'list'.")

        payload = dict(input_data)
        if "UUID" not in payload or not payload["UUID"]:
            payload["UUID"] = self.get_system_uuid()

        payload["SESSION_ID"] = self.get_session_id()
        return payload

    # ES: payload es la solicitud; devuelve el JSON recibido del servidor.
    # ES: Lanza ConnectionError si falla la conexión y RuntimeError si la respuesta no es JSON válido.
    def send_request(self, payload: dict[str, Any]) -> Any:
        """Send JSON payload over TCP socket to the server and return response.

        Args:
            payload: Request dictionary payload.

        Returns:
            Parsed JSON object received from the server.

        Raises:
            ConnectionError: If connection to server fails or times out.
            RuntimeError: If response from server cannot be parsed.
        """
        raw_json = json.dumps(payload)
        self.logger.debug("Connecting to server at %s:%d", self.host, self.port)
        self.logger.debug("Sending payload: %s", raw_json)

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.settimeout(10.0)
                client_socket.connect((self.host, self.port))
                client_socket.sendall(raw_json.encode("utf-8"))

                # Shutdown sending side to signal request end to server
                # ES: Cierra el canal de envío para indicar al servidor que terminó la solicitud.
                try:
                    client_socket.shutdown(socket.SHUT_WR)
                except OSError:
                    pass

                response_chunks: list[bytes] = []
                while True:
                    chunk = client_socket.recv(4096)
                    if not chunk:
                        break
                    response_chunks.append(chunk)

                response_bytes = b"".join(response_chunks)
                if not response_bytes:
                    raise RuntimeError("Received empty response from server.")

                response_str = response_bytes.decode("utf-8")
                self.logger.debug("Received raw response: %s", response_str)
                return json.loads(response_str)

        except (socket.error, socket.timeout) as exc:
            self.logger.error("Network error connecting to %s:%d - %s", self.host, self.port, exc)
            raise ConnectionError(f"Could not connect to server {self.host}:{self.port}") from exc
        except json.JSONDecodeError as exc:
            self.logger.error("Failed to parse response JSON: %s", exc)
            raise RuntimeError("Invalid JSON response received from server") from exc

    # ES: input_path indica el archivo de solicitud; output_path es opcional y señala dónde guardar la respuesta.
    # ES: Si output_path no se especifica, escribe en la salida estándar; devuelve la respuesta del servidor.
    def execute(self, input_path: str | Path, output_path: str | Path | None = None) -> Any:
        """Execute request defined in input JSON file and output results.

        Args:
            input_path: Path to input JSON file.
            output_path: Optional path to output file. Writes to stdout if None.

        Returns:
            Parsed response received from server.
        """
        path_in = Path(input_path)
        if not path_in.exists():
            raise FileNotFoundError(f"Input file not found: {path_in}")

        self.logger.info("Reading request from %s", path_in)
        with open(path_in, "r", encoding="utf-8") as file:
            input_data = json.load(file)

        payload = self.process_request(input_data)
        response = self.send_request(payload)

        formatted_response = json.dumps(response, indent=2, ensure_ascii=False)

        if output_path:
            path_out = Path(output_path)
            self.logger.info("Writing response to %s", path_out)
            with open(path_out, "w", encoding="utf-8") as file:
                file.write(formatted_response + "\n")
        else:
            print(formatted_response)

        return response


# ES: Punto de entrada de la interfaz de línea de comandos (CLI).
def main() -> None:
    """CLI entry point for singletonclient."""
    parser = argparse.ArgumentParser(
        description="SingletonClient: Query and update CorporateData via TCP Socket server."
    )
    parser.add_argument("-i", "--input", required=True, help="Path to input JSON file")
    parser.add_argument("-o", "--output", required=False, default=None, help="Path to output JSON file (optional)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")
    parser.add_argument("-s", "--server", default="localhost", help="Server hostname (default: localhost)")
    parser.add_argument("-p", "--port", type=int, default=8080, help="Server port (default: 8080)")

    args = parser.parse_args()

    client = SingletonClient(host=args.server, port=args.port, verbose=args.verbose)
    try:
        client.execute(input_path=args.input, output_path=args.output)
    except Exception as exc:
        if args.verbose:
            logging.exception("Error executing SingletonClient:")
        else:
            sys.stderr.write(f"Error: {exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
