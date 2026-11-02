"""Importa el centro declarado en Fundanet como afiliación con procedencia.

Piloto sobre los 9 ORCID que aparecen en el volcado de Fundanet. El ORCID de
Fundanet ya coincide 9/9 con la base, así que aquí no se toca la identidad:
solo se añade el *centro* cuando la persona no lo tiene.

Honestidad de la fuente (importante):
  - El campo del volcado es «Centro del Tercero», no «Colectivo de Pertenencia».
    Para Ana Belso sabemos que el Colectivo es «Hospital General de Elda»
    (coincide con la base); para el resto solo tenemos el centro truncado.
  - Los valores truncados se marcan en `evidence_literal` y bajan la confianza.
  - Se escribe `source='fundanet'` y `method='fundanet_centro_tercero'`, y
    NUNCA se sobrescribe un centro ya existente del portal: si hay otro centro,
    se reporta como conflicto y no se toca.

Uso:
    python scripts/importa_centros_fundanet.py            # dry-run
    python scripts/importa_centros_fundanet.py --write    # escribe (con backup)
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

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "rip_osiris.sqlite"
ENTRADA = ROOT / "data" / "centros_fundanet.csv"

STOPWORDS = {"de", "del", "la", "las", "el", "los", "y", "e", "d"}

# Correcciones manuales: literal normalizado -> org_id.
# Solo para casos en que el matcher no pueda decidir por sí solo.
OVERRIDES: dict[str, int] = {}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    return " ".join(s.split())


def tokens(s: str) -> set[str]:
    return {t for t in norm(s).split() if t not in STOPWORDS and len(t) > 1}


def resolver_org(literal: str, orgs: list[sqlite3.Row]) -> tuple[sqlite3.Row | None, str, list[sqlite3.Row]]:
    """Devuelve (org, motivo, candidatos). motivo: exacto | prefijo | tokens | ambiguo | sin_match."""
    clave = norm(literal)
    if clave in OVERRIDES:
        org = next((o for o in orgs if o["id"] == OVERRIDES[clave]), None)
        return org, "override", [org] if org else []

    exactos = [o for o in orgs if norm(o["name"]) == clave]
    if len(exactos) == 1:
        return exactos[0], "exacto", exactos

    # Prefijo: el literal puede venir truncado ("HOSPITAL FRANCESC D").
    prefijos = [o for o in orgs if len(clave) >= 12 and norm(o["name"]).startswith(clave)]
    if len(prefijos) == 1:
        return prefijos[0], "prefijo", prefijos
    if len(prefijos) > 1:
        return None, "ambiguo", prefijos

    # Tokens: todas las palabras del literal están en el nombre del centro.
    tk = tokens(literal)
    if len(tk) >= 2:
        cands = [o for o in orgs if tk <= tokens(o["name"])]
        if len(cands) == 1:
            return cands[0], "tokens", cands
        if len(cands) > 1:
            return None, "ambiguo", cands

    return None, "sin_match", []


def siguiente_backup(db: Path) -> Path:
    hoy = date.today().isoformat()
    base = db.parent / f"rip_osiris.backup-{hoy}.sqlite"
    if not base.exists():
        return base
    for letra in "bcdefghijklmnopqrstuvwxyz":
        cand = db.parent / f"rip_osiris.backup-{hoy}-{letra}.sqlite"
        if not cand.exists():
            return cand
    raise SystemExit("no queda hueco de backup para hoy")


def main(write: bool) -> None:
    if not ENTRADA.exists():
        raise SystemExit(f"falta {ENTRADA}")

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    orgs = list(con.execute("SELECT id, name, kind FROM orgs WHERE kind='centro' ORDER BY name"))
    hoy = date.today().isoformat()

    plan = []
    for fila in csv.DictReader(ENTRADA.open(encoding="utf-8-sig")):
        nombre = fila["nombre"].strip()
        orcid = fila["orcid"].strip().upper()
        literal = fila["centro_literal"].strip()
        truncado = (fila["fragmento_truncado"] or "").strip().lower() == "si"

        # Identidad: el ORCID manda. Sin ORCID coincidente, no se toca nada.
        r = con.execute(
            "SELECT id, name, orcid FROM researchers WHERE UPPER(REPLACE(orcid,' ',''))=?",
            (orcid,)).fetchone()
        if not r:
            plan.append(dict(nombre=nombre, orcid=orcid, accion="sin_researcher",
                             detalle="ORCID no está en la base", org=None))
            continue

        org, motivo, cands = resolver_org(literal, orgs)
        if not org:
            plan.append(dict(nombre=nombre, orcid=orcid, accion="sin_org",
                             detalle=f"{motivo}: {literal} ({len(cands)} candidatos)",
                             org=None))
            continue

        actual = con.execute(
            """SELECT o.id, o.name FROM researcher_affiliations ra JOIN orgs o ON o.id=ra.org_id
               WHERE ra.researcher_id=? AND ra.affiliation_type='centro'""",
            (r["id"],)).fetchall()

        if len(actual) > 1:
            plan.append(dict(nombre=nombre, orcid=orcid, accion="multi_centro",
                             detalle=f"ya tiene {len(actual)} centros", org=org))
            continue
        if actual:
            mismo = actual[0]["id"] == org["id"]
            plan.append(dict(nombre=nombre, orcid=orcid,
                             accion="ya_tiene_centro" if mismo else "conflicto",
                             detalle=actual[0]["name"], org=org))
            continue

        plan.append(dict(nombre=nombre, orcid=orcid, accion="insertar",
                         detalle=f"match {motivo}" + (" · truncado" if truncado else ""),
                         org=org, researcher_id=r["id"], deducido_de=literal,
                         truncado=truncado,
                         unidad=fila["unidad_investigacion"] or "",
                         departamento=fila["departamento"] or ""))

    print(f"{'persona':30} {'acción':16} {'centro resuelto':44} detalle")
    for p in plan:
        print(f"{p['nombre'][:30]:30} {p['accion']:16} "
              f"{(p['org']['name'] if p['org'] else '')[:44]:44} {p['detalle']}")

    nuevas = [p for p in plan if p["accion"] == "insertar"]
    print(f"\nresumen: {len(plan)} filas · insertar {len(nuevas)} · "
          f"ya_tiene_centro {sum(1 for p in plan if p['accion']=='ya_tiene_centro')} · "
          f"conflicto {sum(1 for p in plan if p['accion']=='conflicto')} · "
          f"sin_resolver {sum(1 for p in plan if p['accion'] in ('sin_org','sin_researcher'))}")

    if not write:
        print("\nDRY-RUN. Para escribir: python scripts/importa_centros_fundanet.py --write")
        con.close()
        return

    if not nuevas:
        print("\nNada que escribir.")
        con.close()
        return

    backup = siguiente_backup(DB)
    shutil.copy2(DB, backup)
    print(f"\nbackup: {backup.name}")

    insertadas = 0
    try:
        con.execute("BEGIN")
        for p in nuevas:
            evidencia = f"Centro del Tercero: {p['deducido_de']}"
            if p["truncado"]:
                evidencia += " (valor truncado en el volcado)"
            if p["unidad"]:
                evidencia += f" · Unidad de Investigación: {p['unidad']}"
            if p["departamento"]:
                evidencia += f" · Departamento: {p['departamento']}"
            con.execute(
                """INSERT INTO researcher_affiliations
                   (researcher_id, org_id, affiliation_type, method, status, confidence,
                    source, source_id, url, evidence_literal, first_seen, last_seen)
                   VALUES (?,?,'centro','fundanet_centro_tercero','declarado_institucion',
                           ?, 'fundanet', ?, NULL, ?, ?, ?)""",
                (p["researcher_id"], p["org"]["id"],
                 0.85 if p["truncado"] else 0.95,
                 p["orcid"], evidencia, hoy, hoy))
            insertadas += 1
        con.commit()
    except Exception as exc:  # noqa: BLE001
        con.rollback()
        print(f"ERROR, rollback completo: {exc}")
        raise

    print(f"insertadas: {insertadas}")
    print("integridad:", con.execute("PRAGMA integrity_check").fetchone()[0])
    print("FK rotas:", con.execute("PRAGMA foreign_key_check").fetchall())
    con.close()


if __name__ == "__main__":
    main(write="--write" in sys.argv[1:])
