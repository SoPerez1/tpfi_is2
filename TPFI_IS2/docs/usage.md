# Uso local de los tres programas

Ejecutar desde la raíz `TPFI_IS2` con Python y las dependencias del proyecto
instaladas. Para probar sin AWS, definir `TPFI_USE_MEMORY=1` en el entorno
**del servidor**; los clientes se comunican por HTTP POST con ese servidor.
El almacenamiento en memoria se pierde cuando termina el proceso.

```bash
export TPFI_USE_MEMORY=1
python singletonproxyobserver.py -p=8080 -v
```

En otra terminal, iniciar la suscripción (Ctrl+C la detiene):

```bash
python observerclient.py -s=localhost -p=8080 -v
```

En una tercera terminal, usar los archivos JSON incluidos como ejemplos:

```bash
python singletonclient.py -i=prueba_set.json -v
python singletonclient.py -i=prueba_get.json
python singletonclient.py -i=prueba_list.json
```

`set` necesita `ID` y al menos un campo corporativo; `get` necesita `ID` y
`list` no lo necesita. El cliente agrega `UUID` y `SESSION_ID`; el servidor
registra la auditoría y envía actualizaciones de `set` a los observadores.
`-o=salida.json` guarda la respuesta del cliente de operaciones o las
notificaciones del observador; `--retry-interval=30` ajusta la reconexión del
observador. Los tres programas admiten `--version` sin iniciar conexiones.

Para el contrato de solicitudes y respuestas, véase [protocolo HTTP](protocolo_http.md).
Para clases y métodos, véase la [API generada](api.md). Los resultados de
la prueba manual en DynamoDB y sus límites están en [validación AWS](validacion_aws.md).
