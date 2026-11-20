#!/usr/bin/env python3
"""
Revisa precios de neveras directamente en las páginas oficiales de LG y Samsung
Colombia, que cargan el precio vía JavaScript (por eso no se puede leer con un
fetch simple). Usa un navegador real (headless) con Playwright para renderizar
la página como lo haría una persona, y luego extrae el precio del DOM.

Uso:
    python scrape_precios.py

Salida:
    - precios_actuales.json  (snapshot de la corrida actual)
    - historial_precios.csv  (se va acumulando, una fila por corrida y producto)
"""
import json
import csv
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_DIR = Path(__file__).parent
PRODUCTOS_FILE = BASE_DIR / "productos.json"
SALIDA_JSON = BASE_DIR / "precios_actuales.json"
HISTORIAL_CSV = BASE_DIR / "historial_precios.csv"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"

# Patrón para encontrar precios en pesos colombianos en el texto de la página,
# p.ej. "$ 5.616.900" o "$5.616.900". Exige al menos 6 dígitos (de lo contrario
# captura cosas como "$99.900" de accesorios/kombos, no el precio del producto).
PATRON_PRECIO = re.compile(r"\$\s?[\d\.]{7,}")


def extraer_precio_de_texto(texto: str) -> list[str]:
    """Devuelve todos los precios candidatos encontrados en el texto, sin duplicar."""
    candidatos = PATRON_PRECIO.findall(texto)
    vistos = []
    for c in candidatos:
        c_limpio = c.strip()
        if c_limpio not in vistos:
            vistos.append(c_limpio)
    return vistos


def revisar_producto(page, producto: dict) -> dict:
    url = producto["url"]
    resultado = {
        "id": producto["id"],
        "nombre": producto["nombre"],
        "url": url,
        "fuente": producto["fuente"],
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "precios_encontrados": [],
        "precio_principal": None,
        "estado": "pendiente",
        "error": None,
    }

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)

        # Cerrar banner de cookies si aparece (común en ambos sitios)
        for texto_boton in ["Accept all", "Aceptar todo", "Aceptar", "ACEPTAR"]:
            try:
                boton = page.get_by_text(texto_boton, exact=False).first
                if boton.is_visible(timeout=2000):
                    boton.click(timeout=2000)
                    break
            except Exception:
                pass

        # Dar tiempo a que el JS cargue el precio (es exactamente lo que
        # WebFetch no puede hacer: esperar y ejecutar scripts de la página)
        page.wait_for_timeout(6000)

        # Intento 1: acotar la búsqueda a la zona de compra (donde está el
        # precio del producto principal), para no mezclar precios de
        # productos relacionados, cuotas de financiamiento o kombos.
        # Samsung normalmente pone el precio dentro de un contenedor cerca
        # del botón "Comprar ahora" / "Añadir al carrito".
        zona_precio = None
        for selector in [
            "[class*='price']",
            "[class*='Price']",
            "[data-testid*='price']",
            "main",
        ]:
            try:
                loc = page.locator(selector).first
                if loc.count() > 0 and loc.is_visible(timeout=1000):
                    zona_precio = loc.inner_text(timeout=2000)
                    if PATRON_PRECIO.search(zona_precio):
                        break
            except Exception:
                continue

        texto_relevante = zona_precio if zona_precio else page.inner_text("body")
        precios = extraer_precio_de_texto(texto_relevante)

        # Si la zona acotada no trajo nada, caer de vuelta al texto completo
        if not precios:
            precios = extraer_precio_de_texto(page.inner_text("body"))

        resultado["precios_encontrados"] = precios
        if precios:
            precios_num = []
            for p in precios:
                limpio = re.sub(r"[^\d]", "", p)
                if limpio:
                    precios_num.append(int(limpio))
            # Filtra valores irreales para un electrodoméstico de esta gama
            # (descarta cuotas chiquitas, ahorros en pesos, etc.)
            precios_plausibles = [n for n in precios_num if 1_000_000 <= n <= 30_000_000]
            if precios_plausibles:
                # El precio de contado con descuento suele ser el más bajo
                # DENTRO del rango plausible (evita elegir el precio "antes de descuento")
                resultado["precio_principal"] = min(precios_plausibles)
            resultado["estado"] = "ok" if precios_plausibles else "precio_no_confiable"
        else:
            resultado["estado"] = "sin_precio_visible"

    except PlaywrightTimeoutError as e:
        resultado["estado"] = "timeout"
        resultado["error"] = str(e)
    except Exception as e:
        resultado["estado"] = "error"
        resultado["error"] = str(e)

    # Screenshot de respaldo siempre, para poder revisar manualmente si algo falló
    try:
        SCREENSHOTS_DIR.mkdir(exist_ok=True)
        screenshot_path = SCREENSHOTS_DIR / f"{producto['id']}.png"
        page.screenshot(path=str(screenshot_path), full_page=False)
    except Exception:
        pass

    return resultado


def main():
    productos = json.loads(PRODUCTOS_FILE.read_text(encoding="utf-8"))
    resultados = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="es-CO",
            timezone_id="America/Bogota",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 900},
        )
        page = context.new_page()

        for producto in productos:
            print(f"Revisando: {producto['nombre']} ...")
            resultado = revisar_producto(page, producto)
            resultados.append(resultado)
            estado = resultado["estado"]
            precio = resultado["precio_principal"]
            print(f"  -> estado={estado} precio_principal={precio}")

        browser.close()

    # Guardar snapshot JSON de esta corrida
    SALIDA_JSON.write_text(
        json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Acumular en historial CSV
    es_nuevo = not HISTORIAL_CSV.exists()
    with open(HISTORIAL_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if es_nuevo:
            writer.writerow(
                ["timestamp_utc", "id", "nombre", "fuente", "estado", "precio_principal", "url"]
            )
        for r in resultados:
            writer.writerow(
                [
                    r["timestamp_utc"],
                    r["id"],
                    r["nombre"],
                    r["fuente"],
                    r["estado"],
                    r["precio_principal"],
                    r["url"],
                ]
            )

    print(f"\nListo. {len(resultados)} productos revisados.")
    print(f"Snapshot: {SALIDA_JSON}")
    print(f"Historial: {HISTORIAL_CSV}")


if __name__ == "__main__":
    main()
