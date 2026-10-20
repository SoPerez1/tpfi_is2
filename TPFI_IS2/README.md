# Trabajo Práctico Final Integrador (TPFI) - Ingeniería de Software II (2024)
**Patrones de Diseño: Proxy, Singleton y Observer en Entorno Python / AWS DynamoDB**

Este proyecto implementa una arquitectura distribuida orientada a servicios para la gestión centralizada de datos corporativos (`CorporateData`) y registro auditable de accesos (`CorporateLog`), comunicándose mediante sockets TCP y soportando persistencia física en AWS DynamoDB o emulación en memoria para desarrollo local.

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
   - Mantiene la conexión TCP abierta a la espera de notificaciones de cambios en `CorporateData`.
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
- [`docs/diagramas_uml.md`](docs/diagramas_uml.md): diagramas UML de actividad (Proxy) y estados (Observer).
- [`docs/informe_tpfi.md`](docs/informe_tpfi.md): Informe de implementación detallado del TPFI.
- [`CHANGELOG.md`](CHANGELOG.md): Historial de versiones y cambios del sistema.
- [`CONTEXT.md`](CONTEXT.md): Bitácora de prompts utilizados durante el desarrollo asistido con IA.

---

## 📄 Licencia
Este proyecto está bajo la Licencia MIT - ver el archivo [`LICENSE`](LICENSE) para más detalles.
