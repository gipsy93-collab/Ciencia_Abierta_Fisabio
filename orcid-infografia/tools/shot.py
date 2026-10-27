"""Capturas de la pieza con Chromium (Playwright) en varios anchos.

Uso:  python tools/shot.py [archivo.html] [carpeta_salida]
"""
from __future__ import annotations

import pathlib
import sys
import time

from playwright.sync_api import sync_playwright

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ARCHIVO = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "muestra.html"
SALIDA = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else RAIZ / "capturas"
SALIDA.mkdir(parents=True, exist_ok=True)

VISTAS = [
    ("movil", 390, 844, 2),
    ("tablet", 768, 1024, 2),
    ("escritorio", 1440, 900, 1),
]


def main() -> int:
    url = ARCHIVO.resolve().as_uri()
    errores: list[str] = []

    with sync_playwright() as p:
        nav = None
        for intento in ({"channel": "chrome"}, {}):
            try:
                nav = p.chromium.launch(**intento)
                print("navegador:", intento.get("channel", "chromium empaquetado"))
                break
            except Exception as exc:  # noqa: BLE001
                print("fallo lanzando", intento, exc)
        if nav is None:
            print("ERROR: no hay navegador disponible", file=sys.stderr)
            return 1

        for nombre, ancho, alto, escala in VISTAS:
            ctx = nav.new_context(
                viewport={"width": ancho, "height": alto},
                device_scale_factor=escala,
                reduced_motion="no-preference",
            )
            pagina = ctx.new_page()
            pagina.on("console", lambda m: errores.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)
            pagina.on("pageerror", lambda e: errores.append(f"pageerror: {e}"))
            pagina.goto(url, wait_until="load")
            pagina.evaluate("document.fonts.ready")
            pagina.wait_for_timeout(1400)
            # desplazar para activar la lámina diferida
            pagina.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.55)")
            pagina.wait_for_timeout(700)
            pagina.evaluate("window.scrollTo(0, 0)")
            pagina.wait_for_timeout(400)
            destino = SALIDA / f"muestra-{nombre}.png"
            pagina.screenshot(path=str(destino), full_page=True)
            print("OK", destino, destino.stat().st_size // 1024, "KB")
            ctx.close()

        # modal abierto
        ctx = nav.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        pagina = ctx.new_page()
        pagina.on("pageerror", lambda e: errores.append(f"pageerror(modal): {e}"))
        pagina.goto(url, wait_until="load")
        pagina.evaluate("document.fonts.ready")
        pagina.click("[data-abrir='quiz']")
        pagina.wait_for_timeout(400)
        pagina.click("[data-opcion='si']")
        pagina.wait_for_timeout(900)
        destino = SALIDA / "muestra-modal.png"
        pagina.screenshot(path=str(destino))
        print("OK", destino, destino.stat().st_size // 1024, "KB")

        # movil con modal
        pagina.set_viewport_size({"width": 390, "height": 844})
        pagina.wait_for_timeout(500)
        destino = SALIDA / "muestra-modal-movil.png"
        pagina.screenshot(path=str(destino))
        print("OK", destino, destino.stat().st_size // 1024, "KB")
        ctx.close()
        nav.close()

    if errores:
        print("\n--- consola ---")
        for e in errores:
            print(e)
    else:
        print("\nconsola: sin errores ni avisos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
