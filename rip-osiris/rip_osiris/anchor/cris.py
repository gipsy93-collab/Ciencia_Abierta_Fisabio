"""Capa 0 — portal FISABIO: roster, identidad y ORCID (P1).

Endpoints verificados en S84:
- POST {BASE}/get-researchers   (form-encoded) -> tarjetas con /investigadores/{id}
- POST {BASE}/get-publications  -> obras con DOI, tipo, año y autores enlazados
- GET  {BASE}/investigadores/{id} -> perfil con ORCID
- GET  {BASE}/robots.txt -> 404 (sin reglas)

Rastreo respetuoso: 1 req/s, caché en disco por hash, reintentos con backoff.
Uso interno: no se redistribuyen nombres, ORCID ni contenidos (ver P0 §11).
"""
from __future__ import annotations

import hashlib
import html as _html
import pathlib
import re
import ssl
import sys
import time
from dataclasses import dataclass, field

from ..cascade.normalize import normalizar_doi
from .orcid import normalizar_orcid

BASE = "https://fisabio.portalinvestigacion.com"


class PortalError(RuntimeError):
    """Fallo de red o de contenido inesperado en el portal."""


def contexto_ssl() -> ssl.SSLContext:
    """Contexto con la cadena completa: el portal no envía su intermedio.

    En Windows el intermedio vive en el almacén `CA`, que OpenSSL no consulta
    por defecto; se añade para no desactivar la verificación del certificado.
    """
    ctx = ssl.create_default_context()
    if sys.platform == "win32":
        for almacen in ("ROOT", "CA"):
            try:
                certificados = ssl.enum_certificates(almacen)
            except (AttributeError, OSError):
                continue
            for der, tipo, _ in certificados:
                if tipo != "x509_asn":
                    continue
                try:
                    ctx.load_verify_locations(cadata=der)
                except (ssl.SSLError, ValueError):
                    pass
    return ctx


# --------------------------------------------------------------------- modelos
@dataclass
class Perfil:
    perfil_id: str
    nombre: str
    area: str | None = None
    rol: str | None = None
    orcid: str | None = None


@dataclass
class PublicacionPortal:
    pub_id: str
    titulo: str
    doi: str | None = None
    tipo: str | None = None
    anio: int | None = None
    autores: str | None = None
    autores_ids: list[str] = field(default_factory=list)


# --------------------------------------------------------------------- parsing
_RE_LI = re.compile(r"<li\b", re.IGNORECASE)
_RE_ID_INV = re.compile(r"/investigadores/(\d+)")
_RE_ID_PUB = re.compile(r"/publicaciones/(\d+)")
_RE_H4_INV = re.compile(
    r'<h4[^>]*class="[^"]*card__name[^"]*"[^>]*>\s*<a[^>]*>(.*?)</a>', re.S | re.I
)
_RE_P_ITALIC = re.compile(
    r'<p[^>]*class="[^"]*style-italic[^"]*"[^>]*>(.*?)</p>', re.S | re.I
)
_RE_P_BOLD = re.compile(
    r'<p[^>]*class="[^"]*weight-bold[^"]*"[^>]*>(.*?)</p>', re.S | re.I
)
_RE_H4_PUB = re.compile(
    r'<h4[^>]*class="[^"]*results-list__title[^"]*"[^>]*>\s*'
    r'<a[^>]*href="?[^">]*?/publicaciones/(\d+)"?[^>]*>(.*?)</a>',
    re.S | re.I,
)
_RE_P = re.compile(r"<p[^>]*>(.*?)</p>", re.S | re.I)
_RE_DOI_EN_TEXTO = re.compile(r"10\.\d{4,9}/[^\s<]+")
_RE_ANIO_EN_TEXTO = re.compile(r"\b((?:19|20)\d{2})\b")
_RE_H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S | re.I)
_RE_ORCID = re.compile(
    r"orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dXx])", re.IGNORECASE
)
_RE_ORCID_SUELTO = re.compile(r"\b(\d{4}-\d{4}-\d{4}-\d{3}[\dXx])\b")


def _limpiar(fragmento: str | None) -> str:
    if not fragmento:
        return ""
    texto = re.sub(r"<[^>]+>", " ", fragmento)
    return " ".join(_html.unescape(texto).split())


