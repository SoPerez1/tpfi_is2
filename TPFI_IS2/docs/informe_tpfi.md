# Informe de implementación del TPFI IS2

El sistema implementa Proxy, Singleton y Observer con transporte HTTP POST sobre
sockets TCP. La validación local usa memoria: **no constituye evidencia de
conexión ni de escritura en AWS DynamoDB**.

## Componentes entregados

| Programa | Implementación actual | Responsabilidad |
| --- | --- | --- |
| `singletonproxyobserver.py` | `tpfi_is2.proxy_server.ProxyApplicationServer` | Atiende `get`, `set`, `list` y `subscribe`; audita las operaciones y notifica las modificaciones. |
| `singletonclient.py` | `tpfi_is2.singleton_client.SingletonClient` | Valida las solicitudes, agrega UUID y sesión, y envía un POST JSON. |
| `observerclient.py` | `tpfi_is2.observer_client.ObserverClient` | Se suscribe a NDJSON y vuelve a conectar tras una interrupción. |

`tpfi_is2.proxy.CorporateDataProxy` valida y audita antes del acceso a datos;
`tpfi_is2.storage` ofrece gateways en memoria y singletons para las tablas
`CorporateData` y `CorporateLog` de DynamoDB. Las consultas responden JSON y
cierran su conexión; las suscripciones mantienen una respuesta abierta con un
objeto JSON por línea. Véanse el [protocolo HTTP](protocolo_http.md), las
[instrucciones de uso](usage.md) y la [referencia de API](api.md).

## Diagramas del diseño

Los dos diagramas provistos se consultan en la página de
[diagramas UML](diagramas_uml.md): [actividad del Proxy](img/diagrama_actividad_proxy.png)
y [estados del Observer](img/diagrama_estado_observer.png).

## Evidencia local

En el entorno local Python 3.10, la suite final de esta entrega documental
terminó con **71 pruebas aprobadas en 44,87 s** y cobertura con ramas del
**89,64 %** (umbral configurado: 85 %). La prueba se ejecutó con
el gateway en memoria; no prueba la disponibilidad ni los permisos de AWS.
Los controles Ruff, Black, PEP257, MyPy, PyRight y Bandit pasaron.
Se generaron 12 páginas HTML con pdoc. Zensical 0.0.67 construyó el sitio
sin errores en 0,98 s; la revisión independiente confirmó que los 13 archivos
pdoc y los dos diagramas se copiaron sin cambios. Se comprobaron 3.371
referencias locales del sitio, incluidas 3.155 comprobaciones de fragmentos:
los enlaces de API, diagramas e informe funcionan. Como observación menor,
la plantilla generada `404.html` contiene un enlace de salto `#__skip` sin
destino. La ejecución alojada de GitHub Actions todavía no se verificó.
Los casos de aceptación cubren operaciones, auditoría, entradas inválidas,
servidor desconectado y puerto ocupado. GitHub Actions ejecuta controles de
calidad; el workflow de documentación valida en PR, push a `main` e inicio
manual. La publicación desde push o inicio manual en `main` requiere habilitación
explícita; no se publica desde PR.

## Evidencia AWS: identidad y estructura

Con autorización explícita se verificaron la identidad del perfil `tpfi-is2`
y la región `us-east-1`, mediante el SDK. `CorporateData` y `CorporateLog`
están `ACTIVE`; ambas usan una clave de partición `id` de tipo texto (`S`),
compatible con el código. La comprobación terminó con código 0 y solo usó
`GetCallerIdentity` y `DescribeTable`: no leyó ni modificó registros.

## Validación funcional AWS por consola

Tras una autorización específica posterior, el usuario ejecutó las pruebas
con el perfil `tpfi-is2`, en `us-east-1`, usando únicamente el registro
`TPFI-VALIDACION-IS2-MICAELA-01`. El servidor se inició en `127.0.0.1:8080`
con el modo memoria desactivado. Los siguientes resultados fueron confirmados
por el usuario durante la guía; **son pruebas manuales, no una suite AWS
automatizada ni una inspección independiente de sus salidas**.

| Comprobación | Resultado confirmado por el usuario |
| --- | --- |
| Precondición | El ID no existía antes de crear el registro. |
| `subscribe` | El observador conectó y recibió confirmación de suscripción. |
| Primer `set` | El cliente recibió el registro y el observador recibió la notificación. |
| `get` | Se recuperó el registro con sede y teléfono; los campos no enviados estaban vacíos. |
| Actualización parcial | El teléfono cambió de `0000000000` a `0000000001`, la sede `TPFI_VALIDACION` se conservó y llegó otra notificación. |
| `list` | Incluyó el registro actualizado y no generó una notificación adicional. |
| Auditoría | Se encontraron `subscribe`, al menos dos `set`, `get` y `list`, con `CPUid`, `sessionid` y `timestamp`; `get`/`set` referenciaban el ID de prueba. |

Un primer intento de `get` por CLI falló con `Could not connect to server`.
El intento diagnóstico posterior mediante `SingletonClient.send` devolvió el
registro; no se determinó la causa inicial ni se modificó código para corregirla.
No se conservaron capturas ni salidas funcionales completas. El registro y la
auditoría permanecen en AWS: no se autorizó ni ejecutó su eliminación.
Los casos negativos y la reconexión están cubiertos por la suite local; no se
repitieron contra AWS en esta demostración. Véase la
[validación AWS controlada](validacion_aws.md). La ejecución alojada de GitHub
Actions sigue sin comprobarse.
