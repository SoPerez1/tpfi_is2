import json
import socket
import time
import uuid


class ObserverClient:
    # Cliente que se suscribe y recibe notificaciones del servidor

    def __init__(self, host="localhost", port=8080):
        self.host = host
        self.port = port
        self.socket = None
        self.uuid = str(uuid.getnode())
        self.session_id = str(uuid.uuid4())
        self.running = False

    def connect(self):
        # Establece una conexión TCP con el servidor
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print("Conectado al servidor")
            return True

        except OSError as error:
            print(f"Error de conexión: {error}")
            self.disconnect()
            return False

    def disconnect(self):
        # Cierra la conexión TCP
        if self.socket is not None:
            self.socket.close()
            self.socket = None
            print("Desconectado del servidor")

    def subscribe(self):
        # Envía una solicitud de suscripción al servidor
        if self.socket is None:
            print("No hay conexión con el servidor")
            return False

        request = {
            "ACTION": "subscribe",
            "UUID": self.uuid,
            "SESSION_ID": self.session_id
        }

        try:
            message = json.dumps(request) + "\n"
            self.socket.sendall(message.encode("utf-8"))
            print("Solicitud de suscripción enviada")
            return True

        except OSError as error:
            print(f"Error al suscribirse: {error}")
            self.disconnect()
            return False

    def listen(self):
        # Escucha mensajes y notificaciones del servidor
        if self.socket is None:
            return False

        buffer = ""

        try:
            while self.running:
                data = self.socket.recv(4096)

                if not data:
                    print("El servidor cerró la conexión")
                    return False

                buffer += data.decode("utf-8")

                # Procesa los mensajes JSON completos
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)

                    if not line.strip():
                        continue

                    try:
                        notification = json.loads(line)
                        self.notify(notification)

                    except json.JSONDecodeError:
                        print("Se recibió un mensaje JSON inválido")

        except (OSError, UnicodeDecodeError) as error:
            print(f"Error al recibir notificaciones: {error}")
            return False

        return True

    def notify(self, notification):
        # Muestra las notificaciones recibidas
        print(f"Notificación recibida: {notification}")

    def run(self):
        # Conecta, se suscribe y escucha notificaciones
        self.running = True

        while self.running:
            if self.connect():
                if self.subscribe():
                    self.listen()

                self.disconnect()

            if self.running:
                print("Reintentando conexión en 5 segundos...")
                time.sleep(5)

    def stop(self):
        # Detiene el cliente y cierra la conexión
        self.running = False
        self.disconnect()


if __name__ == "__main__":
    client = ObserverClient()

    try:
        client.run()

    except KeyboardInterrupt:
        print("\nCliente detenido")
        client.stop()