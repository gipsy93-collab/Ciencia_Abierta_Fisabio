"""Crea la tabla `datasets` y carga el censo con esquema alineado al EHDS.

Principio: lo declarado y lo propuesto no se mezclan.
  health_category            -> solo si la institución lo declara (hoy: vacío)
  health_category_propuesta  -> inferencia nuestra, marcada como tal

Uso:
    python scripts/crea_tabla_datasets.py            # dry-run
    python scripts/crea_tabla_datasets.py --write    # crea y carga
"""
from __future__ import annotations

import csv
import re
import shutil
import sqlite3
import sys
import unicodedata
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from backup_util import siguiente_backup  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "rip_osiris.sqlite"
CENSO = ROOT / "data" / "censo_datasets_fisabio.csv"

DDL = """
CREATE TABLE IF NOT EXISTS datasets (
  id INTEGER PRIMARY KEY,
  pid TEXT UNIQUE,
  title TEXT NOT NULL,
  title_norm TEXT NOT NULL,
  year INTEGER,
  type TEXT NOT NULL CHECK (type IN ('dataset','software')),
  source TEXT,
  sources TEXT,
  n_versiones INTEGER DEFAULT 1,
  holder TEXT,
  access_rights TEXT CHECK (access_rights IN ('public','restricted','non_public','unknown')),
  license TEXT,
  health_category TEXT,
  health_category_propuesta TEXT,
  applicable_legislation TEXT,
  hdab TEXT,
  structured_data INTEGER,
  quality_annotation TEXT,
  legal_basis TEXT,
  purpose TEXT,
  personal_data TEXT,
  temporal_coverage TEXT,
  spatial_coverage TEXT,
  language TEXT,
  version TEXT,
  url TEXT,
  work_id INTEGER REFERENCES works(id),
  notes TEXT,
  first_seen TEXT,
  last_seen TEXT
)
"""
INDICES = [
    "CREATE INDEX IF NOT EXISTS idx_datasets_type ON datasets(type)",
    "CREATE INDEX IF NOT EXISTS idx_datasets_norm ON datasets(title_norm)",
    "CREATE INDEX IF NOT EXISTS idx_datasets_work ON datasets(work_id)",
]

# Propuesta de categoría de salud (art. 51) por palabras clave del título.
# Es una INFERENCIA, no una declaración: va a la columna _propuesta.
CATEGORIAS = [
    (r"\bpadchest\b|\bbimcv\b|\bcovid|x-?ray|radiogra|imagen(es)? medic|\bimaging\b|\bprostate\b|\bmri\b|resonancia|\bct\b", "Medical imaging"),
    (r"retina|retinopat|oftalm|\bdhr\b|distrofia", "Electronic health records"),
    (r"genom|sequenc|microbiom|mutano|bacteri|streptoc|pseudomon", "Genomic and molecular data"),
    (r"\bregistry\b|\bregistro\b|\bcohort", "Health data from registries"),
    (r"\btrial\b|\bensayo\b", "Clinical trial data"),
]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in s if not unicodedata.combining(c))).strip()


def clasifica(titulo: str) -> str:
    t = norm(titulo)
    for patron, categoria in CATEGORIAS:
        if re.search(patron, t):
            return categoria
    return ""


def acceso(valor: str) -> str:
    v = (valor or "").strip().lower()
    if v == "public":
        return "public"
    if v == "restricted":
        return "restricted"
    if v in ("false", "non-public", "non_public"):
        return "non_public"
    return "unknown"


