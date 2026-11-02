"""Cruza el export completo de Fundanet con la base RIP-OSIRIS (sin escribir nada).

Columnas del export: Primer Apellido | Segundo Apellido | Nombre | Nacionalidad |
Centro del Tercero | Departamento del Tercero | Área de Conocimiento | Orcid Id

Salida: data/cruce_fundanet_completo.csv + resumen por pantalla.
"""
from __future__ import annotations

import csv
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\Users\gipsy\repos\Ciencia_Abierta_Fisabio\rip-osiris")
DB = ROOT / "data" / "rip_osiris.sqlite"
XLSX = Path(r"C:\Users\gipsy\Downloads\qtkfmbyx.hzt.xlsx")
SALIDA = ROOT / "data" / "cruce_fundanet_completo.csv"

CABECERA = 3  # fila 4 del Excel (0-indexed 3)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def tokens(s: str) -> frozenset[str]:
    return frozenset(t for t in norm(s).split() if len(t) > 1)


def checksum_ok(orcid: str) -> bool:
    s = (orcid or "").replace("-", "").upper()
    if not re.fullmatch(r"\d{15}[\dX]", s):
        return False
    total = 0
    for c in s[:15]:
        total = (total + int(c)) * 2
    control = (12 - total % 11) % 11
    return s[15] == ("X" if control == 10 else str(control))


def nd_orcid(o: str) -> str:
    return re.sub(r"^https?://(www\.)?orcid\.org/", "", str(o or "").strip()).upper()


# ---------- 1. Leer el export ----------
wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
ws = wb["Datos"]
export = []
for i, fila in enumerate(ws.iter_rows(min_row=CABECERA + 1, values_only=True)):
    if not fila or not any(fila):
        continue
    ap1, ap2, nombre, nac, centro, depto, area, orcid = (list(fila) + [None] * 8)[:8]
    if not (ap1 or nombre):
        continue
    export.append({
        "ap1": str(ap1 or "").strip(),
        "ap2": str(ap2 or "").strip(),
        "nombre": str(nombre or "").strip(),
        "nacionalidad": str(nac or "").strip(),
        "centro": str(centro or "").strip(),
        "departamento": str(depto or "").strip(),
        "area": str(area or "").strip(),
        "orcid": nd_orcid(orcid),
    })
wb.close()

print(f"filas del export: {len(export)}")
print(f"con ORCID: {sum(1 for e in export if e['orcid'])}")
print(f"con centro: {sum(1 for e in export if e['centro'])}")

# ---------- 2. Base ----------
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
gente = [dict(r) for r in con.execute(
    "SELECT id, portal_id, name, orcid, orcid_source, area FROM researchers")]
centro_db = {r["rid"]: r["centro"] for r in con.execute(
    """SELECT ra.researcher_id rid, o.name centro FROM researcher_affiliations ra
       JOIN orgs o ON o.id=ra.org_id WHERE ra.affiliation_type='centro' ORDER BY ra.id""")}
con.close()

print(f"roster en la base: {len(gente)}")
print(f"ORCID en la base: {sum(1 for g in gente if g['orcid'])}")

por_orcid = {nd_orcid(g["orcid"]): g for g in gente if g["orcid"]}
por_tokens = defaultdict(list)
for g in gente:
    por_tokens[tokens(g["name"])].append(g)

