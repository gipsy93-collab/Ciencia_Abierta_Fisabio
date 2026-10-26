"""Capa 2 — menciones institucionales.

En normativa, planes y recomendaciones lo normal no es citar el artículo:
se nombra la institución, el grupo o la red. Este módulo busca esas
menciones como **texto literal** y las registra en `mentions`.

Qué NO hace: no crea aristas de impacto. Una mención institucional no es
atribuible a una salida concreta, así que se declara aparte como **N6** y
nunca se suma al recuento de salidas citadas.
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass

from ..cascade.normalize import normalizar_texto
from ..corpus.pages import pagina_de
from ..provenance import nueva_acta
from .titles import normalizar_con_mapa

# (entidad, tipo, variantes literales que se reconocen)
ENTIDADES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "FISABIO",
        "institucion",
        (
            "FISABIO",
            "FISABIO-Public Health",
            "FISABIO Public Health",
            "Fundación para el Fomento de la Investigación Sanitaria y Biomédica de la Comunitat Valenciana",
            "Fundació per al Foment de la Investigació Sanitària i Biomèdica de la Comunitat Valenciana",
            "Foundation for the Promotion of Health and Biomedical Research in the Valencia Region",
        ),
    ),
    (
        "Área de Investigación en Vacunas",
        "grupo",
        (
            "Área de Investigación en Vacunas",
            "Area de Investigacion en Vacunas",
        ),
    ),
)


@dataclass(frozen=True)
class Mencion:
    entidad: str
    tipo: str
    literal: str
    offset: int


def _buscar_variante(norm: str, mapa: list[int], texto: str, variante: str) -> list[tuple[int, int]]:
    """Spans `(desde, hasta)` en el texto original para una variante."""
    objetivo = " ".join(normalizar_texto(variante).split())
    if not objetivo:
        return []
    objetivo = " " + objetivo + " "
    norm = " " + norm + " "
    spans: list[tuple[int, int]] = []
    pos = norm.find(objetivo)
    while pos != -1:
        inicio = pos
        fin = pos + len(objetivo) - 3
        if 0 <= inicio < len(mapa) and 0 <= fin < len(mapa):
            spans.append((mapa[inicio], mapa[fin] + 1))
        pos = norm.find(objetivo, pos + 1)
    return spans


def buscar_entidades(texto: str, entidades=ENTIDADES) -> list[Mencion]:
    """Menciones literales, sin solapes (gana la variante más larga)."""
    if not texto:
        return []
    norm, mapa = normalizar_con_mapa(texto)
    if not mapa:
        return []

    candidatas: list[tuple[int, int, str, str]] = []
    for entidad, tipo, variantes in entidades:
        for variante in variantes:
            for desde, hasta in _buscar_variante(norm, mapa, texto, variante):
                candidatas.append((desde, hasta, entidad, tipo))

    # Sin solapes: primero los spans más largos; luego por posición.
    candidatas.sort(key=lambda c: (c[0], -(c[1] - c[0])))
    elegidas: list[Mencion] = []
    ocupado: list[tuple[int, int]] = []
    for desde, hasta, entidad, tipo in candidatas:
        if any(desde < f and i < hasta for i, f in ocupado):
            continue
        literal = texto[desde:hasta]
        if not literal.strip():
            continue
        ocupado.append((desde, hasta))
        elegidas.append(Mencion(entidad=entidad, tipo=tipo, literal=literal, offset=desde))

    return sorted(elegidas, key=lambda m: m.offset)


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


def procesar_documento_menciones(
    store, doc_id: int, cfg, *, texto: str | None = None
) -> dict:
    """Registra menciones institucionales literales del documento."""
    texto = texto if texto is not None else _texto_documento(store, doc_id)
    menciones = buscar_entidades(texto)

    nuevas = 0
    descartadas = 0
    for m in menciones:
        pagina = pagina_de(cfg, doc_id, m.offset)
        try:
            if store.insert_mention(
                doc_id,
                m.entidad,
                m.tipo,
                m.literal,
                offset=m.offset,
                page=pagina,
                method="mencion_literal",
                texto_fuente=texto,
                acta=nueva_acta(
                    kind="mention",
                    literal=m.literal,
                    method="mencion_literal",
                    source=f"document:{doc_id}",
                    extra={"entidad": m.entidad, "offset": m.offset, "page": pagina},
                ),
            ):
                nuevas += 1
        except ValueError:
            descartadas += 1

    return {
        "doc_id": doc_id,
        "menciones": len(menciones),
        "nuevas": nuevas,
        "descartadas": descartadas,
    }