def _limpiar_titulo(fragmento: str | None) -> str:
    """El portal envuelve algunos títulos en comillas repetidas."""
    titulo = _limpiar(fragmento)
    titulo = re.sub(r'^[\s"“”«»]+', "", titulo)
    return re.sub(r'[\s"“”«»]+$', "", titulo)


def parsear_investigadores(texto: str) -> list[Perfil]:
    """Tarjetas del listado `/get-researchers` -> perfiles únicos por id."""
    vistos: dict[str, Perfil] = {}
    for trozo in _RE_LI.split(texto)[1:]:
        mid = _RE_ID_INV.search(trozo)
        if not mid:
            continue
        perfil_id = mid.group(1)
        if perfil_id in vistos:
            continue
        m_nombre = _RE_H4_INV.search(trozo)
        if not m_nombre:
            continue
        m_area = _RE_P_ITALIC.search(trozo)
        m_rol = _RE_P_BOLD.search(trozo)
        vistos[perfil_id] = Perfil(
            perfil_id=perfil_id,
            nombre=_limpiar(m_nombre.group(1)),
            area=_limpiar(m_area.group(1)) or None if m_area else None,
            rol=_limpiar(m_rol.group(1)) or None if m_rol else None,
        )
    return list(vistos.values())


def parsear_publicaciones(texto: str) -> list[PublicacionPortal]:
    """Tarjetas de `/get-publications` -> publicaciones únicas por id."""
    vistos: dict[str, PublicacionPortal] = {}
    for trozo in _RE_LI.split(texto)[1:]:
        m_pub = _RE_H4_PUB.search(trozo)
        if not m_pub:
            continue
        pub_id, titulo_html = m_pub.group(1), m_pub.group(2)
        if pub_id in vistos:
            continue

        parrafos = _RE_P.findall(trozo[m_pub.end():])
        tipo = doi = None
        anio = None
        autores_html = None
        for indice, parrafo in enumerate(parrafos):
            m_doi = _RE_DOI_EN_TEXTO.search(parrafo)
            if not m_doi:
                continue
            plano = _limpiar(parrafo)
            doi = normalizar_doi(m_doi.group(0))
            tipo = plano.split(".")[0].strip() or None
            anios = _RE_ANIO_EN_TEXTO.findall(plano)
            anio = int(anios[-1]) if anios else None
            if indice > 0:
                autores_html = parrafos[indice - 1]
            break

        vistos[pub_id] = PublicacionPortal(
            pub_id=pub_id,
            titulo=_limpiar_titulo(titulo_html),
            doi=doi,
            tipo=tipo,
            anio=anio,
            autores=_limpiar(autores_html),
            autores_ids=sorted(set(_RE_ID_INV.findall(autores_html or ""))),
        )
    return list(vistos.values())


def parsear_perfil(texto: str) -> Perfil:
    """Perfil individual -> nombre y ORCID (sin inferir por nombre)."""
    m_h1 = _RE_H1.search(texto)
    nombre = _limpiar(m_h1.group(1)) if m_h1 else ""
    orcid = None
    m_orcid = _RE_ORCID.search(texto) or _RE_ORCID_SUELTO.search(texto)
    if m_orcid:
        orcid = normalizar_orcid(m_orcid.group(1))
    return Perfil(perfil_id="", nombre=nombre, orcid=orcid)


