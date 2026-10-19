"""Clasificación de documentos en la tipología N1–N6 (CoARA/DORA)."""
from __future__ import annotations

NIVEL = {
    "normativa": "N1",
    "ley": "N1",
    "real_decreto": "N1",
    "hta": "N2",
    "gpc": "N2",
    "guia": "N2",
    "estrategia": "N3",
    "plan": "N3",
    "plan_salud": "N3",
    "parlamento": "N4",
    "informe_agencia": "N5",
    "informe": "N5",
    "think_tank": "N5",
    "mencion": "N6",
    "institucional": "N6",
}


def nivel(doc_type: str | None) -> str:
    return NIVEL.get((doc_type or "").strip().lower(), "N6")


def descripcion(n: str) -> str:
    return {
        "N1": "Normativa que cita la salida",
        "N2": "HTA / guía de práctica clínica",
        "N3": "Estrategia / plan gubernamental",
        "N4": "Documento parlamentario",
        "N5": "Informe de agencia / think-tank",
        "N6": "Mención institucional",
    }.get(n, "Sin clasificar")
