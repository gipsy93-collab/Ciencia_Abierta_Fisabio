"""Aplica correcciones de ORCID resueltas con evidencia externa.

Caso documentado (03-11-2026): José Marcelo Galbis Caravajal tenía declarado en el
portal un ORCID **vacío** (0 obras en ORCID y sin autor en OpenAlex). Fundanet
registra otro con 58 obras en ORCID y 153 en OpenAlex. Se corrige.

Qué hace, en una transacción:
  1. Cambia `researchers.orcid` y marca `orcid_source='confirmado_institucion'`.
  2. Registra la corrección en `orcid_verifications` con la evidencia.
  3. Trae las obras del ORCID nuevo desde OpenAlex y las enlaza (`orcid_exacto`).

Uso:
    python scripts/aplica_correccion_orcid.py            # dry-run
    python scripts/aplica_correccion_orcid.py --write
"""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from backup_util import siguiente_backup  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "rip_osiris.sqlite"
UA = {"User-Agent": "OSIRIS-research (mailto:gipsy93@gmail.com)"}

CORRECCIONES = [
    {
        "researcher_id": 1024,
        "nombre": "José Marcelo Galbis Caravajal",
        "orcid_viejo": "0000-0002-0762-8023",
        "orcid_nuevo": "0000-0002-1058-0171",
        "evidencia": ("ORCID declarado en el portal vacío (0 obras en el registro ORCID, sin autor "
                      "en OpenAlex). Fundanet registra 0000-0002-1058-0171 con 58 obras en ORCID "
                      "y 153 en OpenAlex. Corrección institucional del 03-11-2026."),
        "confianza": 0.90,
    },
]


def checksum_ok(orcid: str) -> bool:
    s = orcid.replace("-", "").upper()
    if not re.fullmatch(r"\d{15}[\dX]", s):
        return False
    total = 0
    for c in s[:15]:
        total = (total + int(c)) * 2
    control = (12 - total % 11) % 11
    return s[15] == ("X" if control == 10 else str(control))


def get(url: str, timeout: int = 90, intentos: int = 3) -> dict:
    for i in range(intentos):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and i < intentos - 1:
                time.sleep(2 * (i + 1))
                continue
            raise
    raise RuntimeError("inaccesible")


def obras_openalex(orcid: str) -> tuple[str, list[dict]]:
    """Devuelve (author_id, obras) del autor OpenAlex de ese ORCID."""
    d = get("https://api.openalex.org/authors?" + urllib.parse.urlencode(
        {"filter": f"orcid:{orcid}", "select": "id,display_name,works_count"}))
    if not d["results"]:
        return "", []
    autor = d["results"][0]
    aid = autor["id"].rsplit("/", 1)[-1]
    obras, page = [], 1
    while True:
        w = get("https://api.openalex.org/works?" + urllib.parse.urlencode({
            "filter": f"author.id:{aid}",
            "per-page": 200, "page": page,
            "select": "id,doi,title,publication_year,type"}))
        obras.extend(w["results"])
        if len(obras) >= w["meta"]["count"] or not w["results"]:
            break
        page += 1
    return aid, obras


def nd(d: str | None) -> str:
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", (d or "").strip().lower())