# ----------------------------------------------------------------------- red
class PortalCris:
    """Cliente del portal. Inyecta `client` (httpx.Client o falso) en tests."""

    def __init__(self, cfg, *, client=None, cache_dir=None):
        self.cfg = cfg
        self.client = client
        self.cache_dir = pathlib.Path(cache_dir or cfg.portal_cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.user_agent = (
            f"{cfg.user_agent} (contact {cfg.portal_contacto})"
            if cfg.portal_contacto not in cfg.user_agent
            else cfg.user_agent
        )
        self.llamadas: list[dict] = []
        self._ultima = 0.0
        self._verify = contexto_ssl()

    # ------------------------------------------------------------- solicitudes
    @staticmethod
    def _filtro(limite: int, area_id: int | None = None) -> dict:
        datos = {
            "filter[limit]": str(limite),
            "filter[sort]": "ASC",
            "filter[letter]": "",
            "filter[search]": "",
        }
        if area_id is not None:
            datos.update(
                {
                    "filter[advanced][0][type]": "area",
                    "filter[advanced][0][id]": str(area_id),
                    "filter[advanced][0][name]": "",
                }
            )
        return datos

    def _esperar(self) -> None:
        espera = self.cfg.rate_limit_s - (time.monotonic() - self._ultima)
        if espera > 0:
            time.sleep(espera)

    def _solicitar(self, metodo: str, ruta: str, datos: dict | None = None) -> str:
        url = f"{self.cfg.portal_base}{ruta}"
        clave = hashlib.sha256(
            f"{metodo} {url} {sorted((datos or {}).items())}".encode("utf-8")
        ).hexdigest()[:32]
        destino = self.cache_dir / f"{clave}.frag"
        if destino.exists():
            crudo = destino.read_bytes()
            self._registrar(url, metodo, 200, crudo, cache=True)
            return crudo.decode("utf-8", errors="replace")

        import httpx  # import local: el paquete funciona sin red instalada

        cabeceras = {"User-Agent": self.user_agent}
        propio = self.client is None
        cliente = self.client or httpx.Client(
            timeout=self.cfg.http_timeout_s,
            follow_redirects=True,
            verify=self._verify,
        )
        try:
            ultimo_error = None
            for espera in (0.0, 2.0, 8.0):
                self._esperar()
                if espera:
                    time.sleep(espera)
                try:
                    if metodo == "POST":
                        resp = cliente.post(url, data=datos or {}, headers=cabeceras)
                    else:
                        resp = cliente.get(url, headers=cabeceras)
                    self._ultima = time.monotonic()
                except Exception as exc:  # red
                    ultimo_error = exc
                    continue
                if resp.status_code in (429, 503):
                    retry = resp.headers.get("Retry-After")
                    time.sleep(float(retry) if retry and retry.isdigit() else 60.0)
                    continue
                if resp.status_code != 200:
                    self._registrar(url, metodo, resp.status_code, None, cache=False)
                    raise PortalError(f"HTTP {resp.status_code} en {url}")
                crudo = resp.content
                if not crudo:
                    raise PortalError(f"respuesta vacía en {url}")
                destino.write_bytes(crudo)
                self._registrar(url, metodo, 200, crudo, cache=False)
                return crudo.decode("utf-8", errors="replace")
            self._registrar(url, metodo, 0, None, cache=False)
            raise PortalError(f"fallo de red en {url}: {ultimo_error}")
        finally:
            if propio:
                cliente.close()

    def _registrar(self, url, metodo, status, crudo: bytes | None, *, cache):
        self.llamadas.append(
            {
                "url": url,
                "method": metodo,
                "status": status,
                "bytes": len(crudo) if crudo is not None else 0,
                "sha256": hashlib.sha256(crudo).hexdigest() if crudo is not None else None,
                "cache": cache,
            }
        )

    # ------------------------------------------------------------- operaciones
    def listar_todos(self, limite: int = 2000) -> list[Perfil]:
        return parsear_investigadores(
            self._solicitar("POST", "/get-researchers", self._filtro(limite))
        )

    def listar_area(self, area_id: int, limite: int = 200) -> list[Perfil]:
        """Filtro por área (avanzado). No verificado en S84."""
        return parsear_investigadores(
            self._solicitar("POST", "/get-researchers", self._filtro(limite, area_id))
        )

    def publicaciones(self, limite: int = 12000) -> list[PublicacionPortal]:
        return parsear_publicaciones(
            self._solicitar("POST", "/get-publications", self._filtro(limite))
        )

    def leer_perfil(self, perfil_id: str | int) -> Perfil:
        perfil = parsear_perfil(self._solicitar("GET", f"/investigadores/{perfil_id}"))
        perfil.perfil_id = str(perfil_id)
        return perfil

    def leer_orcid(self, perfil_id: str | int) -> str | None:
        return self.leer_perfil(perfil_id).orcid
