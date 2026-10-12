# Informe de Implementación - TPFI IS2 (2024)
**Patrón Proxy/Singleton/Observer en entorno AWS**

Este documento detalla el progreso e historia de las implementaciones realizadas en este repositorio para el Trabajo Práctico Final Integrador de la materia Ingeniería de Software II.

## 1. Configuración Inicial del Entorno

### Entorno Virtual
Se estableció un entorno virtual de Python (`.venv`) para aislar las dependencias del proyecto. Todas las tareas de desarrollo y pruebas se ejecutan dentro de este entorno para garantizar la reproducibilidad y evitar conflictos a nivel de sistema. Como se vio en terminales anteriores, el entorno se activa con `source .venv/bin/activate`.

### Estructura Base (Cookiecutter)
El proyecto fue inicializado utilizando un andamiaje basado en **Cookiecutter PyPackage**. Esto proveyó una base sólida que incluye:
- Archivos estándar como `README.md`, `CHANGELOG.md` (con registro de versiones no publicadas), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` y la licencia `MIT`.
- Configuración en `pyproject.toml` para herramientas de linting y formateo.
- Soporte inicial para pruebas automatizadas e integración continua (CI vía GitHub Actions).

### Dependencias (`REQUERIMENTS.TXT`)
Se generó el archivo de dependencias (`REQUERIMENTS.TXT`) conteniendo las librerías necesarias para cumplir con los requerimientos técnicos y no funcionales indicados en la consigna:
- `boto3>=1.34.0`: Para la comunicación con los servicios de AWS (DynamoDB).
- Herramientas de control de calidad estático: `ruff>=0.3.0`, `black>=24.0.0` (formateo PEP8), `mypy>=1.9.0`, `pyright>=1.1.350` (tipado estático).
- Seguridad: `bandit>=1.7.8` para análisis estático de vulnerabilidades.
- Testing: `pytest>=8.0.0` y `pytest-cov>=4.1.0` para asegurar la cobertura de código.
- Documentación: `pdoc>=14.0.0`.

## 2. Configuración y Conexión con AWS

### Instalación de AWS CLI y Boto3
Al tratarse de un entorno Linux (Fedora), la herramienta de línea de comandos de AWS (`aws-cli/2.37.6`) fue instalada descargando y descomprimiendo el paquete oficial para Linux (se evidencia la presencia de los archivos `awscliv2.zip` y el directorio `aws` en el repositorio). Posteriormente, el SDK para Python (`boto3`) se instaló dentro del entorno virtual.

### Configuración de Credenciales
Las credenciales de acceso (Access Key ID y Secret Access Key) fueron configuradas utilizando el comando `aws configure`, apuntando a la región por defecto (`us-east-1` o `us-west-2` según el archivo de credenciales provisto).

> **Nota Importante:** Por motivos de seguridad (y siguiendo la advertencia explícita en la consigna), el archivo provisto con credenciales (`IS2_TPFI_credentials.json`) no debe subirse nunca al repositorio público.

*A continuación, la evidencia de la configuración exitosa validando la conexión mediante el comando `aws dynamodb list-tables` para listar las tablas:*

![Evidencia de configuración AWS](./capturas/aws_config_terminal.jpg)
*(Nota: Asegúrate de agregar la captura de tu consola en la carpeta `capturas`)*

### Programa de Diagnóstico (`IS2_TPFI_test.py`)
Se implementó el script de diagnóstico inicial en `src/IS2_TPFI_test.py` para validar la conectividad con DynamoDB de AWS a nivel de código Python.
- **Funcionalidad:** Recupera el identificador único de CPU (`UUID` a través de la librería `uuid` y `platform`) y genera un ID de sesión.
- **Conexión AWS:** Instancia el recurso `boto3` para conectarse a DynamoDB.
- **Validación de Tablas:** Verifica la existencia de las tablas requeridas por la arquitectura: `CorporateData` y `CorporateLog`, imprimiendo por pantalla sus fechas de creación exitosamente.

## 3. Implementación de Componentes del Sistema (Cliente)

De acuerdo con el diseño de componentes solicitado en la segunda parte del práctico, se ha avanzado en la construcción del cliente principal de la arquitectura:

### SingletonClient (`src/singleton_client.py`)
Se desarrolló el módulo cliente encargado de realizar requerimientos de información a la base de datos `CorporateData` de manera centralizada. Este cliente permite simular las operaciones que luego irán al Proxy en AWS.

**Características implementadas en el código actual:**
- **Clase SingletonClient:** Implementa la lógica de conexión mediante sockets TCP (`socket.AF_INET`, `socket.SOCK_STREAM`) apuntando al servidor aplicativo (por defecto a `localhost:8080`).
- **Generación de metadatos:** Genera el identificador de nodo/CPU y un identificador de sesión único (`SESSION_ID`) para cada transacción para que quede rastreable.
- **Procesamiento de JSON:** Interpreta el archivo JSON de entrada (con formato `--input`), inyecta los metadatos necesarios y valida que la acción a realizar sea `get`, `set` o `list`.
- **Comunicación TCP:** Envía la carga útil en formato JSON al servidor configurado y espera la respuesta correspondiente en formato JSON.
- **Interfaz CLI (Command Line Interface):** Implementada mediante `argparse`, soporta los argumentos requeridos por la consigna (`-i`, `-o` para salida de archivo en lugar de stdout, `-v` para logging detallado/debug, y opciones de puerto/servidor).

## 4. Estado Actual y Próximos Pasos

El repositorio actualmente cuenta con la infraestructura base, el cliente implementado y las pruebas de conexión. 

**Resumen de lo completado:**
1. ✅ Inicialización con Cookiecutter y estructura base.
2. ✅ Dependencias configuradas (`REQUERIMENTS.TXT`).
3. ✅ CLI AWS configurado y validado en la terminal del entorno virtual `(.venv)`.
4. ✅ Programa de conexión de prueba funcionando (`IS2_TPFI_test.py`).
5. ✅ Desarrollo de `SingletonClient` completado en `src/singleton_client.py`.

**Pendientes de Implementación para cumplir la consigna completa:**
- **Servidor Proxy/Singleton/Observer (`singleton_proxy_observer.py`):** Es el servidor central que levantará en el puerto TCP 8080. Estará encargado de procesar peticiones, gestionar la conexión Singleton a la base de datos de AWS y generar la bitácora auditable en `CorporateLog`.
- **Observer Client (`observer_client.py`):** El cliente que se suscribirá a las notificaciones y dejará el puerto abierto esperando actualizaciones constantes del servidor cada vez que alguien modifique los datos (`set`).
- **Diagramas:** Construcción de Diagramas UML de Actividad y de Estado.
- **Flujos CI/CD:** Habilitar GitHub Actions para control estricto (Ruff, Mypy, Bandit).
