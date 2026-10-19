"""Rama (c) real: documento de política cita otro por número de norma.

Los documentos jurídicos y de política no se citan como «Autor (año)»:
citan «Ley 14/1986», «Real Decreto 1030/2006», «Orden de 21 de julio de
2001». El matcher académico (org+año+tokens de título) no los ve.

Aquí se añade una señal explícita: el `source_id` del documento guarda su
identificador normativo normalizado («ley-14-1986»), y la cita se reconoce
con un patrón de tipo normativo + número + año. Es una coincidencia de
identificador, no difusa: no necesita umbral.
"""
from __future__ import annotations

import re

_TIPOS = (
    "ley organica",
    "ley",
    "real decreto legislativo",
    "real decreto-ley",
    "real decreto",
    "decreto legislativo",
    "decreto",
    "orden",
    "resolucion",
    "constitucion",
)

_RE_CITA_NORMA = re.compile(
    r"\b(?P<tipo>"
    + "|".join(t.replace(" ", r"\s+") for t in _TIPOS)
    + r")\s+(?P<num>\d{1,4})\s*/\s*(?P<anio>\d{4})\b",
    re.IGNORECASE,
)

_RE_CITA_ORDEN = re.compile(
    r"\b(?P<tipo>orden|decreto)\s+de\s+(?P<dia>\d{1,2})\s+de\s+"
    r"(?P<mes>enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|"
    r"octubre|noviembre|diciembre)\s+de\s+(?P<anio>\d{4})\b",
    re.IGNORECASE,
)

_MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12,
}

_RE_ESPACIOS = re.compile(r"[\s_]+")
_RE_NO_CLAVE = re.compile(r"[^a-z0-9]+")


def normalizar_source_id(source_id: str) -> str:
    """«BOE-A-2014-13612» / «Ley 14/1986» -> «ley-14-1986» (forma canónica)."""
    s = source_id.strip().lower()
    s = _RE_ESPACIOS.sub("-", s)
    s = _RE_NO_CLAVE.sub("-", s)
    return s.strip("-")


def claves_normativas(texto: str) -> list[tuple[str, str]]:
    """Devuelve `[(literal, clave)]` de cada cita normativa del texto.

    `literal` es el fragmento exacto tal como aparece (para el guardián);
    `clave` es la forma canónica comparable con `source_id`.
    """
    salida: list[tuple[str, str]] = []
    vistos: set[str] = set()

    for m in _RE_CITA_NORMA.finditer(texto):
        tipo = re.sub(r"\s+", " ", m.group("tipo").lower())
        num = str(int(m.group("num")))
        anio = m.group("anio")
        clave = f"{tipo.replace(' ', '-')}-{num}-{anio}"
        if clave in vistos:
            continue
        vistos.add(clave)
        salida.append((m.group(0), clave))

    for m in _RE_CITA_ORDEN.finditer(texto):
        tipo = m.group("tipo").lower()
        dia = int(m.group("dia"))
        mes = _MESES[m.group("mes").lower()]
        anio = m.group("anio")
        clave = f"{tipo}-{dia:02d}-{mes:02d}-{anio}"
        if clave in vistos:
            continue
        vistos.add(clave)
        salida.append((m.group(0), clave))

    return salida
