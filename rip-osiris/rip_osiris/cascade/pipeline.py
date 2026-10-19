"""El pipeline de la cascada: texto -> referencias -> aristas.

Encadena lo que antes eran piezas sueltas:

    texto del documento
      -> references.extraer()
      -> resolve.resolver()  (a) DOI inline -> (b) Crossref -> (c) corpus
      -> store.insert_ref()
      -> store.insert_edge()  con literal verificado

Dos tipos de arista salen de aquí:

- `cascade`: documento de política -> documento de política (rama c).
- `impact`:  salida FISABIO -> documento de política (rama a/b, o mención
  directa del DOI de la salida en el texto).

Ninguna arista se escribe sin `evidence_literal` presente en el texto fuente:
`Store.insert_edge` lo vuelve a comprobar.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..provenance import nueva_acta
from . import references
from .legal import claves_normativas, normalizar_source_id
from .match import CorpusIndex, Doc
from .normalize import normalizar_doi
from .resolve import resolver


@dataclass
class ResumenCascada:
    doc_id: int
    referencias: int = 0
    por_doi_inline: int = 0
    por_crossref: int = 0
    por_corpus: int = 0
    sin_resolver: int = 0
    aristas_cascade: int = 0
    aristas_impact: int = 0
    impactos_por_mencion: int = 0
    aristas_norma: int = 0
    aristas_existentes: int = 0
    aristas_descartadas: int = 0
    detalles: list[dict] = field(default_factory=list)

    def como_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "referencias": self.referencias,
            "por_doi_inline": self.por_doi_inline,
            "por_crossref": self.por_crossref,
            "por_corpus": self.por_corpus,
            "sin_resolver": self.sin_resolver,
            "aristas_cascade": self.aristas_cascade,
            "aristas_impact": self.aristas_impact,
            "impactos_por_mencion": self.impactos_por_mencion,
            "aristas_norma": self.aristas_norma,
            "aristas_existentes": self.aristas_existentes,
            "aristas_descartadas": self.aristas_descartadas,
        }


def _indice(store) -> CorpusIndex:
    filas = store.conn.execute(
        "SELECT id, title, org, year FROM documents WHERE title IS NOT NULL"
    ).fetchall()
    return CorpusIndex(
        [
            Doc(
                doc_id=int(f["id"]),
                title=f["title"],
                org=f["org"],
                year=f["year"],
            )
            for f in filas
        ]
    )


def _mapa_outputs(store) -> dict[str, int]:
    filas = store.conn.execute(
        "SELECT id, doi FROM outputs WHERE doi IS NOT NULL"
    ).fetchall()
    salida: dict[str, int] = {}
    for f in filas:
        doi = normalizar_doi(f["doi"])
        if doi:
            salida[doi] = int(f["id"])
    return salida


def _mapa_normas(store) -> dict[str, int]:
    """`source_id` normalizado -> doc_id, para citas del tipo «Ley 14/1986»."""
    filas = store.conn.execute("SELECT id, source_id FROM documents").fetchall()
    salida: dict[str, int] = {}
    for f in filas:
        clave = normalizar_source_id(f["source_id"])
        if clave:
            salida[clave] = int(f["id"])
    return salida


def _texto_documento(store, doc_id: int) -> str:
    fila = store.conn.execute(
        "SELECT fulltext_path FROM documents WHERE id = ?", (doc_id,)
    ).fetchone()
    if fila is None:
        raise KeyError(f"document {doc_id} no existe")
    ruta = fila["fulltext_path"]
    if not ruta:
        raise ValueError(f"document {doc_id} no tiene fulltext_path")
    from pathlib import Path

    return Path(ruta).read_text(encoding="utf-8", errors="replace")


def procesar_documento(
    store,
    doc_id: int,
    cfg,
    *,
    crossref=None,
    texto: str | None = None,
) -> ResumenCascada:
    """Extrae, resuelve y persiste las aristas de un documento del corpus."""
    fila = store.conn.execute(
        "SELECT id FROM documents WHERE id = ?", (doc_id,)
    ).fetchone()
    if fila is None:
        raise KeyError(f"document {doc_id} no existe")

    texto = texto if texto is not None else _texto_documento(store, doc_id)
    resumen = ResumenCascada(doc_id=doc_id)
    indice = _indice(store)
    outputs_por_doi = _mapa_outputs(store)
    impactos_ya_registrados: set[str] = set()

    for ref in references.extraer(texto):
        resumen.referencias += 1
        acta = nueva_acta(
            kind="ref",
            literal=ref.raw,
            method="references.heuristica",
            source=f"document:{doc_id}",
            extra={"section": ref.section, "offset": ref.offset},
        )
        resuelto = resolver(ref.raw, indice, crossref, cfg)

        try:
            store.insert_ref(
                doc_id,
                ref.raw,
                section=ref.section,
                offset=ref.offset,
                resolved_doi=resuelto.doi,
                resolved_doc_id=resuelto.doc_id,
                method=resuelto.method,
                confidence=resuelto.confidence,
                texto_fuente=texto,
                acta=acta,
            )
        except ValueError:
            resumen.aristas_descartadas += 1
            continue

        if resuelto.method == "doi_inline":
            resumen.por_doi_inline += 1
        elif resuelto.method == "crossref_query":
            resumen.por_crossref += 1
        elif resuelto.method == "corpus_match":
            resumen.por_corpus += 1
        else:
            resumen.sin_resolver += 1

        if resuelto.doc_id is not None and resuelto.doc_id != doc_id:
            _insertar_cascade(store, resumen, doc_id, resuelto, ref.raw, texto)
        if resuelto.doi and resuelto.doi in outputs_por_doi:
            impactos_ya_registrados.add(resuelto.doi)
            _insertar_impact(
                store,
                resumen,
                outputs_por_doi[resuelto.doi],
                doc_id,
                ref.raw,
                texto,
                resuelto.method,
                resuelto.confidence,
            )

    resumen.impactos_por_mencion = _impactos_por_mencion(
        store, resumen, texto, doc_id, outputs_por_doi, impactos_ya_registrados
    )
    resumen.aristas_norma = _insertar_normas(store, resumen, doc_id, texto)
    return resumen


def _insertar_normas(store, resumen, doc_id, texto) -> int:
    """Aristas `cascade` por cita normativa («Ley 14/1986»).

    Los documentos de política se citan por número de norma, no por autor-año.
    La clave sale del `source_id` del documento destino, así que la coincidencia
    es exacta y no necesita umbral difuso.
    """
    normas = _mapa_normas(store)
    nuevas = 0
    for literal, clave in claves_normativas(texto):
        destino = normas.get(clave)
        if destino is None or destino == doc_id:
            continue
        try:
            nueva = store.insert_edge(
                src_kind="document",
                src_id=doc_id,
                dst_kind="document",
                dst_id=destino,
                edge_type="cascade",
                evidence_literal=literal,
                method="cita_normativa",
                confidence=1.0,
                texto_fuente=texto,
                acta=nueva_acta(
                    kind="edge",
                    literal=literal,
                    method="cita_normativa",
                    source=f"document:{doc_id}",
                    confidence=1.0,
                ),
            )
            if nueva:
                nuevas += 1
            else:
                resumen.aristas_existentes += 1
        except ValueError:
            resumen.aristas_descartadas += 1
    return nuevas


def _insertar_cascade(store, resumen, doc_id, resuelto, literal, texto) -> None:
    try:
        nueva = store.insert_edge(
            src_kind="document",
            src_id=doc_id,
            dst_kind="document",
            dst_id=resuelto.doc_id,
            edge_type="cascade",
            evidence_literal=literal,
            method=resuelto.method,
            confidence=resuelto.confidence,
            texto_fuente=texto,
            acta=nueva_acta(
                kind="edge",
                literal=literal,
                method=resuelto.method,
                source=f"document:{doc_id}",
                confidence=resuelto.confidence,
            ),
        )
        if nueva:
            resumen.aristas_cascade += 1
        else:
            resumen.aristas_existentes += 1
    except ValueError:
        resumen.aristas_descartadas += 1


def _insertar_impact(
    store, resumen, output_id, doc_id, literal, texto, method, confidence
) -> None:
    try:
        nueva = store.insert_edge(
            src_kind="output",
            src_id=output_id,
            dst_kind="document",
            dst_id=doc_id,
            edge_type="impact",
            evidence_literal=literal,
            method=method,
            confidence=confidence,
            texto_fuente=texto,
            acta=nueva_acta(
                kind="edge",
                literal=literal,
                method=method,
                source=f"document:{doc_id}",
                confidence=confidence,
            ),
        )
        if nueva:
            resumen.aristas_impact += 1
        else:
            resumen.aristas_existentes += 1
    except ValueError:
        resumen.aristas_descartadas += 1


def _impactos_por_mencion(
    store, resumen, texto, doc_id, outputs_por_doi, ya_registrados: set[str]
) -> int:
    """DOI de una salida citado directamente en el cuerpo (sin cadena de ref).

    Cubre el caso en que el documento menciona el DOI en el texto y la
    heurística de referencias no lo aísla como cadena. Los DOI ya convertidos
    en arista desde una referencia no se repiten: una mención no duplica una
    cita bibliográfica.
    """
    encontrados = 0
    for doi, output_id in outputs_por_doi.items():
        if doi in ya_registrados:
            continue
        pos = texto.lower().find(doi)
        if pos == -1:
            continue
        literal = texto[pos : pos + len(doi)]
        try:
            nueva = store.insert_edge(
                src_kind="output",
                src_id=output_id,
                dst_kind="document",
                dst_id=doc_id,
                edge_type="impact",
                evidence_literal=literal,
                method="doi_mencion_directa",
                confidence=1.0,
                texto_fuente=texto,
                acta=nueva_acta(
                    kind="edge",
                    literal=literal,
                    method="doi_mencion_directa",
                    source=f"document:{doc_id}",
                    confidence=1.0,
                ),
            )
            encontrados += 1
        except ValueError:
            resumen.aristas_descartadas += 1
    return encontrados
