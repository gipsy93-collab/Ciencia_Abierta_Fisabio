"""Ingesta del corpus de política: URL -> documento + texto + huella.

Regla de la casa: el documento se trae DEL ORIGEN (nunca de un agregado
truncado), se respeta `robots.txt` y se guarda `sha256` para que el
hallazgo sea reproducible mañana.
"""
from __future__ import annotations

import pathlib
import re
import urllib.parse
from dataclasses import dataclass, field

from .corpus.fetch import Fetcher, FetchError
from .corpus.pages import extraer_con_paginas, guardar_mapa

_TIPOS_POR_HOST = (
    ("boe.es", "normativa"),
    ("dogv.gva.es", "normativa"),
    ("eur-lex.europa.eu", "normativa"),
    ("guiasalud.es", "gpc"),
    ("inahta.org", "hta"),
    ("sanidad.gob.es", "estrategia"),
    ("who.int", "informe_agencia"),
    ("paho.org", "informe_agencia"),
    ("ecdc.europa.eu", "informe_agencia"),
)

_TIPOS_POR_RUTA = (
    ("/plan", "plan"),
    ("/estrategia", "estrategia"),
    ("/guia", "gpc"),
    ("/protocolo", "gpc"),
    ("/informe", "informe"),
)


def host_de(url: str) -> str:
    host = (urllib.parse.urlsplit(url).netloc or "").lower()
    return host[4:] if host.startswith("www.") else host


def inferir_doc_type(url: str) -> str:
    host = host_de(url)
    for dominio, tipo in _TIPOS_POR_HOST:
        if host == dominio or host.endswith("." + dominio):
            return tipo
    ruta = urllib.parse.urlsplit(url).path.lower()
    for fragmento, tipo in _TIPOS_POR_RUTA:
        if fragmento in ruta:
            return tipo
    return "informe"


_RE_BOILERPLATE = re.compile(r"^(fecha|sustituye|p[áa]gina|page)\b", re.IGNORECASE)
_RE_ROTULO = re.compile(
    r"^(technical report|report|informe t[ée]cnico|summary|executive summary|"
    r"surveillance report|guidance|an agency of the european union)$",
    re.IGNORECASE,
)


def _es_boilerplate(linea: str) -> bool:
    return bool(_RE_BOILERPLATE.match(linea) or _RE_ROTULO.match(linea))


def titulo_probable(texto: str, limite: int = 140, metadatos: str | None = None) -> str | None:
    """Título del documento: metadatos del PDF si existen, si no, cabecera.

    La cabecera de un informe de política no es una línea: el título va partido
    en varias. Se unen las primeras líneas útiles (hasta tres) sin rótulos.
    """
    if metadatos and len(metadatos) >= 20 and not metadatos.lower().startswith("microsoft word"):
        return metadatos.strip()[:240]

    lineas = [" ".join(linea.split()) for linea in texto.splitlines()[:30]]
    lineas = [l for l in lineas if len(l) >= 4 and not _es_boilerplate(l)]
    if not lineas:
        return None

    partes: list[str] = []
    for linea in lineas[:3]:
        candidato = " ".join(partes + [linea])
        if len(candidato) > limite:
            break
        partes.append(linea)
        if linea.endswith("."):
            break
    return " ".join(partes)[:limite] or None


def leer_urls(ruta: str | pathlib.Path) -> list[str]:
    """Una URL por línea; `#` abre comentario y se ignoran vacías."""
    urls: list[str] = []
    for linea in pathlib.Path(ruta).read_text(encoding="utf-8").splitlines():
        limpia = linea.split("#", 1)[0].strip()
        if limpia:
            urls.append(limpia)
    return urls


@dataclass
class DocumentoIngerido:
    doc_id: int
    url: str
    source: str
    doc_type: str
    caracteres: int
    sha256: str
    paginas: int
    cache: bool