def main(write: bool) -> None:
    filas_csv = list(csv.DictReader(CENSO.open(encoding="utf-8-sig")))
    print(f"filas del censo: {len(filas_csv)}")

    # Deduplicar por título normalizado (versiones de Zenodo con DOI distinto)
    grupos: dict[str, list[dict]] = {}
    for f in filas_csv:
        grupos.setdefault(norm(f["titulo"]), []).append(f)

    hoy = date.today().isoformat()
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    works_doi = {r["doi"].lower(): r["id"] for r in con.execute(
        "SELECT id, doi FROM works WHERE doi IS NOT NULL")}

    registros = []
    for clave, grupo in grupos.items():
        grupo.sort(key=lambda f: (-len(f["fuentes"].split("|")), f["doi"] or "zzz"))
        rep = grupo[0]
        doi = (rep["doi"] or "").lower()
        if doi:
            pid = doi
        elif "dataset/" in (rep["url"] or ""):
            pid = "ckan:" + rep["url"].rstrip("/").split("/")[-1]
        else:
            pid = None
        if not pid:
            continue
        es_ckan = pid.startswith("ckan:")
        registros.append({
            "pid": pid,
            "title": rep["titulo"],
            "title_norm": clave,
            "year": int(rep["anio"]) if (rep["anio"] or "").isdigit() else None,
            "type": "software" if (rep["tipo"] or "").lower() == "software" else "dataset",
            "source": (rep["fuentes"].split("|")[0]),
            "sources": rep["fuentes"],
            "n_versiones": len(grupo),
            "holder": "FISABIO" if not es_ckan else (rep["detalle"] or "FISABIO"),
            "access_rights": acceso(rep["acceso"]) if es_ckan else "unknown",
            "license": rep["licencia"] or None,
            "health_category": None,
            "health_category_propuesta": clasifica(rep["titulo"]) or None,
            "applicable_legislation": "http://data.europa.eu/eli/reg/2025/327/oj" if es_ckan else None,
            "hdab": None,
            "structured_data": None,
            "quality_annotation": None,
            "legal_basis": None,
            "purpose": None,
            "personal_data": None,
            "temporal_coverage": None,
            "spatial_coverage": None,
            "language": None,
            "version": None,
            "url": rep["url"] or None,
            "work_id": works_doi.get(doi) if doi else None,
            "notes": ("Catálogo CKAN institucional" if es_ckan else None),
            "first_seen": hoy,
            "last_seen": hoy,
        })

    print(f"recursos únicos a cargar: {len(registros)}")
    print(f"  datasets: {sum(1 for r in registros if r['type']=='dataset')}")
    print(f"  software: {sum(1 for r in registros if r['type']=='software')}")
    print(f"  con work_id enlazado: {sum(1 for r in registros if r['work_id'])}")
    print(f"  con categoria propuesta: {sum(1 for r in registros if r['health_category_propuesta'])}")

    if not write:
        print("\nDRY-RUN. Para escribir: python scripts/crea_tabla_datasets.py --write")
        con.close()
        return

    backup = siguiente_backup(DB)
    shutil.copy2(DB, backup)
    print(f"\nbackup: {backup.name}")

    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute(DDL)
        for sql in INDICES:
            con.execute(sql)
        nuevas = 0
        for r in registros:
            existe = con.execute("SELECT 1 FROM datasets WHERE pid=?", (r["pid"],)).fetchone()
            if existe:
                continue
            cols = ", ".join(r)
            marcas = ", ".join("?" * len(r))
            con.execute(f"INSERT INTO datasets ({cols}) VALUES ({marcas})", list(r.values()))
            nuevas += 1
        con.execute("COMMIT")
    except Exception as exc:  # noqa: BLE001
        con.execute("ROLLBACK")
        print(f"ERROR, rollback completo: {exc}")
        raise

    print(f"insertadas: {nuevas}")
    print("total en datasets:", con.execute("SELECT COUNT(*) FROM datasets").fetchone()[0])
    print("por tipo:")
    for r in con.execute("SELECT type, COUNT(*) n FROM datasets GROUP BY type"):
        print(f"  {r['type']:10} {r['n']}")
    print("por acceso:")
    for r in con.execute("SELECT access_rights, COUNT(*) n FROM datasets GROUP BY access_rights"):
        print(f"  {str(r['access_rights']):12} {r['n']}")
    print("integridad:", con.execute("PRAGMA integrity_check").fetchone()[0])
    print("FK rotas:", con.execute("PRAGMA foreign_key_check").fetchall())
    con.close()


if __name__ == "__main__":
    main(write="--write" in sys.argv[1:])
