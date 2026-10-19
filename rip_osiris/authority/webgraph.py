"""Capa 3 — autoridad propia (Common Crawl + motor SCIVIS).

Esqueleto: el diseño la aísla aquí para poder sustituirla si el convenio
Thinkuy/SCIVIS lo exige (diseño §3).
"""
from __future__ import annotations


class WebGraph:
    def __init__(self, cfg):
        self.cfg = cfg

    def in_links(self, dominio: str) -> dict:  # pragma: no cover
        raise NotImplementedError("Common Crawl WebGraph / CDX (Fase 3)")

    def serie_temporal(self, dominio: str) -> list[dict]:  # pragma: no cover
        raise NotImplementedError("Serie temporal de capturas (Fase 3)")
