"""Sensibilidad de las medianas del mapa a las piezas frágiles.

Escenarios:
  base          actual (ORCID declarado + recuperado + portal)
  sin_rec       quita las obras ORCID de los 80 recuperados
  sin_nodoi     solo obras con DOI
  sin_hom       quita pares ORCID con año <1975 o >2026
  solo_doi      solo DOI en ambas vías
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\Users\gipsy\repos\Ciencia_Abierta_Fisabio\rip-osiris")
DB = ROOT / "data" / "rip_osiris.sqlite"
SALIDA = ROOT / "data" / "sensibilidad_medianas.csv"

FUENTES_RECUPERADO = {
    "reverso_doi", "reverso_nombre_afiliacion", "reverso_multisenal",
    "reverso_nombre_variante", "reverso_openalex",
    "reverso_nombre_invertido", "reverso_nombre_incompleto",
    "confirmado_persona", "confirmado_institucion",
}


def nd(d):
    d = (d or "").strip().lower()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", d)


def es_doi(k):
    return k.startswith("10.")


con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
gente = {r["id"]: dict(r) for r in con.execute(
    "SELECT id, name, orcid, orcid_source FROM researchers")}
centro = {r["rid"]: r["centro"] for r in con.execute(
    """SELECT ra.researcher_id rid, o.name centro FROM researcher_affiliations ra
       JOIN orgs o ON o.id=ra.org_id WHERE ra.affiliation_type='centro'""")}
con.close()

recuperados = {rid for rid, g in gente.items() if g["orcid_source"] in FUENTES_RECUPERADO}

# ORCID: cosecha inicial + caché de recuperados
orcid = defaultdict(dict)
for linea in (ROOT / "data" / "author_work.jsonl").open(encoding="utf-8"):
    a = json.loads(linea)
    oid = (a.get("work_id") or "").rstrip("/").split("/")[-1]
    key = nd(a.get("doi")) or (f"openalex:{oid}" if oid.startswith("W") else "")
    if key:
        orcid[a["researcher_id"]][key] = {"year": a.get("year"), "source": "orcid"}

cache = json.loads((ROOT / "data" / "orcid_oa_cache.json").read_text(encoding="utf-8"))
for rid in recuperados:
    ident = (gente[rid]["orcid"] or "").strip().upper()
    for w in (cache.get(ident) or {}).get("results") or []:
        oid = (w.get("id") or "").rstrip("/").split("/")[-1]
        key = nd(w.get("doi")) or (f"openalex:{oid}" if oid.startswith("W") else "")
        if key:
            orcid[rid][key] = {"year": w.get("publication_year"), "source": "orcid"}

portal = defaultdict(dict)
for linea in (ROOT / "data" / "portal_publicaciones.jsonl").open(encoding="utf-8"):
    f = json.loads(linea)
    for p in f["pubs"]:
        key = nd(p.get("doi")) or f"portal:{p['pub_id']}"
        portal[f["researcher_id"]][key] = {"year": p.get("anio"), "source": "portal"}

union = {}
for rid in set(orcid) | set(portal):
    union[rid] = {**orcid.get(rid, {}), **portal.get(rid, {})}

centros = defaultdict(list)
for rid in gente:
    centros[centro.get(rid, "(sin centro)")].append(rid)


def mediana(escenario):
    out = {}
    for c, rids in centros.items():
        vals = [len(escenario.get(rid, {})) for rid in rids if escenario.get(rid)]
        out[c] = statistics.median(vals) if vals else None
    return out


base = {rid: dict(w) for rid, w in union.items()}
sin_rec = {}
for rid, w in union.items():
    if rid in recuperados:
        sin_rec[rid] = dict(portal.get(rid, {}))
    else:
        sin_rec[rid] = dict(w)
sin_nodoi = {rid: {k: v for k, v in w.items() if es_doi(k)} for rid, w in union.items()}
sin_hom = {
    rid: {k: v for k, v in w.items()
          if not (v.get("source") == "orcid" and v.get("year")
                  and (int(v["year"]) < 1975 or int(v["year"]) > 2026))}
    for rid, w in union.items()
}
solo_doi = {
    rid: {k: v for k, v in w.items() if es_doi(k)}
    for rid, w in union.items()
}

m_base = mediana(base)
m_rec = mediana(sin_rec)
m_nodoi = mediana(sin_nodoi)
m_hom = mediana(sin_hom)
m_doi = mediana(solo_doi)

# Comparación con el dataset publicado
dataset = {c["centro"]: c["mediana_union"] for c in json.loads(
    (ROOT / "data" / "mapa_orcid_dataset_v2.json").read_text(encoding="utf-8"))["centros"]}
dif = [abs((m_base.get(c) or 0) - (dataset.get(c) or 0)) for c in dataset]
print(f"base vs dataset publicado: diferencia máxima {max(dif) if dif else 0}")

filas = []
for c in centros:
    vals = [x for x in (m_base.get(c), m_rec.get(c), m_nodoi.get(c),
                        m_hom.get(c), m_doi.get(c)) if x is not None]
    if not vals:
        continue
    filas.append({
        "centro": c,
        "n_roster": len(centros[c]),
        "base": m_base.get(c),
        "sin_recuperados": m_rec.get(c),
        "sin_no_doi": m_nodoi.get(c),
        "sin_homonimos": m_hom.get(c),
        "solo_doi": m_doi.get(c),
        "rango": max(vals) - min(vals),
    })

filas.sort(key=lambda x: (-x["rango"], -(x["base"] or 0)))
with SALIDA.open("w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
    w.writeheader()
    w.writerows(filas)

print(f"\n{'centro':40} {'n':>4} {'base':>5} {'s/rec':>5} {'s/nodoi':>7} "
      f"{'s/hom':>5} {'soloDOI':>7} {'rango':>5}")
for f in filas:
    if f["n_roster"] < 5:
        continue
    print(f"{f['centro'][:40]:40} {f['n_roster']:4} "
          f"{(f['base'] or 0):5.0f} {(f['sin_recuperados'] or 0):5.0f} "
          f"{(f['sin_no_doi'] or 0):7.0f} {(f['sin_homonimos'] or 0):5.0f} "
          f"{(f['solo_doi'] or 0):7.0f} {f['rango']:5.0f}")

print("\nresumen:")
print(f"  centros con rango >= 1: {sum(1 for f in filas if f['rango'] >= 1)}")
print(f"  centros con rango >= 2: {sum(1 for f in filas if f['rango'] >= 2)}")
print(f"  centros con rango >= 5: {sum(1 for f in filas if f['rango'] >= 5)}")
print(f"  rango máximo: {max(f['rango'] for f in filas):.1f}")
print(f"  escrito {SALIDA}")
