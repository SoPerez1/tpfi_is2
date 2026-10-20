# Trabajo Práctico Final Integrador (TPFI) - Ingeniería de Software II (2024)
**Patrones de Diseño: Proxy, Singleton y Observer en Entorno Python / AWS DynamoDB**

Este proyecto implementa una arquitectura distribuida orientada a servicios para la gestión centralizada de datos corporativos (`CorporateData`) y registro auditable de accesos (`CorporateLog`), comunicándose mediante HTTP POST sobre sockets TCP y soportando persistencia física en AWS DynamoDB o emulación en memoria para desarrollo local.

---

## 🏗️ Arquitectura y Patrones de Diseño

El sistema está compuesto por tres programas ejecutables principales:

1. **`singletonproxyobserver.py` (Servidor de Aplicaciones)**
   - Escucha peticiones TCP (por defecto en el puerto `8080`).
   - **Patrón Proxy:** Intercepta todas las operaciones (`get`, `set`, `list`), valida los campos corporativos requeridos y audita cada solicitud en `CorporateLog` antes de interactuar con la base de datos.
   - **Patrón Singleton:** Garantiza una única instancia thread-safe para la conexión física a las tablas de DynamoDB (`CorporateData` y `CorporateLog`).
   - **Patrón Observer:** Mantiene un registro de clientes suscriptos y retransmite inmediatamente en formato JSON cualquier actualización de datos producida por una acción `set`.

2. **`singletonclient.py` (Cliente de Operaciones)**
   - Envía solicitudes de lectura (`get`), modificación (`set`) o listado completo (`list`).
   - Inyecta automáticamente el identificador de nodo/CPU (`UUID`) y el identificador de sesión (`SESSION_ID`).
   - Muestra la respuesta en formato JSON legible o la almacena en un archivo de salida.

3. **`observerclient.py` (Cliente Observador)**
   - Se suscribe al servidor mediante la acción `subscribe`.
   - Mantiene una respuesta HTTP abierta con notificaciones NDJSON de cambios en `CorporateData`.
   - Dispone de lógica de reconexión automática periódica (cada 30 segundos) si la conexión con el servidor se interrumpe.

---

## 🚀 Guía Rápida de Ejecución

### 1. Requisitos Previos e Instalación
Se recomienda utilizar un entorno virtual de Python (`venv`):

```bash
# Crear y activar el entorno virtual
python -m venv .venv
# En Windows:
.venv\Scripts\activate
# En Linux / Mac:
source .venv/bin/activate

# Instalar dependencias
pip install -r REQUIREMENTS.TXT
```

> **Nota para ejecución local sin AWS:** Si no se tienen configuradas las credenciales de AWS, se puede activar el modo en memoria definiendo la variable de entorno:
> - En PowerShell: `$env:TPFI_USE_MEMORY="1"`
> - En Bash: `export TPFI_USE_MEMORY=1`

---

### 2. Ejecución del Servidor
Inicia el servidor en el puerto deseado (por defecto `8080`) con logging de depuración (`-v`):

```bash
python singletonproxyobserver.py -p=8080 -v
```

---

### 3. Ejecución del Cliente Observador (ObserverClient)
En una segunda terminal, suscríbete para recibir cambios en tiempo real:

```bash
python observerclient.py -s=localhost -p=8080 -v
```
*(Opcionalmente se puede indicar `-o=notificaciones.json` para grabar los eventos en disco).*

---

### 4. Ejecución del Cliente de Datos (SingletonClient)
En una tercera terminal, envía operaciones mediante archivos JSON:

#### Ejemplo de archivo `input.json` (para modificar datos con `set`):
```json
{
  "ACTION": "set",
  "ID": "UADER-FCYT-IS2",
  "domicilio": "25 de Mayo 385-1P",
  "localidad": "Concepción del Uruguay",
  "sede": "FCyT",
  "telefono": "03442 43-1442"
}
```

#### Ejecutar el cliente:
```bash
# Modificar / insertar datos (el observador recibirá la actualización de inmediato)
python singletonclient.py -i=input.json -v

# Consultar datos con 'get':
# (crear input_get.json con {"ACTION": "get", "ID": "UADER-FCYT-IS2"})
python singletonclient.py -i=input_get.json

# Listar todos los datos con 'list':
# (crear input_list.json con {"ACTION": "list"})
python singletonclient.py -i=input_list.json
```

---

