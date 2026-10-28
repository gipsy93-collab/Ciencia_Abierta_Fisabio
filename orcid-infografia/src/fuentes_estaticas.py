"""Genera las fuentes estáticas que incrusta la pieza.

Las variables de Google Fonts traen por defecto pesos extremos
(Fraunces 900 y Outfit 100), y hay motores que, al no aplicar el eje,
caen a ese peso por defecto: los titulares salían negros y el texto finísimo.
Instanciar en los pesos que usa el diseño lo deja igual en todos los motores.

Uso:  python src/fuentes_estaticas.py
Requiere fonttools y brotli (pip install fonttools brotli).
"""
from __future__ import annotations

import pathlib
import sys

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "assets" / "fonts"
DESTINO = ORIGEN / "estaticas"

# (archivo de origen, archivo de salida, ejes)
INSTANCIAS = [
    ("fraunces-variable.woff2", "fraunces-600.woff2", {"wght": 600, "opsz": 96}),
    ("fraunces-variable.woff2", "fraunces-700.woff2", {"wght": 700, "opsz": 24}),
    ("fraunces-italic-variable.woff2", "fraunces-300-italic.woff2", {"wght": 300, "opsz": 20}),
    ("fraunces-italic-variable.woff2", "fraunces-400-italic.woff2", {"wght": 400, "opsz": 96}),
    ("outfit-variable.woff2", "outfit-400.woff2", {"wght": 400}),
    ("outfit-variable.woff2", "outfit-500.woff2", {"wght": 500}),
    ("outfit-variable.woff2", "outfit-600.woff2", {"wght": 600}),
]


def main() -> int:
    DESTINO.mkdir(parents=True, exist_ok=True)
    total = 0
    for origen, salida, ejes in INSTANCIAS:
        fuente = TTFont(ORIGEN / origen)
        instantiateVariableFont(fuente, ejes, inplace=True, updateFontNames=False)
        fuente.flavor = "woff2"
        ruta = DESTINO / salida
        fuente.save(ruta)
        kb = ruta.stat().st_size / 1024
        total += kb
        print("OK %-30s %6.1f KB  %s" % (salida, kb, ejes))
    print("total %.1f KB" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
