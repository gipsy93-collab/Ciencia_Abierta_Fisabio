"""Expediente tipado por salida (no un score)."""
from __future__ import annotations

from ..cascade import graph
from . import classify


def construir(store, output_id: int, max_hops: int = 3) -> dict:
    fila = store.conn.execute(
        "SELECT * FROM outputs WHERE id = ?", (output_id,)
    ).fetchone()
    if fila is None:
        raise KeyError(f"output {output_id} no existe")

    items: list[dict] = []
    for arista in graph.recorrer(store.conn, "output", output_id, max_hops):
        doc = store.conn.execute(
            "SELECT * FROM documents WHERE id = ?", (arista["dst_id"],)
        ).fetchone()
        doc_d = dict(doc) if doc is not None else None
        n = classify.nivel(doc_d.get("doc_type") if doc_d else None)
        items.append(
            {
                "nivel": n,
                "descripcion": classify.descripcion(n),
                "edge_type": arista["edge_type"],
                "hops": arista["hops"],
                "document": doc_d,
            }
        )

    return {
        "output": dict(fila),
        "items": items,
        "cobertura": store.coverage(),
    }