# ---------- 3. Cruce ----------
filas = []
for e in export:
    full = f"{e['nombre']} {e['ap1']} {e['ap2']}"
    tk = tokens(full)

    # identidad
    g = por_orcid.get(e["orcid"]) if e["orcid"] else None
    metodo = "orcid" if g else ""
    if not g:
        cands = por_tokens.get(tk) or []
        if cands:
            g, metodo = cands[0], "nombre_exacto"
        else:
            mejor, score = None, 0.0
            for tk_db, lista in por_tokens.items():
                inter = len(tk & tk_db)
                if not inter:
                    continue
                s = inter / len(tk | tk_db)
                if s > score:
                    mejor, score = lista[0], s
            if mejor and score >= 0.8:
                g, metodo = mejor, "nombre_aproximado"

    if not g:
        filas.append({**e, "nombre_export": full, "bd_id": "", "bd_nombre": "",
                      "bd_orcid": "", "bd_fuente": "", "bd_centro": "",
                      "estado": "no_en_roster", "metodo": "", "detalle": ""})
        continue

    o_db = nd_orcid(g["orcid"]) if g["orcid"] else ""
    c_db = centro_db.get(g["id"], "")
    d_db, d_exp = norm(c_db), norm(e["centro"])

    if not e["orcid"]:
        estado = "sin_orcid_en_fundanet"
        detalle = f"la base tiene {o_db}" if o_db else "sin ORCID en ninguna"
    elif not o_db:
        estado = "gap_orcid"
        detalle = "la base no lo tenía"
    elif o_db != e["orcid"]:
        estado = "conflicto_orcid"
        detalle = f"base={o_db} · fundanet={e['orcid']}"
    else:
        estado = "orcid_coincide"
        detalle = ""

    if e["centro"]:
        if not c_db:
            estado += "|centro_nuevo"
            detalle += " · sin centro en la base"
        elif d_db == d_exp:
            estado += "|centro_igual"
        elif d_exp and (d_exp in d_db or d_db in d_exp):
            estado += "|centro_compatible"
        else:
            estado += "|centro_distinto"
            detalle += f" · base={c_db[:40]} / fundanet={e['centro'][:40]}"

    filas.append({**e, "nombre_export": full, "bd_id": g["id"], "bd_nombre": g["name"],
                  "bd_orcid": o_db, "bd_fuente": g["orcid_source"] or "",
                  "bd_centro": c_db, "estado": estado, "metodo": metodo,
                  "detalle": detalle.strip(" ·")})

with SALIDA.open("w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
    w.writeheader()
    w.writerows(filas)

# ---------- 4. Resumen ----------
print(f"\n=== CRUCE ({len(filas)} filas) ===")
print("\nidentificación:")
for k, v in Counter(f["metodo"] if f["metodo"] else "—" for f in filas).most_common():
    print(f"  {k or 'sin match':18} {v}")

print("\nestado de ORCID:")
for k, v in Counter(f["estado"].split("|")[0] for f in filas).most_common():
    print(f"  {k:24} {v}")

print("\nestado de centro (solo con centro en Fundanet):")
centro_estados = Counter(
    [p for p in f["estado"].split("|") if p.startswith("centro_")][0]
    for f in filas if any(p.startswith("centro_") for p in f["estado"].split("|")))
for k, v in centro_estados.most_common():
    print(f"  {k:22} {v}")

nuevos = [f for f in filas if f["estado"].startswith("gap_orcid")]
print(f"\nORCID que la base no tenía: {len(nuevos)}")
for f in nuevos[:10]:
    print(f"  {f['nombre_export'][:38]:38} {f['orcid']} · centro {f['centro'][:30]}")

conflictos = [f for f in filas if "conflicto_orcid" in f["estado"]]
print(f"\nconflictos de ORCID: {len(conflictos)}")
for f in conflictos[:10]:
    print(f"  {f['nombre_export'][:34]:34} base={f['bd_orcid']} fundanet={f['orcid']}")

nuevos_centro = [f for f in filas if "centro_nuevo" in f["estado"]]
print(f"\npersonas que ganan centro: {len(nuevos_centro)}")
for f in nuevos_centro[:10]:
    print(f"  {f['nombre_export'][:38]:38} → {f['centro'][:40]}")

distintos = [f for f in filas if "centro_distinto" in f["estado"]]
print(f"\ncentros distintos: {len(distintos)}")
for f in distintos[:10]:
    print(f"  {f['nombre_export'][:30]:30} base={f['bd_centro'][:28]:28} fundanet={f['centro'][:28]}")

orcid_export = {f["orcid"] for f in filas if f["orcid"]}
solo_base = [o for o in por_orcid if o not in orcid_export]
print(f"\nORCID en la base que NO están en el export: {len(solo_base)}")
print(f"\nescrito {SALIDA}")
