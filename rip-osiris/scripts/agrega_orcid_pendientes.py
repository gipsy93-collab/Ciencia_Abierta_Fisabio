"""Añade los 12 candidatos ORCID con evidencia fuerte (nombre alto + ≥1 DOI).

No toca los 13 'probable' ni los 36 'revisar' ni los 3 sospechosos.
Backup propio antes de escribir.
"""
from __future__ import annotations

import csv
import shutil
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\Users\gipsy\repos\Ciencia_Abierta_Fisabio\rip-osiris")
DB = ROOT / "data" / "rip_osiris.sqlite"
BACKUP = ROOT / "data" / "rip_osiris.backup-2026-11-01-b.sqlite"
SOSPECHOSOS = {"Cristina Fernandez Martinez", "Jose Luis Rodrigo Perez", "Monica Romero Nieto"}

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
ya = {r["id"]: r["orcid"] for r in con.execute("SELECT id, orcid FROM researchers")}

filas = list(csv.DictReader(
    (ROOT / "data" / "orcid_revision_pendientes.csv").open(encoding="utf-8-sig")))
nuevos = [r for r in filas
          if r["sugerencia"] == "añadir"
          and r["nombre"] not in SOSPECHOSOS
          and not ya.get(int(r["researcher_id"]))]

print(f"candidatos a añadir: {len(nuevos)}")
for r in nuevos:
    print(f"  {r['nombre'][:34]:34} {r['orcid']}  (solape {r['n_solape']}/{r['n_dois_portal']}, apoyo {r['apoyo']})")

if not BACKUP.exists():
    shutil.copy2(DB, BACKUP)
    print(f"backup: {BACKUP.name} ({BACKUP.stat().st_size:,} bytes)")
else:
    print(f"backup ya existe: {BACKUP.name}")

try:
    con.execute("BEGIN IMMEDIATE")
    con.executemany(
        "UPDATE researchers SET orcid=?, orcid_source='reverso_multisenal' "
        "WHERE id=? AND (orcid IS NULL OR orcid='')",
        [(r["orcid"], int(r["researcher_id"])) for r in nuevos])
    con.execute("COMMIT")
    print("COMMIT OK")
except Exception as exc:
    con.execute("ROLLBACK")
    print("ROLLBACK:", exc)
    raise

print("\n=== verificación ===")
print("ORCID total:", con.execute("SELECT COUNT(*) c FROM researchers WHERE orcid IS NOT NULL").fetchone()["c"])
for r in con.execute("SELECT orcid_source, COUNT(*) c FROM researchers WHERE orcid IS NOT NULL GROUP BY orcid_source ORDER BY c DESC"):
    print(f"  {r['orcid_source']:28} {r['c']:>4}")
print("integrity:", con.execute("PRAGMA integrity_check").fetchone()[0])
con.close()
