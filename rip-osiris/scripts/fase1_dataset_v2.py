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
from datetime import date
from pathlib import Path
from statistics import mean, median

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BASE = json.loads((ROOT / "data" / "mapa_orcid_dataset.json").read_text(encoding="utf-8"))
SALIDA = ROOT / "data" / "mapa_orcid_dataset_v2.json"


def nd(d):
    d = (d or "").strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    d = re.sub(r"^doi:\s*", "", d)
    m = re.search(r"10\.\d{4,9}/[-._;()/:a-z0-9]+", d, re.I)
    return m.group(0).rstrip(".,;)") if m else ""


con = sqlite3.connect(ROOT / "data" / "rip_osiris.sqlite")
con.row_factory = sqlite3.Row
gente = [dict(r) for r in con.execute("SELECT id, portal_id, name FROM researchers")]
centros_por_rid: dict[int, list[str]] = defaultdict(list)
for r in con.execute(
    """SELECT ra.researcher_id rid, o.name centro FROM researcher_affiliations ra
       JOIN orgs o ON o.id=ra.org_id WHERE ra.affiliation_type='centro'
       ORDER BY ra.id"""
):
    rid_row = int(r["rid"])
    if r["centro"] not in centros_por_rid[rid_row]:
        centros_por_rid[rid_row].append(r["centro"])
centro = {rid_row: cs[0] for rid_row, cs in centros_por_rid.items()}
investigadores_multicentro = sum(1 for cs in centros_por_rid.values() if len(cs) > 1)

fuentes_recuperado = {
    "reverso_doi", "reverso_nombre_afiliacion", "reverso_multisenal",
    "reverso_nombre_variante", "reverso_openalex", "reverso_nombre_invertido",
    "reverso_nombre_incompleto", "confirmado_persona", "confirmado_institucion",
}
filas_orcid = list(con.execute(
    "SELECT id, orcid, orcid_source FROM researchers "
    "WHERE orcid IS NOT NULL AND orcid != ''"
))
duenos_orcid = defaultdict(set)
for r in filas_orcid:
    ident = re.sub(r"^https?://(www\.)?orcid\.org/", "", r["orcid"].strip()).upper()
    duenos_orcid[ident].add(int(r["id"]))
declarado = {
    int(r["id"]) for r in filas_orcid
    if r["orcid_source"] in {"portal", "portal_ficha"}
}
recuperados_ambiguos = {
    int(r["id"]) for r in filas_orcid
    if r["orcid_source"] in fuentes_recuperado
    and len(duenos_orcid[re.sub(r"^https?://(www\.)?orcid\.org/", "", r["orcid"].strip()).upper()]) > 1
}
orcid_recuperado = {
    int(r["id"]): r["orcid"] for r in filas_orcid
    if r["orcid_source"] in fuentes_recuperado
    and int(r["id"]) not in recuperados_ambiguos
}
recuperado = set(orcid_recuperado)

# Verificaciones: quién confirmó el ORCID (tabla orcid_verifications), distinto de
# la procedencia (orcid_source). Puede haber varias por persona; se guarda la más fuerte.
jerarquia_metodo = {"oauth": 3, "persona": 2, "institucion": 1}
verificados: dict[int, str] = {}
try:
    for r in con.execute("SELECT researcher_id, metodo FROM orcid_verifications"):
        rid_v = int(r["researcher_id"])
        previo = verificados.get(rid_v)
        if previo is None or jerarquia_metodo.get(r["metodo"], 0) > jerarquia_metodo.get(previo, 0):
            verificados[rid_v] = r["metodo"]
except sqlite3.OperationalError:
    print("aviso: no existe orcid_verifications; se cuenta 0 verificados")

orcid_works = defaultdict(set)
for linea in (ROOT / "data" / "author_work.jsonl").open(encoding="utf-8"):
    a = json.loads(linea)
    d = nd(a.get("doi"))
    orcid_works[a["researcher_id"]].add(d if d else "openalex:" + a["work_id"])

# Los ORCID recuperados no estaban en la cosecha inicial de author_work.jsonl.
# Añadir sus obras OpenAlex solo cuando la caché acredita que la lista está
# completa; así no se presentan primeras páginas parciales como producción total.
cache_path = ROOT / "data" / "orcid_oa_cache.json"
cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
recuperados_con_obras = 0
recuperados_pendientes = 0
for rid, ident in orcid_recuperado.items():
    ident = re.sub(r"^https?://(www\.)?orcid\.org/", "", ident.strip()).upper()
    entrada = cache.get(ident)
    if not entrada:
        recuperados_pendientes += 1
        continue
    obras = entrada.get("results") or []
    esperado = (entrada.get("meta") or {}).get("count")
    try:
        completa = esperado is not None and len(obras) >= int(esperado)
    except (TypeError, ValueError):
        completa = False
    if not completa:
        recuperados_pendientes += 1
        continue
    for obra in obras:
        doi = nd(obra.get("doi"))
        work_id = (obra.get("id") or "").rstrip("/").split("/")[-1]
        clave = doi or (f"openalex:{work_id}" if work_id.startswith("W") else "")
        if clave:
            orcid_works[rid].add(clave)
    recuperados_con_obras += 1

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
    "total": 0, "decl": 0, "rec": 0, "ver": 0, "prod": 0,
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
    a["ver"] += rid in verificados
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
        "orcid_verificados": a["ver"],
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
    "generado": date.today().isoformat(),
    "fuente": "roster portal FISABIO + ORCID declarado + ORCID inverso + publicaciones del portal + OpenAlex",
    "orcid_recuperados_con_obras_completas": recuperados_con_obras,
    "orcid_recuperados_pendientes_de_cosecha": recuperados_pendientes,
    "orcid_recuperados_ambiguos": len(recuperados_ambiguos),
    "orcid_verificados_total": len(verificados),
    "orcid_verificados_por_metodo": {
        m: sum(1 for v in verificados.values() if v == m)
        for m in ("oauth", "persona", "institucion")
    },
    "investigadores_multicentro": investigadores_multicentro,
    "nota_metodo": (
        "Cobertura declarada = ORCID en la ficha. Ampliada = declarada + recuperada "
        "por solape de DOI/nombre+afiliación. Producción = personas con obras por ORCID o por "
        "el portal. Mediana ORCID = solo personas con obras vía ORCID. Mediana unión = personas "
        "con obras por cualquiera de las dos vías. Las obras OpenAlex de ORCID recuperados "
        "se incorporan solo si la caché contiene todas las páginas; las pendientes se cuentan "
        "por el portal hasta completar esa cosecha."
    ),
    "centros": centros,
}
SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"centros: {len(centros)} · ORCID recuperados con obras completas: "
      f"{recuperados_con_obras} · pendientes: {recuperados_pendientes} · "
      f"ORCID duplicados excluidos: {len(recuperados_ambiguos)} · "
      f"multicentro: {investigadores_multicentro} · escrito {SALIDA}\n")
print(f"{'centro':44} {'n':>4} {'decl':>5} {'amp':>5} {'prod':>5} {'medO':>5} {'medU':>5}")
for c in centros:
    if c["total_roster"] < 5:
        continue
    print(f"{c['centro'][:44]:44} {c['total_roster']:4} "
          f"{c['cobertura_declarada_pct']:4.0f}% {c['cobertura_ampliada_pct']:4.0f}% "
          f"{c['cobertura_produccion_pct']:4.0f}% "
          f"{(c['mediana_orcid'] or 0):5.0f} {(c['mediana_union'] or 0):5.0f}")
