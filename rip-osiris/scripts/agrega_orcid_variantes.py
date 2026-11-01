"""Añade los 6 casos claros de variante / 1-de-1 DOI.

- 4 con 1/1 DOI en común y nombre alto.
- 1 variante Purificación → Pura (1/1 DOI).
- 1 variante Mª de los Reyes → Reyes (OpenAlex authorships; ORCID sin obras).
Backup propio y transacción.
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\Users\gipsy\repos\Ciencia_Abierta_Fisabio\rip-osiris")
DB = ROOT / "data" / "rip_osiris.sqlite"
BACKUP = ROOT / "data" / "rip_osiris.backup-2026-11-01-c.sqlite"

CASOS = [
    (296, "0000-0003-1734-9383", "reverso_multisenal"),        # Daniel Guzmán Llorens
    (882, "0000-0003-2345-3179", "reverso_multisenal"),        # Emilio Garrote Sánchez
    (854, "0009-0008-8380-9679", "reverso_multisenal"),        # Maria Sanchez Galan
    (734, "0009-0005-9769-2772", "reverso_multisenal"),        # María Dolores Linares Latorre
    (419, "0000-0002-9473-6267", "reverso_nombre_variante"),   # Mª Purificación de Vicente
    (135, "0000-0002-4607-0077", "reverso_openalex"),          # Mª de los Reyes Pascual Pérez
]

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
print("casos:")
for rid, orcid, fuente in CASOS:
    r = con.execute("SELECT name, orcid FROM researchers WHERE id=?", (rid,)).fetchone()
    print(f"  {r['name'][:40]:40} {orcid}  {fuente}  (antes: {r['orcid'] or 'NULL'})")

if not BACKUP.exists():
    shutil.copy2(DB, BACKUP)
    print(f"\nbackup: {BACKUP.name} ({BACKUP.stat().st_size:,} bytes)")
else:
    print(f"\nbackup ya existe: {BACKUP.name}")

try:
    con.execute("BEGIN IMMEDIATE")
    con.executemany(
        "UPDATE researchers SET orcid=?, orcid_source=? "
        "WHERE id=? AND (orcid IS NULL OR orcid='')",
        [(orcid, fuente, rid) for rid, orcid, fuente in CASOS])
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
