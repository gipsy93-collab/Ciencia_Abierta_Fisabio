"""Añade los 2 candidatos finales con evidencia suficiente.

Ángel Antonio Moya Herraiz: nombre alto, 3/12 DOI, 121/162 coautores.
Maria Cuenca Torres: nombre exacto, 1/5 DOI, 8/26 coautores.
Carmen Hernández Prats queda fuera: ORCID con afiliación UAB y 1 sola obra.
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\Users\gipsy\repos\Ciencia_Abierta_Fisabio\rip-osiris")
DB = ROOT / "data" / "rip_osiris.sqlite"
BACKUP = ROOT / "data" / "rip_osiris.backup-2026-11-01-h.sqlite"

CASOS = [
    (953, "Ángel Antonio Moya Herraiz", "0000-0002-5986-9304", "reverso_multisenal"),
    (534, "Maria Cuenca Torres", "0000-0001-7282-0639", "reverso_multisenal"),
    (968, "Juan Francisco Navarro Gracia", "0000-0002-7839-1297", "reverso_multisenal"),
]

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
actualizar = []
for rid, nombre, orcid, fuente in CASOS:
    r = con.execute("SELECT name, orcid FROM researchers WHERE id=?", (rid,)).fetchone()
    if not r or r["name"] != nombre:
        print(f"  NO COINCIDE id={rid}: {r['name'] if r else 'no existe'} != {nombre}")
        continue
    if r["orcid"]:
        print(f"  YA TIENE ORCID: {nombre} → {r['orcid']}")
        continue
    actualizar.append((orcid, fuente, rid, nombre))

print(f"casos a escribir: {len(actualizar)}")
for orcid, fuente, rid, nombre in actualizar:
    print(f"  {nombre:34} {orcid}  {fuente}")

if not actualizar:
    sys.exit(0)

if not BACKUP.exists():
    shutil.copy2(DB, BACKUP)
    print(f"backup: {BACKUP.name} ({BACKUP.stat().st_size:,} bytes)")

try:
    con.execute("BEGIN IMMEDIATE")
    con.executemany(
        "UPDATE researchers SET orcid=?, orcid_source=? "
        "WHERE id=? AND (orcid IS NULL OR orcid='')",
        [(orcid, fuente, rid) for orcid, fuente, rid, _ in actualizar])
    con.execute("COMMIT")
    print("COMMIT OK")
except Exception as exc:
    con.execute("ROLLBACK")
    print("ROLLBACK:", exc)
    raise

print("\nORCID total:", con.execute(
    "SELECT COUNT(*) FROM researchers WHERE orcid IS NOT NULL").fetchone()[0])
print("integrity:", con.execute("PRAGMA integrity_check").fetchone()[0])
con.close()
