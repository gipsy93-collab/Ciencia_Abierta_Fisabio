"""Carga el centro de Fundanet para quienes no tenían ninguno.

Solo escribe cuando el centro del export resuelve a una organización
`orgs.kind='centro'` de la base. Los centros externos (universidades, empresas)
no se inventan: se listan y se dejan para una decisión aparte.

Uso:
    python scripts/importa_centros_fundanet_full.py            # dry-run
    python scripts/importa_centros_fundanet_full.py --write
"""
from __future__ import annotations

import csv
import shutil
import sqlite3
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from backup_util import siguiente_backup  # noqa: E402
from importa_centros_fundanet import resolver_org  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "rip_osiris.sqlite"
CRUCE = ROOT / "data" / "cruce_fundanet_completo.csv"


def main(write: bool) -> None:
    filas = list(csv.DictReader(CRUCE.open(encoding="utf-8-sig")))
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    orgs = list(con.execute("SELECT id, name, kind FROM orgs WHERE kind='centro' ORDER BY name"))
    hoy = date.today().isoformat()

    plan, externos = [], []
    for f in filas:
        if "centro_nuevo" not in f["estado"] or not f["centro"]:
            continue
        org, motivo, _ = resolver_org(f["centro"], orgs)
        if org:
            plan.append((f, org, motivo))
        else:
            externos.append(f)

    print(f"personas que ganan centro: {len(plan) + len(externos)}")
    print(f"  resuelven a un centro nuestro: {len(plan)}")
    print(f"  centro externo o desconocido:  {len(externos)}")

    print("\n=== centros externos (no se tocan) ===")
    for k, v in Counter(f["centro"] for f in externos).most_common():
        print(f"  {v:>3}  {k}")

    print("\n=== a escribir (top) ===")
    for k, v in Counter(o["name"] for _, o, _ in plan).most_common():
        print(f"  {v:>3}  {k}")

    if not write:
        print("\nDRY-RUN. Para escribir: python scripts/importa_centros_fundanet_full.py --write")
        con.close()
        return

    backup = siguiente_backup(DB)
    shutil.copy2(DB, backup)
    print(f"\nbackup: {backup.name}")

    nuevas = 0
    try:
        con.execute("BEGIN IMMEDIATE")
        for f, org, motivo in plan:
            rid = int(f["bd_id"])
            existe = con.execute(
                """SELECT 1 FROM researcher_affiliations
                   WHERE researcher_id=? AND affiliation_type='centro'""", (rid,)).fetchone()
            if existe:
                continue
            evidencia = f"Centro del Tercero: {f['centro']}"
            if f["departamento"]:
                evidencia += f" · Departamento: {f['departamento']}"
            con.execute(
                """INSERT INTO researcher_affiliations
                   (researcher_id, org_id, affiliation_type, method, status, confidence,
                    source, source_id, url, evidence_literal, first_seen, last_seen)
                   VALUES (?,?,'centro','fundanet_centro_tercero','declarado_institucion',
                           0.90,'fundanet',?,NULL,?,?,?)""",
                (rid, org["id"], f["orcid"] or None, evidencia, hoy, hoy))
            nuevas += 1
        con.execute("COMMIT")
    except Exception as exc:  # noqa: BLE001
        con.execute("ROLLBACK")
        print(f"ERROR, rollback completo: {exc}")
        raise

    sin_centro = con.execute(
        """SELECT COUNT(*) FROM researchers r WHERE NOT EXISTS (
           SELECT 1 FROM researcher_affiliations ra
           WHERE ra.researcher_id=r.id AND ra.affiliation_type='centro')""").fetchone()[0]
    print(f"insertadas: {nuevas}")
    print(f"sin centro ahora: {sin_centro} (antes 184)")
    print("integridad:", con.execute("PRAGMA integrity_check").fetchone()[0])
    print("FK rotas:", con.execute("PRAGMA foreign_key_check").fetchall())
    con.close()


if __name__ == "__main__":
    main(write="--write" in sys.argv[1:])
