"""Registra confirmaciones de ORCID en la tabla `orcid_verifications`.

Separación de conceptos (importante para no llamar «verificado» a lo inferido):

  researchers.orcid_source  → PROCEDENCIA del identificador
                              (portal_ficha, reverso_doi, confirmado_persona…)
  orcid_verifications       → QUIÉN lo ha confirmado, CUÁNDO y CON QUÉ EVIDENCIA

Métodos admitidos (de más a menos fuerte):
  oauth        el titular autoriza la lectura de su registro ORCID        confianza 1.00
  persona      la persona confirma su propio ORCID (hoja de confirmación) confianza 0.95
  institucion  la institución lo registra en su CRIS (Fundanet)           confianza 0.80

Uso:
    python scripts/registra_verificaciones_orcid.py            # dry-run
    python scripts/registra_verificaciones_orcid.py --write    # crea tabla e inserta
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
ENTRADA = ROOT / "data" / "verificaciones_orcid.csv"

METODOS = {"oauth": 1.00, "persona": 0.95, "institucion": 0.80}

DDL = """
CREATE TABLE IF NOT EXISTS orcid_verifications (
  id INTEGER PRIMARY KEY,
  researcher_id INTEGER NOT NULL REFERENCES researchers(id) ON DELETE CASCADE,
  orcid TEXT NOT NULL,
  metodo TEXT NOT NULL CHECK (metodo IN ('oauth','persona','institucion')),
  fuente TEXT NOT NULL,
  evidencia TEXT,
  confianza REAL,
  fecha TEXT NOT NULL,
  UNIQUE(researcher_id, orcid, metodo, fuente)
)
"""


def norm_orcid(o: str) -> str:
    return re.sub(r"^https?://(www\.)?orcid\.org/", "", (o or "").strip()).upper()


def norm_text(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z ]", " ", s.lower()).split())


def checksum_ok(orcid: str) -> bool:
    s = orcid.replace("-", "").upper()
    if not re.fullmatch(r"\d{15}[\dX]", s):
        return False
    total = 0
    for c in s[:15]:
        total = (total + int(c)) * 2
    control = (12 - total % 11) % 11
    return s[15] == ("X" if control == 10 else str(control))


def main(write: bool) -> None:
    if not ENTRADA.exists():
        raise SystemExit(f"falta {ENTRADA}")

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    existe = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='orcid_verifications'"
    ).fetchone() is not None
    print(f"tabla orcid_verifications: {'existe' if existe else 'no existe (se creará)'}")

    hoy = date.today().isoformat()
    plan = []
    for f in csv.DictReader(ENTRADA.open(encoding="utf-8-sig")):
        nombre = f["nombre"].strip()
        orcid = norm_orcid(f["orcid"])
        metodo = f["metodo"].strip().lower()
        fuente = (f["fuente"] or "").strip() or "sin_fuente"
        evidencia = (f.get("evidencia") or "").strip()
        try:
            confianza = float(f["confianza"]) if f.get("confianza") else METODOS[metodo]
        except ValueError:
            confianza = METODOS.get(metodo, 0.5)

        if metodo not in METODOS:
            plan.append((nombre, orcid, "metodo_invalido", f"metodo={metodo}", None))
            continue
        if not checksum_ok(orcid):
            plan.append((nombre, orcid, "checksum_invalido", "", None))
            continue

        r = con.execute("SELECT id, name, orcid FROM researchers WHERE UPPER(orcid)=?",
                        (orcid,)).fetchone()
        if not r:
            plan.append((nombre, orcid, "sin_researcher", "ORCID no está en la base", None))
            continue
        if norm_text(r["name"] or "") != norm_text(nombre):
            print(f"  AVISO: nombre distinto · csv={nombre!r} base={r['name']!r}")

        if existe:
            dup = con.execute(
                """SELECT 1 FROM orcid_verifications
                   WHERE researcher_id=? AND orcid=? AND metodo=? AND fuente=?""",
                (r["id"], orcid, metodo, fuente)).fetchone()
            if dup:
                plan.append((nombre, orcid, "ya_registrado", f"{metodo}/{fuente}", None))
                continue

        plan.append((nombre, orcid, "insertar", f"{metodo}/{fuente}", {
            "researcher_id": r["id"], "orcid": orcid, "metodo": metodo,
            "fuente": fuente, "evidencia": evidencia, "confianza": confianza}))

    print(f"\n{'persona':28} {'ORCID':20} {'acción':16} detalle")
    for nombre, orcid, accion, detalle, _ in plan:
        print(f"{nombre[:28]:28} {orcid:20} {accion:16} {detalle}")

    nuevas = [p for p in plan if p[2] == "insertar"]
    print(f"\nresumen: {len(plan)} filas · insertar {len(nuevas)} · "
          f"ya_registrado {sum(1 for p in plan if p[2]=='ya_registrado')} · "
          f"problemas {sum(1 for p in plan if p[2] in ('metodo_invalido','checksum_invalido','sin_researcher'))}")

    if not write:
        print("\nDRY-RUN. Para escribir: python scripts/registra_verificaciones_orcid.py --write")
        con.close()
        return

    backup = siguiente_backup(DB)
    shutil.copy2(DB, backup)
    print(f"\nbackup: {backup.name}")

    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute(DDL)
        for _, _, _, _, datos in nuevas:
            if not datos:
                continue
            con.execute(
                """INSERT INTO orcid_verifications
                   (researcher_id, orcid, metodo, fuente, evidencia, confianza, fecha)
                   VALUES (?,?,?,?,?,?,?)""",
                (datos["researcher_id"], datos["orcid"], datos["metodo"],
                 datos["fuente"], datos["evidencia"], datos["confianza"], hoy))
        con.execute("COMMIT")
    except Exception as exc:  # noqa: BLE001
        con.execute("ROLLBACK")
        print(f"ERROR, rollback completo: {exc}")
        raise

    n = con.execute("SELECT COUNT(*) FROM orcid_verifications").fetchone()[0]
    print(f"verificaciones en la tabla: {n}")
    print("por método:")
    for r in con.execute("""SELECT metodo, COUNT(*) n, MIN(confianza) c
                             FROM orcid_verifications GROUP BY metodo ORDER BY c DESC"""):
        print(f"  {r['metodo']:12} {r['n']:>4}  confianza {r['c']}")
    print("integridad:", con.execute("PRAGMA integrity_check").fetchone()[0])
    print("FK rotas:", con.execute("PRAGMA foreign_key_check").fetchall())
    con.close()


if __name__ == "__main__":
    main(write="--write" in sys.argv[1:])
