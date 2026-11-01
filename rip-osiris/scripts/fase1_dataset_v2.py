"""Dataset v2 del mapa: cobertura declarada, ampliada y de producción.

Añade al dataset actual:
  - ORCID recuperado (confirmados, sin los 3 sospechosos)
  - cobertura ampliada
  - cobertura de producción (ORCID + portal)
  - mediana ORCID vs mediana unión
  - pares y obras de cada vía
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\Users\gipsy\repos\Ciencia_Abierta_Fisabio\rip-osiris")
BASE = json.loads((ROOT / "data" / "mapa_orcid_dataset.json").read_text(encoding="utf-8"))
SALIDA = ROOT / "data" / "mapa_orcid_dataset_v2.json"


def nd(d):
    d = (d or "").strip().lower()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", d)


con = sqlite3.connect(ROOT / "data" / "rip_osiris.sqlite")
con.row_factory = sqlite3.Row
gente = [dict(r) for r in con.execute("SELECT id, portal_id, name FROM researchers")]
centro = {r["rid"]: r["centro"] for r in con.execute(
    """SELECT ra.researcher_id rid, o.name centro FROM researcher_affiliations ra
       JOIN orgs o ON o.id=ra.org_id WHERE ra.affiliation_type='centro'""")}

declarado = {r["id"] for r in con.execute(
    "SELECT id FROM researchers WHERE orcid_source='portal_ficha'")}
recuperado = {r["id"] for r in con.execute(
    "SELECT id FROM researchers WHERE orcid_source IN "
    "('reverso_doi','reverso_nombre_afiliacion','reverso_multisenal')")}

orcid_works = defaultdict(set)
for linea in (ROOT / "data" / "author_work.jsonl").open(encoding="utf-8"):
    a = json.loads(linea)
    d = nd(a.get("doi"))
    orcid_works[a["researcher_id"]].add(d if d else "openalex:" + a["work_id"])

portal_works = defaultdict(set)
for linea in (ROOT / "data" / "portal_publicaciones.jsonl").open(encoding="utf-8"):
    f = json.loads(linea)
    for p in f["pubs"]:
        d = nd(p.get("doi"))
        portal_works[f["researcher_id"]].add(d if d else "portal:" + p["pub_id"])

union = defaultdict(set)
for rid in set(orcid_works) | set(portal_works):
    union[rid] = orcid_works.get(rid, set()) | portal_works.get(rid, set())

# agregación por centro
agg = defaultdict(lambda: {
    "total": 0, "decl": 0, "rec": 0, "prod": 0,
    "n_o": 0, "n_u": 0, "p_o": 0, "p_p": 0, "p_u": 0,
    "obras_o": set(), "obras_p": set(), "obras_u": set(),
    "lista_o": [], "lista_u": [],
})
for g in gente:
    rid = g["id"]
    c = centro.get(rid, "(sin centro)")
    a = agg[c]
    a["total"] += 1
    a["decl"] += rid in declarado
    a["rec"] += rid in recuperado
    if union.get(rid):
        a["prod"] += 1
    if orcid_works.get(rid):
        a["n_o"] += 1
        a["p_o"] += len(orcid_works[rid])
        a["obras_o"] |= orcid_works[rid]
        a["lista_o"].append(len(orcid_works[rid]))
    if portal_works.get(rid):
        a["p_p"] += len(portal_works[rid])
        a["obras_p"] |= portal_works[rid]
    if union.get(rid):
        a["n_u"] += 1
        a["p_u"] += len(union[rid])
        a["obras_u"] |= union[rid]
        a["lista_u"].append(len(union[rid]))

base_por_centro = {c["centro"]: c for c in BASE["centros"]}
centros = []
for c, a in agg.items():
    b = base_por_centro.get(c, {})
    total = a["total"]
    centros.append({
        "centro": c,
        "tipo": b.get("tipo", "otros"),
        "total_roster": total,
        "orcid_declarado": a["decl"],
        "orcid_recuperado": a["rec"],
        "orcid_ampliado": a["decl"] + a["rec"],
        "cobertura_declarada_pct": round(100 * a["decl"] / total, 1),
        "cobertura_ampliada_pct": round(100 * (a["decl"] + a["rec"]) / total, 1),
        "con_publicaciones_portal": sum(1 for g in gente
                                        if centro.get(g["id"], "(sin centro)") == c
                                        and portal_works.get(g["id"])),
        "con_produccion": a["prod"],
        "cobertura_produccion_pct": round(100 * a["prod"] / total, 1),
        "brecha_pct": round(100 * a["prod"] / total - 100 * a["decl"] / total, 1),
        "n_efectivo_orcid": a["n_o"],
        "mediana_orcid": median(a["lista_o"]) if a["lista_o"] else None,
        "media_orcid": round(mean(a["lista_o"]), 1) if a["lista_o"] else None,
        "total_obras_orcid": len(a["obras_o"]),
        "n_efectivo_union": a["n_u"],
        "mediana_union": median(a["lista_u"]) if a["lista_u"] else None,
        "media_union": round(mean(a["lista_u"]), 1) if a["lista_u"] else None,
        "total_obras_union": len(a["obras_u"]),
        "pares_orcid": a["p_o"],
        "pares_portal": a["p_p"],
        "pares_union": a["p_u"],
        "obras_orcid": len(a["obras_o"]),
        "obras_portal": len(a["obras_p"]),
        "obras_union": len(a["obras_u"]),
        "lat": b.get("lat"),
        "lon": b.get("lon"),
        "coord_fuente": b.get("coord_fuente", ""),
    })

centros.sort(key=lambda x: -x["total_roster"])
datos = {
    "generado": "2026-10-30",
    "fuente": "roster portal FISABIO + ORCID declarado + ORCID inverso + publicaciones del portal + OpenAlex",
    "nota_metodo": (
        "Cobertura declarada = ORCID en la ficha. Ampliada = declarada + recuperada "
        "por solape de DOI/nombre+afiliación. Producción = personas con obras por ORCID o por "
        "el portal. Mediana ORCID = solo personas con obras vía ORCID. Mediana unión = personas "
        "con obras por cualquiera de las dos vías; corrige el sesgo de selección del ORCID."
    ),
    "centros": centros,
}
SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"centros: {len(centros)} · escrito {SALIDA}\n")
print(f"{'centro':44} {'n':>4} {'decl':>5} {'amp':>5} {'prod':>5} {'medO':>5} {'medU':>5}")
for c in centros:
    if c["total_roster"] < 5:
        continue
    print(f"{c['centro'][:44]:44} {c['total_roster']:4} "
          f"{c['cobertura_declarada_pct']:4.0f}% {c['cobertura_ampliada_pct']:4.0f}% "
          f"{c['cobertura_produccion_pct']:4.0f}% "
          f"{(c['mediana_orcid'] or 0):5.0f} {(c['mediana_union'] or 0):5.0f}")
