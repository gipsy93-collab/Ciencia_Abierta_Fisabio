"""Importa las confirmaciones de ORCID de la hoja de confirmación.

Uso:
  python scripts/importa_confirmaciones.py            # dry-run: cuenta cambios
  python scripts/importa_confirmaciones.py --write    # aplica con backup

Decisiones en la hoja:
  decision = confirmar | rechazar | revisar
  confirmado_por = persona | institucion   (solo para confirmar)

Efectos:
  confirmar  -> researchers.orcid = ORCID; orcid_source = confirmado_persona
                o confirmado_institucion.
  rechazar   -> researchers.orcid = NULL; orcid_source = rechazado_revision;
                se borran los author_work con source='orcid_reverso' de esa persona.
  revisar    -> sin cambios.
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
HOJA = ROOT / "data" / "hoja_confirmacion_orcid.csv"
BACKUP = ROOT / "data" / "rip_osiris.backup-2026-11-02-b.sqlite"
WRITE = "--write" in sys.argv


def norm_orcid(o: str) -> str:
    o = (o or "").strip().upper()
    return o


filas = list(csv.DictReader(HOJA.open(encoding="utf-8-sig")))
decisiones = [f for f in filas if (f.get("decision") or "").strip()]
if not decisiones:
    print("No hay decisiones en la hoja. Rellena 'decision' y vuelve a ejecutar.")
    sys.exit(0)

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

confirmados_persona = confirmados_institucion = 0
rechazados = borrados = revisar = invalidos = 0
cambios = []

for f in decisiones:
    decision = (f.get("decision") or "").strip().lower()
    rid = int(f["researcher_id"])
    nombre = f["nombre"]
    if decision not in ("confirmar", "rechazar", "revisar"):
        invalidos += 1
        print(f"  IGNORADO (decisión no válida): {nombre} · {decision!r}")
        continue
    if decision == "revisar":
        revisar += 1
        continue
    if decision == "confirmar":
        orcid = norm_orcid(f.get("orcid", ""))
        if not orcid:
            invalidos += 1
            print(f"  IGNORADO (sin ORCID): {nombre}")
            continue
        por = (f.get("confirmado_por") or "").strip().lower()
        if por == "institucion":
            fuente = "confirmado_institucion"
            confirmados_institucion += 1
        else:
            if por != "persona":
                print(f"  AVISO: {nombre} sin confirmado_por; se asume persona")
            fuente = "confirmado_persona"
            confirmados_persona += 1
        cambios.append((orcid, fuente, rid, nombre))
    else:  # rechazar
        rechazados += 1
        cambios.append((None, "rechazado_revision", rid, nombre))

print(f"decisiones: {len(decisiones)} · confirmar persona: {confirmados_persona} · "
      f"confirmar institución: {confirmados_institucion} · rechazar: {rechazados} · "
      f"revisar: {revisar} · inválidas: {invalidos}")

if not WRITE:
    print("\nDRY-RUN. Para aplicar: python scripts/importa_confirmaciones.py --write")
    for c in cambios[:10]:
        print(f"  {c[3][:40]:40} → {c[0] or '(sin ORCID)'} · {c[1]}")
    if len(cambios) > 10:
        print(f"  … y {len(cambios)-10} más")
    con.close()
    sys.exit(0)

if not BACKUP.exists():
    shutil.copy2(DB, BACKUP)
    print(f"backup: {BACKUP.name} ({BACKUP.stat().st_size:,} bytes)")

try:
    con.execute("BEGIN IMMEDIATE")
    for orcid, fuente, rid, nombre in cambios:
        if fuente.startswith("confirmado_"):
            con.execute(
                "UPDATE researchers SET orcid=?, orcid_source=? WHERE id=?",
                (orcid, fuente, rid))
        else:
            con.execute(
                "UPDATE researchers SET orcid=NULL, orcid_source='rechazado_revision' WHERE id=?",
                (rid,))
            cur = con.execute(
                "DELETE FROM author_work WHERE researcher_id=? AND source='orcid_reverso'",
                (rid,))
            borrados += cur.rowcount
    con.execute("COMMIT")
    print("COMMIT OK")
except Exception as exc:
    con.execute("ROLLBACK")
    print("ROLLBACK:", exc)
    raise

print(f"vínculos orcid_reverso borrados: {borrados}")
print("ORCID total:", con.execute(
    "SELECT COUNT(*) FROM researchers WHERE orcid IS NOT NULL").fetchone()[0])
print("integrity:", con.execute("PRAGMA integrity_check").fetchone()[0])
con.close()
