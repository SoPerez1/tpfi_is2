# Validación AWS controlada

**Estado:** comprobación de identidad/estructura ejecutada mediante SDK y prueba
funcional por consola confirmada manualmente por el usuario. La suite automatizada
local usa gateways en memoria; no es una suite automatizada contra AWS.

## Alcance autorizado

- Perfil `tpfi-is2`, región `us-east-1`.
- Único registro de prueba: `TPFI-VALIDACION-IS2-MICAELA-01`.
- Operaciones `get`, `set`, `list`, `subscribe` y auditoría en `CorporateLog`.
- Sin modificaciones en `Log`, `cliente`, `ticket` ni registros ajenos.
- Sin eliminación del registro de prueba ni de su auditoría.

## Identidad y estructura verificadas mediante SDK

- [x] Perfil, región e identidad AWS verificados.
- [x] `CorporateData` y `CorporateLog` están `ACTIVE`; clave `id` de tipo `S`.
- [x] Comprobación finalizada con código 0 usando `GetCallerIdentity` y
      `DescribeTable`, sin leer ni escribir registros en esa etapa.

## Resultados de consola confirmados por el usuario

El usuario ejecutó los comandos desde sus terminales. La guía preparó archivos
JSON temporales bajo `.venv/.tmp`; no ejecutó las operaciones funcionales en su
nombre. Las confirmaciones siguientes no sustituyen capturas ni logs íntegros:

- [x] ID ausente antes de crear el registro, comprobado con lectura consistente.
- [x] Servidor en `127.0.0.1:8080`, perfil AWS seleccionado y memoria desactivada.
- [x] Observador conectado y suscrito.
- [x] Creación con sede `TPFI_VALIDACION` y teléfono `0000000000`; respuesta y
      notificación confirmadas.
- [x] Consulta del registro, con datos cargados y campos no enviados en blanco.
- [x] Cambio del teléfono a `0000000001`, conservando la sede y notificando al
      observador.
- [x] Listado con el registro actualizado, sin notificación adicional. Se guardó
      el resultado localmente y se mostró solo el registro autorizado.
- [x] Auditoría de `subscribe`, al menos dos `set`, `get` y `list`, con `CPUid`,
      `sessionid` y `timestamp`; `get`/`set` referenciaban el ID de prueba.

La consulta de auditoría se filtró por CPU, inicio del servidor y registro/acciones
autorizados. No se solicitaron credenciales ni listados ajenos para el informe.

## Incidencias y límites

Un primer `get` por CLI devolvió un error de conexión genérico. El puerto local
aceptaba TCP, el servidor no mostraba errores y una consulta posterior mediante
`SingletonClient.send` funcionó. La causa inicial no quedó determinada y no se
cambió código para corregirla.

No se repitieron en AWS los casos negativos ni la reconexión de la suite local.
No se conservaron capturas ni salidas funcionales completas. GitHub Actions
alojado sigue sin ejecutarse para estos cambios. El registro de prueba y las
entradas de auditoría permanecen en AWS; cualquier limpieza o nueva prueba fuera
del alcance acordado requiere autorización explícita.

Ver [informe](informe_tpfi.md), [uso](usage.md) y [protocolo HTTP](protocolo_http.md).
