"""Extracción heurística de cadenas de referencia (sin Java, decisión F0).

Calidad POR MEDIR sobre PDF de política (diseño §9). No promete paridad con
GROBID: entrega cadenas candidatas y marca la sección. El resto del pipeline
(resolve/match) tolera ruido porque exige literal + umbral.

La división del bloque usa tres señales, en este orden:

1. numeración explícita (`[1]`, `(1)`, `1.`) al inicio de línea;
2. inicio de referencia reconocible (autor-apellido + inicial, u
   organización + año entre paréntesis);
3. línea en blanco, como último recurso.

La señal 2 existe porque los PDF de política suelen traer la bibliografía
como un bloque continuo sin numerar ni separar: sin ella, todas las
referencias colapsan en una sola cadena y el `literal` deja de ser trazable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_SECCIONES = (
    "referencias",
    "referencias bibliograficas",
    "bibliografia",
    "bibliography",
    "references",
    "fuentes consultadas",
)

_RE_NUM = re.compile(r"^\s{0,3}(?:\[\d+\]|\(\d+\)|\d{1,3}[.)])\s+")

# "Abadal-Falgueras, E." / "Gertrudix, M., Rajas, M." / "European Commission (2016)."
_RE_APELLIDO_INICIAL = re.compile(
    r"^[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ'’\-]*(?:-[A-ZÁÉÍÓÚÑ][\wáéíóúñ'’\-]*)?"
    r",\s+[A-ZÁÉÍÓÚÑ]\."
)
_RE_ORG_ANIO = re.compile(
    r"^[A-ZÁÉÍÓÚÑ][^.]{1,90}?\(\d{4}[a-z]?\)"
)
_RE_ORG_ANIO_PUNTO = re.compile(
    r"^[A-ZÁÉÍÓÚÑ][^()]{1,60}\.\s*\(\d{4}[a-z]?\)"
)
_RE_CONTINUACION = re.compile(r"(?:,|;\s*|\by\b|\band\b|\bdel?\b)\s*$")
_RE_URL_SUELTA = re.compile(r"^(?:https?://|www\.|doi:)", re.IGNORECASE)

# Una cadena de referencia real no ocupa miles de caracteres. Sin este tope,
# un documento sin bibliografía devuelve el texto entero como una «referencia»
# y el matcher lo puntúa contra sí mismo.
MAX_LONGITUD_REF = 3000


@dataclass
class RefString:
    raw: str
    section: str
    offset: int


def _normalizar_clave(texto: str) -> str:
    from .normalize import normalizar_texto

    return normalizar_texto(texto)


def detectar_inicio_bibliografia(texto: str) -> int | None:
    """Posición de la cabecera de bibliografía más temprana del texto.

    Solo se acepta una línea que SEA la cabecera. Buscar la palabra suelta
    produce falsos positivos letales: en una ley, «las referencias que en esta
    ley se realizan...» a mitad del articulado abriría una pseudo-bibliografía
    de decenas de miles de caracteres, y el matcher la puntuaría alto.
    """
    posicion = 0
    for linea in texto.splitlines(keepends=True):
        if _es_cabecera(linea):
            return posicion
        posicion += len(linea)
    return None


def _es_inicio_ref(linea: str) -> bool:
    limpia = linea.strip()
    if not limpia:
        return False
    if _RE_NUM.match(limpia):
        return True
    if _RE_URL_SUELTA.match(limpia):
        return False
    return bool(
        _RE_APELLIDO_INICIAL.match(limpia)
        or _RE_ORG_ANIO.match(limpia)
        or _RE_ORG_ANIO_PUNTO.match(limpia)
    )


def _es_continuacion(anterior: str) -> bool:
    """La línea anterior quedó abierta (coma, 'y', 'del', etc.)."""
    return bool(_RE_CONTINUACION.search(anterior.rstrip()))


def _es_cabecera(linea: str) -> bool:
    clave = _normalizar_clave(linea.strip())
    if len(clave) > 40:
        return False
    return any(clave == s or clave.startswith(s) for s in _SECCIONES)


def _unir(partes: list[str]) -> list[str]:
    salida: list[str] = []
    for p in partes:
        p = _RE_NUM.sub("", p).strip()
        p = " ".join(p.split())
        if 15 <= len(p) <= MAX_LONGITUD_REF:
            salida.append(p)
    return salida


def _por_inicio(bloque: str) -> list[str]:
    partes: list[str] = []
    actual: list[str] = []
    for linea in bloque.splitlines():
        es_inicio = _es_inicio_ref(linea)
        # una línea que arranca como autor pero continúa la anterior (coma
        # final, "y", "del"...) pertenece a la misma referencia
        if es_inicio and actual and _es_continuacion(actual[-1]):
            es_inicio = False
        if es_inicio:
            if actual:
                partes.append("\n".join(actual))
            actual = [linea]
        elif actual:
            actual.append(linea)
        elif linea.strip():
            actual = [linea]
    if actual:
        partes.append("\n".join(actual))

    # una URL suelta tras un salto es cola de la referencia anterior
    unidas: list[str] = []
    for p in partes:
        limpia = p.strip()
        if unidas and _RE_URL_SUELTA.match(limpia) and len(limpia) < 80:
            unidas[-1] = unidas[-1] + " " + limpia
        else:
            unidas.append(p)
    return unidas


def dividir_referencias(bloque: str) -> list[str]:
    # recomponer palabras partidas por guion de fin de línea, conservando saltos
    bloque = re.sub(r"-\s*\n\s*", "", bloque)

    lineas = bloque.splitlines()
    while lineas and (_es_cabecera(lineas[0]) or not lineas[0].strip()):
        lineas.pop(0)
    bloque = "\n".join(lineas)

    if _RE_NUM.search("\n" + bloque):
        partes = re.split(
            r"(?m)(?=^[ \t]{0,3}(?:\[\d+\]|\(\d+\)|\d{1,3}[.)])[ \t]+)", bloque
        )
    else:
        partes = _por_inicio(bloque)
        if len(partes) <= 1:
            partes = re.split(r"\n\s*\n", bloque)
    return _unir(partes)


def extraer(texto: str) -> list[RefString]:
    """Devuelve las cadenas candidatas del bloque de bibliografía (o del cuerpo)."""
    if not texto:
        return []
    ini = detectar_inicio_bibliografia(texto)
    bloque = texto[ini:] if ini is not None else texto
    seccion = "bibliografia" if ini is not None else "cuerpo"
    base = ini or 0

    refs: list[RefString] = []
    cursor = 0
    for raw in dividir_referencias(bloque):
        # offset aproximado: primera aparición desde el cursor
        rel = bloque.find(raw, cursor)
        if rel == -1:
            rel = cursor
        refs.append(RefString(raw=raw, section=seccion, offset=base + rel))
        cursor = rel + len(raw)
    return refs
