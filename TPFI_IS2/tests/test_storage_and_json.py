"""Pruebas unitarias adicionales para storage, json_util y observer_client."""

from __future__ import annotations

import socket
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tpfi_is2.corporate_fields import CORPORATE_DATA_FIELDS
from tpfi_is2.json_util import dynamodb_to_json, read_tcp_json, write_tcp_json
from tpfi_is2.observer_client import ObserverClient
from tpfi_is2.proxy_server import ProxyApplicationServer
from tpfi_is2.proxy_server import main as server_main
from tpfi_is2.storage import (
    AwsCorporateDataSingleton,
    AwsCorporateLogSingleton,
    MemoryCorporateDataGateway,
    MemoryCorporateLogGateway,
    _blank_record,
    _merge_item,
    _to_dynamo,
    default_data_gateway,
    default_log_gateway,
)


# -----------------------------------------------------------------------------
# Pruebas de json_util
# -----------------------------------------------------------------------------
def test_dynamodb_to_json_conversions() -> None:
    """Verifica conversión de tipos Decimal a int/float y estructuras anidadas."""
    assert dynamodb_to_json(Decimal("10")) == 10
    assert dynamodb_to_json(Decimal("10.5")) == 10.5
    assert dynamodb_to_json("texto") == "texto"
    assert dynamodb_to_json({"a": Decimal("2"), "b": [Decimal("3.5")]}) == {
        "a": 2,
        "b": [3.5],
    }


def test_read_tcp_json_empty_raises_error() -> None:
    """read_tcp_json lanza ValueError si la conexión no envía datos."""
    mock_sock = MagicMock()
    mock_sock.recv.return_value = b""
    with pytest.raises(ValueError, match="Empty request"):
        read_tcp_json(mock_sock)


def test_read_tcp_json_newline_and_direct() -> None:
    """read_tcp_json procesa JSON con o sin delimitador de línea."""
    # Con salto de línea
    mock_sock1 = MagicMock()
    mock_sock1.recv.side_effect = [b'{"ACTION": "list"}\n']
    assert read_tcp_json(mock_sock1) == {"ACTION": "list"}

    # Sin salto de línea (bloque completo)
    mock_sock2 = MagicMock()
    mock_sock2.recv.side_effect = [b'{"ACTION": "list"}', b""]
    assert read_tcp_json(mock_sock2) == {"ACTION": "list"}


def test_write_tcp_json() -> None:
    """write_tcp_json envía los bytes y cierra el extremo de escritura."""
    mock_sock = MagicMock()
    write_tcp_json(mock_sock, {"ok": True})
    mock_sock.sendall.assert_called_once()
    mock_sock.shutdown.assert_called_once_with(socket.SHUT_WR)


# -----------------------------------------------------------------------------
# Pruebas de storage helpers y singletons
# -----------------------------------------------------------------------------
def test_storage_blank_and_merge() -> None:
    """Verifica inicialización en blanco y mezcla de campos corporativos."""
    blank = _blank_record("REG-1")
    assert blank["id"] == "REG-1"
    for field in CORPORATE_DATA_FIELDS:
        assert field in blank
        assert blank[field] == ""

    # Merge con registro nuevo
    merged = _merge_item(None, "REG-1", {"domicilio": "Urquiza 100", "ignorar": 123})
    assert merged["id"] == "REG-1"
    assert merged["domicilio"] == "Urquiza 100"
    assert "ignorar" not in merged

    # Merge con registro existente
    existing = {"id": "REG-1", "domicilio": "Urquiza 100", "cp": "3260"}
    merged2 = _merge_item(existing, "REG-1", {"domicilio": "San Martin 200"})
    assert merged2["domicilio"] == "San Martin 200"
    assert merged2["cp"] == "3260"


def test_storage_to_dynamo() -> None:
    """_to_dynamo convierte números con punto flotante a Decimal."""
    data = {"seq": 1, "ratio": 3.14, "name": "FCyT"}
    dynamo_data = _to_dynamo(data)
    assert isinstance(dynamo_data["ratio"], Decimal)
    assert dynamo_data["name"] == "FCyT"


