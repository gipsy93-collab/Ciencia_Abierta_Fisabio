"""Construcción y recorrido del grafo (SQLite, CTE recursiva).

El grafo vive en la tabla `edges`. Recorrer desde una salida da las aristas
`impact` (hops=1) y las `cascade` de segundo orden y siguientes.
"""
from __future__ import annotations

SQL_RECORRIDO = """
WITH RECURSIVE camino(src_kind, src_id, dst_kind, dst_id, edge_type, order_hops, hops) AS (
    SELECT src_kind, src_id, dst_kind, dst_id, edge_type, order_hops, 1
    FROM edges
    WHERE src_kind = ? AND src_id = ?
  UNION ALL
    SELECT e.src_kind, e.src_id, e.dst_kind, e.dst_id, e.edge_type, e.order_hops, c.hops + 1
    FROM edges e
    JOIN camino c ON e.src_kind = c.dst_kind AND e.src_id = c.dst_id
    WHERE c.hops < ?
)
SELECT * FROM camino;
"""


def recorrer(conn, src_kind: str, src_id: int, max_hops: int = 3) -> list[dict]:
    cur = conn.execute(SQL_RECORRIDO, (src_kind, src_id, max_hops))
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, fila)) for fila in cur.fetchall()]
