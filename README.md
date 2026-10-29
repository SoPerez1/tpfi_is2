# TPFI IS2

El aplicativo y las instrucciones de ejecución están en [TPFI_IS2/README.md](TPFI_IS2/README.md).

Para la exposición, consultar [Comandos para mostrar el TP](COMANDOS_DEMO.md)
(instalación, demo en tres terminales, errores controlados y pruebas).

Los workflows **activos** de este repositorio están en [`.github/workflows/`](.github/workflows/):
CI y documentación usan `TPFI_IS2/` para los comandos. Los archivos en
[`TPFI_IS2/.github/workflows/`](TPFI_IS2/.github/workflows/) son plantillas
anidadas, no descubiertas por GitHub desde la raíz de este repositorio.

La primera ejecución remota debe comprobarse mediante push de
`ci/tpfi-actions-root`: las ramas anteriores aún no contienen estas entradas
en su propio ref y `workflow_dispatch` requiere registro en la rama por defecto.
Las verificaciones locales no prueban que los jobs alojados hayan terminado.
