"""Interfaz común de fuentes de la Capa 1."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class DocumentoFuente:
    source: str
    source_id: str
    url: str | None = None
    doc_type: str | None = None
    title: str | None = None
    org: str | None = None
    year: int | None = None
    doi: str | None = None
    license: str | None = None


class Fuente(Protocol):
    nombre: str

    def buscar(self, consulta: str) -> list[DocumentoFuente]:  # pragma: no cover
        ...

    def descargar(self, doc: DocumentoFuente) -> bytes:  # pragma: no cover
        ...
