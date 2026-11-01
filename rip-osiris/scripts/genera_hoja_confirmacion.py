"""Genera la hoja de confirmación ORCID: 80 recuperados + 3 en revisión.

Salida:
  data/hoja_confirmacion_orcid.csv  (para rellenar y reimportar)
  data/hoja_confirmacion_orcid.md   (para leer)

Columnas de decisión (vacías para que las rellene la persona/institución):
  decision        confirmar | rechazar | revisar
  confirmado_por  persona | institucion
  fecha           AAAA-MM-DD
  notas           texto libre
"""
from __future__ import annotations

import csv
import difflib
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\Users\gipsy\repos\Ciencia_Abierta_Fisabio\rip-osiris")
DB = ROOT / "data" / "rip_osiris.sqlite"
SALIDA_CSV = ROOT / "data" / "hoja_confirmacion_orcid.csv"
SALIDA_MD = ROOT / "data" / "hoja_confirmacion_orcid.md"

FUENTES_RECUPERADO = {
    "reverso_doi", "reverso_nombre_afiliacion", "reverso_multisenal",
    "reverso_nombre_variante", "reverso_openalex",
    "reverso_nombre_invertido", "reverso_nombre_incompleto",
    "confirmado_persona", "confirmado_institucion",
}
REVISION = {
    "Carlos Javier Diaz Lara",
    "Sandra Beltran Catalan",
    "Maria Nieves Diaz Fernandez",
}


def nd(d):
    d = (d or "").strip().lower()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", d)


def tokens(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z ]", " ", s.lower())
    return [t for t in s.split() if len(t) > 1]


def tset(s):
    return set(tokens(s))


def score_nombre(portal, orcid):
    a, b = tokens(portal), tokens(orcid)
    if not a or not b:
        return {"ratio": 0.0, "nivel": "rechazado"}
    ga, gb = set(a[:2]), set(b[:2])
    sa, sb = set(a[-2:]), set(b[-2:])
    given, surname = bool(ga & gb), bool(sa & sb)
    ratio = difflib.SequenceMatcher(None, " ".join(a), " ".join(b)).ratio()
    nivel = ("alto" if given and surname and ratio >= 0.80 else
             "medio" if given and surname and ratio >= 0.60 else
             "bajo" if given and surname else "rechazado")
    return {"ratio": round(ratio, 2), "nivel": nivel}


def es_la_persona(nombre_persona, nombre_autor):
    a, b = tset(nombre_persona), tset(nombre_autor)
    return bool(a) and bool(b) and (a <= b or b <= a)


# ---------------------------------------------------------------- carga
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
gente = {r["id"]: dict(r) for r in con.execute(
    "SELECT id, portal_id, name, orcid, orcid_source FROM researchers")}
centro = {r["rid"]: r["centro"] for r in con.execute(
    """SELECT ra.researcher_id rid, o.name centro FROM researcher_affiliations ra
       JOIN orgs o ON o.id=ra.org_id WHERE ra.affiliation_type='centro'""")}
con.close()

portal_pubs = {}
for linea in (ROOT / "data" / "portal_publicaciones.jsonl").open(encoding="utf-8"):
    f = json.loads(linea)
    portal_pubs[f["researcher_id"]] = f
portal_oa = json.loads((ROOT / "data" / "portal_doi_openalex.json").read_text(encoding="utf-8"))
cache = json.loads((ROOT / "data" / "orcid_oa_cache.json").read_text(encoding="utf-8"))

validado = {int(r["researcher_id"]): r for r in csv.DictReader(
    (ROOT / "data" / "orcid_reverso_validado.csv").open(encoding="utf-8-sig"))}
multisenal = {int(r["researcher_id"]): r for r in csv.DictReader(
    (ROOT / "data" / "orcid_reverso_multisenal.csv").open(encoding="utf-8-sig"))}
