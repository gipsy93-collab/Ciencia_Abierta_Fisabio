"""Lleva año y tipo del JSONL del portal a la tabla works.

Solo rellena valores nulos (`COALESCE`); no pisa años ya existentes.
Backup previo y transacción.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\Users\gipsy\repos\Ciencia_Abierta_Fisabio\rip-osiris")
DB = ROOT / "data" / "rip_osiris.sqlite"
BACKUP = ROOT / "data" / "rip_osiris.backup-2026-11-02.sqlite"
JSONL = ROOT / "data" / "portal_publicaciones.jsonl"

pubs = {}
for linea in JSONL.open(encoding="utf-8"):
    f = json.loads(linea)
    for p in f["pubs"]:
        if p.get("anio") or p.get("tipo"):
            pubs[p["pub_id"]] = (p.get("anio"), p.get("tipo"))

if not BACKUP.exists():
    shutil.copy2(DB, BACKUP)
    print(f"backup: {BACKUP.name} ({BACKUP.stat().st_size:,} bytes)")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
antes_anio = con.execute("SELECT COUNT(*) FROM works WHERE year IS NULL").fetchone()[0]
antes_tipo = con.execute("SELECT COUNT(*) FROM works WHERE type IS NULL OR type=''").fetchone()[0]

actualizados = 0
sin_work = 0
try:
    con.execute("BEGIN IMMEDIATE")
    for pid, (anio, tipo) in pubs.items():
        row = con.execute(
            "SELECT work_id FROM work_ids WHERE scheme='portal' AND value=? LIMIT 1",
            (pid,)).fetchone()
        if not row:
            sin_work += 1
            continue
        cur = con.execute(
            "UPDATE works SET year=COALESCE(year, ?), type=COALESCE(type, ?) WHERE id=?",
            (anio, tipo, row["work_id"]))
        actualizados += cur.rowcount
    con.execute("COMMIT")
    print("COMMIT OK")
except Exception as exc:
    con.execute("ROLLBACK")
    print("ROLLBACK:", exc)
    raise

despues_anio = con.execute("SELECT COUNT(*) FROM works WHERE year IS NULL").fetchone()[0]
despues_tipo = con.execute("SELECT COUNT(*) FROM works WHERE type IS NULL OR type=''").fetchone()[0]
print(f"pubs con año/tipo: {len(pubs)} · sin work_id: {sin_work}")
print(f"año nulo:  {antes_anio} → {despues_anio}")
print(f"tipo nulo: {antes_tipo} → {despues_tipo}")
print(f"filas actualizadas (matched): {actualizados}")
print("integrity:", con.execute("PRAGMA integrity_check").fetchone()[0])
con.close()
