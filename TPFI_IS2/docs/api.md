# Referencia de API

La API aplicativa se genera con pdoc dentro de `docs/html/`. Se incluyen los
módulos actuales explícitamente, sin ampliar las exportaciones de
`tpfi_is2.__all__` ni documentar las plantillas Cookiecutter `cli` y `__main__`.

| Componente | API |
| --- | --- |
| Persistencia Singleton | [storage](html/tpfi_is2/storage.html) |
| Acceso y auditoría Proxy | [proxy](html/tpfi_is2/proxy.html) |
| Notificaciones Observer | [observer](html/tpfi_is2/observer.html) |
| Servidor | [proxy_server](html/tpfi_is2/proxy_server.html) |
| Cliente de operaciones | [singleton_client](html/tpfi_is2/singleton_client.html) |
| Cliente observador | [observer_client](html/tpfi_is2/observer_client.html) |
| Transporte HTTP | [http_transport](html/tpfi_is2/http_transport.html) |
| Campos, JSON y versión | [corporate_fields](html/tpfi_is2/corporate_fields.html), [json_util](html/tpfi_is2/json_util.html), [version](html/tpfi_is2/version.html) |

Desde la raíz del proyecto, `just docs-build` regenera la API y construye el
sitio Zensical en `site/`; `just docs-serve` la regenera y sirve el sitio. Si
no se dispone de `just`/`uv`, con pdoc instalado se puede regenerar el HTML:

```bash
PYTHONPATH=src python -m pdoc tpfi_is2 tpfi_is2.storage tpfi_is2.proxy tpfi_is2.observer tpfi_is2.proxy_server tpfi_is2.singleton_client tpfi_is2.observer_client tpfi_is2.http_transport tpfi_is2.corporate_fields tpfi_is2.json_util tpfi_is2.version -o docs/html
```

El workflow activo del repositorio está en `../../.github/workflows/docs.yml`;
el ubicado en `../.github/workflows/docs.yml` es una plantilla anidada. La
validación genera pdoc y construye Zensical en PR, inicio manual y push a
`main`, `tpfi/docs-automation`, `tpfi/aws-evidence` o `ci/tpfi-actions-root`.
La publicación en GitHub Pages se permite únicamente para push a `main` o
ejecución manual desde `main`, con `DOCS_DEPLOYMENT_ENABLED=true`; nunca desde
PR ni desde las ramas de entrega. La generación local no acredita la ejecución
alojada en GitHub Actions. El HTML también puede abrirse localmente desde
[la portada de pdoc](html/index.html).
