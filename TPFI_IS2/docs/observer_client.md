# ObserverClient

`observerclient.py` se suscribe mediante HTTP POST sobre TCP y recibe un flujo
NDJSON en una respuesta HTTP abierta. El contrato se detalla en
[Protocolo HTTP](protocolo_http.md).

```bash
python observerclient.py -s=localhost -p=8080 -o=notificaciones.json --retry-interval=30 -v
```

`subscribe()` espera la confirmación del servidor antes de retornar. `listen()`
procesa cada actualización JSON y `notify()` la muestra en consola y la agrega al
archivo opcional. Una interrupción hace que `run()` vuelva a conectar y suscribir
tras el intervalo configurado. Ctrl+C termina la ejecución.

Las pruebas de integración verifican múltiples actualizaciones y la reconexión
con nueva suscripción, incluidos caracteres UTF-8 fragmentados entre lecturas TCP.
