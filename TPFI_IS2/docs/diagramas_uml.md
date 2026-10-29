# Diagramas UML

Estos diagramas describen los flujos implementados de Proxy y Observer; no
son capturas de una prueba AWS. Véanse las [instrucciones de uso](usage.md) y
el [informe de implementación](informe_tpfi.md) para la ejecución y su evidencia.

## Actividad: `get`, `set` y `list` (Proxy)

El servidor recibe y valida la solicitud JSON; el Proxy audita la operación
antes de delegar el acceso a `CorporateData`. Tras un `set` exitoso, notifica
a los clientes suscriptos además de responder al solicitante.

![Diagrama UML de actividad del Proxy](img/diagrama_actividad_proxy.png)

## Estados: suscripción y notificaciones (Observer)

El observador se suscribe, escucha las notificaciones NDJSON de cambios y
vuelve a intentar la suscripción cuando se interrumpe la conexión. El diagrama
representa también las transiciones por notificación, desconexión y fallo de
envío.

![Diagrama UML de estados del Observer](img/diagrama_estado_observer.png)
