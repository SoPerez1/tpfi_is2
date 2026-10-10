# Implementación de ObserverClient

## 1. Objetivo

Implementar un cliente TCP capaz de suscribirse a un servidor y recibir notificaciones cuando se producen cambios en los datos.

Este componente forma parte del trabajo práctico final de Ingeniería de Software II.

## 2. Tecnologías utilizadas

- Python 3.10
- Sockets TCP/IP
- JSON
- Pytest
- Patrón de diseño Observer

## 3. Implementación

### Paso 1 — Inicialización

Se creó la clase `ObserverClient` en `src/tpfi_is2/observer_client.py`.

El constructor `__init__()` inicializa la dirección del servidor, el puerto, el socket y los identificadores del cliente.

### Paso 2 — Conexión TCP

Se implementó el método `connect()`, que crea un socket TCP e intenta establecer una conexión con el servidor.

Se incorporó un manejo básico de errores para las conexiones fallidas.

### Paso 3 — Prueba inicial de conexión

Se utilizó un servidor HTTP temporal en `localhost:8080` para verificar la conexión TCP.

El cliente mostró el mensaje `Conectado al servidor`.

**Resultado:** conexión TCP exitosa.

Durante la primera ejecución se corrigió un problema de indentación del método `connect()`.

### Paso 4 — Desconexión

Se implementó `disconnect()` para cerrar el socket y liberar la conexión.

### Paso 5 — Suscripción

Se implementó `subscribe()` para enviar un mensaje JSON al servidor.

El mensaje contiene:

- `ACTION`: operación solicitada.
- `UUID`: identificador del cliente.
- `SESSION_ID`: identificador de sesión.

Se propuso utilizar la acción `subscribe`.

**Pendiente:** confirmar el formato del mensaje con el equipo.

### Paso 6 — Recepción de notificaciones

Se implementó `listen()` para recibir mensajes mediante el socket TCP.

Los mensajes se procesan como JSON y se muestran mediante `notify()`.

Se propone utilizar un salto de línea como separador entre mensajes.

### Paso 7 — Reconexión automática

Se implementó `run()` para coordinar la conexión, la suscripción y la recepción de notificaciones.

Cuando se pierde la conexión, el cliente espera cinco segundos antes de intentar conectarse nuevamente.

Después de reconectarse, vuelve a enviar la solicitud de suscripción.

### Paso 8 — Detención del cliente

Se implementó `stop()` para detener la ejecución y cerrar el socket.

También se contempla la interrupción manual mediante Ctrl + C.

## 4. Pruebas

Se creó `tests/test_observer_client.py` con pruebas para:

1. Inicialización del cliente.
2. Conexión y desconexión TCP.
3. Envío del mensaje de suscripción.
4. Visualización de notificaciones.

Comando de ejecución:

`PYTHONPATH=src python -m pytest tests/test_observer_client.py -v`

**Resultado de pruebas automáticas:** pendiente de registrar.

## 5. Integración pendiente

Antes de integrar el componente con el servidor real, se debe acordar con el equipo:

- Formato JSON de suscripción.
- Formato JSON de notificaciones.
- Confirmación de suscripción.
- Separación de mensajes TCP.
- Manejo de desconexiones y suscripciones.

También se deben probar la recepción continua de notificaciones y la reconexión automática.

## 6. Conclusión

Se preparó una implementación inicial de ObserverClient que permite conectarse mediante TCP, solicitar una suscripción, escuchar mensajes JSON y reintentar la conexión ante interrupciones.

La conexión TCP inicial fue comprobada. La validación completa de las funcionalidades restantes y la integración con el servidor real continúan pendientes.

**Resultado de las pruebas automáticas:**

Se ejecutaron las pruebas utilizando Pytest.

- Inicialización del cliente: PASSED.
- Conexión y desconexión TCP: PASSED.
- Envío de suscripción: PASSED.
- Visualización de notificaciones: PASSED.

**Resultado final: 4 pruebas aprobadas en 0,10 segundos.**

Las pruebas se realizaron utilizando servidores TCP simulados, sin depender del servidor real ni de AWS.

Quedan pendientes las pruebas de recepción continua, reconexión automática e integración con el servidor del equipo.