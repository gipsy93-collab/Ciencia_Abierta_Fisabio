"""Normalización para el emparejamiento (rama c de la cascada)."""
from __future__ import annotations

import re
import unicodedata

_RE_DOI = re.compile(r"10\.\d{4,9}/[-._;()/:a-z0-9]+", re.IGNORECASE)
_RE_ANIO = re.compile(r"\b(?:19|20)\d{2}\b")
_RE_PUNCT = re.compile(r"[^\w\s]+", re.UNICODE)


def sin_acentos(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def normalizar_texto(s: str) -> str:
    s = sin_acentos(s or "").lower()
    s = _RE_PUNCT.sub(" ", s)
    return " ".join(s.split())


def tokens(s: str) -> list[str]:
    """Tokens significativos (se descartan artículos/preposiciones cortos)."""
    return [t for t in normalizar_texto(s).split() if len(t) > 2]


def normalizar_doi(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip().lower()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s)
    s = re.sub(r"^doi:\s*", "", s)
    m = _RE_DOI.search(s)
    return m.group(0).rstrip(".,;)") if m else None


def extraer_doi(s: str | None) -> str | None:
    return normalizar_doi(s)


def extraer_anio(s: str | None) -> int | None:
    if not s:
        return None
    ms = _RE_ANIO.findall(s)
    return int(ms[-1]) if ms else None
