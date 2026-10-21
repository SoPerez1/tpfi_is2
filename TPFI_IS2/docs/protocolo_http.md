# Protocolo HTTP del TPFI

Los tres programas utilizan HTTP/1.1 sobre sockets TCP. Todas las operaciones
se envían mediante `POST /` con `Content-Type: application/json`, `Host` y
`Content-Length` calculado sobre los bytes UTF-8. El cuerpo conserva los campos
`ACTION`, `UUID`, `SESSION_ID`, `ID` y los datos corporativos de la consigna.

## Consultas y modificaciones

Para `get`, `set` y `list`, el servidor responde un documento JSON con
`Content-Length` y cierra la conexión al completar la respuesta. Devuelve
`200 OK` cuando la operación tiene éxito y `400 Bad Request` con un objeto
`{"Error": "..."}` cuando la operación no es válida o el registro no existe.

Ejemplo de consulta desde un cliente HTTP estándar:

```bash
curl -i http://localhost:8080/ \
  -H 'Content-Type: application/json' \
  --data '{"ACTION":"list","UUID":"demo","SESSION_ID":"sesion-demo"}'
```

El servidor rechaza otros métodos con `405` y `Allow: POST`, rutas desconocidas
con `404`, longitud ausente o duplicada con `411`, cuerpos mayores que 1 MiB o
longitudes negativas con `413` y tipos de contenido incorrectos con `415`.
Los cuerpos JSON malformados, incompletos o que no sean objetos reciben `400`.
Las solicitudes deben usar `Content-Length`; no se aceptan solicitudes chunked.
El servidor limita a diez segundos la lectura de cada solicitud.

## Suscripción y notificaciones

La acción `subscribe` también se envía mediante `POST /`. La respuesta es
`200 OK` con `Content-Type: application/x-ndjson; charset=utf-8` y
`Cache-Control: no-store`. El cuerpo es una secuencia de objetos JSON, uno por
línea. La primera línea confirma la suscripción:

```json
{"status":"subscribed"}
```

Después se envía el registro completo actualizado por cada `set` exitoso.
Una misma respuesta puede transportar muchas notificaciones y permanece abierta
mientras dure la suscripción. La confirmación se consume en `subscribe()`;
solo las actualizaciones se muestran en consola y se guardan en el archivo.

```bash
curl -N http://localhost:8080/ \
  -H 'Content-Type: application/json' \
  --data '{"ACTION":"subscribe","UUID":"demo","SESSION_ID":"sesion-demo"}'
```

La respuesta del observador usa delimitación por cierre: omite `Content-Length`
y `Transfer-Encoding`, declara `Connection: close` y termina cuando se cierra
el socket. Ese encabezado indica que la conexión no se reutiliza para otra
petición; no exige cerrar antes de terminar el cuerpo transmitido. Así se
implementa la respuesta persistente solicitada sin convertirla en múltiples
respuestas HTTP ni concatenar documentos JSON sin delimitador.

El cliente utiliza el lector HTTP de la biblioteca estándar, conserva los bytes
que lleguen junto con los encabezados y decodifica cada línea completa. Esto
permite recibir varias líneas juntas o caracteres UTF-8 repartidos entre paquetes.

Si la conexión termina, `ObserverClient` cierra la respuesta, espera el intervalo
configurado (30 segundos por defecto), vuelve a conectarse y realiza otro POST de
suscripción. No se almacenan ni se recuperan eventos ocurridos durante la desconexión.

## Ejecución y compatibilidad

Se conservan los argumentos CLI y los archivos JSON de entrada existentes.
Clientes y servidor deben actualizarse juntos: el intercambio anterior de JSON
directo sobre TCP ya no es aceptado por el servidor.

El backend puede ser DynamoDB o memoria (`TPFI_USE_MEMORY=1`); esta decisión
no modifica el protocolo ni los patrones Proxy, Singleton y Observer.

Las pruebas usan tanto sockets como `http.client.HTTPConnection` para verificar
respuestas finitas, múltiples eventos, errores HTTP, reconexión y UTF-8 fragmentado.
La validación local usa memoria; no demuestra acceso real a las tablas AWS.
