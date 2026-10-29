# Comandos para demostrar el TP con AWS

El servidor y los clientes se ejecutan en tu equipo; los datos se guardan en
AWS DynamoDB. No es necesario desplegar el servidor en EC2.

Guía para Linux, macOS o WSL (Bash), con tres terminales abiertas inicialmente
en la raíz del repositorio (`tpfi_is2`, donde está este archivo).

> **Operaciones reales:** `set` modifica `CorporateData`. Además, `get`, `list`
> y la suscripción del observador escriben auditoría en `CorporateLog`.
> Ejecutar la demo solo con autorización para esas operaciones. Esta guía no
> autoriza escrituras, cambios de permisos ni eliminación de registros.

## 1. Requisitos y alcance

- Python 3.10 o superior y dependencias instaladas; ver la
  [preparación de la demo local](COMANDOS_DEMO.md#1-preparación-una-sola-vez-antes-de-la-exposición).
- Conexión a Internet.
- Perfil AWS `tpfi-is2` configurado y credenciales vigentes.
- Región `us-east-1`.
- Tablas `CorporateData` y `CorporateLog`, ambas `ACTIVE`, con clave de partición
  `id` de tipo String y sin clave de ordenamiento.
- Permisos para consultar identidad (`sts:GetCallerIdentity`), describir ambas
  tablas (`dynamodb:DescribeTable`), leer y escribir `CorporateData`
  (`dynamodb:GetItem`, `dynamodb:PutItem`) y escribir `CorporateLog`
  (`dynamodb:PutItem`). Para `list`, también `dynamodb:Scan` en `CorporateData`.
  La revisión de auditoría desde la consola requiere permisos de lectura
  adicionales sobre `CorporateLog`.

El proyecto tiene documentados este perfil, región y registro de prueba:
`TPFI-VALIDACION-IS2-MICAELA-01`. Es evidencia anterior, no una verificación
actual ni una autorización para volver a modificar AWS. El registro podría
seguir existiendo: esta guía lo reutiliza, no garantiza una creación nueva.

No usar los archivos `prueba_set.json` o `prueba_get.json` de la demo local:
apuntan a otros IDs. No modificar `Log`, `cliente`, `ticket` ni registros ajenos.

## 2. Terminal 1: seleccionar AWS y desactivar la memoria

Desde la raíz del repositorio:

```bash
source .venv/bin/activate
cd TPFI_IS2

export AWS_PROFILE=tpfi-is2
export AWS_DEFAULT_REGION=us-east-1
unset TPFI_USE_MEMORY
```

Si hay credenciales exportadas en variables de entorno, pueden prevalecer sobre
el perfil. Verificar la identidad en el siguiente paso. No compartir claves,
mostrarlas durante la exposición ni guardarlas en el repositorio.

## 3. Verificar identidad y estructura sin modificar registros

En la terminal 1:

```bash
python - <<'PY'
import boto3

identity = boto3.client("sts").get_caller_identity()
print("Cuenta:", identity["Account"])
print("Identidad:", identity["Arn"])

db = boto3.client("dynamodb")
for name in ("CorporateData", "CorporateLog"):
    table = db.describe_table(TableName=name)["Table"]
    print(name, table["TableStatus"])
    print("Clave:", table["KeySchema"])
    print("Tipos:", table["AttributeDefinitions"])
    assert table["TableStatus"] == "ACTIVE", f"{name}: tabla no activa"
    assert table["KeySchema"] == [{"AttributeName": "id", "KeyType": "HASH"}], (
        f"{name}: se esperaba solo la clave de partición id"
    )
    assert any(
        field["AttributeName"] == "id" and field["AttributeType"] == "S"
        for field in table["AttributeDefinitions"]
    ), f"{name}: id debe ser String"
PY
```

Confirmar que la cuenta y la identidad son las esperadas. Si no lo son, si falla
la autenticación o alguna tabla no cumple la estructura, detenerse antes de las
escrituras. No crear tablas ni ampliar permisos como parte de esta guía.

## 4. Terminal 1: iniciar el servidor

Detener previamente con `Ctrl+C` cualquier servidor de la demo en memoria que
ocupe el puerto 8080. En la terminal 1, con el entorno anterior:

```bash
python singletonproxyobserver.py -p=8080 -v
```

Esperar `Proxy server listening on 0.0.0.0:8080` y dejarlo ejecutándose.
El servidor escucha en todas las interfaces: usar una red de confianza y no
exponer el puerto 8080 a Internet.

**La selección de AWS depende de haber quitado `TPFI_USE_MEMORY` antes de iniciar
el proceso.** Los clientes no necesitan las credenciales AWS: se comunican con
el servidor local por HTTP POST.

## 5. Terminal 2: iniciar el observador

Desde la raíz del repositorio:

```bash
source .venv/bin/activate
cd TPFI_IS2

python observerclient.py -s=localhost -p=8080 -v
```

Dejarlo conectado antes de modificar datos. La suscripción ya genera una entrada
real en `CorporateLog`; continuar solo si esa escritura está autorizada.

## 6. Terminal 3: preparar los archivos de demostración

Desde la raíz del repositorio:

```bash
source .venv/bin/activate
cd TPFI_IS2

DEMO_DIR=$(mktemp -d .demo-aws.XXXXXX)

printf '%s\n' \
'{"ACTION":"set","ID":"TPFI-VALIDACION-IS2-MICAELA-01","sede":"TPFI_VALIDACION","telefono":"0000000000"}' \
> "$DEMO_DIR/set.json"

printf '%s\n' \
'{"ACTION":"get","ID":"TPFI-VALIDACION-IS2-MICAELA-01"}' \
> "$DEMO_DIR/get.json"

printf '%s\n' \
'{"ACTION":"set","ID":"TPFI-VALIDACION-IS2-MICAELA-01","telefono":"0000000001"}' \
> "$DEMO_DIR/actualizar.json"
```

Estos comandos solo crean archivos locales en una carpeta temporal dentro del
proyecto. Mantener esta terminal abierta para conservar `DEMO_DIR`.

## 7. Guardar, consultar y actualizar en AWS

**Solo con autorización para reutilizar el registro de prueba**, ejecutar en la
terminal 3, uno por uno:

```bash
# Guardar los datos en DynamoDB
python singletonclient.py -s=localhost -p=8080 -i="$DEMO_DIR/set.json"

# Consultar el registro
python singletonclient.py -s=localhost -p=8080 -i="$DEMO_DIR/get.json"

# Cambiar únicamente el teléfono
python singletonclient.py -s=localhost -p=8080 -i="$DEMO_DIR/actualizar.json"

# Confirmar el cambio
python singletonclient.py -s=localhost -p=8080 -i="$DEMO_DIR/get.json"
```

Resultados esperados:

- Primer teléfono: `0000000000`.
- Después de actualizar: `0000000001`.
- La sede `TPFI_VALIDACION` se conserva al actualizar únicamente el teléfono.
- El observador recibe una notificación por cada `set` exitoso, no por los `get`.

Las lecturas del aplicativo no solicitan consistencia fuerte en DynamoDB. Una
consulta inmediata podría reflejar brevemente el valor anterior; no confundir
eso con una pérdida de persistencia ni repetir escrituras para resolverlo.

### Listado opcional

`list` escanea toda `CorporateData`, no solo el registro de prueba, y genera
su propia auditoría. Omitirlo si no está permitido leer los demás registros.
Si está autorizado, guardar la respuesta y mostrar únicamente el registro de
la demo:

```bash
python singletonclient.py -s=localhost -p=8080 -i=prueba_list.json -o="$DEMO_DIR/listado.json"
python - "$DEMO_DIR/listado.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as file:
    records = json.load(file)
if not isinstance(records, list):
    raise SystemExit("El servidor no devolvió una lista; revisar el error sin proyectar datos ajenos.")
for record in records:
    if record.get("id") == "TPFI-VALIDACION-IS2-MICAELA-01":
        print(json.dumps(record, indent=2, ensure_ascii=False))
PY
```

Aunque la pantalla muestre solo el registro de prueba, el archivo local contiene
el resultado completo del escaneo. Tratarlo como información potencialmente
sensible; no subirlo al repositorio ni compartirlo.

## 8. Mostrar la persistencia en la consola AWS

En la consola de AWS, seleccionar **Norte de Virginia (`us-east-1`)**:

1. Abrir **DynamoDB → Tables → CorporateData → Explore table items**.
2. Usar una consulta por la clave de partición
   `id = TPFI-VALIDACION-IS2-MICAELA-01`, evitando un escaneo general.
3. Mostrar el teléfono actualizado y la sede.
4. En `CorporateLog`, revisar las entradas de esta demo: `subscribe`, `set`,
   `get` y, si se ejecutó, `list`. Identificarlas por CPU, sesión y horario;
   `get` y `set` también referencian el ID de prueba.
5. Mostrar los campos de auditoría `CPUid`, `sessionid`, `action` y `timestamp`,
   sin proyectar registros ajenos.

El filtro de una exploración de `CorporateLog` puede requerir un escaneo:
solo realizarlo con los permisos y autorización correspondientes. No eliminar
el registro de prueba ni las entradas de auditoría.

## 9. Probar que los datos sobreviven al reinicio

1. Detener el observador en la terminal 2 con `Ctrl+C`.
2. Detener el servidor en la terminal 1 con `Ctrl+C`.
3. En la misma terminal 1, reiniciar manteniendo AWS y memoria desactivada:

```bash
export AWS_PROFILE=tpfi-is2
export AWS_DEFAULT_REGION=us-east-1
unset TPFI_USE_MEMORY
python singletonproxyobserver.py -p=8080 -v
```

4. En la terminal 3, consultar nuevamente:

```bash
python singletonclient.py -s=localhost -p=8080 -i="$DEMO_DIR/get.json"
```

El registro debe seguir existiendo con teléfono `0000000001`. A diferencia del
modo en memoria, reiniciar el servidor no elimina los datos de DynamoDB.
Esta consulta también genera una entrada nueva de auditoría.

## 10. Cierre y problemas frecuentes

Detener los procesos restantes con `Ctrl+C` y salir del entorno con `deactivate`.
No eliminar datos AWS ni auditoría como parte del cierre.

| Síntoma | Qué comprobar |
| --- | --- |
| `ProfileNotFound` | Existe el perfil `tpfi-is2` en la configuración AWS local. |
| `NoCredentialsError` o credenciales vencidas | El perfil tiene credenciales válidas; renovar la sesión con el mecanismo habitual de la cuenta. |
| `AccessDeniedException` | Identidad, acción y tabla; solicitar al responsable los permisos mínimos, no conceder acceso administrativo. |
| `ResourceNotFoundException` | Cuenta, región y nombres exactos de las tablas. |
| `Could not connect to server` | Servidor activo, host y puerto correctos; revisar también la terminal del servidor. |
| Datos desaparecen al reiniciar | Confirmar que `TPFI_USE_MEMORY` no estaba activada al iniciar el servidor. |

## Guion mínimo para exponer

1. Comprobar identidad y tablas antes de la presentación.
2. Iniciar servidor AWS y observador.
3. Guardar el registro, recibir una notificación y consultarlo.
4. Cambiar el teléfono y mostrar la nueva notificación.
5. Mostrar el registro y la auditoría en DynamoDB, sin datos ajenos.
6. Reiniciar el servidor y consultar el mismo registro para probar persistencia.

La [validación AWS anterior](TPFI_IS2/docs/validacion_aws.md) detalla la evidencia
y sus límites. La creación de esta guía no ejecuta ni verifica operaciones AWS.
