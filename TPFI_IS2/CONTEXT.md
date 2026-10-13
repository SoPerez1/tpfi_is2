# Registro de Prompts y Asistencia de IA (CONTEXT.md)

Este documento registra los prompts y contextos utilizados en la asistencia de herramientas de IA para el desarrollo del Trabajo Práctico Final Integrador (TPFI) de Ingeniería de Software II (2024).

---

## 1. Diseño y Arquitectura General
- **Prompt:** "Analizar los requerimientos del TPFI para implementar un servidor aplicativo en Python que integre los patrones Proxy, Singleton y Observer comunicándose por TCP Sockets con soporte para DynamoDB (CorporateData y CorporateLog) y un modo de pruebas en memoria."
- **Resultado:** Se definió la estructura modular en `src/tpfi_is2/`:
  - `storage.py`: Patrones Singleton `AwsCorporateDataSingleton`, `AwsCorporateLogSingleton` y alternativas en memoria.
  - `proxy.py`: Capa `CorporateDataProxy` para control de acceso, auditoría y validación.
  - `observer.py`: Notificador `CorporateDataObserver` para retransmitir notificaciones JSON a clientes suscriptos.
  - `proxy_server.py`: Servidor TCP `ProxyApplicationServer` / `SingletonProxyObserverTPFI`.
  - `singleton_client.py`: Cliente `SingletonClient` para operaciones `get`, `set` y `list`.
  - `observer_client.py`: Cliente `ObserverClient` para suscripción y recepción continua de eventos.

---

## 2. Implementación del Patrón Singleton
- **Prompt:** "Implementar el patrón Singleton en Python para el acceso físico a las tablas de DynamoDB (CorporateData y CorporateLog) garantizando seguridad entre hilos (thread-safety) mediante locks y método estático instance()."
- **Resultado:** Implementación de `_instance` y `_lock` en `AwsCorporateDataSingleton` y `AwsCorporateLogSingleton`, así como en `MemoryCorporateDataGateway` y `MemoryCorporateLogGateway`.

---

## 3. Implementación del Cliente Observer
- **Prompt:** "Implementar ObserverClient con interfaz de línea de comandos (CLI) que soporte los argumentos -s/--server, -p/--port, -o/--output, -v/--verbose y --retry-interval para mantener la conexión TCP abierta, recibir eventos JSON, escribirlos en el archivo de salida y reconectarse automáticamente ante caídas del socket."
- **Resultado:** Desarrollo completo en `src/tpfi_is2/observer_client.py` y punto de entrada raíz `observerclient.py`.

---

## 4. Pruebas Automatizadas y Cobertura
- **Prompt:** "Escribir pruebas unitarias e integradoras con pytest para validar la comunicación TCP, la reconexión de clientes, la auditoría en CorporateLog y la correcta notificación a los suscriptores Observer."
- **Resultado:** Creación de test suites en `tests/test_singleton_client.py`, `tests/test_proxy_server.py`, `tests/test_observer_client.py` y `tests/test_integration_client_server.py`.

---

## 5. Casos de Prueba de Aceptación (Validación y Verificación)
- **Prompt:** "Completar los casos de prueba y validación requeridos en la consigna de forma simple y didáctica: camino feliz con auditoría, argumentos CLI malformados para cada programa, requerimientos sin datos mínimos, manejo de servidor caído e intento de levantar dos veces el servidor."
- **Resultado:** Creación de `tests/test_acceptance.py` con 8 tests específicos que validan los 5 puntos exigidos, y elevación de la cobertura de código con pytest al **87.32%** (superando el requisito del 85%).

---

## 6. Aseguramiento de Calidad, Seguridad y Documentación
- **Prompt:** "Verificar y subsanar observaciones de linters (Ruff/Black/PEP8), evaluación estática de seguridad con Bandit y generación automática de documentación con pdoc."
- **Resultado:**
  - `ruff check .` y `ruff format --check .`: 0 errores, formato consistente PEP8.
  - `bandit -r src/`: 0 observaciones de seguridad.
  - Documentación generada con `pdoc` en `docs/html/`.
  - Normalización de archivos del repositorio: `REQUIREMENTS.TXT`, `CHANGELOG.md` y `README.md`.

