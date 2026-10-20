"""Casos de prueba de aceptación y validación requeridos por la consigna TPFI.

Este archivo agrupa de forma clara, sencilla y didáctica los 5 casos de prueba
exigidos en la sección 'Validación y Verificación' del Trabajo Práctico:

1. Camino feliz de cada una de las acciones (get, set, list, subscribe) con auditoría.
2. Intento de llamar a los programas con argumentos malformados.
3. Intento de requerimientos sin los datos mínimos obligatorios.
4. Manejo en clientes cuando el servidor aplicativo se encuentra caído.
5. Intento de levantar dos instancias del servidor en el mismo puerto.
"""

from __future__ import annotations

import json
import socket
import sys
import threading
import time

import pytest

from tpfi_is2.http_transport import open_response, send_post
from tpfi_is2.observer_client import ObserverClient
from tpfi_is2.observer_client import main as observer_main
from tpfi_is2.proxy import CorporateDataProxy
from tpfi_is2.proxy_server import ProxyApplicationServer
from tpfi_is2.proxy_server import main as server_main
from tpfi_is2.singleton_client import SingletonClient
from tpfi_is2.singleton_client import main as singleton_main
from tpfi_is2.storage import MemoryCorporateDataGateway, MemoryCorporateLogGateway


# -----------------------------------------------------------------------------
# Fixtures para servidor de pruebas en memoria
# -----------------------------------------------------------------------------
@pytest.fixture
def running_server(monkeypatch: pytest.MonkeyPatch):
    """Inicia un servidor de pruebas en memoria en un puerto libre efímero."""
    monkeypatch.setenv("TPFI_USE_MEMORY", "1")
    MemoryCorporateDataGateway.reset()
    MemoryCorporateLogGateway.reset()

    data_gateway = MemoryCorporateDataGateway.instance()
    log_gateway = MemoryCorporateLogGateway.instance()
    proxy = CorporateDataProxy(data=data_gateway, log=log_gateway)

    server = ProxyApplicationServer(
        host="127.0.0.1",
        port=0,  # 0 indica que el S.O. asignará un puerto disponible automáticamente
        proxy=proxy,
        log_gateway=log_gateway,
    )

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)  # Breve pausa para asegurar que el socket esté listo

    yield "127.0.0.1", server.port

    server.shutdown()
    thread.join(timeout=1)


# =============================================================================
# CASO 1: Camino feliz de cada acción (get, set, list, subscribe) con auditoría
# =============================================================================
def test_caso_1_camino_feliz_y_auditoria(running_server: tuple[str, int]) -> None:
    """Verifica que get, set, list y subscribe funcionen y dejen registro en CorporateLog."""
    host, port = running_server
    client = SingletonClient(host=host, port=port)
    log_gateway = MemoryCorporateLogGateway.instance()

    # 1. Acción 'set': Crear/actualizar un registro corporativo
    req_set = client.build_request(
        {
            "ACTION": "set",
            "ID": "FCYT-01",
            "sede": "FCyT Central",
            "localidad": "Concepción del Uruguay",
            "telefono": "03442 43-1442",
        }
    )
    res_set = client.send(req_set)
    assert res_set["id"] == "FCYT-01"
    assert res_set["sede"] == "FCyT Central"

    # 2. Acción 'get': Recuperar el registro creado
    req_get = client.build_request({"ACTION": "get", "ID": "FCYT-01"})
    res_get = client.send(req_get)
    assert res_get["id"] == "FCYT-01"
    assert res_get["sede"] == "FCyT Central"

    # 3. Acción 'list': Listar todos los registros de la base
    req_list = client.build_request({"ACTION": "list"})
    res_list = client.send(req_list)
    assert isinstance(res_list, list)
    assert len(res_list) >= 1
    assert any(item["id"] == "FCYT-01" for item in res_list)

    # 4. Acción 'subscribe': Un cliente Observer se suscribe exitosamente
    observer = ObserverClient(host=host, port=port)
    assert observer.connect() is True
    assert observer.subscribe() is True
    # Wait for the server to persist the audit entry and acknowledge subscription.
    assert observer.socket is not None
    observer.socket.settimeout(2)
    observer.disconnect()

    # 5. Auditoría: Verificar que todas las acciones impactaron en la tabla CorporateLog
    acciones_registradas = [entry["action"] for entry in log_gateway.entries]
    assert "set" in acciones_registradas
    assert "get" in acciones_registradas
    assert "list" in acciones_registradas
    assert "subscribe" in acciones_registradas


