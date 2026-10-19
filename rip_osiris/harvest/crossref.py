"""Crossref — resolución de referencias (ramas a/b de la cascada).

Endpoints (verificados en S83):
  - GET https://api.crossref.org/works/{doi}
  - GET https://api.crossref.org/works?query.bibliographic=...&rows=N

Regla de fidelidad: `query.bibliographic` nunca acepta el primer resultado a
ciegas. Se exige (1) `score` mínimo de Crossref y (2) solape de tokens del
título con la cadena de referencia. Por debajo de cualquiera de los dos, la
rama (b) devuelve `None` y el caso sigue a la rama (c) o queda `unresolved`.
"""
from __future__ import annotations

import difflib
import time
from dataclasses import dataclass

import httpx

from ..cascade.normalize import normalizar_doi, tokens

API = "https://api.crossref.org/works"
USER_AGENT = "rip-osiris/0.1 (+mailto:{mailto})"


class CrossrefError(RuntimeError):
    """Fallo de red o respuesta inesperada de Crossref."""


@dataclass
class Candidato:
    doi: str
    titulo: str | None
    score: float
    solape: float
    prefijo: bool


def coincidencia_titulo(titulo: str | None, referencia: str) -> tuple[float, bool]:
    """Cobertura del título por el mayor bloque contiguo presente en la cita.

    Devuelve `(cobertura, es_prefijo)`. Las citas suelen truncar el subtítulo,
    por eso se distingue el caso en que lo citado es el **arranque literal**
    del título: es una señal fuerte aunque la cobertura sea baja.
    """
    tokens_titulo = tokens(titulo or "")
    if not tokens_titulo:
        return 0.0, False
    tokens_ref = tokens(referencia)
    if not tokens_ref:
        return 0.0, False

    bloques = [
        b
        for b in difflib.SequenceMatcher(
            None, tokens_titulo, tokens_ref, autojunk=False
        ).get_matching_blocks()
        if b.size
    ]
    if not bloques:
        return 0.0, False

    mejor = max(bloques, key=lambda b: b.size)
    cobertura = mejor.size / len(tokens_titulo)
    es_prefijo = mejor.a == 0 and mejor.size >= min(6, len(tokens_titulo))
    return round(cobertura, 4), es_prefijo


class CrossrefClient:
    """Cliente mínimo con caché en memoria, rate limit y reintentos."""

    def __init__(
        self,
        mailto: str,
        timeout: float = 30.0,
        *,
        user_agent: str | None = None,
        min_score: float = 60.0,
        min_title_overlap: float = 0.70,
        rate_limit_s: float = 0.0,
        max_reintentos: int = 2,
        client: httpx.Client | None = None,
    ):
        self.mailto = mailto
        self.timeout = timeout
        self.user_agent = user_agent or USER_AGENT.format(mailto=mailto)
        self.min_score = min_score
        self.min_title_overlap = min_title_overlap
        self.rate_limit_s = rate_limit_s
        self.max_reintentos = max_reintentos
        self._cliente = client
        self._ultima_llamada = 0.0
        self._cache_existe: dict[str, bool] = {}
        self._cache_query: dict[str, str | None] = {}

    @classmethod
    def desde_config(cls, cfg) -> "CrossrefClient":
        return cls(
            mailto=cfg.crossref_mailto,
            timeout=cfg.http_timeout_s,
            user_agent=cfg.user_agent,
            rate_limit_s=cfg.rate_limit_s,
        )

    # ------------------------------------------------------------------ HTTP
    def _pedir(self, ruta: str, params: dict | None = None) -> httpx.Response:
        espera = self.rate_limit_s - (time.monotonic() - self._ultima_llamada)
        if espera > 0:
            time.sleep(espera)

        cabeceras = {
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        url = ruta if ruta.startswith("http") else f"{API}/{ruta}"

        cliente = self._cliente or httpx.Client(timeout=self.timeout)
        propio = self._cliente is None
        try:
            for intento in range(self.max_reintentos + 1):
                try:
                    resp = cliente.get(url, params=params, headers=cabeceras)
                except httpx.HTTPError as exc:
                    if intento >= self.max_reintentos:
                        raise CrossrefError(f"fallo de red: {exc}") from exc
                    time.sleep(2**intento)
                    continue

                self._ultima_llamada = time.monotonic()
                if resp.status_code in (429, 500, 502, 503, 504):
                    if intento >= self.max_reintentos:
                        raise CrossrefError(f"HTTP {resp.status_code} tras reintentos")
                    time.sleep(2**intento)
                    continue
                return resp
            raise CrossrefError("reintentos agotados")  # pragma: no cover
        finally:
            if propio:
                cliente.close()

    # --------------------------------------------------------------- consultas
    def existe(self, doi: str) -> bool:
        """True si Crossref reconoce el DOI. 404 no es error: es ausencia."""
        ident = normalizar_doi(doi)
        if ident is None:
            return False
        if ident in self._cache_existe:
            return self._cache_existe[ident]

        resp = self._pedir(ident)
        if resp.status_code == 404:
            self._cache_existe[ident] = False
            return False
        if resp.status_code != 200:
            raise CrossrefError(f"HTTP {resp.status_code} al verificar {ident}")
        self._cache_existe[ident] = True
        return True

    def query_bibliographic(self, texto: str) -> str | None:
        """DOI del mejor candidato que supere umbral de score y de título."""
        if not texto or not texto.strip():
            return None
        if texto in self._cache_query:
            return self._cache_query[texto]

        resp = self._pedir(
            "",
            params={
                "query.bibliographic": texto,
                "rows": 5,
                "select": "DOI,title,score",
                "mailto": self.mailto,
            },
        )
        if resp.status_code != 200:
            raise CrossrefError(f"HTTP {resp.status_code} en query.bibliographic")

        candidatos = self._candidatos(resp.json(), texto)
        elegido = next(
            (
                c
                for c in candidatos
                if c.score >= self.min_score
                and (c.solape >= self.min_title_overlap or c.prefijo)
            ),
            None,
        )
        resultado = elegido.doi if elegido else None
        self._cache_query[texto] = resultado
        return resultado

    # ---------------------------------------------------------------- parseo
    @staticmethod
    def _candidatos(datos: dict, referencia: str) -> list[Candidato]:
        salida: list[Candidato] = []
        for item in (datos.get("message") or {}).get("items") or []:
            doi = normalizar_doi(item.get("DOI"))
            if doi is None:
                continue
            titulo = (item.get("title") or [None])[0]
            solape, prefijo = coincidencia_titulo(titulo, referencia)
            salida.append(
                Candidato(
                    doi=doi,
                    titulo=titulo,
                    score=float(item.get("score") or 0.0),
                    solape=solape,
                    prefijo=prefijo,
                )
            )
        return salida


class CrossrefNulo:
    """Doble de prueba: no resuelve nada, nunca toca la red."""

    disponible = False

    def existe(self, doi: str) -> bool:
        return False

    def query_bibliographic(self, texto: str) -> str | None:
        return None
