"""Compone el arte del cerebro con el original de Genially.

El visor de la plantilla original («Infografía Neurociencia»,
`view.genially.com/665edab80214af0014a70aba`) guarda el dibujo en dos capas:

- la **línea**: PNG con transparencia (966 x 811 la vista lateral, 697 x 866
  cada mitad de la vista superior), negro puro y antialias limpio;
- el **color**: una mancha por zona, en SVG vectorial.

La captura que se usó al principio de la pieza (516 x 433) era una reducción de
esa composición: de ahí el aspecto lavado. Aquí se recomponen las dos capas en
un SVG por lámina —relleno vectorial, línea original— y se guardan en
`assets/cerebro/`. `build.py` los incrusta tal cual.

Datos de origen en `assets/origen/`:
- `zonas.json` — manchas de color con su caja en pantalla y su `viewBox`.
- `tinta_apaisado.png` — unión de las seis capas de línea (966 x 811).
- `tinta_vertical_izq.png`, `tinta_vertical_der.png` — mitades (697 x 866).

Uso:
    python src/compone_cerebro.py
"""

import base64
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGEN = os.path.join(BASE, "assets", "origen")
DESTINO = os.path.join(BASE, "assets", "cerebro")

# Cajas en pantalla de las imágenes de línea (medidas en el visor, 1440x900).
CAJA_AP = (438.0, 280.0, 581.0, 488.0)
CAJA_VE = (524.0, 289.0, 385.0, 469.0)
TAM_AP = (966, 811)
ESCALA_VE = 1.85                     # unidades nativas por píxel de pantalla
TAM_VE = (round(CAJA_VE[2] * ESCALA_VE), round(CAJA_VE[3] * ESCALA_VE))

TINTAS = {
    "apaisado": [("tinta_apaisado.png", CAJA_AP, 1.0)],
    "vertical": [("tinta_vertical_izq.png", (529.0, 289.0, 380.0, 467.0), ESCALA_VE),
                 ("tinta_vertical_der.png", (524.0, 289.0, 377.0, 469.0), ESCALA_VE)],
}

# Lámina -> (arte, color de la zona que va coloreada; None = todas)
LAMINAS = [
    ("brain_cover", "apaisado", None),
    ("brain_m1", "apaisado", "#FAAB6D"),
    ("brain_m2", "apaisado", "#F07575"),
    ("brain_m3", "apaisado", "#BDB7ED"),
    ("brain_m4", "apaisado", "#F6B6DC"),
    ("brain_m5", "apaisado", "#B2E084"),
    ("brain_p2", "vertical", None),
    ("brain_p2m1", "vertical", "#FAAB6D"),
    ("brain_p2m2", "vertical", "#F6B6DC"),
]


def _data_uri(ruta):
    with open(ruta, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def _mancha(z, caja, escala, color):
    """Coloca una mancha de color en el lienzo, con el relleno indicado."""
    b, (vx, vy, vw, vh) = z["box"], z["viewBox"]
    x = (b["x"] - caja[0]) * escala
    y = (b["y"] - caja[1]) * escala
    sx, sy = (b["w"] * escala) / vw, (b["h"] * escala) / vh
    cuerpo = z["path"].replace(z["color"], color)
    return f'<g transform="translate({x:.2f},{y:.2f}) scale({sx:.5f},{sy:.5f})">{cuerpo}</g>'


def compone(arte, zonas, color):
    """Devuelve el SVG de una lámina (relleno vectorial + línea original).

    Las manchas se pintan dos veces: primero todas en blanco —así se tapan los
    desbordes de una zona sobre la vecina y no quedan huecos dentro del
    cerebro— y después la que va coloreada (o todas, en la portada).
    """
    if arte == "apaisado":
        caja, (ancho, alto), escala = CAJA_AP, TAM_AP, TAM_AP[0] / CAJA_AP[2]
    else:
        caja, (ancho, alto), escala = CAJA_VE, TAM_VE, ESCALA_VE

    partes = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}">']
    for z in zonas:
        partes.append(_mancha(z, caja, escala, "#FFFFFF"))
    for z in zonas:
        if color and z["color"] != color:
            continue
        partes.append(_mancha(z, caja, escala, z["color"]))

    for archivo, caja_img, factor in TINTAS[arte]:
        x = (caja_img[0] - caja[0]) * escala
        y = (caja_img[1] - caja[1]) * escala
        w = caja_img[2] * escala
        h = caja_img[3] * escala
        partes.append(
            f'<image x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'preserveAspectRatio="none" href="{_data_uri(os.path.join(ORIGEN, archivo))}"/>'
        )

    partes.append("</svg>")
    return "\n".join(partes)


def main(verboso=True):
    zonas = json.load(open(os.path.join(ORIGEN, "zonas.json"), encoding="utf-8"))
    os.makedirs(DESTINO, exist_ok=True)
    for nombre, arte, color in LAMINAS:
        svg = compone(arte, zonas[arte], color)
        ruta = os.path.join(DESTINO, nombre + ".svg")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(svg)
        if verboso:
            print(nombre, len(svg) // 1024, "KB")


if __name__ == "__main__":
    main()