# =============================================================================
# CASO 2: Llamada a los programas con argumentos malformados
# =============================================================================
def test_caso_2_argumentos_malformados_singleton_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica que SingletonClient falle limpiamente ante argumentos CLI inválidos."""
    # Falta el argumento obligatorio -i/--input
    monkeypatch.setattr(sys, "argv", ["singletonclient.py"])
    with pytest.raises(SystemExit) as exc:
        singleton_main()
    assert exc.value.code == 2

    # Argumento desconocido o puerto no numérico
    monkeypatch.setattr(sys, "argv", ["singletonclient.py", "-i", "in.json", "-p", "no_es_numero"])
    with pytest.raises(SystemExit) as exc:
        singleton_main()
    assert exc.value.code == 2


def test_caso_2_argumentos_malformados_observer_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica que ObserverClient falle limpiamente ante argumentos CLI inválidos."""
    # Puerto que no es número entero
    monkeypatch.setattr(sys, "argv", ["observerclient.py", "-p", "puerto_invalido"])
    with pytest.raises(SystemExit) as exc:
        observer_main()
    assert exc.value.code == 2

    # Opción no reconocida
    monkeypatch.setattr(sys, "argv", ["observerclient.py", "--opcion-inexistente"])
    with pytest.raises(SystemExit) as exc:
        observer_main()
    assert exc.value.code == 2


def test_caso_2_argumentos_malformados_servidor(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica que el Servidor falle limpiamente ante argumentos CLI inválidos."""
    # Puerto que no es número entero
    monkeypatch.setattr(sys, "argv", ["singletonproxyobserver.py", "-p", "texto_invalido"])
    with pytest.raises(SystemExit) as exc:
        server_main()
    assert exc.value.code == 2


# =============================================================================
# CASO 3: Requerimientos sin indicar los datos mínimos necesarios
# =============================================================================
def test_caso_3_requerimiento_sin_datos_minimos(running_server: tuple[str, int]) -> None:
    """Verifica el rechazo de peticiones cuando faltan datos obligatorios."""
    host, port = running_server
    client = SingletonClient(host=host, port=port)

    # A) Acción 'get' sin indicar ID
    with pytest.raises(ValueError, match="requires an ID"):
        client.build_request({"ACTION": "get"})

    # B) Acción 'set' sin indicar ID
    with pytest.raises(ValueError, match="requires an ID"):
        client.build_request({"ACTION": "set", "sede": "FCyT"})

    # C) Acción 'set' con ID pero sin campos corporativos para modificar
    with pytest.raises(ValueError, match="CorporateData field"):
        client.build_request({"ACTION": "set", "ID": "UADER-1"})

    # D) Envío directo al servidor de un JSON con campos faltantes (por socket crudo)
    with socket.create_connection((host, port)) as sock:
        # Petición get sin ID directo al servidor
        send_post(sock, {"ACTION": "get", "UUID": "cpu1", "SESSION_ID": "s1"}, host, port)
        with open_response(sock) as response:
            assert response.status == 400
            respuesta = json.loads(response.read())
        assert "Error" in respuesta


# =============================================================================
# CASO 4: Manejo en clientes de servidor aplicativo caído
# =============================================================================
def test_caso_4_cliente_singleton_con_servidor_caido() -> None:
    """Verifica que SingletonClient maneje adecuadamente la desconexión o servidor caído."""
    # Buscamos un puerto cerrado donde no haya ningún servidor escuchando
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        puerto_cerrado = probe.getsockname()[1]

    client = SingletonClient(host="127.0.0.1", port=puerto_cerrado)
    peticion = {"ACTION": "list", "UUID": "cpu-test", "SESSION_ID": "sess-test"}

    # Debe lanzar ConnectionError informando la imposibilidad de conectarse
    with pytest.raises(ConnectionError, match="Could not connect"):
        client.send(peticion)


def test_caso_4_cliente_observer_con_servidor_caido() -> None:
    """Verifica que ObserverClient detecte el servidor caído sin fallar bruscamente."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        puerto_cerrado = probe.getsockname()[1]

    client = ObserverClient(host="127.0.0.1", port=puerto_cerrado)
    # Al intentar conectar con el server caído, connect() retorna False ordenadamente
    assert client.connect() is False
    assert client.socket is None


# =============================================================================
# CASO 5: Intento de levantar dos veces el servidor de aplicaciones
# =============================================================================
def test_caso_5_levantar_servidor_dos_veces(running_server: tuple[str, int]) -> None:
    """Verifica que el servidor rechace iniciar si el puerto ya está en uso."""
    host, port = running_server

    # Intentamos crear e iniciar una segunda instancia del servidor en el mismo puerto
    segundo_servidor = ProxyApplicationServer(host=host, port=port)

    with pytest.raises(SystemExit, match="cannot bind"):
        segundo_servidor.serve_forever()
