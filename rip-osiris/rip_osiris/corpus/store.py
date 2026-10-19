"""Almacén SQLite: esquema, upserts idempotentes e invariantes de fidelidad."""
from __future__ import annotations

import hashlib
import json
import pathlib
import sqlite3

from ..guardian import exigir_literal
from ..provenance import ahora

_SCHEMA_PATH = pathlib.Path(__file__).with_name("schema.sql")


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class Store:
    def __init__(self, path: str | pathlib.Path):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.migrar()

    # ------------------------------------------------------------------ schema
    def migrar(self) -> None:
        self.conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
        self.conn.commit()

    # ----------------------------------------------------------------- outputs
    def upsert_output(
        self,
        *,
        doi: str | None = None,
        orcid: str | None = None,
        ror: str | None = None,
        grant_code: str | None = None,
        title: str | None = None,
        year: int | None = None,
        source: str | None = None,
    ) -> int:
        fila = None
        if doi:
            fila = self.conn.execute(
                "SELECT id FROM outputs WHERE doi = ?", (doi,)
            ).fetchone()
        if fila is None and orcid and title:
            fila = self.conn.execute(
                "SELECT id FROM outputs WHERE orcid = ? AND title = ?", (orcid, title)
            ).fetchone()

        if fila is not None:
            self.conn.execute(
                """UPDATE outputs
                   SET doi=?, orcid=?, ror=?, grant_code=?, title=?, year=?, source=?
                   WHERE id=?""",
                (doi, orcid, ror, grant_code, title, year, source, fila["id"]),
            )
            oid = fila["id"]
        else:
            cur = self.conn.execute(
                """INSERT INTO outputs(doi, orcid, ror, grant_code, title, year, source)
                   VALUES(?,?,?,?,?,?,?)""",
                (doi, orcid, ror, grant_code, title, year, source),
            )
            oid = int(cur.lastrowid)
        self.conn.commit()
        return oid

    # --------------------------------------------------------------- documents
    def upsert_document(
        self,
        *,
        source: str,
        source_id: str,
        url: str | None = None,
        doc_type: str | None = None,
        title: str | None = None,
        org: str | None = None,
        year: int | None = None,
        doi: str | None = None,
        license: str | None = None,
        fulltext_path: str | None = None,
        sha256: str | None = None,
    ) -> int:
        self.conn.execute(
            """INSERT INTO documents
                 (source, source_id, url, doc_type, title, org, year, doi,
                  license, fetched_at, sha256, fulltext_path)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(source, source_id) DO UPDATE SET
                 url=COALESCE(excluded.url, documents.url),
                 doc_type=COALESCE(excluded.doc_type, documents.doc_type),
                 title=COALESCE(excluded.title, documents.title),
                 org=COALESCE(excluded.org, documents.org),
                 year=COALESCE(excluded.year, documents.year),
                 doi=COALESCE(excluded.doi, documents.doi),
                 license=COALESCE(excluded.license, documents.license),
                 sha256=COALESCE(excluded.sha256, documents.sha256),
                 fulltext_path=COALESCE(excluded.fulltext_path, documents.fulltext_path)""",
            (
                source,
                source_id,
                url,
                doc_type,
                title,
                org,
                year,
                doi,
                license,
                ahora(),
                sha256,
                fulltext_path,
            ),
        )
        self.conn.commit()
        fila = self.conn.execute(
            "SELECT id FROM documents WHERE source = ? AND source_id = ?",
            (source, source_id),
        ).fetchone()
        return int(fila["id"])

    # -------------------------------------------------------------------- refs
    def insert_ref(
        self,
        doc_id: int,
        raw_string: str,
        *,
        section: str | None = None,
        offset: int | None = None,
        resolved_doi: str | None = None,
        resolved_doc_id: int | None = None,
        method: str | None = None,
        confidence: float | None = None,
        texto_fuente: str | None = None,
        acta: dict | None = None,
    ) -> int:
        if not raw_string or not raw_string.strip():
            raise ValueError("una referencia sin cadena literal no se registra")
        if texto_fuente is not None:
            exigir_literal(texto_fuente, raw_string)
        pid = self._guardar_acta(acta)

        existente = self.conn.execute(
            "SELECT id FROM refs WHERE doc_id = ? AND raw_string = ?",
            (doc_id, raw_string),
        ).fetchone()
        if existente is not None:
            self.conn.execute(
                """UPDATE refs
                   SET section=?, offset=?, resolved_doi=?, resolved_doc_id=?,
                       method=?, confidence=?, provenance_id=?
                   WHERE id=?""",
                (
                    section,
                    offset,
                    resolved_doi,
                    resolved_doc_id,
                    method,
                    confidence,
                    pid,
                    existente["id"],
                ),
            )
            self.conn.commit()
            return int(existente["id"])

        cur = self.conn.execute(
            """INSERT INTO refs
                 (doc_id, raw_string, section, offset, resolved_doi,
                  resolved_doc_id, method, confidence, provenance_id)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                doc_id,
                raw_string,
                section,
                offset,
                resolved_doi,
                resolved_doc_id,
                method,
                confidence,
                pid,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    # ------------------------------------------------------------------- edges
    def insert_edge(
        self,
        *,
        src_kind: str,
        src_id: int,
        dst_kind: str,
        dst_id: int,
        edge_type: str,
        evidence_literal: str,
        method: str | None = None,
        confidence: float | None = None,
        order_hops: int = 1,
        texto_fuente: str | None = None,
        acta: dict | None = None,
    ) -> bool:
        # Invariante de fidelidad: sin literal no hay arista.
        if not evidence_literal or not evidence_literal.strip():
            raise ValueError(
                "una arista sin evidence_literal no se registra (guardián de fidelidad)"
            )
        if texto_fuente is not None:
            exigir_literal(texto_fuente, evidence_literal)

        pid = self._guardar_acta(acta)
        cur = self.conn.execute(
            """INSERT OR IGNORE INTO edges
                 (src_kind, src_id, dst_kind, dst_id, edge_type, order_hops,
                  evidence_literal, method, confidence, provenance_id)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                src_kind,
                src_id,
                dst_kind,
                dst_id,
                edge_type,
                order_hops,
                evidence_literal,
                method,
                confidence,
                pid,
            ),
        )
        self.conn.commit()
        return cur.rowcount > 0

    # ---------------------------------------------------------------- coverage
    def set_coverage(
        self,
        source: str,
        query: str,
        *,
        queried: bool = True,
        hits: int = 0,
        declared: str = "cubierta",
    ) -> None:
        self.conn.execute(
            """INSERT INTO coverage(source, query, queried, hits, measured_at, declared)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(source, query) DO UPDATE SET
                 queried=excluded.queried, hits=excluded.hits,
                 measured_at=excluded.measured_at, declared=excluded.declared""",
            (source, query, int(queried), hits, ahora(), declared),
        )
        self.conn.commit()

    def coverage(self) -> list[dict]:
        cur = self.conn.execute("SELECT * FROM coverage ORDER BY source, query")
        return [dict(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------ actas
    def _guardar_acta(self, acta: dict | None) -> str | None:
        if not acta:
            return None
        self.conn.execute(
            """INSERT OR REPLACE INTO provenance
                 (id, kind, literal, method, source, fetched_at, payload_json)
               VALUES(?,?,?,?,?,?,?)""",
            (
                acta["id"],
                acta.get("kind"),
                acta.get("literal"),
                acta.get("method"),
                acta.get("source"),
                acta.get("fetched_at"),
                json.dumps(acta, ensure_ascii=False, sort_keys=True),
            ),
        )
        return acta["id"]

    # ------------------------------------------------------------------ cierre
    def close(self) -> None:
        self.conn.close()


def sha256_bytes(b: bytes) -> str:
    return _sha256_bytes(b)
