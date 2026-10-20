# Diagramas UML

Estos diagramas documentan los flujos principales de los patrones Proxy y
Observer implementados en el servidor.

## Diagrama de actividad: gestion de `get`, `set` y `list` (Proxy)

Muestra el recorrido de una solicitud desde que el servidor recibe y valida el
JSON hasta que registra la auditoria, ejecuta la operacion sobre `CorporateData`
y responde al cliente. En una modificacion exitosa (`set`), tambien se notifica
a los clientes suscriptos.

![Diagrama de actividad del servidor para get, set y list](img/diagrama_actividad_proxy.png)

## Diagrama de estados: suscripciones y notificaciones (Observer)

Representa los estados de una suscripcion y los eventos que producen las
transiciones: suscripcion, notificacion de un cambio y desconexion o fallo de
envio.

![Diagrama de estados de una suscripcion](img/diagrama_estado_observer.png)
