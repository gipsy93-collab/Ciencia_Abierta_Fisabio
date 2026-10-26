"""Semilla: obras de FISABIO en OpenAlex por ROR.

OpenAlex no sustituye al CRIS: `ror.org/0116vew40` devuelve ~4.760 obras
frente a las ~11.500 del portal, porque la filiación FISABIO falta en miles
de artículos. Aquí solo se usa para arrancar una muestra rastreable; la
unión con CRIS/ORCID y la medición del hueco llegan en la fase 2.

Nota de datos: OpenAlex contiene registros duplicados con el mismo DOI
(p. ej. `W2752326209` y `W7211999992`). Se deduplica por DOI y se conserva
el registro con más referencias declaradas.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass

import httpx

from ..cascade.normalize import normalizar_doi

API = "https://api.openalex.org"
SELECT = "id,doi,title,publication_year,type,cited_by_count,referenced_works_count"


class OpenAlexError(RuntimeError):
    """Fallo de red o respuesta inesperada de OpenAlex."""


@dataclass(frozen=True)
class Obra:
    openalex_id: str
    doi: str | None
    titulo: str
    anio: int | None
    tipo: str | None
    citas: int
    referencias: int


def ror_corto(ror: str) -> str:
    """`https://ror.org/0116vew40` -> `0116vew40`."""
    limpio = (ror or "").strip().rstrip("/")
    return limpio.rsplit("/", 1)[-1] if limpio else ""


def _id_corto(valor: str | None) -> str:
    return (valor or "").strip().rsplit("/", 1)[-1]


def parsear(payload: dict) -> list[Obra]:
    """Convierte una página de la API en obras (dedupe por id de OpenAlex).

    Un mismo DOI puede venir en dos registros distintos; aquí se conservan
    ambos para que `_mejor_por_doi` elija el más rico.
    """
    salida: list[Obra] = []
    vistos: set[str] = set()
    for item in payload.get("results") or []:
        openalex_id = _id_corto(item.get("id"))
        if not openalex_id or openalex_id in vistos:
            continue
        doi = normalizar_doi(item.get("doi"))
        titulo = (item.get("title") or "").strip()
        if not titulo:
            continue
        vistos.add(openalex_id)
        salida.append(
            Obra(
                openalex_id=openalex_id,
                doi=doi,
                titulo=titulo,
                anio=item.get("publication_year"),
                tipo=item.get("type"),
                citas=int(item.get("cited_by_count") or 0),
                referencias=int(item.get("referenced_works_count") or 0),
            )
        )
    return salida


def _mejor_por_doi(obras: list[Obra]) -> list[Obra]:
    """Entre duplicados con el mismo DOI, conserva el registro más rico."""
    mejores: dict[str, Obra] = {}
    orden: list[str] = []
    for obra in obras:
        clave = obra.doi or f"id:{obra.openalex_id}"
        if clave not in mejores:
            mejores[clave] = obra
            orden.append(clave)
        elif obra.referencias > mejores[clave].referencias:
            mejores[clave] = obra
    return [mejores[c] for c in orden]


class OpenAlexClient:
    """Cliente mínimo: filtro por ROR, paginación por cursor y cortesía."""

    def __init__(
        self,
        ror: str = "0116vew40",
        *,
        mailto: str = "",
        timeout: float = 30.0,
        rate_limit_s: float = 0.2,
        per_page: int = 200,
        max_reintentos: int = 2,
        client: httpx.Client | None = None,
    ):
        self.ror = ror_corto(ror)
        self.mailto = mailto
        self.timeout = timeout
        self.rate_limit_s = rate_limit_s
        self.per_page = max(1, min(200, per_page))
        self.max_reintentos = max_reintentos
        self._client = client
        self._ultima_llamada = 0.0
        self._cache: dict[str, dict] = {}
        self.llamadas: list[dict] = []

    @classmethod
    def desde_config(cls, cfg, **kw) -> "OpenAlexClient":
        return cls(
            cfg.ror_fisabio,
            mailto=cfg.openalex_mailto,
            timeout=cfg.http_timeout_s,
            **kw,
        )

    # ------------------------------------------------------------------ HTTP
    def _pedir(self, ruta: str, params: dict) -> dict:
        clave = ruta + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        if clave in self._cache:
            return self._cache[clave]

        espera = self.rate_limit_s - (time.monotonic() - self._ultima_llamada)
        if espera > 0:
            time.sleep(espera)

        cliente = self._client or httpx.Client(timeout=self.timeout, follow_redirects=True)
        propio = self._client is None
        url = f"{API}/{ruta}"
        try:
            for intento in range(self.max_reintentos + 1):
                try:
                    resp = cliente.get(url, params=params)
                except httpx.HTTPError as exc:
                    if intento >= self.max_reintentos:
                        raise OpenAlexError(f"fallo de red: {exc}") from exc
                    time.sleep(2**intento)
                    continue

                self._ultima_llamada = time.monotonic()
                self.llamadas.append({"url": url, "params": dict(params), "status": resp.status_code})
                if resp.status_code == 404:
                    self._cache[clave] = {"results": [], "meta": {}}
                    return self._cache[clave]
                if resp.status_code in (429, 500, 502, 503, 504):
                    if intento >= self.max_reintentos:
                        raise OpenAlexError(f"HTTP {resp.status_code} tras reintentos")
                    time.sleep(2 ** (intento + 1))
                    continue
                if resp.status_code != 200:
                    raise OpenAlexError(f"HTTP {resp.status_code} en {ruta}")
                datos = resp.json()
                self._cache[clave] = datos
                return datos
            raise OpenAlexError("reintentos agotados")  # pragma: no cover
        finally:
            if propio:
                cliente.close()

    # -------------------------------------------------------------- consultas
    def obras(
        self,
        max_obras: int = 25,
        *,
        buscar: str | None = None,
        orden: str = "publication_year:desc",
    ) -> list[Obra]:
        """Obras con autoría FISABIO, deduplicadas por DOI."""
        filtros = [f"authorships.institutions.ror:{self.ror}", "has_doi:true"]
        if buscar:
            filtros.append(f"default.search:{buscar}")
        params = {
            "filter": ",".join(filtros),
            "select": SELECT,
            "per-page": str(self.per_page),
            "sort": orden,
            "cursor": "*",
        }
        if self.mailto:
            params["mailto"] = self.mailto

        acumuladas: list[Obra] = []
        while len(acumuladas) < max_obras:
            datos = self._pedir("works", params)
            pagina = parsear(datos)
            if not pagina:
                break
            acumuladas.extend(pagina)
            cursor = (datos.get("meta") or {}).get("next_cursor")
            if not cursor:
                break
            params = {**params, "cursor": cursor}

        return _mejor_por_doi(acumuladas)[:max_obras]

    def por_dois(self, dois: list[str]) -> list[Obra]:
        """Resuelve una lista de DOI en una sola petición (filtro OR)."""
        limpios = [d for d in (normalizar_doi(x) for x in dois) if d]
        if not limpios:
            return []
        params = {
            "filter": "doi:" + "|".join(limpios),
            "select": SELECT,
            "per-page": str(len(limpios) + 10),
        }
        if self.mailto:
            params["mailto"] = self.mailto
        return _mejor_por_doi(parsear(self._pedir("works", params)))


class OpenAlexNulo:
    """Doble de prueba: nunca toca la red."""

    def __init__(self, obras: list[Obra] | None = None):
        self._obras = obras or []
        self.llamadas: list[dict] = []

    def obras(self, max_obras: int = 25, **kw) -> list[Obra]:
        return self._obras[:max_obras]

    def por_dois(self, dois: list[str]) -> list[Obra]:
        return [o for o in self._obras if o.doi in {normalizar_doi(d) for d in dois}]


def guardar_semilla(store, obras: list[Obra], *, fuente: str = "openalex") -> list[int]:
    """Persiste la semilla en `outputs`. Devuelve los ids."""
    ids = [
        store.upsert_output(
            doi=obra.doi,
            title=obra.titulo,
            year=obra.anio,
            source=f"{fuente}:{obra.openalex_id}",
        )
        for obra in obras
    ]
    store.set_coverage(fuente, "semilla", hits=len(obras), declared="muestra")
    return ids


def como_dict(obra: Obra) -> dict:
    return json.loads(json.dumps(obra.__dict__, ensure_ascii=False))
