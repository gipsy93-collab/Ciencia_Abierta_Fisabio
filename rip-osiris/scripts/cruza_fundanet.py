"""Cruza los 9 ORCID de Fundanet con el roster y la base RIP-OSIRIS."""
from __future__ import annotations

import csv
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\Users\gipsy\repos\Ciencia_Abierta_Fisabio\rip-osiris")
DB = ROOT / "data" / "rip_osiris.sqlite"
SALIDA = ROOT / "data" / "cruce_fundanet.csv"

# (primer apellido, segundo apellido, nombre, ORCID, centro Fundanet, departamento)
CASOS = [
    ("BOU", "BOLUDA", "LAIA", "0000-0003-2033-8669", "HOSPITAL ARNAU DE VILANOVA", "DERMATOLOGÍA"),
    ("SEQUI", "SABATER", "JOSÉ MIGUEL", "0000-0001-8437-1623", "HOSPITAL FRANCESC DE BORJA", "PEDIATRÍA"),
    ("BELSO", "CANDELA", "ANA", "0009-0000-9307-927X", "HOSPITAL GENERAL UNIVERSITARIO", "MEDICINA INTERNA"),
    ("BLASCO", "PERIS", "DÉBORA", "0009-0002-8843-7890", "HOSPITAL LA PLANA", ""),
    ("GALLEGO", "CLEMENTE", "ANDREU", "0009-0007-1231-9173", "HOSPITAL LA PLANA", ""),
    ("FALCO", "MARTINEZ", "JAIME", "0009-0005-5051-2957", "HOSPITAL VINALOPÓ SALUD", "ENFERMERÍA"),
    ("FERNANDEZ", "DE MAYA", "JOSE", "0000-0002-6925-4389", "HOSPITAL VINALOPÓ SALUD", ""),
    ("MIRO", "VICEDO", "CARLA", "0009-0006-1180-8787", "HOSPITAL VIRGEN DE LOS LIRIOS", "PEDIATRÍA"),
    ("ROMERO", "ESPINÓS", "AINHOA", "0009-0008-6636-0929", "HOSPITAL VIRGEN DE LOS LIRIOS", ""),
]


def norm(s: str) -> list[str]:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z ]", " ", s.lower())
    return [t for t in s.split() if len(t) > 1]


def score(a: str, b: str) -> float:
    ta, tb = set(norm(a)), set(norm(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta), len(tb))


def valido_orcid(orcid: str) -> bool:
    s = orcid.replace("-", "").upper()
    if not re.fullmatch(r"\d{15}[\dX]", s):
        return False
    total = 0
    for c in s[:15]:
        total = (total + int(c)) * 2
    control = (12 - total % 11) % 11
    return s[15] == ("X" if control == 10 else str(control))


con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
gente = [dict(r) for r in con.execute(
    "SELECT id, portal_id, name, orcid, orcid_source FROM researchers")]
centro = {r["rid"]: r["centro"] for r in con.execute(
    """SELECT ra.researcher_id rid, o.name centro FROM researcher_affiliations ra
       JOIN orgs o ON o.id=ra.org_id WHERE ra.affiliation_type='centro'""")}
con.close()

print(f"{'Fundanet':32} {'ORCID':20} {'BD':34} {'ORCID BD':20} {'fuente':22} {'estado':12} {'centro BD'}")
filas = []
for ap1, ap2, nombre, orcid, centro_f, depto in CASOS:
    full = f"{nombre} {ap1} {ap2}"
    ranking = sorted(((score(full, g["name"]), g) for g in gente), key=lambda x: -x[0])
    mejor = ranking[0] if ranking and ranking[0][0] >= 0.6 else None
    if not mejor:
        estado, bd, o_bd, fuente, centro_bd = "no_roster", None, "", "", ""
    else:
        bd = mejor[1]
        o_bd = (bd["orcid"] or "").upper()
        fuente = bd["orcid_source"] or ""
        centro_bd = centro.get(bd["id"], "")
        if not o_bd:
            estado = "gap"
        elif o_bd == orcid.upper():
            estado = "coincide"
        else:
            estado = "conflicto"
    filas.append({
        "fundanet_nombre": full,
        "fundanet_orcid": orcid,
        "fundanet_centro": centro_f,
        "fundanet_departamento": depto,
        "checksum": valido_orcid(orcid),
        "bd_id": bd["id"] if bd else "",
        "bd_nombre": bd["name"] if bd else "",
        "bd_orcid": o_bd,
        "bd_fuente": fuente,
        "bd_centro": centro_bd,
        "match": round(mejor[0], 2) if mejor else 0,
        "estado": estado,
    })
    print(f"{full[:32]:32} {orcid:20} {(bd['name'] if bd else '(no encontrado)')[:34]:34} "
          f"{o_bd:20} {fuente:22} {estado:12} {centro_bd[:28]}")

with SALIDA.open("w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
    w.writeheader()
    w.writerows(filas)
print(f"\nescrito {SALIDA}")
print("checksum:", sum(1 for f in filas if f["checksum"]), "/", len(filas))
