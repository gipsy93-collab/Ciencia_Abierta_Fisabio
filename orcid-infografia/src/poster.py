"""Render del cartel estático para el boletín.

Salida: boletin/crea-tu-orcid-facil-1080x1920.png

Uso: python src/poster.py
"""
from __future__ import annotations

import pathlib

from playwright.sync_api import sync_playwright

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "boletin"
SALIDA.mkdir(exist_ok=True)


def main() -> int:
    url = (RAIZ / "poster.html").as_uri()
    destino = SALIDA / "crea-tu-orcid-facil-1080x1920.png"
    with sync_playwright() as pw:
        navegador = pw.chromium.launch(channel="chrome")
        pg = navegador.new_page(viewport={"width": 1080, "height": 1920},
                                device_scale_factor=1)
        errores = []
        pg.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errores.append(str(e)))
        pg.goto(url + "?render=1", wait_until="load")
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(900)
        pg.screenshot(path=str(destino), full_page=True)
        alto = pg.evaluate("document.documentElement.scrollHeight")
        ancho = pg.evaluate("document.documentElement.scrollWidth")
        navegador.close()

    print("OK %s %.0f KB · %dx%d" % (destino, destino.stat().st_size / 1024, ancho, alto))
    if errores:
        print("ERRORES: %s" % errores[:3])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