def test_gateways_environment_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    """default_data_gateway y default_log_gateway devuelven instancias correctas."""
    monkeypatch.setenv("TPFI_USE_MEMORY", "1")
    assert isinstance(default_data_gateway(), MemoryCorporateDataGateway)
    assert isinstance(default_log_gateway(), MemoryCorporateLogGateway)


def test_aws_singletons_with_mock() -> None:
    """Verifica que las clases AwsCorporateDataSingleton y AwsCorporateLogSingleton sigan el patrón Singleton."""
    mock_boto3 = MagicMock()
    mock_table = MagicMock()
    mock_boto3.resource.return_value.Table.return_value = mock_table

    with patch.dict("sys.modules", {"boto3": mock_boto3}):
        # Reset de instancias privadas para la prueba
        AwsCorporateDataSingleton._instance = None
        AwsCorporateLogSingleton._instance = None

        inst1 = AwsCorporateDataSingleton.instance()
        inst2 = AwsCorporateDataSingleton.instance()
        assert inst1 is inst2

        log1 = AwsCorporateLogSingleton.instance()
        log2 = AwsCorporateLogSingleton.instance()
        assert log1 is log2

        # Prueba de get_record y put_record con mock
        mock_table.get_item.return_value = {"Item": {"id": "1", "sede": "FCyT"}}
        rec = inst1.get_record("1")
        assert rec == {"id": "1", "sede": "FCyT"}

        mock_table.scan.return_value = {"Items": [{"id": "1"}]}
        items = inst1.list_records()
        assert len(items) == 1

        inst1.merge_record("1", {"sede": "Nueva Sede"})
        mock_table.put_item.assert_called()

        log1.write_audit(cpu_uuid="cpu1", session_id="s1", action="test", record_id="1")
        mock_table.put_item.assert_called()


# -----------------------------------------------------------------------------
# Pruebas de observer_client
# -----------------------------------------------------------------------------
def test_observer_client_edge_cases(tmp_path: Path) -> None:
    """Verifica casos borde y manejo de desconexión en ObserverClient."""
    client = ObserverClient()
    # Sin socket conectado:
    assert client.subscribe() is False
    assert client.listen() is False

    # Escritura de log en archivo de salida
    log_file = tmp_path / "obs_out.json"
    client_with_file = ObserverClient(output_file=log_file)
    client_with_file.notify({"status": "event"})
    assert log_file.exists()
    assert "event" in log_file.read_text(encoding="utf-8")

    # Detener ejecución de cliente
    client.running = True
    client.stop()
    assert client.running is False


# -----------------------------------------------------------------------------
# Pruebas de proxy_server
# -----------------------------------------------------------------------------
def test_proxy_server_unknown_action() -> None:
    """El servidor responde con error si la acción no es get, set, list o subscribe."""
    server = ProxyApplicationServer()
    mock_conn = MagicMock()
    server.handle_request({"ACTION": "accion_desconocida"}, mock_conn)
    mock_conn.sendall.assert_called_once()
    payload_sent = mock_conn.sendall.call_args[0][0].decode("utf-8")
    assert "Unknown ACTION" in payload_sent


# -----------------------------------------------------------------------------
# Pruebas de CLI boilerplate y ObserverClient listen
# -----------------------------------------------------------------------------
def test_proxy_server_main_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica que el punto de entrada CLI del servidor parsee los argumentos."""
    with patch.object(ProxyApplicationServer, "serve_forever", return_value=None):
        monkeypatch.setattr("sys.argv", ["singletonproxyobserver.py", "-p", "8888", "-v"])
        server_main()


def test_observer_client_listen_closed() -> None:
    """ObserverClient.listen retorna False si el servidor cierra la conexión."""
    client = ObserverClient()
    mock_sock = MagicMock()
    mock_sock.recv.return_value = b""
    client.socket = mock_sock
    client.running = True
    assert client.listen() is False
