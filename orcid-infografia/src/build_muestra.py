"""Genera muestra.html autocontenida (fuentes, logo y motor de arte incrustados).

Uso:  python src/build_muestra.py
"""
from __future__ import annotations

import base64
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SRC = RAIZ / "src"
ASSETS = RAIZ / "assets"

FUENTES = [
    ("Fraunces", "normal", ASSETS / "fonts" / "fraunces-variable.woff2"),
    ("Fraunces", "italic", ASSETS / "fonts" / "fraunces-italic-variable.woff2"),
    ("Outfit", "normal", ASSETS / "fonts" / "outfit-variable.woff2"),
]


def facades() -> str:
    trozos: list[str] = []
    for familia, estilo, ruta in FUENTES:
        datos = base64.b64encode(ruta.read_bytes()).decode("ascii")
        trozos.append(
            "@font-face{font-family:%s;font-style:%s;font-weight:300 900;"
            "font-display:block;src:url(data:font/woff2;base64,%s) format('woff2')}"
            % (familia, estilo, datos)
        )
    return "\n".join(trozos)


def logo() -> str:
    svg = (ASSETS / "orcid-id.svg").read_text(encoding="utf-8")
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg).strip()
    svg = svg.replace('role="img"', 'role="img" class="orcid-mark" aria-hidden="true" focusable="false"')
    # el tamaño lo manda el CSS
    svg = svg.replace('viewBox="0 0 72 72"', 'viewBox="0 0 72 72" width="54" height="54"')
    return svg


def main() -> int:
    plantilla = (SRC / "muestra.src.html").read_text(encoding="utf-8")
    arte = (SRC / "arte" / "art.js").read_text(encoding="utf-8")

    html = plantilla.replace("/*__FUENTES__*/", facades())
    html = html.replace("/*__ARTE__*/", arte)
    html = html.replace("__LOGO__", logo())

    faltan = [m for m in ("__FUENTES__", "__ARTE__", "__LOGO__") if m in html]
    if faltan:
        print("ERROR: marcadores sin sustituir:", faltan, file=sys.stderr)
        return 1

    salida = RAIZ / "muestra.html"
    salida.write_text(html, encoding="utf-8")
    print(f"OK {salida} {salida.stat().st_size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
