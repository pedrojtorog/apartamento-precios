# Apartamento – Revisor de precios LG/Samsung

Este repo revisa automáticamente, una vez al día, el precio que muestran las
páginas **oficiales** de LG Colombia y Samsung Colombia para algunos modelos
de nevecón Side by Side. Esas páginas cargan el precio con JavaScript (no está
en el HTML inicial), así que un `curl`/fetch simple no lo ve — por eso este
repo usa un navegador real automatizado (Playwright) en vez de una petición
HTTP simple.

## Cómo funciona

1. `productos.json` — lista de productos a revisar (nombre, URL, fuente).
2. `scrape_precios.py` — abre cada URL con un navegador headless, espera a
   que cargue el precio, lo extrae del texto visible de la página, y guarda:
   - `precios_actuales.json`: snapshot de la última corrida.
   - `historial_precios.csv`: una fila por producto y por corrida (se va
     acumulando con el tiempo).
   - `screenshots/<id>.png`: captura de cada página, útil para revisar
     manualmente si el precio no se detectó bien.
3. `.github/workflows/revisar-precios.yml` — corre el script todos los días a
   las 8:00 am hora Bogotá, y si el resultado cambió, hace commit automático.

## Agregar o quitar productos

Edita `productos.json`. Cada entrada necesita `id`, `nombre`, `url` y `fuente`.

## Correrlo manualmente (sin esperar al cron)

Desde la pestaña **Actions** de este repo en GitHub, entra al workflow
"Revisar precios LG/Samsung" y usa el botón **Run workflow**.

## Correrlo localmente

```bash
pip install -r requirements.txt
playwright install --with-deps chromium
python scrape_precios.py
```

## Limitaciones conocidas

- Si LG o Samsung cambian el diseño de su página, el script puede dejar de
  encontrar el precio (`estado: sin_precio_visible`). En ese caso, revisar el
  screenshot correspondiente en `screenshots/` para ver qué está pasando.
- El precio detectado es el número más bajo encontrado en la página — en la
  mayoría de los casos corresponde al precio con descuento vigente, pero vale
  la pena confirmar visualmente con el screenshot si hay dudas.
