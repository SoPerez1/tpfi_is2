# Comandos para mostrar el TP

Guion para una demostración **local, sin AWS**, en Linux, macOS o WSL (Bash).
Se necesitan Python 3.10 o superior y tres terminales abiertas en la raíz del
repositorio (`tpfi_is2`, donde está este archivo). Ejecutar los bloques en orden.

> El modo en memoria no utiliza credenciales ni modifica DynamoDB. Los datos y
> la auditoría local se pierden al detener el servidor. Esta demo no acredita
> persistencia en AWS.

## 1. Preparación (una sola vez, antes de la exposición)

Desde la raíz del repositorio:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r TPFI_IS2/REQUIREMENTS.TXT
```

La instalación necesita conexión a Internet. Si `venv` no está disponible,
instalar primero el soporte de entornos virtuales de la distribución.

## 2. Terminal 1: iniciar el servidor

Desde la raíz del repositorio:

```bash
source .venv/bin/activate
cd TPFI_IS2
export TPFI_USE_MEMORY=1
python singletonproxyobserver.py -p=8080 -v
```

Esperar el mensaje `Proxy server listening on 0.0.0.0:8080` y dejar esta
terminal abierta. Aquí se ven las solicitudes que procesa el Proxy.

Si el puerto está ocupado, detener la instancia anterior con `Ctrl+C` o elegir
otro puerto en **todos** los comandos del servidor y los clientes.

## 3. Terminal 2: iniciar el observador

Desde la raíz del repositorio, en otra terminal:

```bash
source .venv/bin/activate
cd TPFI_IS2
python observerclient.py -s=localhost -p=8080 -v
```

Dejarlo ejecutándose antes de modificar datos. Es normal que aún no muestre
actualizaciones: las recibe cuando se ejecuta un `set` exitoso.

## 4. Terminal 3: modificar, consultar y listar

Desde la raíz del repositorio, en la tercera terminal:

```bash
source .venv/bin/activate
cd TPFI_IS2
```

### 4.1. Preparar archivos de demostración

Crear una carpeta temporal dentro del proyecto para no sobrescribir ejemplos:

```bash
DEMO_DIR=$(mktemp -d .demo-tpfi.XXXXXX)
printf '%s\n' '{"ACTION":"get","ID":"TEST-OBSERVER-01"}' > "$DEMO_DIR/get.json"
printf '%s\n' '{"ACTION":"set","ID":"TEST-OBSERVER-01","telefono":"03442 44-4444"}' > "$DEMO_DIR/set_actualizado.json"
printf '%s\n' '{"ACTION":"set","ID":"TEST-OBSERVER-01"}' > "$DEMO_DIR/set_invalido.json"
```

Mantener esta terminal: la variable `DEMO_DIR` se utiliza en los pasos siguientes.
El archivo incluido `prueba_get.json` consulta otro ID; por eso esta guía crea
una consulta que coincide con el ID de `prueba_set.json`.

### 4.2. Insertar un registro (`set`)

```bash
python singletonclient.py -s=localhost -p=8080 -i=prueba_set.json -v
```

Resultado esperado: un registro con `id` igual a `TEST-OBSERVER-01` y teléfono
`03442 33-3333`. La terminal 2 recibe una notificación del registro.

### 4.3. Consultar el mismo registro (`get`)

```bash
python singletonclient.py -s=localhost -p=8080 -i="$DEMO_DIR/get.json"
```

Resultado esperado: el registro recién insertado, con el mismo teléfono.

### 4.4. Listar los registros (`list`)

```bash
python singletonclient.py -s=localhost -p=8080 -i=prueba_list.json
```

Resultado esperado: una lista que incluye `TEST-OBSERVER-01`.

### 4.5. Cambiar el teléfono y mostrar Observer

```bash
python singletonclient.py -s=localhost -p=8080 -i="$DEMO_DIR/set_actualizado.json"
python singletonclient.py -s=localhost -p=8080 -i="$DEMO_DIR/get.json"
```

Resultado esperado: teléfono `03442 44-4444` tanto en la respuesta como en
la nueva notificación de la terminal 2. `get` y `list` no generan notificaciones.

### 4.6. Guardar una respuesta en un archivo

```bash
python singletonclient.py -s=localhost -p=8080 -i="$DEMO_DIR/get.json" -o="$DEMO_DIR/respuesta.json"
python -m json.tool "$DEMO_DIR/respuesta.json"
```

## 5. Mostrar validaciones y fallos controlados (opcional)

Estos comandos producen errores intencionales; ejecutarlos por separado.

### Argumento obligatorio ausente

```bash
python singletonclient.py
```

Resultado esperado: error de argumentos por faltar `-i` (código de salida 2).

### Modificación sin campos corporativos

En la terminal 3, con la variable `DEMO_DIR` todavía definida:

```bash
python singletonclient.py -i="$DEMO_DIR/set_invalido.json"
```

Resultado esperado: `Error: ACTION 'set' requires at least one CorporateData field`
(código de salida 1). El cliente rechaza la solicitud antes de enviarla.

### Segundo servidor en el mismo puerto

Con el primer servidor todavía activo, ejecutar en la terminal 3:

```bash
TPFI_USE_MEMORY=1 python singletonproxyobserver.py -p=8080 -v
```

Resultado esperado: `Error: cannot bind ...` (el detalle depende del sistema
operativo), código de salida 1. El servidor original sigue funcionando.

### Servidor caído

Al finalizar la demo, detener primero el observador (terminal 2) y luego el
servidor (terminal 1) con `Ctrl+C`. En la terminal 3:

```bash
python singletonclient.py -s=localhost -p=8080 -i="$DEMO_DIR/get.json"
```

Resultado esperado: `Error: Could not connect to server localhost:8080`
(código de salida 1). Para repetir la demo, iniciar servidor y observador y
volver a insertar el registro: la memoria anterior ya no existe.

## 6. Mostrar versión y ayuda

Desde `TPFI_IS2/`, con el entorno virtual activo:

```bash
python singletonproxyobserver.py --version
python singletonclient.py --version
python observerclient.py --version
python singletonproxyobserver.py --help
python singletonclient.py --help
python observerclient.py --help
```

## 7. Pruebas automatizadas y calidad (antes de exponer u opcional)

Desde `TPFI_IS2/`, con el entorno virtual activo. No es necesario mantener el
servidor de la demo encendido; las pruebas crean sus propios recursos locales.

```bash
python -m pytest -q
```

Para ejecutar las pruebas con cobertura, usar este bloque **en lugar del anterior**:

```bash
python -m coverage run -m pytest
python -m coverage combine
python -m coverage report
```

La configuración exige cobertura mínima del 85 %. Los siguientes controles no
modifican el código:

```bash
python -m ruff check .
python -m ruff format --check .
python -m black --check .
python -m ruff check --select D src/tpfi_is2 singletonclient.py observerclient.py singletonproxyobserver.py
python -m mypy
python -m pyright
python -m bandit -r src/tpfi_is2 singletonclient.py observerclient.py singletonproxyobserver.py
```

## 8. Mostrar la documentación

Abrir en el editor `TPFI_IS2/docs/informe_tpfi.md` y
`TPFI_IS2/docs/diagramas_uml.md`. Para navegar la API HTML ya incluida,
desde `TPFI_IS2/`:

```bash
python -m http.server 8000 --bind 127.0.0.1 --directory docs/html
```

Abrir <http://127.0.0.1:8000/> en el navegador. Detener con `Ctrl+C`.
La evidencia y las limitaciones de AWS están en
[`TPFI_IS2/docs/validacion_aws.md`](TPFI_IS2/docs/validacion_aws.md);
no ejecutar escrituras en AWS como parte de esta demo local.

## Orden breve para la exposición

1. Explicar Proxy, Singleton y Observer con los diagramas.
2. Iniciar servidor y observador.
3. Ejecutar `set`, `get` y `list`.
4. Cambiar el teléfono y mostrar la notificación en tiempo real.
5. Mostrar los errores controlados y los resultados de pruebas.
6. Cerrar los procesos con `Ctrl+C` y salir del entorno con `deactivate`.
