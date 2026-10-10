import json
import socket
import threading

from tpfi_is2.observer_client import ObserverClient


def test_initialization():
    # Verifica los valores iniciales
    client = ObserverClient()

    assert client.host == "localhost"
    assert client.port == 8080
    assert client.socket is None


def test_connection_and_disconnection():
    # Crea un servidor TCP temporal
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)

    port = server.getsockname()[1]

    def accept_connection():
        connection, _ = server.accept()
        connection.close()

    thread = threading.Thread(target=accept_connection)
    thread.start()

    client = ObserverClient(host="127.0.0.1", port=port)

    assert client.connect() is True
    assert client.socket is not None

    client.disconnect()

    assert client.socket is None

    thread.join(timeout=2)
    server.close()


def test_subscribe():
    # Comprueba el mensaje JSON de suscripción
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)

    port = server.getsockname()[1]
    messages = []

    def receive_subscription():
        connection, _ = server.accept()
        data = connection.recv(4096)
        messages.append(json.loads(data.decode("utf-8")))
        connection.close()

    thread = threading.Thread(target=receive_subscription)
    thread.start()

    client = ObserverClient(host="127.0.0.1", port=port)

    assert client.connect() is True
    assert client.subscribe() is True

    thread.join(timeout=2)

    assert len(messages) == 1
    assert messages[0]["ACTION"] == "subscribe"
    assert messages[0]["UUID"] == client.uuid
    assert messages[0]["SESSION_ID"] == client.session_id

    client.disconnect()
    server.close()


def test_notify(capsys):
    # Comprueba que se muestra una notificación
    client = ObserverClient()

    notification = {
        "EVENT": "data_updated",
        "ID": "UADER-FCYT-IS2"
    }

    client.notify(notification)

    output = capsys.readouterr().out

    assert "Notificación recibida" in output
    assert "data_updated" in output