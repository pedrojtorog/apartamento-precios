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

- **LG Colombia no está incluido.** Se probó y su sitio (lg.com/co) bloquea
  las solicitudes del servidor de GitHub Actions con un firewall anti-bot
  (Akamai) — devuelve "Access Denied" antes de siquiera cargar la página.
  No es un problema de JavaScript ni de selectores: es un bloqueo a nivel de
  red que no se puede resolver ajustando el script. Para ver el precio de LG
  hay que seguir revisándolo manualmente (abrir la página en un navegador
  normal) o desde un retailer (Falabella, Alkosto, Ktronix, Homecenter).
- **El Bespoke RS23CB760A12CO/RS23CB70NA12CO tampoco está incluido.**
  Se confirmó que samsung.com/co ya no lo tiene en su catálogo de la
  categoría Side by Side — cualquier URL que se intente para ese modelo
  redirige al home. Sigue disponible en retailers (Falabella, Homecenter),
  solo no en la tienda directa de Samsung.
- Si Samsung cambia el diseño de su página, el script puede dejar de
  encontrar el precio (`estado: sin_precio_visible` o `precio_no_confiable`).
  En ese caso, revisar el screenshot correspondiente en `screenshots/`.
- Si una URL de producto deja de existir y Samsung redirige a otra página
  (p.ej. al home), el estado queda como `ok_pero_redirigido_revisar` —
  revisar manualmente antes de confiar en ese precio.
- El precio detectado es el más bajo dentro de un rango plausible
  (1.000.000–30.000.000 COP) encontrado cerca del bloque de compra — pensado
  para electrodomésticos grandes. Para otro tipo de producto, ajustar ese
  rango en `scrape_precios.py`.
