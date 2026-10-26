"""Capa 1b — mención por título literal.

Los documentos de política citan mucho sin DOI: reproducen el título del
artículo en la bibliografía. Este módulo busca el título como **frase
literal** en el texto (normalizado, tolerante a acentos y a los cortes de
línea del PDF) y devuelve el fragmento exacto del original, que es lo que
exige el guardián de fidelidad.

Lo que NO hace: fuzzy contra la página entera. Un título a medias no es
una mención; es una pista.
"""
from __future__ import annotations

import pathlib
import unicodedata
from dataclasses import dataclass

from ..cascade.normalize import normalizar_texto
from ..corpus.pages import pagina_de
from ..provenance import nueva_acta


@dataclass(frozen=True)
class Coincidencia:
    output_id: int
    titulo: str
    literal: str
    offset: int
    tokens: int


def normalizar_con_mapa(texto: str) -> tuple[str, list[int]]:
    """Texto normalizado + mapa de cada carácter normalizado a su offset original."""
    salida: list[str] = []
    mapa: list[int] = []
    en_espacio = False
    pegar = False  # venimos de un guion de fin de línea: la palabra continúa
    for i, ch in enumerate(texto):
        if ch == "\u00ad":
            pegar = True
            continue
        if ch in ("-", "\u2010", "\u2011") and i + 1 < len(texto) and texto[i + 1] in "\r\n":
            pegar = True
            continue
        if pegar and ch in "\r\n\t ":
            continue  # el salto de línea no separa: "influen-\nza" -> "influenza"
        if ch.isalnum():
            for c in unicodedata.normalize("NFKD", ch):
                if unicodedata.combining(c):
                    continue
                salida.append(c.lower())
                mapa.append(i)
            en_espacio = False
            pegar = False
        elif not en_espacio:
            salida.append(" ")
            mapa.append(i)
            en_espacio = True
            pegar = False
        else:
            pegar = False
    return "".join(salida), mapa


def _clave_titulo(titulo: str) -> str:
    return " ".join(normalizar_texto(titulo).split())


def buscar_titulos(
    texto: str,
    salidas: list[tuple[int, str]],
    *,
    min_tokens: int = 8,
    max_por_titulo: int = 3,
) -> list[Coincidencia]:
    """Coincidencias literales de título, con el fragmento exacto del texto."""
    if not texto or not salidas:
        return []

    norm, mapa = normalizar_con_mapa(texto)
    if not mapa:
        return []
    norm = " " + norm + " "
    coincidencias: list[Coincidencia] = []

    for output_id, titulo in salidas:
        palabras = _clave_titulo(titulo or "").split()
        if not palabras:
            continue
        significativas = [p for p in palabras if len(p) > 2]
        if len(significativas) < min_tokens:
            continue

        objetivo = " " + " ".join(palabras) + " "
        pos = norm.find(objetivo)
        encontrados = 0
        while pos != -1 and encontrados < max_por_titulo:
            # norm = " " + texto_normalizado + " "  ->  el primer carácter
            # del objetivo cae en el índice `pos` del texto normalizado.
            inicio = pos
            fin = pos + len(objetivo) - 3  # descuenta los dos espacios de guarda
            if 0 <= inicio < len(mapa) and 0 <= fin < len(mapa):
                desde = mapa[inicio]
                hasta = mapa[fin] + 1
                literal = texto[desde:hasta]
                if literal.strip():
                    coincidencias.append(
                        Coincidencia(
                            output_id=output_id,
                            titulo=titulo,
                            literal=literal,
                            offset=desde,
                            tokens=len(significativas),
                        )
                    )
                    encontrados += 1
            pos = norm.find(objetivo, pos + 1)

    return coincidencias


def _texto_documento(store, doc_id: int) -> str:
    fila = store.conn.execute(
        "SELECT fulltext_path FROM documents WHERE id = ?", (doc_id,)
    ).fetchone()
    if fila is None:
        raise KeyError(f"document {doc_id} no existe")
    ruta = fila["fulltext_path"]
    if not ruta:
        raise ValueError(f"document {doc_id} no tiene fulltext_path")
    return pathlib.Path(ruta).read_text(encoding="utf-8", errors="replace")


def procesar_documento_titulos(
    store,
    doc_id: int,
    cfg,
    *,
    texto: str | None = None,
    min_tokens: int | None = None,
) -> dict:
    """Inserta aristas `impact` por título literal. Sin literal no hay arista."""
    texto = texto if texto is not None else _texto_documento(store, doc_id)
    mínimo = cfg.demo_min_tokens_titulo if min_tokens is None else min_tokens

    salidas = [
        (int(f["id"]), f["title"])
        for f in store.conn.execute(
            "SELECT id, title FROM outputs WHERE title IS NOT NULL"
        ).fetchall()
    ]
    coincidencias = buscar_titulos(texto, salidas, min_tokens=mínimo)

    aristas = 0
    descartadas = 0
    for c in coincidencias:
        pagina = pagina_de(cfg, doc_id, c.offset)
        try:
            nueva = store.insert_edge(
                src_kind="output",
                src_id=c.output_id,
                dst_kind="document",
                dst_id=doc_id,
                edge_type="impact",
                evidence_literal=c.literal,
                method="titulo_literal",
                confidence=0.95,
                texto_fuente=texto,
                acta=nueva_acta(
                    kind="edge",
                    literal=c.literal,
                    method="titulo_literal",
                    source=f"document:{doc_id}",
                    confidence=0.95,
                    extra={"offset": c.offset, "page": pagina, "tokens": c.tokens},
                ),
            )
            aristas += int(nueva)
        except ValueError:
            descartadas += 1

    return {
        "doc_id": doc_id,
        "coincidencias": len(coincidencias),
        "aristas_nuevas": aristas,
        "descartadas": descartadas,
    }
