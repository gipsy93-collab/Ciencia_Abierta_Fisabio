PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS outputs (
  id INTEGER PRIMARY KEY,
  doi TEXT UNIQUE,
  orcid TEXT,
  ror TEXT,
  grant_code TEXT,
  title TEXT,
  year INTEGER,
  source TEXT
);

CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY,
  source TEXT NOT NULL,
  source_id TEXT NOT NULL,
  url TEXT,
  doc_type TEXT,
  title TEXT,
  org TEXT,
  year INTEGER,
  doi TEXT,
  license TEXT,
  fetched_at TEXT,
  sha256 TEXT,
  fulltext_path TEXT,
  UNIQUE(source, source_id)
);

CREATE TABLE IF NOT EXISTS refs (
  id INTEGER PRIMARY KEY,
  doc_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
  raw_string TEXT NOT NULL,
  section TEXT,
  offset INTEGER,
  resolved_doi TEXT,
  resolved_doc_id INTEGER REFERENCES documents(id),
  method TEXT,
  confidence REAL,
  provenance_id TEXT
);

CREATE TABLE IF NOT EXISTS edges (
  id INTEGER PRIMARY KEY,
  src_kind TEXT NOT NULL,
  src_id INTEGER NOT NULL,
  dst_kind TEXT NOT NULL,
  dst_id INTEGER NOT NULL,
  edge_type TEXT NOT NULL,
  order_hops INTEGER DEFAULT 1,
  evidence_literal TEXT NOT NULL,
  method TEXT,
  confidence REAL,
  provenance_id TEXT,
  UNIQUE(src_kind, src_id, dst_kind, dst_id, edge_type, evidence_literal)
);

CREATE TABLE IF NOT EXISTS provenance (
  id TEXT PRIMARY KEY,
  kind TEXT,
  literal TEXT,
  method TEXT,
  source TEXT,
  fetched_at TEXT,
  payload_json TEXT
);

CREATE TABLE IF NOT EXISTS coverage (
  source TEXT NOT NULL,
  query TEXT NOT NULL,
  queried INTEGER DEFAULT 0,
  hits INTEGER DEFAULT 0,
  measured_at TEXT,
  declared TEXT,
  PRIMARY KEY (source, query)
);

CREATE INDEX IF NOT EXISTS idx_refs_doc ON refs(doc_id);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src_kind, src_id);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst_kind, dst_id);
CREATE INDEX IF NOT EXISTS idx_documents_doi ON documents(doi);
