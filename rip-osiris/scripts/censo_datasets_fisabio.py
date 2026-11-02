"""Censo de datasets de FISABIO: dos vías independientes (afiliación y ORCID).

Fuentes:
  A. DataCite   - registro autoritativo de DOI de dataset (afiliación + ORCID)
  B. Zenodo     - repositorio (afiliación + ORCID); sus DOI son de DataCite
  C. OpenAlex   - institución, type=dataset
  D. CKAN       - catálogo institucional DCAT
  E. Figshare   - búsqueda libre, filtrada a dataset

Salida: data/censo_datasets_fisabio.csv + resumen por fuente y solapamiento.
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\gipsy\repos\Ciencia_Abierta_Fisabio\rip-osiris")
DB = ROOT / "data" / "rip_osiris.sqlite"
SALIDA = ROOT / "data" / "censo_datasets_fisabio.csv"
UA = {"User-Agent": "OSIRIS-research (mailto:gipsy93@gmail.com)"}

AFILIACIONES = [
    "FISABIO",
    "Fundación para el Fomento de la Investigación Sanitaria y Biomédica",
    "FISABIO-Salud Pública",
    "Fundación FISABIO",
]


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


def nd(d: str | None) -> str:
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", (d or "").strip().lower())


def norm_text(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in s if not unicodedata.combining(c))).strip()


registros: dict[str, dict] = {}
sin_doi: list[dict] = []


def add(doi, titulo, anio, tipo, fuente, detalle="", url="", licencia="", acceso=""):
    clave = nd(doi)
    if clave:
        r = registros.get(clave)
        if r:
            if fuente not in r["fuentes"].split("|"):
                r["fuentes"] += "|" + fuente
            return r
        r = {"doi": clave, "titulo": titulo, "anio": anio, "tipo": tipo,
             "fuentes": fuente, "detalle": detalle, "url": url,
             "licencia": licencia, "acceso": acceso}
        registros[clave] = r
        return r
    sin_doi.append({"doi": "", "titulo": titulo, "anio": anio, "tipo": tipo,
                    "fuentes": fuente, "detalle": detalle, "url": url,
                    "licencia": licencia, "acceso": acceso})
    return None


# ---------- A. DataCite por afiliación ----------
print("A. DataCite por afiliación…")
for af in AFILIACIONES:
    try:
        d = get("https://api.datacite.org/dois?" + urllib.parse.urlencode({
            "query": f'creators.affiliation.name:"{af}"', "page[size]": 1000}))
    except Exception as e:  # noqa: BLE001
        print(f"   {af}: ERROR {e}")
        continue
    print(f"   {af}: {d['meta']['total']} registros")
    for x in d["data"]:
        a = x["attributes"]
        tipo = a["types"]["resourceTypeGeneral"]
        if tipo != "Dataset":
            continue
        titulo = (a["titles"][0]["title"] if a.get("titles") else "")
        add(a["doi"], titulo, a.get("publicationYear"), tipo, "datacite_afiliacion",
            af, a.get("url", ""), a.get("rightsList") and (a["rightsList"][0].get("rights") or "") or "",
            "")

# ---------- B. DataCite por ORCID ----------
print("B. DataCite por ORCID (669)…")
con = sqlite3.connect(DB)
orcid_list = [r[0].strip().upper() for r in con.execute(
    "SELECT orcid FROM researchers WHERE orcid IS NOT NULL AND orcid!=''")]
con.close()
print(f"   ORCID a consultar: {len(orcid_list)}")

lote = 25
for i in range(0, len(orcid_list), lote):
    grupo = orcid_list[i:i + lote]
    q = "creators.nameIdentifiers.nameIdentifier:(" + " OR ".join(f'"{o}"' for o in grupo) + ")"
    try:
        d = get("https://api.datacite.org/dois?" + urllib.parse.urlencode(
            {"query": q, "page[size]": 1000}))
    except Exception as e:  # noqa: BLE001
        print(f"   lote {i//lote}: ERROR {e}")
        continue
    for x in d["data"]:
        a = x["attributes"]
        if a["types"]["resourceTypeGeneral"] not in ("Dataset", "Software"):
            continue
        titulo = (a["titles"][0]["title"] if a.get("titles") else "")
        add(a["doi"], titulo, a.get("publicationYear"),
            a["types"]["resourceTypeGeneral"], "datacite_orcid", "", a.get("url", ""))
    if i % 250 == 0:
        print(f"   …{i + len(grupo)}/{len(orcid_list)}")
print(f"   acumulado: {len(registros)} DOI")

# ---------- C. Zenodo ----------
print("C. Zenodo (afiliación + ORCID)…")
fallidos: list[tuple[str, str]] = []


def zenodo(q: str, etiqueta: str):
    page = 1
    total = None
    while True:
        time.sleep(1.2)
        try:
            d = get("https://zenodo.org/api/records?" + urllib.parse.urlencode(
                {"q": q, "size": 25, "page": page}), intentos=5)
        except Exception as e:  # noqa: BLE001
            print(f"   {etiqueta} p{page}: ERROR {e}")
            fallidos.append((q, etiqueta))
            return
        total = d["hits"]["total"]
        for h in d["hits"]["hits"]:
            m = h["metadata"]
            tipo = (m.get("resource_type") or {}).get("type", "")
            if tipo not in ("dataset", "software"):
                continue
            doi = m.get("doi") or ""
            add(doi, m.get("title", ""), (m.get("publication_date") or "")[:4], tipo,
                "zenodo", etiqueta, h.get("links", {}).get("self_html", ""),
                (m.get("license") or {}).get("id", "") if isinstance(m.get("license"), dict) else "")
        if page * 25 >= total or page >= 40:
            break
        page += 1
    print(f"   {etiqueta}: {total} registros")


for af in AFILIACIONES:
    zenodo(f'creators.affiliation:"{af}"', f"afiliacion:{af}")

for i in range(0, len(orcid_list), 25):
    grupo = orcid_list[i:i + 25]
    q = "creators.orcid:(" + " OR ".join(f'"{o}"' for o in grupo) + ")"
    zenodo(q, f"orcid:lote{i//25}")

# Reintento de los lotes que cayeron por límite de tasa
if fallidos:
    print(f"   reintentando {len(fallidos)} consultas fallidas…")
    pendientes = fallidos[:]
    fallidos.clear()
    for q, etiqueta in pendientes:
        time.sleep(5)
        zenodo(q, etiqueta)
print(f"   acumulado: {len(registros)} DOI")

# ---------- D. OpenAlex ----------
print("D. OpenAlex institución…")
INST = "I4210097149"
for tipo in ("dataset", "software"):
    try:
        d = get("https://api.openalex.org/works?" + urllib.parse.urlencode({
            "filter": f"authorships.institutions.id:{INST},type:{tipo}",
            "per-page": 200, "select": "doi,title,publication_year,type"}))
    except Exception as e:  # noqa: BLE001
        print(f"   {tipo}: ERROR {e}")
        continue
    print(f"   {tipo}: {d['meta']['count']}")
    for w in d["results"]:
        add(w.get("doi"), w.get("title"), w.get("publication_year"), tipo,
            "openalex_institucion", INST, w.get("id", ""))

# ---------- E. CKAN ----------
print("E. CKAN institucional…")
BASE = "https://health-dcat.fisabio.san.gva.es"
try:
    ids = get(BASE + "/api/3/action/package_list")["result"]
    for i in ids:
        p = get(f"{BASE}/api/3/action/package_show?id={i}")["result"]
        add("", p.get("title"), (p.get("metadata_modified") or "")[:4], "dataset",
            "ckan_fisabio", (p.get("organization") or {}).get("title", ""),
            f"{BASE}/dataset/{i}", p.get("license_title") or "no especificada",
            str(p.get("access_rights")))
    print(f"   {len(ids)} datasets")
except Exception as e:  # noqa: BLE001
    print(f"   ERROR {e}")

# ---------- F. Figshare ----------
print("F. Figshare…")
try:
    req = urllib.request.Request(
        "https://api.figshare.com/v2/articles/search",
        data=json.dumps({"search_for": "FISABIO", "page_size": 100}).encode(),
        headers={**UA, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.loads(r.read().decode("utf-8"))
    n = 0
    for x in d:
        if x.get("defined_type_name") == "dataset":
            add(x.get("doi"), x.get("title"), (x.get("published_date") or "")[:4],
                "dataset", "figshare", "", x.get("url_public_html", ""))
            n += 1
    print(f"   {len(d)} resultados · {n} datasets")
except Exception as e:  # noqa: BLE001
    print(f"   ERROR {e}")

# ---------- Salida ----------
filas = list(registros.values()) + sin_doi
filas.sort(key=lambda r: (str(r["anio"] or ""), str(r["titulo"] or "")), reverse=True)
with SALIDA.open("w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=["doi", "titulo", "anio", "tipo", "fuentes",
                                       "detalle", "url", "licencia", "acceso"])
    w.writeheader()
    w.writerows(filas)

print("\n=== RESUMEN ===")
print(f"registros con DOI (únicos): {len(registros)}")
print(f"registros sin DOI: {len(sin_doi)}")
print("\npor fuente (un registro puede estar en varias):")
for k, v in Counter(f for r in filas for f in r["fuentes"].split("|")).most_common():
    print(f"  {k:24} {v}")
print("\npor tipo:")
for k, v in Counter(r["tipo"] for r in filas).most_common():
    print(f"  {k:16} {v}")
print("\nsolapamiento entre fuentes:")
multi = [r for r in filas if "|" in r["fuentes"]]
print(f"  registros en >1 fuente: {len(multi)}")
print("\npor año:")
for k, v in sorted(Counter(str(r["anio"]) for r in filas).items(), reverse=True)[:12]:
    print(f"  {k}: {v}")
print(f"\nescrito {SALIDA}")
