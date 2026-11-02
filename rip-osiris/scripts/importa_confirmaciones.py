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
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rip_osiris.anchor.orcid import normalizar_orcid  # noqa: E402
from backup_util import siguiente_backup  # noqa: E402
from registra_verificaciones_orcid import DDL as DDL_VERIFICACIONES  # noqa: E402

DB = ROOT / "data" / "rip_osiris.sqlite"
HOJA = ROOT / "data" / "hoja_confirmacion_orcid.csv"
WRITE = "--write" in sys.argv


def norm_orcid(o: str) -> str:
    return normalizar_orcid((o or "").strip()) or ""


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
            print(f"  IGNORADO (ORCID inválido o vacío): {nombre} · {f.get('orcid')!r}")
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
        cambios.append((norm_orcid(f.get("orcid", "")), "rechazado_revision", rid, nombre))

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

destino_backup = siguiente_backup(DB)
shutil.copy2(DB, destino_backup)
print(f"backup: {destino_backup.name} ({destino_backup.stat().st_size:,} bytes)")

try:
    con.execute("BEGIN IMMEDIATE")
    con.execute(DDL_VERIFICACIONES)
    for orcid, fuente, rid, nombre in cambios:
        if fuente.startswith("confirmado_"):
            con.execute(
                "UPDATE researchers SET orcid=?, orcid_source=? WHERE id=?",
                (orcid, fuente, rid))
            metodo = "institucion" if fuente == "confirmado_institucion" else "persona"
            con.execute(
                """INSERT OR IGNORE INTO orcid_verifications
                   (researcher_id, orcid, metodo, fuente, evidencia, confianza, fecha)
                   VALUES (?,?,?,?,?,?,?)""",
                (rid, orcid, metodo, "hoja_confirmacion",
                 f"Hoja de confirmación: {nombre}", 0.80 if metodo == "institucion" else 0.95,
                 date.today().isoformat()))
        else:
            con.execute(
                "UPDATE researchers SET orcid=NULL, orcid_source='rechazado_revision' WHERE id=?",
                (rid,))
            cur = con.execute(
                "DELETE FROM author_work WHERE researcher_id=? AND source='orcid_reverso'",
                (rid,))
            borrados += cur.rowcount
            if orcid:
                con.execute(
                    "DELETE FROM orcid_verifications WHERE researcher_id=? AND orcid=?",
                    (rid, orcid))
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
