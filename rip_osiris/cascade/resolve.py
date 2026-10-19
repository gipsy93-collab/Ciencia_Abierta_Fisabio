"""Resolución de una cadena de referencia en las tres ramas de la cascada."""
from __future__ import annotations

from dataclasses import dataclass

from .normalize import normalizar_doi


@dataclass
class Resolved:
    raw: str
    method: str  # 'doi_inline' | 'crossref_query' | 'corpus_match' | 'unresolved'
    doi: str | None = None
    doc_id: int | None = None
    confidence: float = 0.0
    verificado: bool = True


def resolver(ref: str, index, crossref, cfg) -> Resolved:
    """Orden: (a) DOI inline -> (b) Crossref -> (c) match in-corpus.

    Si no hay cliente capaz de verificar (modo `--sin-red`), el DOI literal de
    la cita se acepta igualmente, pero se marca `verificado=False` y baja la
    confianza: el dato está en el texto, su existencia en Crossref no.
    """
    doi = normalizar_doi(ref)
    disponible = crossref is not None and getattr(crossref, "disponible", True)

    if doi and disponible:
        if crossref.existe(doi):
            return Resolved(ref, "doi_inline", doi=doi, confidence=cfg.conf_doi_inline)
    elif doi and crossref is not None:
        return Resolved(
            ref,
            "doi_inline",
            doi=doi,
            confidence=cfg.conf_doi_inline_sin_verificar,
            verificado=False,
        )

    if disponible:
        hallado = crossref.query_bibliographic(ref)
        if hallado:
            return Resolved(
                ref, "crossref_query", doi=hallado, confidence=cfg.conf_crossref_query
            )

    m = index.match(ref, cfg)
    if m is not None:
        return Resolved(ref, "corpus_match", doc_id=m.doc_id, confidence=m.score)

    return Resolved(ref, "unresolved")
