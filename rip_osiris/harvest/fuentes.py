"""Conectores de Capa 1 — stubs con la nota operativa de cada fuente.

Todas las búsquedas reales llegan en F1. Aquí solo se documenta el contrato
y lo ya verificado en S73/S71 para no re-descubrirlo.
"""
from __future__ import annotations

from .base import DocumentoFuente


class Epistemonikos:
    """API con TOKEN (registro previo). Su web NO indexa DOI (S73)."""

    nombre = "epistemonikos"

    def buscar(self, consulta: str) -> list[DocumentoFuente]:  # pragma: no cover
        raise NotImplementedError("Requiere token de Epistemonikos (pendiente S73)")


class Inahta:
    """HTA Database: fuente TEMÁTICA (MeSH/tema). NO es índice de citas (S73)."""

    nombre = "inahta"

    def buscar(self, consulta: str) -> list[DocumentoFuente]:  # pragma: no cover
        raise NotImplementedError("Búsqueda temática + lectura de referencias (Fase 1)")


class Boe:
    nombre = "boe"

    def buscar(self, consulta: str) -> list[DocumentoFuente]:  # pragma: no cover
        raise NotImplementedError("BOE datos abiertos / API (Fase 1; verificar endpoint)")


class Dogv:
    nombre = "dogv"

    def buscar(self, consulta: str) -> list[DocumentoFuente]:  # pragma: no cover
        raise NotImplementedError("DOGV (Fase 1; verificar endpoint)")


class EurLex:
    nombre = "eurlex"

    def buscar(self, consulta: str) -> list[DocumentoFuente]:  # pragma: no cover
        raise NotImplementedError("EUR-Lex / Cellar SPARQL (Fase 1; verificar endpoint)")


class GvaCkan:
    nombre = "gva_ckan"

    def buscar(self, consulta: str) -> list[DocumentoFuente]:  # pragma: no cover
        raise NotImplementedError("Dades Obertes GVA, API CKAN (Fase 1; verificar endpoint)")


class WhoIris:
    nombre = "who_iris"

    def buscar(self, consulta: str) -> list[DocumentoFuente]:  # pragma: no cover
        raise NotImplementedError("WHO/PAHO IRIS (Fase 1)")
