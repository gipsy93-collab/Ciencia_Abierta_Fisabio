"""Capa 0 — ROR FISABIO (desambiguación de filiación / movilidad)."""
from __future__ import annotations

import re

ROR_FISABIO = "https://ror.org/0116vew40"

_RE_ROR = re.compile(r"ror\.org/([0-9a-z]{9})", re.IGNORECASE)


def normalizar_ror(valor: str | None) -> str | None:
    if not valor:
        return None
    m = _RE_ROR.search(valor)
    return f"https://ror.org/{m.group(1).lower()}" if m else valor.strip()


def es_fisabio(valor: str | None) -> bool:
    return normalizar_ror(valor) == ROR_FISABIO
