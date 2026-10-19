"""Capa 0 — portal FISABIO.

Endpoint verificado en S73: POST https://fisabio.portalinvestigacion.com/get-researchers
(form-encoded ; filtro de área `filter[advanced][0][type]=area&...id=N`).
El listado NO trae ORCID: hay que abrir cada perfil.

Esqueleto: interfaz fijada, red sin implementar.
"""
from __future__ import annotations

from dataclasses import dataclass

BASE = "https://fisabio.portalinvestigacion.com"


@dataclass
class Perfil:
    perfil_id: str
    nombre: str
    area: str | None = None
    orcid: str | None = None


class PortalCris:
    def __init__(self, cfg, fetcher=None):
        self.cfg = cfg
        self.fetcher = fetcher

    def listar_area(self, area_id: int, limite: int = 50) -> list[Perfil]:  # pragma: no cover - red
        raise NotImplementedError("POST /get-researchers (Fase 0.5)")

    def leer_orcid(self, perfil_id: str) -> str | None:  # pragma: no cover - red
        raise NotImplementedError("GET /investigadores/{id} y parseo del ORCID (Fase 0.5)")
