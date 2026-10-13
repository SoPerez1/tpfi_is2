"""TCP application server: Proxy + Singleton DB access + Observer notifications."""

from __future__ import annotations

import argparse
import json
import logging
import socket
import sys
import threading
from typing import Any

from tpfi_is2.corporate_fields import has_corporate_updates
from tpfi_is2.json_util import read_tcp_json, write_tcp_json
from tpfi_is2.observer import CorporateDataObserver
from tpfi_is2.proxy import CorporateDataProxy
from tpfi_is2.storage import CorporateLogGateway


class ProxyApplicationServer:
    """SingletonProxyObserverTPFI: one JSON request per connection (except subscribe)."""

    def __init__(
        self,
        host: str = "0.0.0.0",  # nosec B104
        port: int = 8080,
        *,
        proxy: CorporateDataProxy | None = None,
        observer: CorporateDataObserver | None = None,
        log_gateway: CorporateLogGateway | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self._proxy = proxy or CorporateDataProxy()
        self._observer = observer or CorporateDataObserver()
        self._log = log_gateway
        self._listen: socket.socket | None = None
        self._running = False

    def handle_request(
        self,
        payload: dict[str, Any],
        conn: socket.socket,
    ) -> None:
        # Obtiene los datos de la solicitud
        action = payload.get("ACTION")
        cpu_uuid = str(payload.get("UUID", ""))
        session_id = str(payload.get("SESSION_ID", ""))

        # Suscribe un cliente para recibir notificaciones
        if action == "subscribe":
            self._handle_subscribe(conn, cpu_uuid, session_id)
            return

        # Consulta un registro
        if action == "get":
            record_id = payload.get("ID")

            if not record_id:
                write_tcp_json(conn, {"Error": "get requires ID"})
                return

            response = self._proxy.get(
                cpu_uuid=cpu_uuid,
                session_id=session_id,
                record_id=str(record_id),
            )

            write_tcp_json(conn, response)
            return

        # Lista los registros
        if action == "list":
            response = self._proxy.list_all(
                cpu_uuid=cpu_uuid,
                session_id=session_id,
            )

            write_tcp_json(conn, response)
            return

        # Modifica los datos de un registro
        if action == "set":
            record_id = payload.get("ID")

            if not record_id:
                write_tcp_json(conn, {"Error": "set requires ID"})
                return

            if not has_corporate_updates(payload):
                write_tcp_json(
                    conn,
                    {"Error": "set requires at least one CorporateData field"},
                )
                return

            response = self._proxy.set_fields(
                cpu_uuid=cpu_uuid,
                session_id=session_id,
                record_id=str(record_id),
                payload=payload,
            )

            write_tcp_json(conn, response)

            # Notifica a los observadores si la modificación fue exitosa
            if "Error" not in response:
                self._observer.notify(response)

            return

        # Responde si la acción no existe
        write_tcp_json(
            conn,
            {"Error": f"Unknown ACTION: {action!r}"},
        )

    def _handle_subscribe(
        self,
        conn: socket.socket,
        cpu_uuid: str,
        session_id: str,
    ) -> None:
        # Obtiene el servicio de auditoría
        log = self._log

        if log is None:
            from tpfi_is2.storage import default_log_gateway

            log = default_log_gateway()

        # Registra la suscripción
        log.write_audit(
            cpu_uuid=cpu_uuid,
            session_id=session_id,
            action="subscribe",
        )

        # Agrega el cliente a la lista de observadores
        self._observer.subscribe(conn, cpu_uuid)

        # Confirma la suscripción
        conn.sendall(
            json.dumps(
                {"status": "subscribed"},
                ensure_ascii=False,
            ).encode("utf-8")
            + b"\n"
        )

        try:
            # Mantiene la conexión mientras el cliente esté conectado
            while conn.recv(4096):
                pass

        except OSError:
            pass

        finally:
            # Elimina al observador cuando se desconecta
            self._observer.unsubscribe(conn)
            conn.close()

    def _client_thread(
        self,
        conn: socket.socket,
        _address: tuple[str, int],
    ) -> None:
        try:
            # Recibe la solicitud JSON
            payload = read_tcp_json(conn)

            logging.debug("Request %s", payload)

            # Procesa la solicitud
            self.handle_request(payload, conn)

        except (ValueError, json.JSONDecodeError) as exc:
            logging.debug("Bad request: %s", exc)

            try:
                write_tcp_json(conn, {"Error": str(exc)})
            except OSError:
                pass

        except OSError as exc:
            logging.debug("Connection error: %s", exc)

        finally:
            try:
                conn.close()
            except OSError:
                pass

    def serve_forever(self) -> None:
        # Crea el socket TCP del servidor
        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        # Configura el socket según el sistema operativo
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_EXCLUSIVEADDRUSE,
                1,
            )
        else:
            sock.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEADDR,
                1,
            )

        # Asocia el servidor al host y puerto
        try:
            sock.bind((self.host, self.port))

        except OSError as exc:
            raise SystemExit(f"Error: cannot bind {self.host}:{self.port} ({exc})") from exc

        self.port = int(sock.getsockname()[1])

        # Comienza a escuchar conexiones
        sock.listen()

        self._listen = sock
        self._running = True

        logging.info(
            "Proxy server listening on %s:%s",
            self.host,
            self.port,
        )

        # Acepta conexiones de clientes
        while self._running:
            try:
                conn, address = sock.accept()

            except OSError:
                break

            # Atiende cada cliente en un hilo independiente
            threading.Thread(
                target=self._client_thread,
                args=(conn, address),
                daemon=True,
            ).start()

    def shutdown(self) -> None:
        # Detiene el servidor
        self._running = False

        if self._listen is not None:
            try:
                self._listen.close()
            except OSError:
                pass

            self._listen = None


def main() -> None:
    # Configura los argumentos de ejecución
    parser = argparse.ArgumentParser(description="SingletonProxyObserverTPFI application server.")

    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8080,
        help="TCP port (default 8080)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="debug logging on stdout",
    )

    args = parser.parse_args()

    # Activa los mensajes de depuración
    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            stream=sys.stdout,
            force=True,
        )

    # Inicia el servidor
    ProxyApplicationServer(
        port=args.port,
    ).serve_forever()


if __name__ == "__main__":
    main()
