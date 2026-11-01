"""Ficha de revisión por persona para los candidatos ORCID pendientes.

Evidencia:
  - nombre (nombre de pila + apellidos + ratio)
  - apoyo (obras OpenAlex con ese ORCID)
  - solape de DOI (portal ∩ ORCID)
  - solape de coautores (coautores del portal ∩ coautores del ORCID)
  - afiliación ORCID
"""
from __future__ import annotations

import csv
import difflib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
MAIL = os.environ.get("OPENALEX_MAILTO", "rip-osiris@localhost")
CACHE = ROOT / "data" / "orcid_oa_cache.json"
SALIDA_MD = ROOT / "data" / "revision_orcid_personas.md"
SALIDA_CSV = ROOT / "data" / "revision_orcid_personas.csv"

SOSPECHOSOS = {"Cristina Fernandez Martinez", "Jose Luis Rodrigo Perez", "Monica Romero Nieto"}


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


def get_json(url, intentos=3):
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": f"rip-osiris/0.1 (mailto:{MAIL})", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except Exception:
            if i < intentos - 1:
                time.sleep(2 ** (i + 1))
    return None


def obras_openalex_completas(orcid, cache):
    """Devuelve todas las páginas de obras; una primera página no es el censo."""
    entrada = cache.get(orcid)
    if entrada:
        resultados = entrada.get("results") or []
        esperado = (entrada.get("meta") or {}).get("count")
        try:
            if esperado is not None and len(resultados) >= int(esperado):
                return entrada
        except (TypeError, ValueError):
            pass

    resultados = []
    meta = {}
    pagina = 1
    while True:
        url = (f"https://api.openalex.org/works?filter=author.orcid:{orcid}"
               f"&select=id,title,publication_year,doi,authorships&per-page=200"
               f"&page={pagina}&mailto={MAIL}")
        respuesta = get_json(url)
        if not respuesta:
            # Si la red falla, se conserva la caché antigua, pero el consumidor
            # detectará que count > results y no la tratará como completa.
            return entrada or {"results": [], "meta": {"count": None}}
        lote = respuesta.get("results") or []
        meta = respuesta.get("meta") or meta
        resultados.extend(lote)
        esperado = meta.get("count")
        if not lote or (esperado is not None and len(resultados) >= int(esperado)):
            break
        pagina += 1
        time.sleep(0.15)
    return {"meta": meta, "results": resultados}


# ---------------------------------------------------------------- carga
con_db = __import__("sqlite3").connect(ROOT / "data" / "rip_osiris.sqlite")
con_db.row_factory = __import__("sqlite3").Row
ya = {r["id"] for r in con_db.execute("SELECT id FROM researchers WHERE orcid IS NOT NULL")}
orcid_recuperados = [r["orcid"] for r in con_db.execute(
    "SELECT orcid FROM researchers WHERE orcid IS NOT NULL AND orcid != '' "
    "AND orcid_source IN ('reverso_doi','reverso_nombre_afiliacion',"
    "'reverso_multisenal','reverso_nombre_variante','reverso_openalex',"
    "'reverso_nombre_invertido','reverso_nombre_incompleto')"
)]
con_db.close()

review = list(csv.DictReader((ROOT / "data" / "orcid_revision_pendientes.csv").open(encoding="utf-8-sig")))
pendientes = [r for r in review
              if int(r["researcher_id"]) not in ya and r["nombre"] not in SOSPECHOSOS]

portal_pubs = {}
for linea in (ROOT / "data" / "portal_publicaciones.jsonl").open(encoding="utf-8"):
    f = json.loads(linea)
    portal_pubs[f["researcher_id"]] = f

portal_oa = json.loads((ROOT / "data" / "portal_doi_openalex.json").read_text(encoding="utf-8"))
cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

# Refrescar también las obras de ORCID ya recuperados: no figuran en la cosecha
# inicial de author_work.jsonl, pero sí deben entrar en la mediana de unión.
for ident in sorted(set(orcid_recuperados)):
    ident = re.sub(r"^https?://(www\.)?orcid\.org/", "", ident.strip()).upper()
    cache[ident] = obras_openalex_completas(ident, cache)
    time.sleep(0.15)

print(f"pendientes: {len(pendientes)}", flush=True)

