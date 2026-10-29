"""Verificación de la infografía publicable y del editor.

- index.html: 3 anchos, consola limpia, sin peticiones externas, sin desbordamiento,
  8 nodos, 8 fichas, cada ficha pinta su lámina, las 4 interacciones y el teclado.
- editor.html: edición, persistencia, exportación y descarga final.
- Capturas en capturas/.

Uso: python src/verificar.py
"""
from __future__ import annotations

import json
import pathlib
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


VACIA = """
    (cv) => {
        const ctx = cv.getContext('2d');
        const d = ctx.getImageData(0, 0, cv.width, cv.height).data;
        let min = 255, max = 0;
        for (let i = 0; i < d.length; i += 4 * 97) {
            const v = d[i] + d[i+1] + d[i+2];
            if (v < min) min = v;
            if (v > max) max = v;
        }
        return (max - min) < 30;
    }
"""


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
            pg.wait_for_timeout(1600)

            check(not errores, f"{nombre}: consola limpia {errores[:3]}")
            check(not externas, f"{nombre}: sin peticiones externas {externas[:3]}")

            desborde = pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            check(desborde <= 1, f"{nombre}: sin desbordamiento horizontal ({desborde}px)")

            nodos = pg.eval_on_selector_all(".nodo", "els => els.length")
            check(nodos == 8, f"{nombre}: 8 nodos en el anillo ({nodos})")

            fichas = pg.eval_on_selector_all(".ficha", "els => els.length")
            check(fichas == 8, f"{nombre}: 8 ventanas ({fichas})")

            cerradas = pg.evaluate("Array.from(document.querySelectorAll('.ficha')).every(f => f.hidden)")
            check(cerradas, f"{nombre}: las ventanas arrancan cerradas")

            if nombre == "movil":
                pg.screenshot(path=str(CAPTURAS / "pieza-movil.png"), full_page=True)
                pg.screenshot(path=str(CAPTURAS / "m-hero.png"))
            else:
                pg.screenshot(path=str(CAPTURAS / f"pieza-{nombre}.png"))

            # cada nodo abre su ficha y pinta su lámina
            for i in range(1, 9):
                nid = f"n0{i}"
                pg.click(f'.nodo[data-ficha="{nid}"]')
                pg.wait_for_timeout(700)
                abierta = pg.evaluate(
                    f"""() => {{
                        const f = document.getElementById('f-{nid}');
                        return {{
                            visible: !f.hidden && !document.getElementById('velo').hidden,
                            pintada: f.querySelector('canvas').dataset.pintada === '1',
                            vacia: ({VACIA.strip()})(f.querySelector('canvas')),
                            hash: location.hash
                        }};
                    }}"""
                )
                check(abierta["visible"], f"{nombre}: {nid} abre su ventana")
                check(abierta["pintada"] and not abierta["vacia"], f"{nombre}: {nid} pinta la lámina")
                check(abierta["hash"] == "#" + nid, f"{nombre}: {nid} deja enlace directo")
                if nombre == "escritorio" and nid in ("n01", "n05", "n08"):
                    pg.screenshot(path=str(CAPTURAS / f"d-{nid}.png"))
                if nombre == "escritorio" and nid == "n01":
                    pg.screenshot(path=str(CAPTURAS / "ficha-escritorio.png"))
                if nombre == "movil" and nid == "n01":
                    pg.screenshot(path=str(CAPTURAS / "ficha-movil.png"))
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(200)

            if nombre == "movil":
                lista = pg.evaluate("getComputedStyle(document.querySelector('.nodo')).display")
                check(lista == "flex", f"móvil: el anillo pasa a lista de conexiones ({lista})")
                pg.click('.nodo[data-ficha="n07"]')
                pg.wait_for_timeout(600)
                xok = pg.evaluate("""() => {
                    const c = document.querySelector('#f-n07 .cerrar').getBoundingClientRect();
                    return c.top >= 0 && c.bottom <= innerHeight && c.right <= innerWidth && c.width >= 40;
                }""")
                check(xok, "móvil: la X de la ventana queda a la vista")
                desliza = pg.evaluate("""() => {
                    const v = document.getElementById('velo');
                    v.scrollTo(0, v.scrollHeight);
                    return v.scrollTop;
                }""")
                check(desliza > 0, f"móvil: la ventana se desplaza ({desliza:.0f}px)")
                pg.screenshot(path=str(CAPTURAS / "ficha-movil-abajo.png"))
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(300)

            if nombre == "escritorio":
                # 1 · prueba rápida
                pg.click('.nodo[data-ficha="n01"]')
                pg.wait_for_timeout(500)
                pg.click('#f-n01 [data-opcion="si"]')
                check(pg.is_visible("#f-n01 [data-sello]"), "quiz: sella la respuesta")
                pg.screenshot(path=str(CAPTURAS / "quiz.png"))
                pg.keyboard.press("Escape")

                # 2 · fórmulas + copiar
                pg.click('.nodo[data-ficha="n02"]')
                pg.wait_for_timeout(500)
                enlace = pg.evaluate("""() => {
                    const a = document.querySelector('#f-n02 a.boton');
                    return a ? {href: a.href, target: a.target, rel: a.rel} : null;
                }""")
                check(enlace and "fs-pe010-firmas-publicaciones.pdf" in enlace["href"]
                      and enlace["target"] == "_blank" and "noopener" in (enlace["rel"] or ""),
                      f"n02: enlace al procedimiento PE010 {enlace}")
                check(not pg.is_visible("#formulas"), "fórmulas: el panel arranca cerrado")
                pg.click('#f-n02 [data-toggle="formulas"]')
                check(pg.is_visible("#formulas"), "fórmulas: despliega el panel")
                pg.click("#formulas .copiar")
                pg.wait_for_timeout(250)
                check(pg.inner_text("#formulas .copiar").strip().lower() in ("copiado", "copiar"),
                      "fórmulas: el botón de copiar responde")
                pg.screenshot(path=str(CAPTURAS / "formulas.png"))

                # navegación con teclado dentro de la ventana
                pg.keyboard.press("ArrowRight")
                pg.wait_for_timeout(400)
                check(not pg.is_hidden("#f-n03"), "teclado: la flecha pasa a la siguiente")
                pg.keyboard.press("ArrowLeft")
                pg.wait_for_timeout(400)
                check(not pg.is_hidden("#f-n02"), "teclado: la flecha vuelve a la anterior")
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(250)

                # 3 · simulador
                pg.click('.nodo[data-ficha="n05"]')
                pg.wait_for_timeout(500)
                pg.click('#f-n05 [data-vis="todo"]')
                check(pg.get_attribute('#f-n05 [data-vis="todo"]', "aria-pressed") == "true",
                      "visibilidad: marca la opción")
                check("Así te encuentran" in pg.inner_text("#f-n05 [data-aviso]"),
                      "visibilidad: muestra el comentario")
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(250)

                # 4 · + Add
                pg.click('.nodo[data-ficha="n07"]')
                pg.wait_for_timeout(500)
                pg.click("#f-n07 details summary")
                check(pg.is_visible("#f-n07 details p"), "+ Add: despliega el detalle")

                pg.keyboard.press("Escape")
                check(pg.is_hidden("#velo"), "cerrar: Escape devuelve a la lámina")

                # sin restos del editor
                check(pg.eval_on_selector_all('[contenteditable="true"]', "e => e.length") == 0,
                      "publicable: sin elementos editables")
                check(pg.query_selector("#editbar") is None, "publicable: sin barra de edición")

                # enlace directo
                pg2 = navegador.new_page(viewport={"width": 1440, "height": 900})
                pg2.goto(url + "#n06", wait_until="load")
                pg2.wait_for_timeout(900)
                check(pg2.evaluate("() => !document.getElementById('f-n06').hidden"),
                      "enlace directo: #n06 abre su ventana")
                pg2.close()

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

        pg.once("dialog", lambda d: d.accept())
        pg.click("#btn-reset")
        pg.wait_for_timeout(300)
        check(pg.inner_text('[data-edit="portada.titulo2"]').strip() == "fácil",
              "editor: restablece los textos")
        pg.close()

        # ---- contraste -------------------------------------------------
        pares = [
            ("marca de seccion sobre papel", "#1D0F44", "#F7F1E4"),
            ("sello sobre papel alto", "#1D0F44", "#FCF8EE"),
            ("tinta sobre papel", "#1D0F44", "#F7F1E4"),
            ("tinta suave sobre papel", "#5B4B7E", "#F7F1E4"),
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
