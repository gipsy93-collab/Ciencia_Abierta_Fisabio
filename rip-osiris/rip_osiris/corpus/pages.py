"""Mapa de páginas de un documento: offset de carácter -> página.

El texto completo se guarda plano (un `.txt`), pero el expediente necesita
decir en qué página está el literal. Al ingerir un PDF se guarda un mapa
lateral con el offset inicial de cada página; aquí solo se consulta.
"""
from __future__ import annotations

import bisect
import json
import pathlib
import tempfile


def _ruta(cfg, doc_id: int) -> pathlib.Path:
    return pathlib.Path(cfg.corpus_dir) / f"{doc_id}.paginas.json"


def guardar_mapa(cfg, doc_id: int, inicios: list[int]) -> pathlib.Path:
    destino = _ruta(cfg, doc_id)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps({"inicios": inicios}), encoding="utf-8")
    return destino


def cargar_mapa(cfg, doc_id: int) -> list[int]:
    ruta = _ruta(cfg, doc_id)
    if not ruta.exists():
        return []
    try:
        return list(json.loads(ruta.read_text(encoding="utf-8")).get("inicios") or [])
    except (ValueError, OSError):
        return []


def pagina_de(cfg, doc_id: int, offset: int | None) -> int | None:
    """Página (1-based) que contiene `offset`, o `None` si no hay mapa."""
    if offset is None:
        return None
    inicios = cargar_mapa(cfg, doc_id)
    if not inicios:
        return None
    return bisect.bisect_right(inicios, offset)


def extraer_con_paginas(datos: bytes, content_type: str = "") -> tuple[str, list[int], str | None]:
    """Texto plano + offset inicial de cada página + título de metadatos.

    HTML = una sola página y sin metadatos.
    """
    if "pdf" in content_type.lower() or datos[:5] == b"%PDF-":
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:  # pragma: no cover - depende del entorno
            raise RuntimeError("PyMuPDF no instalado: pip install pymupdf") from exc

        with tempfile.TemporaryDirectory() as tmp:
            ruta = pathlib.Path(tmp) / "doc.pdf"
            ruta.write_bytes(datos)
            doc = fitz.open(str(ruta))
            try:
                paginas = [pagina.get_text("text") for pagina in doc]
                titulo = ((doc.metadata or {}).get("title") or "").strip() or None
            finally:
                doc.close()

        inicios: list[int] = []
        partes: list[str] = []
        cursor = 0
        for texto in paginas:
            inicios.append(cursor)
            partes.append(texto)
            cursor += len(texto) + 1  # el "\n" de unión
        return "\n".join(partes), inicios, titulo

    from .fulltext import extraer_texto_bytes

    return extraer_texto_bytes(datos, content_type), [0], None
