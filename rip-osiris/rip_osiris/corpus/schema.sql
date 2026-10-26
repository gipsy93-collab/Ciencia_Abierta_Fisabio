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

-- ---------------------------------------------------------------------------
-- Capa 2: menciones institucionales (no atribuibles a una salida concreta)
-- ---------------------------------------------------------------------------
-- En normativa y planes lo normal no es citar el artículo: se nombra la
-- institución. Sin `output_id` no hay arista de impacto (N1-N6 por salida),
-- pero sí un rastro documentado y literal que se declara como N6.
CREATE TABLE IF NOT EXISTS mentions (
  id INTEGER PRIMARY KEY,
  doc_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
  entidad TEXT NOT NULL,
  tipo TEXT NOT NULL,
  literal TEXT NOT NULL,
  offset INTEGER,
  page INTEGER,
  method TEXT,
  provenance_id TEXT,
  UNIQUE(doc_id, entidad, literal)
);

CREATE INDEX IF NOT EXISTS idx_mentions_doc ON mentions(doc_id);

-- ---------------------------------------------------------------------------
-- P1: mapeo de producción y fuentes (roster del portal + obras + presencia)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS researchers (
  id INTEGER PRIMARY KEY,
  portal_id TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  area TEXT,
  role TEXT,
  orcid TEXT,
  orcid_source TEXT,
  status TEXT DEFAULT 'activo',
  first_seen TEXT,
  last_seen TEXT
);

CREATE TABLE IF NOT EXISTS works (
  id INTEGER PRIMARY KEY,
  doi TEXT UNIQUE,
  title TEXT NOT NULL,
  year INTEGER,
  type TEXT,
  canonical_key TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS work_ids (
  id INTEGER PRIMARY KEY,
  work_id INTEGER REFERENCES works(id) ON DELETE CASCADE,
  scheme TEXT NOT NULL,
  value TEXT NOT NULL,
  UNIQUE(scheme, value)
);

CREATE TABLE IF NOT EXISTS author_work (
  researcher_id INTEGER REFERENCES researchers(id) ON DELETE CASCADE,
  work_id INTEGER REFERENCES works(id) ON DELETE CASCADE,
  source TEXT NOT NULL,
  confidence REAL,
  PRIMARY KEY (researcher_id, work_id, source)
);

CREATE TABLE IF NOT EXISTS presence (
  work_id INTEGER REFERENCES works(id) ON DELETE CASCADE,
  source TEXT NOT NULL,
  status TEXT NOT NULL,
  method TEXT,
  confidence REAL,
  matched_id TEXT,
  checked_at TEXT,
  http_status INTEGER,
  note TEXT,
  PRIMARY KEY (work_id, source)
);

CREATE TABLE IF NOT EXISTS source_registry (
  source TEXT PRIMARY KEY,
  tipo TEXT,
  acceso TEXT,
  licencia TEXT,
  robots TEXT,
  api TEXT,
  cobertura_desde INTEGER,
  cobertura_hasta INTEGER,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS crawl_log (
  id INTEGER PRIMARY KEY,
  url TEXT NOT NULL,
  method TEXT,
  status INTEGER,
  bytes INTEGER,
  sha256 TEXT,
  cache INTEGER DEFAULT 0,
  fetched_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_author_work_res ON author_work(researcher_id);
CREATE INDEX IF NOT EXISTS idx_presence_source ON presence(source);
CREATE INDEX IF NOT EXISTS idx_works_doi ON works(doi);
CREATE INDEX IF NOT EXISTS idx_crawl_log_url ON crawl_log(url);