def main(write: bool) -> None:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    hoy = date.today().isoformat()
    plan = []

    for c in CORRECCIONES:
        r = con.execute("SELECT id, name, orcid, orcid_source FROM researchers WHERE id=?",
                        (c["researcher_id"],)).fetchone()
        print(f"\n=== {c['nombre']} (id {c['researcher_id']}) ===")
        if not r:
            print("  no existe; se omite")
            continue
        actual = (r["orcid"] or "").upper()
        if actual != c["orcid_viejo"]:
            print(f"  el ORCID actual es {actual}, no {c['orcid_viejo']}; se omite")
            continue
        if not checksum_ok(c["orcid_nuevo"]):
            print("  el ORCID nuevo no pasa el dígito de control; se omite")
            continue
        otro = con.execute("SELECT id, name FROM researchers WHERE UPPER(orcid)=?",
                           (c["orcid_nuevo"],)).fetchone()
        if otro:
            print(f"  el ORCID nuevo ya está en {otro['name']} (id {otro['id']}); se omite")
            continue

        aid, obras = obras_openalex(c["orcid_nuevo"])
        print(f"  ORCID nuevo : {c['orcid_nuevo']} ({r['orcid_source']} → confirmado_institucion)")
        print(f"  OpenAlex    : {aid or 'sin autor'} · {len(obras)} obras")
        if not aid:
            print("  sin autor en OpenAlex; se omite para no dejar el ORCID sin obras")
            continue
        plan.append((c, obras))

    if not write:
        print("\nDRY-RUN. Para escribir: python scripts/aplica_correccion_orcid.py --write")
        con.close()
        return

    backup = siguiente_backup(DB)
    shutil.copy2(DB, backup)
    print(f"\nbackup: {backup.name}")

    total_new = total_relink = 0
    try:
        con.execute("BEGIN IMMEDIATE")
        for c, obras in plan:
            rid = c["researcher_id"]
            con.execute("UPDATE researchers SET orcid=?, orcid_source='confirmado_institucion' WHERE id=?",
                        (c["orcid_nuevo"], rid))
            con.execute(
                """INSERT OR IGNORE INTO orcid_verifications
                   (researcher_id, orcid, metodo, fuente, evidencia, confianza, fecha)
                   VALUES (?,?,'institucion','fundanet',?,?,?)""",
                (rid, c["orcid_nuevo"], c["evidencia"], c["confianza"], hoy))

            for w in obras:
                doi = nd(w.get("doi"))
                oid = (w.get("id") or "").rsplit("/", 1)[-1]
                key = "doi:" + doi if doi else "openalex:" + oid
                wid = None
                if doi:
                    fila = con.execute("SELECT id FROM works WHERE doi=?", (doi,)).fetchone()
                    wid = fila["id"] if fila else None
                if wid is None:
                    fila = con.execute("SELECT id FROM works WHERE canonical_key=?", (key,)).fetchone()
                    wid = fila["id"] if fila else None
                if wid is None:
                    con.execute(
                        "INSERT INTO works (doi, title, year, type, canonical_key) VALUES (?,?,?,?,?)",
                        (doi or None, w.get("title") or "(sin título)",
                         w.get("publication_year"), w.get("type"), key))
                    wid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
                    total_new += 1
                altas = [("openalex", oid)]
                if doi:
                    altas.insert(0, ("doi", doi))
                for scheme, value in altas:
                    if not value:
                        continue
                    con.execute("INSERT OR IGNORE INTO work_ids (work_id, scheme, value) VALUES (?,?,?)",
                                (wid, scheme, value))
                cur = con.execute(
                    "INSERT OR IGNORE INTO author_work (researcher_id, work_id, source, confidence) "
                    "VALUES (?,?,'orcid_exacto',1.0)", (rid, wid))
                total_relink += cur.rowcount
        con.execute("COMMIT")
    except Exception as exc:  # noqa: BLE001
        con.execute("ROLLBACK")
        print(f"ERROR, rollback completo: {exc}")
        raise

    print(f"obras nuevas: {total_new} · vínculos nuevos: {total_relink}")
    print("ORCID total:", con.execute(
        "SELECT COUNT(*) FROM researchers WHERE orcid IS NOT NULL").fetchone()[0])
    print("obras total:", con.execute("SELECT COUNT(*) FROM works").fetchone()[0])
    print("author_work total:", con.execute("SELECT COUNT(*) FROM author_work").fetchone()[0])
    print("integridad:", con.execute("PRAGMA integrity_check").fetchone()[0])
    print("FK rotas:", con.execute("PRAGMA foreign_key_check").fetchall())
    con.close()


if __name__ == "__main__":
    main(write="--write" in sys.argv[1:])