## 🧪 Pruebas Automatizadas y Calidad de Código

El proyecto cuenta con un conjunto exhaustivo de pruebas automatizadas y controles estáticos:

### 1. Ejecución de Tests con Cobertura ($\ge 85\%$)
```bash
pytest --cov=tpfi_is2 --cov-report=term-missing
```
Incluye `tests/test_acceptance.py` que valida los **5 casos de aceptación exigidos por la consigna**:
1. Camino feliz de cada acción (`get`, `set`, `list`, `subscribe`) con auditoría en `CorporateLog`.
2. Manejo de argumentos malformados de línea de comandos en cada programa.
3. Rechazo de requerimientos que omiten datos mínimos necesarios.
4. Manejo y tolerancia a fallos cuando el servidor aplicativo está caído.
5. Prevención de inicio duplicado del servidor en el mismo puerto.

### 2. Linters y Formateo de Código (PEP8 / Black / Ruff)
```bash
ruff check .
ruff format --check .
```

### 3. Análisis de Seguridad (Bandit)
```bash
bandit -r src/
```

---

## 📚 Documentación Adicional
- [`docs/diagramas_uml.md`](docs/diagramas_uml.md): Diagrama UML de Actividad (Proxy) y de Estado (Observer).
- [`docs/informe_tpfi.md`](docs/informe_tpfi.md): Informe de implementación detallado del TPFI.
- [`CHANGELOG.md`](CHANGELOG.md): Historial de versiones y cambios del sistema.
- [`CONTEXT.md`](CONTEXT.md): Bitácora de prompts utilizados durante el desarrollo asistido con IA.

---

## 📄 Licencia
Este proyecto está bajo la Licencia MIT - ver el archivo [`LICENSE`](LICENSE) para más detalles.

### Controles completos de la consigna

Instalar las herramientas con `uv sync` y ejecutar `just check`, o usar los
comandos siguientes desde la raíz del proyecto:

```bash
uv run ruff check .
uv run ruff format --check .
uv run black --check .
uv run ruff check --select D src/tpfi_is2 singletonclient.py observerclient.py singletonproxyobserver.py
uv run mypy
uv run pyright
uv run bandit -r src/tpfi_is2 singletonclient.py observerclient.py singletonproxyobserver.py
uv run coverage run -m pytest
uv run coverage combine
uv run coverage report
```

La verificación PEP257 usa las reglas `D` de Ruff con la convención `pep257`.
Ruff también verifica PEP8 mediante sus reglas `E` y `W`. MyPy, PyRight,
PEP257 y Bandit cubren el paquete aplicativo `src/tpfi_is2` y los tres puntos
de entrada. Los módulos `cli.py` y `__main__.py` del paquete son plantillas
Cookiecutter ajenas a los tres programas del TP y se excluyen del análisis de tipos.
Black y Ruff verifican también las pruebas; los ejemplos docentes de
`tests/sources` y `src/IS2_TPFI_test.py` quedan fuera de formato/lint.

GitHub Actions ejecuta estos controles en cada PR y push a `main`. Cualquier
error bloquea el resultado `All checks pass`, incluida una cobertura inferior al 85 %.

### VERSION y BUILD

El registro versionado está en `src/tpfi_is2/version.py`: `VERSION` identifica la
versión funcional y `BUILD` identifica la entrega dentro de esa versión. La
entrega inicial es `0.1.0 (build 1)`. Incrementar `BUILD` al preparar otra entrega
de la misma versión; al cambiar `__version__`, reiniciar `BUILD` en 1.
El empaquetado y el script de release toman la versión de ese mismo módulo.

Los tres programas permiten consultarlos sin iniciar conexiones ni necesitar AWS:

```bash
python singletonclient.py --version
python observerclient.py --version
python singletonproxyobserver.py --version
```

### HTTP POST y respuesta persistente

Los tres programas envían sus operaciones mediante `POST /` con cuerpo JSON.
Las consultas responden JSON y cierran la conexión; las suscripciones mantienen
una respuesta HTTP abierta con un objeto JSON por línea (NDJSON).
La confirmación de suscripción se procesa internamente y el observador muestra
las actualizaciones recibidas. Se conservan los argumentos CLI y los archivos de
entrada. Actualizar juntos servidor y clientes al migrar desde JSON directo por TCP.

Ver [contrato HTTP, ejemplos curl y reconexión](docs/protocolo_http.md).
