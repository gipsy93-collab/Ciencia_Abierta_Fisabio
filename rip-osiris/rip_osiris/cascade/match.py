"""Matcher in-corpus — LA CASCADA (rama c).

Casa una cadena de referencia con un documento ya presente en el corpus.
Regla de oro (diseño §5): doble campo (org + año) + umbral de tokens del
título. Por debajo del umbral NO es arista; el caso queda `unresolved` y se ve.
"""
from __future__ import annotations

from dataclasses import dataclass

from .normalize import extraer_anio, tokens


@dataclass
class Doc:
    doc_id: int
    title: str
    org: str | None = None
    year: int | None = None


@dataclass
class MatchResult:
    doc_id: int
    score: float
    motivo: dict


class CorpusIndex:
    """Índice normalizado de documentos del corpus para la rama (c)."""

    def __init__(self, docs: list[Doc]):
        self._docs = list(docs)
        self._titulos = {d.doc_id: set(tokens(d.title)) for d in self._docs}
        self._orgs = {d.doc_id: set(tokens(d.org or "")) for d in self._docs}

    def match(self, ref: str, cfg) -> MatchResult | None:
        ref_tokens = set(tokens(ref))
        if not ref_tokens:
            return None
        anio_ref = extraer_anio(ref)
        mejor: MatchResult | None = None

        for d in self._docs:
            titulo = self._titulos[d.doc_id]
            if not titulo:
                continue

            solape = len(titulo & ref_tokens) / len(titulo)
            org_ok = bool(self._orgs[d.doc_id] & ref_tokens)
            anio_ok = (
                anio_ref is not None and d.year is not None and anio_ref == d.year
            )

            if cfg.require_org_and_year and not (org_ok and anio_ok):
                continue
            if solape < cfg.match_min_title_tokens:
                continue

            score = (
                0.6 * solape
                + 0.2 * (1.0 if org_ok else 0.0)
                + 0.2 * (1.0 if anio_ok else 0.0)
            )
            if score < cfg.match_min_score:
                continue

            if mejor is None or score > mejor.score:
                mejor = MatchResult(
                    doc_id=d.doc_id,
                    score=round(score, 4),
                    motivo={
                        "titulo_solape": round(solape, 4),
                        "org": org_ok,
                        "anio": anio_ok,
                    },
                )
        return mejor
