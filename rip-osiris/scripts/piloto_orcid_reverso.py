"""Piloto de recuperación inversa de ORCID.

Para cada investigador sin ORCID con publicaciones en el portal:
  DOI -> OpenAlex -> authorships -> autores con nombre compatible -> ORCID.
Cuenta el apoyo (nº de obras) de cada ORCID candidato.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
import sys
import time
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rip_osiris.anchor.cris import PortalCris, parsear_publicaciones  # noqa: E402
from rip_osiris.config import Config  # noqa: E402

MAIL = os.environ.get("OPENALEX_MAILTO", "rip-osiris@localhost")

con = sqlite3.connect(ROOT / "data" / "rip_osiris.sqlite")
con.row_factory = sqlite3.Row
con_orcid = {
    int(f["researcher_id"])
    for f in csv.DictReader((ROOT / "data" / "cosecha_orcid.csv").open(encoding="utf-8-sig"))
    if f["orcid"]
}
gente = [dict(r) for r in con.execute(
    "SELECT id, portal_id, name, area FROM researchers ORDER BY id")]
sin = [g for g in gente if g["id"] not in con_orcid]
paso = max(1, len(sin) // 30)
muestra = sin[::paso][:30]

cfg = Config(root=ROOT)
portal = PortalCris(cfg)
RE_CONTEO = lambda pid: re.compile(
    rf'/investigadores/{pid}/publicaciones"[^>]*>Publicaciones\s*<span[^>]*>(\d+)</span>')


def norm(s: str) -> list[str]:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z ]", " ", s.lower())
    return [t for t in s.split() if len(t) > 1]


def compatible(a: str, b: str) -> bool:
    ta, tb = set(norm(a)), set(norm(b))
    if not ta or not tb:
        return False
    inter = ta & tb
    return len(inter) >= 2 and len(inter) / min(len(ta), len(tb)) >= 0.5


# 1. publicaciones por investigador
personas = []
for g in muestra:
    pid = g["portal_id"]
    try:
        perfil = portal._solicitar("GET", f"/investigadores/{pid}")
        m = RE_CONTEO(pid).search(perfil)
        declaradas = int(m.group(1)) if m else 0
    except Exception:
        declaradas = 0
    pubs = []
    if declaradas:
        datos = PortalCris._filtro(max(declaradas, 20), avanzado=("participant", str(pid), ""))
        try:
            pubs = parsear_publicaciones(portal._solicitar("POST", "/get-publications", datos))
        except Exception:
            pubs = []
    personas.append((g, pubs))
    print(f"{g['name'][:34]:34} pubs {len(pubs):>3}", flush=True)

# 2. DOIs -> OpenAlex authorships
dois = sorted({p.doi.strip().lower().replace("https://doi.org/", "")
               for _, pubs in personas for p in pubs if p.doi})
print(f"\nDOIs únicos: {len(dois)}", flush=True)
obras = {}
for i in range(0, len(dois), 50):
    lote = dois[i:i + 50]
    url = ("https://api.openalex.org/works?filter=doi:" + "|".join(lote)
           + "&select=id,doi,authorships&per-page=50" + f"&mailto={MAIL}")
    req = urllib.request.Request(url, headers={"User-Agent": f"rip-osiris/0.1 (mailto:{MAIL})"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            d = json.load(r)
        for w in d.get("results") or []:
            doi = (w.get("doi") or "").replace("https://doi.org/", "").lower()
            obras[doi] = w.get("authorships") or []
    except Exception as exc:
        print("  lote fallido:", exc, flush=True)
    time.sleep(0.15)
print(f"obras recuperadas con authorships: {len(obras)}", flush=True)

# 3. cruzar nombre -> ORCID
resumen = []
for g, pubs in personas:
    candidatos = defaultdict(list)
    for p in pubs:
        if not p.doi:
            continue
        doi = p.doi.strip().lower().replace("https://doi.org/", "")
        for a in obras.get(doi, []):
            au = a.get("author") or {}
            if au.get("orcid") and compatible(g["name"], au.get("display_name") or ""):
                candidatos[au["orcid"]].append({
                    "doi": doi, "nombre_openalex": au.get("display_name"),
                    "instituciones": [i.get("display_name") for i in (a.get("institutions") or [])],
                })
    orden = sorted(candidatos.items(), key=lambda x: -len(x[1]))
    resumen.append({
        "researcher_id": g["id"], "portal_id": g["portal_id"], "nombre": g["name"],
        "pubs": len(pubs),
        "candidatos": [{"orcid": o, "apoyo": len(v), "detalle": v[:3]} for o, v in orden],
    })
    top = orden[0] if orden else None
    print(f"  {g['name'][:32]:32} pubs {len(pubs):>3} · "
          f"{'→ ' + top[0] + f' ({len(top[1])} obras)' if top else 'sin candidato'}", flush=True)

print("\n=== RESUMEN ===")
con_cand = sum(1 for r in resumen if r["candidatos"])
conver = sum(1 for r in resumen if r["candidatos"] and r["candidatos"][0]["apoyo"] >= 2)
print(f"investigadores: {len(resumen)}")
print(f"con al menos un candidato ORCID: {con_cand} ({100*con_cand/len(resumen):.0f} %)")
print(f"con candidato convergente (≥2 obras): {conver} ({100*conver/len(resumen):.0f} %)")
print(f"sin candidato: {len(resumen)-con_cand}")

(ROOT / "data" / "piloto_orcid_reverso.json").write_text(
    json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
print("\nescrito data/piloto_orcid_reverso.json")
