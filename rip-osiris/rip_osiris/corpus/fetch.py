"""Traer el documento DEL ORIGEN (nunca el texto de Common Crawl: truncado).

Descarga respetuosa: robots.txt + rate limit + caché en disco por SHA-256.
La caché evita re-descargar y deja el `sha256` listo para el acta.
"""
from __future__ import annotations

import hashlib
import pathlib
import time
import urllib.parse
import urllib.robotparser

import httpx

# Las cabeceras HTTP son ASCII: sin tildes (httpx lanza UnicodeEncodeError).
CABECERAS = {
    "User-Agent": "rip-osiris/0.1 (political impact tracker; honors robots.txt)"
}


class FetchError(RuntimeError):
    """Fallo de red, de permisos o de contenido inesperado."""


def sha256_hex(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


class Fetcher:
    """Descarga respetuosa: robots.txt + rate limit + caché en disco."""

    def __init__(
        self,
        cfg,
        cache_dir: str | pathlib.Path | None = None,
        *,
        client: httpx.Client | None = None,
        user_agent: str | None = None,
        max_reintentos: int = 2,
    ):
        self.cfg = cfg
        self.cache_dir = pathlib.Path(cache_dir or cfg.pdf_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._client = client
        self.user_agent = user_agent or CABECERAS["User-Agent"]
        self.max_reintentos = max(0, max_reintentos)
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._ultima_llamada = 0.0

    # ---------------------------------------------------------------- robots
    def permitido(self, url: str) -> bool:
        if not self.cfg.respetar_robots:
            return True
        partes = urllib.parse.urlsplit(url)
        if not partes.scheme or not partes.netloc:
            return False

        base = f"{partes.scheme}://{partes.netloc}"
        if base not in self._robots:
            self._robots[base] = self._cargar_robots(base)
        robots = self._robots[base]
        if robots is None:
            # Sin robots.txt accesible: se permite, pero queda registrado.
            return True
        return robots.can_fetch(self.user_agent, url)

    def _cargar_robots(self, base: str) -> urllib.robotparser.RobotFileParser | None:
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(f"{base}/robots.txt")
        try:
            resp = self._http(f"{base}/robots.txt")
        except FetchError:
            return None
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            return None
        parser.parse(resp.text.splitlines())
        return parser

    # ------------------------------------------------------------------ HTTP
    def _http(self, url: str) -> httpx.Response:
        espera = self.cfg.rate_limit_s - (time.monotonic() - self._ultima_llamada)
        if espera > 0:
            time.sleep(espera)

        cliente = self._client or httpx.Client(
            timeout=self.cfg.http_timeout_s, follow_redirects=True
        )
        propio = self._client is None
        try:
            try:
                resp = cliente.get(url, headers={"User-Agent": self.user_agent})
            except httpx.HTTPError as exc:
                raise FetchError(f"fallo de red en {url}: {exc}") from exc
            self._ultima_llamada = time.monotonic()
            return resp
        finally:
            if propio:
                cliente.close()

    # --------------------------------------------------------------- descarga
    def obtener(self, url: str) -> tuple[bytes, dict]:
        """Descarga (o sirve de caché) y devuelve `(bytes, metadatos)`.

        Reintenta ante 429/5xx respetando `Retry-After` (sin saltarse robots).
        """
        if not self.permitido(url):
            raise FetchError(f"robots.txt prohíbe {url}")

        destino = self._ruta_cache(url)
        if destino.exists():
            datos = destino.read_bytes()
            return datos, {
                "url": url,
                "sha256": sha256_hex(datos),
                "bytes": len(datos),
                "cache": True,
                "content_type": self._tipo_por_extension(destino),
            }

        resp = None
        for intento in range(self.max_reintentos + 1):
            resp = self._http(url)
            if resp.status_code == 200 and resp.content:
                break
            if resp.status_code in (429, 500, 502, 503, 504) and intento < self.max_reintentos:
                time.sleep(self._espera(resp, intento))
                continue
            raise FetchError(f"HTTP {resp.status_code} al descargar {url}")

        if resp is None or resp.status_code != 200:  # pragma: no cover
            raise FetchError(f"sin respuesta al descargar {url}")
        datos = resp.content
        if not datos:
            raise FetchError(f"respuesta vacía al descargar {url}")

        destino.write_bytes(datos)
        return datos, {
            "url": url,
            "sha256": sha256_hex(datos),
            "bytes": len(datos),
            "cache": False,
            "content_type": resp.headers.get("content-type", ""),
        }

    @staticmethod
    def _espera(resp: httpx.Response, intento: int) -> float:
        """Espera pedida por el servidor, con tope para no colgar el lote."""
        cabecera = resp.headers.get("retry-after", "").strip()
        if cabecera.isdigit():
            return min(30.0, float(cabecera))
        return min(30.0, 2.0 ** (intento + 1))

    # ---------------------------------------------------------------- caché
    def _ruta_cache(self, url: str) -> pathlib.Path:
        clave = sha256_hex(url.encode("utf-8"))[:32]
        return self.cache_dir / f"{clave}.bin"

    @staticmethod
    def _tipo_por_extension(ruta: pathlib.Path) -> str:
        return "application/octet-stream"


class SinRed(Fetcher):
    """Fetcher nulo para el esqueleto/tests: nunca toca la red."""

    def __init__(self, cfg, cache_dir=None):
        super().__init__(cfg, cache_dir)

    def permitido(self, url: str) -> bool:
        return False

    def obtener(self, url: str) -> tuple[bytes, dict]:
        raise FetchError("SinRed: la descarga no está implementada en el esqueleto")
