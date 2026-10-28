"""Genera la pieza completa.

Salidas:
  editor.html  — con editor de textos (para trabajar y exportar)
  index.html   — publicable (sin editor, textos de textos.json incrustados)

Uso:  python src/build.py
"""
from __future__ import annotations

import base64
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SRC = RAIZ / "src"
ASSETS = RAIZ / "assets"

FUENTES = [
    ("Fraunces", "normal", 600, ASSETS / "fonts" / "estaticas" / "fraunces-600.woff2"),
    ("Fraunces", "normal", 700, ASSETS / "fonts" / "estaticas" / "fraunces-700.woff2"),
    ("Fraunces", "italic", 300, ASSETS / "fonts" / "estaticas" / "fraunces-300-italic.woff2"),
    ("Fraunces", "italic", 400, ASSETS / "fonts" / "estaticas" / "fraunces-400-italic.woff2"),
    ("Outfit", "normal", 400, ASSETS / "fonts" / "estaticas" / "outfit-400.woff2"),
    ("Outfit", "normal", 500, ASSETS / "fonts" / "estaticas" / "outfit-500.woff2"),
    ("Outfit", "normal", 600, ASSETS / "fonts" / "estaticas" / "outfit-600.woff2"),
]

RE_CSS_JS = re.compile(r"/\* EDITOR:INICIO \*/.*?/\* EDITOR:FIN \*/", re.S)
RE_HTML = re.compile(r"<!-- EDITOR:INICIO -->.*?<!-- EDITOR:FIN -->", re.S)


def facades() -> str:
    trozos: list[str] = []
    for familia, estilo, peso, ruta in FUENTES:
        datos = base64.b64encode(ruta.read_bytes()).decode("ascii")
        trozos.append(
            "@font-face{font-family:%s;font-style:%s;font-weight:%d;"
            "font-display:block;src:url(data:font/woff2;base64,%s) format('woff2')}"
            % (familia, estilo, peso, datos)
        )
    return "\n".join(trozos)


def logo() -> str:
    svg = (ASSETS / "orcid-id.svg").read_text(encoding="utf-8")
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg).strip()
    svg = svg.replace('role="img"', 'role="img" class="orcid-mark" aria-hidden="true" focusable="false"')
    svg = svg.replace('viewBox="0 0 72 72"', 'viewBox="0 0 72 72" width="102" height="102"')
    return svg


def textos() -> str:
    ruta = SRC / "textos.json"
    if not ruta.exists():
        return "{}"
    datos = json.loads(ruta.read_text(encoding="utf-8-sig"))
    limpio = {k: v for k, v in datos.items() if isinstance(v, str)}
    return json.dumps(limpio, ensure_ascii=False, indent=2)


def montar(con_editor: bool) -> str:
    html = (SRC / "template.html").read_text(encoding="utf-8")

    # se quitan los bloques del editor para la versión publicable
    if not con_editor:
        html = RE_HTML.sub("", html)
        html = RE_CSS_JS.sub("", html)

    html = html.replace("/*__FUENTES__*/", facades())
    html = html.replace("/*__ARTE__*/", (SRC / "arte" / "art.js").read_text(encoding="utf-8"))
    html = html.replace("/*__PLACAS__*/", (SRC / "arte" / "placas.js").read_text(encoding="utf-8"))
    html = html.replace("__TEXTOS__", textos())
    html = html.replace("__LOGO__", logo())

    faltan = [m for m in ("__FUENTES__", "__ARTE__", "__PLACAS__", "__TEXTOS__", "__LOGO__") if m in html]
    if faltan:
        raise SystemExit("ERROR: marcadores sin sustituir: %s" % faltan)

    if not con_editor and ("EDITOR:" in html or "data-editor" in html or "contenteditable" in html):
        raise SystemExit("ERROR: quedan restos del editor en la versión publicable")

    return html


def montar_poster() -> str:
    html = (SRC / "poster.html").read_text(encoding="utf-8")
    html = html.replace("/*__FUENTES__*/", facades())
    html = html.replace("/*__ARTE__*/", (SRC / "arte" / "art.js").read_text(encoding="utf-8"))
    html = html.replace("/*__PLACAS__*/", (SRC / "arte" / "placas.js").read_text(encoding="utf-8"))
    html = html.replace("__LOGO__", logo())
    faltan = [m for m in ("__FUENTES__", "__ARTE__", "__PLACAS__", "__LOGO__") if m in html]
    if faltan:
        raise SystemExit("ERROR: marcadores sin sustituir en el cartel: %s" % faltan)
    return html


def main() -> int:
    editor = montar(True)
    (RAIZ / "editor.html").write_text(editor, encoding="utf-8")
    print("OK editor.html %.0f KB" % ((RAIZ / "editor.html").stat().st_size / 1024))

    publica = montar(False)
    (RAIZ / "index.html").write_text(publica, encoding="utf-8")
    print("OK index.html  %.0f KB" % ((RAIZ / "index.html").stat().st_size / 1024))

    poster = montar_poster()
    (RAIZ / "poster.html").write_text(poster, encoding="utf-8")
    print("OK poster.html %.0f KB" % ((RAIZ / "poster.html").stat().st_size / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
