# Changelog - TPFI IS2

Todos los cambios notables de este proyecto están documentados en este archivo.
El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [0.1.0] - 2026-10-13

### Agregado
- **Servidor de Aplicaciones (`singletonproxyobserver.py`)**:
  - Servidor TCP en puerto configurable (por defecto `8080`).
  - Implementación del **Patrón Proxy** (`CorporateDataProxy`) para validación de datos, campos corporativos y auditoría antes de tocar la base.
  - Implementación del **Patrón Singleton** (`AwsCorporateDataSingleton` y `AwsCorporateLogSingleton`) para acceso único y thread-safe a DynamoDB.
  - Implementación del **Patrón Observer** (`CorporateDataObserver`) para suscribir clientes TCP y notificarles inmediatamente ante operaciones `set`.
  - Soporte de gateways en memoria (`MemoryCorporateDataGateway` y `MemoryCorporateLogGateway`) para testing local sin credenciales de AWS.
- **Cliente Centralizado (`singletonclient.py`)**:
  - Interfaz de línea de comandos (`-i=input.json {-o=output.json} {-v}`).
  - Generación automática de UUID de hardware (`uuid.getnode()`) e identificador de sesión (`uuid.uuid4()`).
  - Soporte para acciones `get`, `set` y `list`.
- **Cliente Observador (`observerclient.py`)**:
  - Interfaz de línea de comandos (`{-s=hostname} {-p=port} {-o=output.json} {-v}`).
  - Suscripción continua por socket TCP y visualización en consola y/o archivo JSON.
  - Manejo de desconexiones y reconexión automática periódica (configurable, default 30 segundos).
- **Pruebas y Verificación**:
  - Suite de pruebas de aceptación (`tests/test_acceptance.py`) cubriendo los 5 escenarios requeridos por la consigna.
  - 54 tests automatizados con `pytest` y cobertura de código superior al 85%.
- **Calidad de Código y Seguridad**:
  - Validación de formato y linter PEP8 mediante `ruff` (0 errores).
  - Análisis estático de vulnerabilidades mediante `bandit` (0 observaciones).
  - Archivo `REQUIREMENTS.TXT` y registro de prompts en `CONTEXT.md`.
