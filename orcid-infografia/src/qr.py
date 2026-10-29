"""Genera el QR de la pieza para el cartel del boletín.

Salida: assets/qr-orcid.png (tinta sobre papel alto, con zona de silencio).
El build lo incrusta como data URI en poster.html (__QR__).

Uso: python src/qr.py        (requiere segno: pip install segno)
"""
from __future__ import annotations

import pathlib
import sys

import segno

RAIZ = pathlib.Path(__file__).resolve().parent.parent
URL = "https://gipsy93-collab.github.io/Ciencia_Abierta_Fisabio/orcid-infografia/"


def main() -> int:
    destino = RAIZ / "assets" / "qr-orcid.png"
    segno.make(URL, error="m").save(
        destino, scale=10, border=2, dark="#1D0F44", light="#FCF8EE")
    print("OK %s (%.1f KB)" % (destino, destino.stat().st_size / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