rev = list(csv.DictReader((ROOT / "data" / "revision_orcid_personas.csv").open(encoding="utf-8-sig")))
rev_por_nombre = {r["nombre"]: r for r in rev}

# Los 80 recuperados actuales
recuperados = [g for g in gente.values() if g["orcid_source"] in FUENTES_RECUPERADO]

filas = []
for g in recuperados:
    rid = g["id"]
    orcid = (g["orcid"] or "").upper()
    f = portal_pubs.get(rid, {"pubs": []})
    portal_dois = {nd(p.get("doi")) for p in f["pubs"] if p.get("doi")}
    co_portal = set()
    for d in portal_dois:
        for a in (portal_oa.get(d, {}) or {}).get("authorships") or []:
            n = a.get("name")
            if n and not es_la_persona(g["name"], n):
                co_portal.add(n)

    entry = cache.get(orcid) or {}
    obras = entry.get("results") or []
    orcid_dois = {nd(w.get("doi")) for w in obras if w.get("doi")}
    co_orcid = set()
    for w in obras:
        for a in w.get("authorships") or []:
            n = (a.get("author") or {}).get("display_name")
            if n and not es_la_persona(g["name"], n):
                co_orcid.add(n)

    solapan = []
    for a in co_portal:
        ta = tset(a)
        for b in co_orcid:
            if len(ta & tset(b)) >= 2:
                solapan.append(a)
                break
    inter = portal_dois & orcid_dois
    val = validado.get(rid, {})
    mult = multisenal.get(rid, {})
    sn = score_nombre(g["name"], val.get("nombre_orcid") or mult.get("nombre_orcid") or "")

    filas.append({
        "researcher_id": rid,
        "portal_id": g["portal_id"],
        "nombre": g["name"],
        "orcid": orcid,
        "nombre_orcid": val.get("nombre_orcid") or mult.get("nombre_orcid") or "",
        "afiliaciones_orcid": val.get("afiliaciones_orcid") or "",
        "centros_portal": centro.get(rid, ""),
        "orcid_source_actual": g["orcid_source"],
        "verification_status": "recuperado",
        "n_obras_portal": len(f["pubs"]),
        "n_obras_orcid": len(obras),
        "doi_overlap": len(inter),
        "doi_ratio": round(len(inter) / max(1, len(portal_dois)), 2),
        "co_portal": len(co_portal),
        "co_orcid": len(co_orcid),
        "co_overlap": len(solapan),
        "co_ratio": round(len(solapan) / max(1, len(co_portal)), 2),
        "apoyo": len(obras),
        "nivel_nombre": sn["nivel"],
        "ratio_nombre": sn["ratio"],
        "ejemplos_doi": ";".join(sorted(inter)[:3]),
        "ejemplos_coautores": ";".join(sorted(set(solapan))[:5]),
        "decision": "",
        "confirmado_por": "",
        "fecha": "",
        "notas": "",
    })

# Los 3 en revisión (no están en la base con ORCID)
for nombre in REVISION:
    rv = rev_por_nombre.get(nombre)
    if not rv:
        continue
    g = next((x for x in gente.values() if x["name"] == nombre), None)
    if not g:
        continue
    filas.append({
        "researcher_id": g["id"],
        "portal_id": g["portal_id"],
        "nombre": g["name"],
        "orcid": rv["orcid"],
        "nombre_orcid": rv.get("nombre_orcid", ""),
        "afiliaciones_orcid": rv.get("afiliaciones_orcid", ""),
        "centros_portal": centro.get(g["id"], ""),
        "orcid_source_actual": "",
        "verification_status": "pendiente",
        "n_obras_portal": rv.get("portal_pubs", ""),
        "n_obras_orcid": rv.get("orcid_pubs", ""),
        "doi_overlap": rv.get("doi_overlap", ""),
        "doi_ratio": rv.get("doi_ratio", ""),
        "co_portal": rv.get("co_portal", ""),
        "co_orcid": rv.get("co_orcid", ""),
        "co_overlap": rv.get("co_overlap", ""),
        "co_ratio": rv.get("co_ratio", ""),
        "apoyo": rv.get("apoyo", ""),
        "nivel_nombre": rv.get("nivel_nombre", ""),
        "ratio_nombre": rv.get("ratio_nombre", ""),
        "ejemplos_doi": "",
        "ejemplos_coautores": "",
        "decision": "",
        "confirmado_por": "",
        "fecha": "",
        "notas": "",
    })