@dataclass
class ResumenIngesta:
    documentos: list[DocumentoIngerido] = field(default_factory=list)
    existentes: list[str] = field(default_factory=list)
    errores: list[dict] = field(default_factory=list)

    def como_dict(self) -> dict:
        return {
            "documentos": len(self.documentos),
            "existentes": len(self.existentes),
            "errores": len(self.errores),
            "detalle": [
                {
                    "doc_id": d.doc_id,
                    "url": d.url,
                    "doc_type": d.doc_type,
                    "caracteres": d.caracteres,
                    "paginas": d.paginas,
                    "cache": d.cache,
                }
                for d in self.documentos
            ],
            "fallos": self.errores,
        }


def _ya_ingerido(store, source: str, source_id: str) -> dict | None:
    fila = store.conn.execute(
        "SELECT id, fulltext_path FROM documents WHERE source = ? AND source_id = ?",
        (source, source_id),
    ).fetchone()
    if fila is None:
        return None
    ruta = fila["fulltext_path"]
    if ruta and pathlib.Path(ruta).exists():
        return {"id": int(fila["id"])}
    return None


def source_id_de(url: str) -> str:
    """Identidad del documento dentro del host: ruta **y** query.

    Hay portales que sirven documentos distintos por query (`boe.es/diario_boe/
    txt.php?id=…`). Si se descarta la query, documentos diferentes colisionan.
    """
    partes = urllib.parse.urlsplit(url)
    ruta = partes.path.strip("/")
    if partes.query:
        return f"{ruta}?{partes.query}" if ruta else f"?{partes.query}"
    return ruta or url


def ingerir_urls(
    store,
    cfg,
    urls: list[str],
    *,
    fetcher: Fetcher | None = None,
    doc_type: str | None = None,
) -> ResumenIngesta:
    """Descarga, extrae y persiste cada URL. Idempotente."""
    resumen = ResumenIngesta()
    fetcher = fetcher or Fetcher(cfg)
    cfg.corpus_dir.mkdir(parents=True, exist_ok=True)

    for url in urls:
        source = host_de(url) or "desconocido"
        source_id = source_id_de(url)
        try:
            existente = _ya_ingerido(store, source, source_id)
            if existente is not None:
                resumen.existentes.append(url)
                continue

            datos, meta = fetcher.obtener(url)
            texto, inicios, titulo_meta = extraer_con_paginas(datos, meta.get("content_type", ""))
            if len(texto.strip()) < 200:
                resumen.errores.append({"url": url, "error": "texto extraído insuficiente (¿escaneado?)"})
                continue

            tipo = doc_type or inferir_doc_type(url)
            doc_id = store.upsert_document(
                source=source,
                source_id=source_id,
                url=url,
                doc_type=tipo,
                title=titulo_probable(texto, metadatos=titulo_meta),
                sha256=meta.get("sha256"),
            )
            destino = pathlib.Path(cfg.corpus_dir) / f"{doc_id}.txt"
            destino.write_text(texto, encoding="utf-8")
            store.conn.execute(
                "UPDATE documents SET fulltext_path = ? WHERE id = ?",
                (str(destino), doc_id),
            )
            store.conn.commit()
            guardar_mapa(cfg, doc_id, inicios)

            store.insert_crawl_log(
                url=url,
                method="GET",
                status=200,
                bytes=int(meta.get("bytes") or len(datos)),
                sha256=meta.get("sha256"),
                cache=bool(meta.get("cache")),
            )
            resumen.documentos.append(
                DocumentoIngerido(
                    doc_id=doc_id,
                    url=url,
                    source=source,
                    doc_type=tipo,
                    caracteres=len(texto),
                    sha256=str(meta.get("sha256") or ""),
                    paginas=len(inicios),
                    cache=bool(meta.get("cache")),
                )
            )
        except (FetchError, OSError, ValueError) as exc:
            resumen.errores.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})

    if resumen.documentos:
        por_fuente: dict[str, int] = {}
        for doc in resumen.documentos:
            por_fuente[doc.source] = por_fuente.get(doc.source, 0) + 1
        for fuente, cuantos in por_fuente.items():
            store.set_coverage(fuente, "ingest", hits=cuantos, declared="muestra")

    return resumen
