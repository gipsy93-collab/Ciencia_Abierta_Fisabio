"""Capa 0 — ORCID works.

Verificado en S73: GET https://pub.orcid.org/v3.0/{orcid}/works responde
SIN token con `Accept: application/json`; los DOI están en
group[].work-summary[].external-ids.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

PUB = "https://pub.orcid.org/v3.0"
_RE_ORCID = re.compile(r"(\d{4})-?(\d{4})-?(\d{4})-?(\d{3}[\dX])", re.IGNORECASE)


def normalizar_orcid(valor: str | None) -> str | None:
    """Acepta URL, ORCID con guiones o sin ellos; devuelve la forma canónica."""
    if not valor:
        return None
    m = _RE_ORCID.search(valor)
    if not m:
        return None
    return "-".join(g.upper() if i == 3 else g for i, g in enumerate(m.groups()))


@dataclass
class Obra:
    titulo: str | None = None
    anio: int | None = None
    doi: str | None = None


def _titulo(resumen: dict) -> str | None:
    valor = ((resumen.get("title") or {}).get("title") or {}).get("value")
    return " ".join(valor.split()) if valor else None


def _anio(resumen: dict) -> int | None:
    valor = (((resumen.get("publication-date") or {}).get("year")) or {}).get("value")
    try:
        return int(valor) if valor else None
    except (TypeError, ValueError):
        return None


def _doi(resumen: dict) -> str | None:
    externos = (resumen.get("external-ids") or {}).get("external-id", [])
    for externo in externos:
        if str(externo.get("external-id-type", "")).lower() == "doi":
            valor = externo.get("external-id-value")
            if valor:
                return valor.strip().lower()
    return None


class OrcidClient:
    def __init__(self, cfg, fetcher=None):
        self.cfg = cfg
        self.fetcher = fetcher

    def obras(self, orcid: str) -> list[Obra]:
        """Obras públicas del ORCID. Lectura pública: no requiere token."""
        ident = normalizar_orcid(orcid)
        if ident is None:
            raise ValueError(f"ORCID no válido: {orcid!r}")

        import httpx  # import local: el paquete funciona sin red instalada

        cabeceras = {
            "Accept": "application/json",
            "User-Agent": self.cfg.user_agent,
        }
        with httpx.Client(timeout=self.cfg.http_timeout_s) as cliente:
            resp = cliente.get(f"{PUB}/{ident}/works", headers=cabeceras)
            resp.raise_for_status()
            datos = resp.json()
        return self._parsear(datos)

    @staticmethod
    def _parsear(datos: dict) -> list[Obra]:
        obras: list[Obra] = []
        vistos: set[str] = set()
        for grupo in datos.get("group") or []:
            for resumen in grupo.get("work-summary") or []:
                obra = Obra(
                    titulo=_titulo(resumen),
                    anio=_anio(resumen),
                    doi=_doi(resumen),
                )
                clave = obra.doi or f"{obra.titulo}|{obra.anio}"
                if clave in vistos:
                    continue
                if not obra.doi and not obra.titulo:
                    continue
                vistos.add(clave)
                obras.append(obra)
        return obras
