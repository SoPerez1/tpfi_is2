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


## 7. Controles exigidos por la consigna
- **Prompt:** "podes implementar esto?", referido a completar Black, MyPy, PyRight, PEP257 y Bandit en CI.
- **Resultado:** Configuración de dependencias, controles obligatorios en GitHub Actions y comandos locales; documentación PEP257 y ajustes de tipos en el aplicativo.

## 8. Registro de VERSION y BUILD
- **Prompt:** Revisar VERSION y BUILD y agregar un registro explícito de BUILD.
- **Resultado:** Módulo de versión compartido, número de entrega y opción `--version` en los tres programas; empaquetado y release usan la misma fuente de versión.

## 9. HTTP POST y notificaciones persistentes
- **Prompt:** "hagamos esto", referido a implementar HTTP POST y mantener una respuesta persistente para los observadores, documentando la decisión.
- **Resultado:** Transporte HTTP compartido, adaptación de clientes y servidor, respuesta NDJSON para suscripciones y pruebas de interoperabilidad, errores, reconexión y Unicode.

## 10. Entrega documental local
- **Mensajes exactos del usuario:** "podes visualizar el pdf IS2_TPFI?? en donde se plantea todo el trabajo, y necesito saber si viene todo listo, o si faltan cosas"; "perfecto, como puedo seguir para completar con lo que falta?"; aprobación del plan: "okey, hagamos".
- **Autorización de lectura:** "autorizar" permitió consultar material instalado; no autorizó credenciales, operaciones AWS ni publicaciones.
- **Resultado local previo a esta edición:** 68 pruebas aprobadas en Python 3.10 y cobertura de ramas 89,64241676942046 % con gateways en memoria. Se actualizó el informe, se enlazaron ambos diagramas UML y se integró pdoc con la generación del sitio Zensical. En ese momento la validación AWS estaba pendiente de elegir y autorizar un ID de prueba.

## 11. Pruebas AWS guiadas por consola
- **Prompt exacto del usuario:** "quiero hacer las prubas por consola". Autorizó después la prueba controlada sobre un único ID y sus entradas de auditoría.
- **Resultado:** El usuario confirmó suscripción, creación, consulta, actualización parcial, notificaciones, listado y auditoría sobre `TPFI-VALIDACION-IS2-MICAELA-01`. Son confirmaciones manuales, separadas de las 71 pruebas automatizadas locales y del 89,64 % de cobertura.
- **Límites:** No se mostraron ni guardaron credenciales; no se eliminaron registros. Un primer `get` por CLI falló y una consulta posterior con el mismo cliente funcionó; la causa inicial no se determinó. No se afirma ejecución de GitHub Actions ni una suite automatizada contra AWS.

## 12. Entrega remota y descubrimiento de workflows
- **Solicitud exacta:** "hagamos la pendiente real de entrega"; después "Sí: subir las ramas y comprobar CI" y, ante la ausencia de workflows descubiertos, "Sí: corregir CI y publicar la tercera rama".
- **Alcance:** Repositorio `github.com/SoPerez1/tpfi_is2`; ramas encadenadas `tpfi/docs-automation`, `tpfi/aws-evidence` y `ci/tpfi-actions-root`. Los workflows CI/documentación activos van en la raíz, ejecutan comandos en `TPFI_IS2/` y usan rutas de artefactos relativas al repositorio. Las plantillas anidadas permanecen sin cambios; no se activan publicación PyPI ni otros workflows.
- **Límites y evidencia:** Sin PR, merge, despliegue de Pages desde estas ramas, cambios de credenciales o código aplicativo. Los controles locales verifican la configuración, pero no son prueba de ejecuciones alojadas; el responsable de la entrega debe observar los runs tras publicar las ramas.
