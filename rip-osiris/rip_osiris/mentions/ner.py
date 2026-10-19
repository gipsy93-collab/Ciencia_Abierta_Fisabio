"""NER local para menciones (Capa 2).

Esqueleto: interfaz. En F2 se implementa con entidades locales + variantes
de nombre derivadas de ORCID. Toda mención exigirá span literal (guardián).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Mencion:
    entidad: str
    tipo: str  # 'autor' | 'grupo' | 'institucion' | 'tema'
    span_literal: str
    offset: int


class NerLocal:
    def __init__(self, entidades: list[str] | None = None):
        self.entidades = entidades or []

    def detectar(self, texto: str) -> list[Mencion]:  # pragma: no cover
        raise NotImplementedError("NER local (F2)")
