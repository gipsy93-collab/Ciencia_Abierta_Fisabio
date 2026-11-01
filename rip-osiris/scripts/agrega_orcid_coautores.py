"""Añade los 28 candidatos con evidencia fuerte (DOI + coautores + nombre).

26 con nombre alto/medio + DOI >=50 % + sin choque de nombre.
2 especiales: nombre invertido (Martínez-Cuesta) y nombre incompleto (Antonio).
Backup propio y transacción.
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
BACKUP = ROOT / "data" / "rip_osiris.backup-2026-11-01-d.sqlite"

CASOS = [
    ("Miguel Fernández Zarzoso", "0000-0003-2369-4722", "reverso_multisenal"),
    ("Samantha Santana Zorrilla", "0009-0000-5861-808X", "reverso_multisenal"),
    ("Monica Jorda Llona", "0000-0002-7486-7657", "reverso_multisenal"),
    ("Andrea Romero Valero", "0000-0003-1339-2552", "reverso_multisenal"),
    ("Elena Becerra Fernández", "0000-0003-2628-469X", "reverso_multisenal"),
    ("Angela Botella Zaragoza", "0000-0002-1599-0030", "reverso_multisenal"),
    ("José Pastor Rosado", "0000-0003-0273-7877", "reverso_multisenal"),
    ("Jose Antonio Anton Blasco", "0009-0003-7627-7444", "reverso_multisenal"),
    ("Laura Armañanzas Ruiz", "0000-0002-6708-7185", "reverso_multisenal"),
    ("Julia Alfonso Diego", "0000-0002-4692-5514", "reverso_multisenal"),
    ("Inmaculada Ortiz Tarín", "0000-0001-6557-8311", "reverso_multisenal"),
    ("Ramon Rodriguez Pacheco", "0009-0009-8574-6402", "reverso_multisenal"),
    ("Alejandro Jose Garcia Segui", "0000-0001-8115-0542", "reverso_multisenal"),
    ("Maria Dolores Belles Medall", "0000-0002-6628-1701", "reverso_multisenal"),
    ("Lucía Guillén Zafra", "0009-0008-4328-0598", "reverso_multisenal"),
    ("Sara Carrascosa Gonzalvo", "0000-0003-4761-7449", "reverso_multisenal"),
    ("Vicente Jover Cerdá", "0000-0002-2602-4532", "reverso_multisenal"),
    ("Vallivana Rodrigo Casares", "0000-0002-1602-6497", "reverso_multisenal"),
    ("Ruben Sanchez Garcia", "0000-0003-4589-1647", "reverso_multisenal"),
    ("Esther Pastor Fernández", "0000-0002-5629-7806", "reverso_multisenal"),
    ("Xueqian Yin", "0000-0001-7189-6236", "reverso_multisenal"),
    ("Maria Remedios Santoyo Perez", "0009-0004-6740-1957", "reverso_multisenal"),
    ("Mireia Juana Ladios Martín", "0000-0002-6127-7746", "reverso_multisenal"),
    ("Rosa María Bravo Jover", "0000-0002-5751-901X", "reverso_multisenal"),
    ("Nuria Monteagudo Martínez", "0000-0002-2720-3321", "reverso_multisenal"),
    ("Jesús Marín Miret", "0000-0002-7042-631X", "reverso_multisenal"),
    # especiales
    ("Antonio Cremades Mira", "0000-0003-0146-4475", "reverso_nombre_incompleto"),
    ("Maria Angeles Martinez Cuesta", "0000-0002-8351-3623", "reverso_nombre_invertido"),
]

review = {r["nombre"]: r for r in csv.DictReader(
    (ROOT / "data" / "orcid_revision_pendientes.csv").open(encoding="utf-8-sig"))}

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

actualizar = []
for nombre, orcid, fuente in CASOS:
    r = review.get(nombre)
    if not r:
        print(f"  NO ENCONTRADO: {nombre}")
        continue
    if r["orcid"] != orcid:
        print(f"  ORCID DISTINTO: {nombre}: csv {r['orcid']} vs {orcid}")
        continue
    rid = int(r["researcher_id"])
    actual = con.execute("SELECT orcid FROM researchers WHERE id=?", (rid,)).fetchone()
    if actual and actual["orcid"]:
        print(f"  YA TIENE ORCID: {nombre} → {actual['orcid']}")
        continue
    actualizar.append((orcid, fuente, rid, nombre))

print(f"\ncasos a escribir: {len(actualizar)} de {len(CASOS)}")
for orcid, fuente, rid, nombre in actualizar:
    print(f"  {nombre[:40]:40} {orcid}  {fuente}")

if not actualizar:
    print("nada que escribir")
    sys.exit(0)

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
        [(orcid, fuente, rid) for orcid, fuente, rid, _ in actualizar])
    con.execute("COMMIT")
    print("COMMIT OK")
except Exception as exc:
    con.execute("ROLLBACK")
    print("ROLLBACK:", exc)
    raise

print("\n=== verificación ===")
print("ORCID total:", con.execute("SELECT COUNT(*) c FROM researchers WHERE orcid IS NOT NULL").fetchone()["c"])
for r in con.execute("SELECT orcid_source, COUNT(*) c FROM researchers WHERE orcid IS NOT NULL GROUP BY orcid_source ORDER BY c DESC"):
    print(f"  {r['orcid_source']:32} {r['c']:>4}")
print("integrity:", con.execute("PRAGMA integrity_check").fetchone()[0])
con.close()