campos = list(filas[0].keys())
with SALIDA_CSV.open("w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=campos)
    w.writeheader()
    w.writerows(filas)

# ---------------------------------------------------------------- markdown
lineas = [
    "# Confirmación ORCID · FISABIO",
    "",
    f"Generado el 02-11-2026 · **{len(filas)} personas** "
    f"({len(recuperados)} recuperadas + {len(filas)-len(recuperados)} en revisión).",
    "",
    "## Cómo rellenar la hoja",
    "",
    "En `data/hoja_confirmacion_orcid.csv`, por cada persona:",
    "",
    "| Columna | Valores |",
    "|---|---|",
    "| `decision` | `confirmar` · `rechazar` · `revisar` |",
    "| `confirmado_por` | `persona` · `institucion` |",
    "| `fecha` | `AAAA-MM-DD` |",
    "| `notas` | texto libre |",
    "",
    "Después: `python scripts/importa_confirmaciones.py`.",
    "",
    "## Resumen",
    "",
    "| Persona | ORCID | Fuente actual | DOI | Coautores | Estado |",
    "|---|---|---|---:|---:|---|",
]
for f in filas:
    lineas.append(
        f"| {f['nombre']} | {f['orcid']} | {f['orcid_source_actual'] or 'candidato'} | "
        f"{f['doi_overlap']}/{f['n_obras_portal']} | {f['co_overlap']}/{f['co_portal']} | "
        f"**{f['verification_status']}** |")

lineas += [
    "",
    "## Notas",
    "",
    "- **`recuperado`**: la ficha del portal no declaraba ORCID; el vínculo se infirió con DOI, coautores y nombre.",
    "- **`pendiente`**: candidato que aún no se ha escrito en la base.",
    "- **`confirmado_persona` / `confirmado_institucion`**: estados que aplicará el importador.",
    "- Un `rechazar` limpia `researchers.orcid` y borra los vínculos `orcid_reverso` de esa persona; no toca las obras del portal.",
    "",
    "## Evidencia por persona",
    "",
]
for f in filas:
    lineas += [
        f"### {f['nombre']}",
        "",
        f"- **ORCID:** {f['orcid']}",
        f"- **Nombre ORCID:** {f['nombre_orcid'] or '(sin dato)'}",
        f"- **Afiliación ORCID:** {f['afiliaciones_orcid'] or '(sin dato)'}",
        f"- **Centro portal:** {f['centros_portal'] or '(sin centro)'}",
        f"- **Fuente actual:** {f['orcid_source_actual'] or 'candidato'}",
        f"- **Obras:** {f['n_obras_portal']} del portal · {f['n_obras_orcid']} del ORCID",
        f"- **DOI en común:** {f['doi_overlap']} ({f['doi_ratio']})",
        f"- **Coautores en común:** {f['co_overlap']} de {f['co_portal']} ({f['co_ratio']})",
        f"- **Nombre:** {f['nivel_nombre']} ({f['ratio_nombre']})",
        f"- **Ejemplos DOI:** {f['ejemplos_doi'] or '(ninguno)'}",
        f"- **Ejemplos coautores:** {f['ejemplos_coautores'] or '(ninguno)'}",
        "",
    ]

SALIDA_MD.write_text("\n".join(lineas), encoding="utf-8")
print(f"filas: {len(filas)} · recuperados: {len(recuperados)} · revisión: {len(filas)-len(recuperados)}")
print(f"escrito {SALIDA_CSV}")
print(f"escrito {SALIDA_MD}")