filas = []
for i, r in enumerate(pendientes, 1):
    rid = int(r["researcher_id"])
    orcid = re.sub(r"^https?://(www\.)?orcid\.org/", "", r["orcid"].strip()).upper()
    nombre = r["nombre"]
    f = portal_pubs.get(rid, {"pubs": []})
    portal_dois = {nd(p.get("doi")) for p in f["pubs"] if p.get("doi")}
    portal_titulos = [(p.get("anio"), p.get("titulo"), p.get("doi")) for p in f["pubs"]]

    # coautores del portal
    co_portal = set()
    for d in portal_dois:
        for a in (portal_oa.get(d, {}) or {}).get("authorships") or []:
            n = a.get("name")
            if n and not es_la_persona(nombre, n):
                co_portal.add(n)

    # obras OpenAlex del ORCID
    cache[orcid] = obras_openalex_completas(orcid, cache)
    obras = cache[orcid].get("results") or []
    orcid_dois = {nd(w.get("doi")) for w in obras if w.get("doi")}
    co_orcid = set()
    for w in obras:
        for a in w.get("authorships") or []:
            n = (a.get("author") or {}).get("display_name")
            if n and not es_la_persona(nombre, n):
                co_orcid.add(n)

    # solapamiento de coautores
    solapan = []
    for a in co_portal:
        ta = tset(a)
        for b in co_orcid:
            if len(ta & tset(b)) >= 2:
                solapan.append(a)
                break
    co_overlap = len(solapan)
    co_ratio = co_overlap / max(1, len(co_portal))

    doi_overlap = len(portal_dois & orcid_dois)
    doi_ratio = doi_overlap / max(1, len(portal_dois))
    sn = score_nombre(nombre, r["nombre_orcid"])

    # recomendación
    if doi_overlap >= 2 and doi_ratio >= 0.5:
        rec = "añadir"
    elif doi_overlap >= 1 and doi_ratio >= 0.5 and sn["nivel"] in ("alto", "medio"):
        rec = "añadir"
    elif co_overlap >= 3 and co_ratio >= 0.3 and sn["nivel"] in ("alto", "medio"):
        rec = "añadir"
    elif co_overlap >= 1 and sn["nivel"] == "alto":
        rec = "probable"
    elif sn["nivel"] == "alto":
        rec = "revisar"
    elif sn["nivel"] == "rechazado" and doi_overlap == 0 and co_overlap == 0:
        rec = "descartar"
    else:
        rec = "revisar"

    filas.append({
        "nombre": nombre,
        "orcid": orcid,
        "nombre_orcid": r["nombre_orcid"],
        "afiliaciones_orcid": r["afiliaciones_orcid"],
        "apoyo": int(r["apoyo"]),
        "nivel_nombre": sn["nivel"],
        "ratio_nombre": sn["ratio"],
        "portal_pubs": len(f["pubs"]),
        "orcid_pubs": len(obras),
        "doi_overlap": doi_overlap,
        "doi_ratio": round(doi_ratio, 2),
        "co_portal": len(co_portal),
        "co_orcid": len(co_orcid),
        "co_overlap": co_overlap,
        "co_ratio": round(co_ratio, 2),
        "recomendacion": rec,
        "portal_titulos": portal_titulos[:5],
        "orcid_titulos": [(w.get("publication_year"), w.get("title"), w.get("doi")) for w in obras[:5]],
        "co_ejemplos": sorted(set(solapan))[:8],
        "sugerencia_previa": r["sugerencia"],
    })
    print(f"  {i:>2}/{len(pendientes)} {nombre[:34]:34} {rec:10} "
          f"DOI {doi_overlap}/{len(portal_dois)} · co {co_overlap}/{len(co_portal)}", flush=True)

CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
with SALIDA_CSV.open("w", newline="", encoding="utf-8-sig") as fh:
    campos = [k for k in filas[0] if k not in ("portal_titulos", "orcid_titulos", "co_ejemplos")]
    w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
    w.writeheader()
    w.writerows(sorted(filas, key=lambda x: (x["recomendacion"], -x["co_overlap"])))

# ---------------------------------------------------------------- markdown
orden = {"añadir": 0, "probable": 1, "revisar": 2, "descartar": 3}
filas.sort(key=lambda x: (orden[x["recomendacion"]], -x["co_overlap"], -x["apoyo"]))
lineas = [
    "# Revisión ORCID · personas pendientes",
    "",
    f"Generado el 01-11-2026 · {len(filas)} personas · fuentes: portal FISABIO, OpenAlex y registro ORCID.",
    "",
    "## Resumen",
    "",
    "| Persona | ORCID | Nombre | Apoyo | DOI | Coautores | Recomendación |",
    "|---|---|---|---:|---|---:|---|",
]
for f in filas:
    lineas.append(
        f"| {f['nombre']} | {f['orcid']} | {f['nivel_nombre']} ({f['ratio_nombre']}) | "
        f"{f['apoyo']} | {f['doi_overlap']}/{f['portal_pubs']} | "
        f"{f['co_overlap']}/{f['co_portal']} | **{f['recomendacion']}** |")

for grupo in ("añadir", "probable", "revisar", "descartar"):
    subset = [f for f in filas if f["recomendacion"] == grupo]
    lineas += ["", f"## {grupo.capitalize()} ({len(subset)})", ""]
    for f in subset:
        lineas += [
            f"### {f['nombre']}",
            "",
            f"- **ORCID:** {f['orcid']}",
            f"- **Nombre ORCID:** {f['nombre_orcid']}",
            f"- **Afiliación ORCID:** {f['afiliaciones_orcid'] or '(ninguna)'}",
            f"- **Nombre:** {f['nivel_nombre']} ({f['ratio_nombre']}) · **Apoyo:** {f['apoyo']} obras OpenAlex",
            f"- **Portal:** {f['portal_pubs']} publicaciones · **ORCID/OpenAlex:** {f['orcid_pubs']} obras",
            f"- **DOI en común:** {f['doi_overlap']} ({f['doi_ratio']*100:.0f} % del portal)",
            f"- **Coautores:** {f['co_overlap']} en común de {f['co_portal']} ({f['co_ratio']*100:.0f} %)",
            f"- **Coautores en común:** {', '.join(f['co_ejemplos']) or '(ninguno)'}",
            "",
            "**Obras del portal:**",
        ]
        for anio, titulo, doi in f["portal_titulos"][:3]:
            lineas.append(f"- {anio or 's/f'} · {doi or '(sin DOI)'} · {titulo[:90] if titulo else ''}")
        lineas += ["", "**Obras del ORCID (OpenAlex):**"]
        for anio, titulo, doi in f["orcid_titulos"][:3]:
            lineas.append(f"- {anio or 's/f'} · {nd(doi) or '(sin DOI)'} · {titulo[:90] if titulo else ''}")
        lineas += ["", f"**Recomendación: {f['recomendacion']}**", ""]

SALIDA_MD.write_text("\n".join(lineas), encoding="utf-8")
print("\n=== RECOMENDACIONES ===", Counter(f["recomendacion"] for f in filas))
print(f"escrito {SALIDA_MD}")
print(f"escrito {SALIDA_CSV}")
