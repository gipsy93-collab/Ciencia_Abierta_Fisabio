"""Verificación de la pieza publicable y del editor.

- index.html: 3 anchos, sin errores de consola, sin peticiones externas,
  sin desbordamiento horizontal, 8 láminas pintadas, 4 interacciones.
- editor.html: edición, persistencia, exportación y descarga final.
- Capturas en capturas/.

Uso: python src/verificar.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

from playwright.sync_api import sync_playwright

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CAPTURAS = RAIZ / "capturas"
CAPTURAS.mkdir(exist_ok=True)

fallos: list[str] = []
notas: list[str] = []


def check(cond: bool, msg: str) -> None:
    if cond:
        notas.append("ok   " + msg)
    else:
        fallos.append("FALLO " + msg)


def contraste(a: str, b: str) -> float:
    def lum(h: str) -> float:
        h = h.lstrip("#")
        v = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
        v = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in v]
        return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]

    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def main() -> int:
    url = (RAIZ / "index.html").as_uri()
    editor_url = (RAIZ / "editor.html").as_uri()

    with sync_playwright() as pw:
        navegador = pw.chromium.launch(channel="chrome")

        for nombre, ancho, alto, escala in [
            ("escritorio", 1440, 900, 1),
            ("tablet", 768, 1024, 1),
            ("movil", 390, 844, 2),
        ]:
            errores: list[str] = []
            externas: list[str] = []
            pg = navegador.new_page(viewport={"width": ancho, "height": alto},
                                    device_scale_factor=escala)
            pg.on("console", lambda m: errores.append(f"{m.type}: {m.text}")
                  if m.type in ("error", "warning") else None)
            pg.on("pageerror", lambda e: errores.append(f"pageerror: {e}"))
            pg.on("request", lambda r: externas.append(r.url)
                  if not r.url.startswith("file://") and not r.url.startswith("data:") else None)
            pg.goto(url, wait_until="load")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(1800)

            check(not errores, f"{nombre}: consola limpia {errores[:3]}")
            check(not externas, f"{nombre}: sin peticiones externas {externas[:3]}")

            desborde = pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            check(desborde <= 1, f"{nombre}: sin desbordamiento horizontal ({desborde}px)")

            secciones = pg.eval_on_selector_all(".seccion", "els => els.length")
            check(secciones == 8, f"{nombre}: 8 secciones ({secciones})")

            nodos = pg.eval_on_selector_all(".nodo", "els => els.length")
            check(nodos == 8, f"{nombre}: 8 nodos en la portada ({nodos})")

            vacias = pg.evaluate("""
                Array.from(document.querySelectorAll('canvas[data-placa]')).filter(cv => {
                    const ctx = cv.getContext('2d');
                    const d = ctx.getImageData(0, 0, cv.width, cv.height).data;
                    let min = 255, max = 0;
                    for (let i = 0; i < d.length; i += 4 * 97) {
                        const v = d[i] + d[i+1] + d[i+2];
                        if (v < min) min = v;
                        if (v > max) max = v;
                    }
                    return (max - min) < 30;
                }).length
            """)
            check(vacias == 0, f"{nombre}: 8 láminas pintadas ({vacias} vacías)")

            if nombre == "escritorio":
                pg.screenshot(path=str(CAPTURAS / "pieza-escritorio.png"), full_page=True)
                pg.screenshot(path=str(CAPTURAS / "d-hero.png"))

                # 1 · prueba
                pg.click('[data-abrir="quiz"]')
                check(pg.is_visible("#velo"), "quiz: abre el diálogo")
                pg.click('[data-opcion="si"]')
                check(pg.is_visible("#sello"), "quiz: sella la respuesta")
                pg.screenshot(path=str(CAPTURAS / "modal.png"))
                pg.keyboard.press("Escape")
                check(not pg.is_visible("#velo"), "quiz: Escape cierra")

                # 2 · fórmulas + copiar
                pg.click('[data-toggle="formulas"]')
                check(pg.is_visible("#formulas"), "fórmulas: despliega el panel")
                pg.click("#formulas .copiar")
                pg.wait_for_timeout(200)
                check(pg.inner_text("#formulas .copiar").strip().lower() in ("copiado", "copiar"),
                      "fórmulas: botón de copiar responde")
                pg.screenshot(path=str(CAPTURAS / "formulas.png"))

                # 3 · simulador
                pg.click('[data-vis="todo"]')
                check(pg.get_attribute('[data-vis="todo"]', "aria-pressed") == "true",
                      "visibilidad: marca la opción")
                check("Así te encuentran" in pg.inner_text("#aviso-vis"),
                      "visibilidad: muestra el comentario")

                # 4 · + Add
                pg.click("#n07 details summary")
                check(pg.is_visible("#n07 details p"), "+ Add: despliega el detalle")

                # navegación
                pg.click('.riel a[data-sec="n05"]')
                pg.wait_for_timeout(900)
                y = pg.evaluate("window.scrollY")
                check(y > 1000, f"navegación: el riel lleva a la sección ({y:.0f}px)")

                # sin restos del editor
                check(pg.eval_on_selector_all('[contenteditable="true"]', "e => e.length") == 0,
                      "publicable: sin elementos editables")
                check(pg.query_selector("#editbar") is None, "publicable: sin barra de edición")

                # secciones para captura
                for sec in ("n01", "n05", "n08"):
                    pg.evaluate(f"window.scrollTo({{top: document.getElementById('{sec}').offsetTop, behavior: 'instant'}})")
                    pg.wait_for_timeout(400)
                    pg.screenshot(path=str(CAPTURAS / f"d-{sec}.png"))

            if nombre == "movil":
                pg.screenshot(path=str(CAPTURAS / "pieza-movil.png"), full_page=True)
                pg.screenshot(path=str(CAPTURAS / "m-hero.png"))
                pg.evaluate("window.scrollTo({top: document.getElementById('n04').offsetTop, behavior: 'instant'})")
                pg.wait_for_timeout(400)
                pg.screenshot(path=str(CAPTURAS / "m-n04.png"))
                pg.close()
                continue

            pg.close()

        # ---- editor ----------------------------------------------------
        contexto = navegador.new_context(viewport={"width": 1280, "height": 900},
                                         accept_downloads=True)
        pg = contexto.new_page()
        pg.goto(editor_url, wait_until="load")
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(1200)

        check(pg.query_selector("#editbar") is not None, "editor: barra presente")
        editables = pg.eval_on_selector_all("[data-edit]", "e => e.length")
        check(editables > 40, f"editor: textos editables ({editables})")

        pg.click("#btn-editar")
        activos = pg.eval_on_selector_all('[contenteditable="true"]', "e => e.length")
        check(activos == editables, f"editor: activa la edición ({activos}/{editables})")

        pg.evaluate("""
            const el = document.querySelector('[data-edit="portada.titulo2"]');
            el.textContent = 'sin miedo';
            el.dispatchEvent(new Event('input', {bubbles: true}));
        """)
        pg.wait_for_timeout(200)
        pg.reload(wait_until="load")
        pg.wait_for_timeout(800)
        check("sin miedo" in pg.inner_text('[data-edit="portada.titulo2"]'),
              "editor: el cambio persiste al recargar")

        pg.click("#btn-editar")
        with pg.expect_download() as descarga:
            pg.click("#btn-exportar")
        ruta = descarga.value.path()
        datos = json.loads(pathlib.Path(ruta).read_text(encoding="utf-8"))
        check("portada.titulo2" in datos, "editor: exporta textos.json")

        with pg.expect_download() as descarga2:
            pg.click("#btn-final")
        final = pathlib.Path(descarga2.value.path()).read_text(encoding="utf-8")
        check("data-editor" not in final, "editor: la versión final no lleva editor")
        check('contenteditable="true"' not in final, "editor: la versión final no es editable")
        check("sin miedo" in final, "editor: la versión final lleva los textos nuevos")

        pg.screenshot(path=str(CAPTURAS / "editor.png"))

        # restablecer
        pg.once("dialog", lambda d: d.accept())
        pg.click("#btn-reset")
        pg.wait_for_timeout(300)
        check(pg.inner_text('[data-edit="portada.titulo2"]').strip() == "fácil",
              "editor: restablece los textos")
        pg.close()

        # ---- contraste -------------------------------------------------
        pares = [
            ("texto verde sobre papel", "#3F7A0C", "#F7F1E4"),
            ("sello sobre papel alto", "#C4002E", "#FCF8EE"),
            ("tinta sobre papel", "#1D0F44", "#F7F1E4"),
            ("tinta suave sobre papel", "#5B4B7E", "#F7F1E4"),
            ("rojo de texto sobre papel alto", "#C4002E", "#FCF8EE"),
        ]
        for etiqueta, a, b in pares:
            r = contraste(a, b)
            check(r >= 4.5, f"contraste AA · {etiqueta}: {r:.2f}")

        navegador.close()

    print("\n".join(notas))
    if fallos:
        print("\n".join(fallos))
        print(f"\n{len(fallos)} fallo(s)")
        return 1
    print(f"\nTodo correcto · {len(notas)} comprobaciones")
    return 0


if __name__ == "__main__":
    sys.exit(main())
