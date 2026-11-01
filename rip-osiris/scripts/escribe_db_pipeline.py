"""Escritura del pipeline en la base (política conservadora).

- researchers.orcid: 589 declarados + 25 confirmados DOI + 6 nombre/afiliación limpios.
- works / work_ids / author_work: unión de la vía ORCID y la vía portal.
- Backup previo y una sola transacción.

Uso:
  python scripts/escribe_db_pipeline.py            # dry-run: cuenta y muestra
  python scripts/escribe_db_pipeline.py --write    # escribe de verdad
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import sqlite3
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\Users\gipsy\repos\Ciencia_Abierta_Fisabio\rip-osiris")
DB = ROOT / "data" / "rip_osiris.sqlite"
BACKUP = ROOT / "data" / "rip_osiris.backup-2026-11-01.sqlite"
MAIL = "gipsy93@gmail.com"
WRITE = "--write" in sys.argv

SOSPECHOSOS = {"Cristina Fernandez Martinez", "Jose Luis Rodrigo Perez", "Monica Romero Nieto"}


def nd(d):
    d = (d or "").strip().lower()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", d)


def norm_orcid(o):
    if not o:
        return None
    o = re.sub(r"^https?://(www\.)?orcid\.org/", "", o.strip())
    return o.strip() or None


# ---------------------------------------------------------------- carga
print("1. cargando investigadores y ORCID...", flush=True)
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
investigadores = {r["id"]: dict(r) for r in con.execute("SELECT id, portal_id, name FROM researchers")}
con.close()

declarado = {}
for f in csv.DictReader((ROOT / "data" / "cosecha_orcid.csv").open(encoding="utf-8-sig")):
    if f["orcid"]:
        declarado[int(f["researcher_id"])] = norm_orcid(f["orcid"])

recuperado = {}
for r in csv.DictReader((ROOT / "data" / "orcid_reverso_multisenal.csv").open(encoding="utf-8-sig")):
    if r["estado_final"] in ("confirmado_doi", "confirmado_nombre_afiliacion") \
       and r["nombre"] not in SOSPECHOSOS:
        fuente = "reverso_doi" if r["estado_final"] == "confirmado_doi" else "reverso_nombre_afiliacion"
        recuperado[int(r["researcher_id"])] = (norm_orcid(r["orcid"]), fuente)

print(f"   declarados {len(declarado)} · recuperados {len(recuperado)}", flush=True)

# ---------------------------------------------------------------- vía ORCID
print("2. cargando obras vía ORCID...", flush=True)
orcid_works = {}
orcid_pairs = set()
for linea in (ROOT / "data" / "author_work.jsonl").open(encoding="utf-8"):
    a = json.loads(linea)
    oid = (a.get("work_id") or "").rstrip("/").split("/")[-1]
    if not oid.startswith("W"):
        continue
    d = orcid_works.setdefault(oid, {
        "openalex_id": oid, "doi": None, "title": None,
        "year": a.get("year"), "type": a.get("type"),
        "researchers": set(), "portal_pub_ids": set(),
    })
    if not d["doi"] and a.get("doi"):
        d["doi"] = nd(a["doi"])
    d["researchers"].add(a["researcher_id"])
    orcid_pairs.add((a["researcher_id"], oid))
print(f"   obras ORCID {len(orcid_works)} · pares {len(orcid_pairs)}", flush=True)

# ---------------------------------------------------------------- vía portal
print("3. cargando obras del portal...", flush=True)
portal_works = {}
portal_pairs = set()
for linea in (ROOT / "data" / "portal_publicaciones.jsonl").open(encoding="utf-8"):
    f = json.loads(linea)
    for p in f["pubs"]:
        pid = p.get("pub_id")
        if not pid:
            continue
        d = portal_works.setdefault(pid, {
            "pub_id": pid, "doi": None, "title": p.get("titulo"),
            "year": p.get("anio"), "type": p.get("tipo"),
            "researchers": set(),
        })
        if not d["doi"] and p.get("doi"):
            d["doi"] = nd(p["doi"])
        if not d["title"] and p.get("titulo"):
            d["title"] = p["titulo"]
        d["researchers"].add(f["researcher_id"])
        portal_pairs.add((f["researcher_id"], pid))
print(f"   obras portal {len(portal_works)} · pares {len(portal_pairs)}", flush=True)

# ---------------------------------------------------------------- unión
print("4. uniendo por DOI...", flush=True)
union = {}            # key -> dict
by_doi = {}
by_openalex = {}
by_portal = {}

for oid, d in orcid_works.items():
    key = "doi:" + d["doi"] if d["doi"] else "openalex:" + oid
    if key in union:
        u = union[key]
        u["researchers"] |= d["researchers"]
    else:
        u = {
            "key": key, "doi": d["doi"], "title": d["title"],
            "year": d["year"], "type": d["type"],
            "openalex_id": oid, "portal_pub_ids": set(),
            "researchers": set(d["researchers"]),
        }
        union[key] = u
    by_openalex[oid] = key
    if d["doi"]:
        by_doi[d["doi"]] = key

for pid, d in portal_works.items():
    if d["doi"] and d["doi"] in by_doi:
        key = by_doi[d["doi"]]
        u = union[key]
        u["portal_pub_ids"].add(pid)
        u["researchers"] |= d["researchers"]
        if not u["title"] and d["title"]:
            u["title"] = d["title"]
        if not u["year"] and d["year"]:
            u["year"] = d["year"]
        if not u["type"] and d["type"]:
            u["type"] = d["type"]
    else:
        key = "doi:" + d["doi"] if d["doi"] else "portal:" + pid
        u = {
            "key": key, "doi": d["doi"], "title": d["title"],
            "year": d["year"], "type": d["type"],
            "openalex_id": None, "portal_pub_ids": {pid},
            "researchers": set(d["researchers"]),
        }
        union[key] = u
        if d["doi"]:
            by_doi[d["doi"]] = key
    by_portal[pid] = key

print(f"   obras únicas {len(union)} · con DOI {sum(1 for u in union.values() if u['doi'])}", flush=True)

# ---------------------------------------------------------------- títulos OpenAlex
print("5. recuperando títulos de OpenAlex...", flush=True)
sin_titulo = [u for u in union.values() if not u["title"] and u["openalex_id"]]
ids = [u["openalex_id"] for u in sin_titulo]
print(f"   obras sin título con ID OpenAlex: {len(ids)}", flush=True)
titulos = {}
for i in range(0, len(ids), 50):
    lote = ids[i:i + 50]
    url = ("https://api.openalex.org/works?filter=openalex:" + "|".join(lote)
           + "&select=id,doi,title,publication_year,type&per-page=50"
           + f"&mailto={MAIL}")
    req = urllib.request.Request(url, headers={"User-Agent": f"rip-osiris/0.1 (mailto:{MAIL})"})
    for intento in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.load(r)
            for w in data.get("results") or []:
                wid = (w.get("id") or "").rstrip("/").split("/")[-1]
                titulos[wid] = {
                    "title": w.get("title"),
                    "year": w.get("publication_year"),
                    "type": w.get("type"),
                    "doi": nd(w.get("doi")),
                }
            break
        except Exception as exc:
            if intento < 2:
                time.sleep(2 ** (intento + 1))
            else:
                print(f"   lote fallido: {exc}", flush=True)
    if (i // 50 + 1) % 50 == 0:
        print(f"   lotes {i//50+1}/{(len(ids)+49)//50} · títulos {len(titulos)}", flush=True)
    time.sleep(0.12)

for u in union.values():
    if u["openalex_id"] and u["openalex_id"] in titulos:
        t = titulos[u["openalex_id"]]
        if not u["title"]:
            u["title"] = t["title"]
        if not u["year"]:
            u["year"] = t["year"]
        if not u["type"]:
            u["type"] = t["type"]

sin_titulo_final = sum(1 for u in union.values() if not u["title"])
print(f"   títulos recuperados {len(titulos)} · obras aún sin título {sin_titulo_final}", flush=True)

# ---------------------------------------------------------------- dry-run
print("\n=== RESUMEN ===")
print(f"investigadores con ORCID a escribir: {len(declarado) + len(recuperado)} "
      f"({len(declarado)} declarados + {len(recuperado)} recuperados)")
print(f"obras a insertar: {len(union)}")
print(f"work_ids: DOI {sum(1 for u in union.values() if u['doi'])} · "
      f"OpenAlex {sum(1 for u in union.values() if u['openalex_id'])} · "
      f"portal {sum(len(u['portal_pub_ids']) for u in union.values())}")
print(f"pares ORCID {len(orcid_pairs)} · portal {len(portal_pairs)} · "
      f"unión {len(orcid_pairs) + len(portal_pairs)} (con fuente)")

if not WRITE:
    print("\nDRY-RUN. Para escribir: python scripts/escribe_db_pipeline.py --write")
    sys.exit(0)

# ---------------------------------------------------------------- backup
print("\n6. backup...", flush=True)
if BACKUP.exists():
    print(f"   ya existe {BACKUP.name}; no se sobrescribe", flush=True)
else:
    shutil.copy2(DB, BACKUP)
print(f"   backup: {BACKUP} ({BACKUP.stat().st_size:,} bytes)", flush=True)

# ---------------------------------------------------------------- escritura
print("7. escribiendo en transacción...", flush=True)
con = sqlite3.connect(DB, isolation_level=None)
con.execute("PRAGMA foreign_keys = ON")
try:
    con.execute("BEGIN IMMEDIATE")

    # ORCID
    con.executemany(
        "UPDATE researchers SET orcid=?, orcid_source='portal_ficha' "
        "WHERE id=? AND (orcid IS NULL OR orcid='')",
        [(o, rid) for rid, o in declarado.items()])
    con.executemany(
        "UPDATE researchers SET orcid=?, orcid_source=? "
        "WHERE id=? AND (orcid IS NULL OR orcid='')",
        [(o, src, rid) for rid, (o, src) in recuperado.items()])

    # works y work_ids
    id_de = {}
    for n, (key, u) in enumerate(union.items(), 1):
        title = u["title"] or "(sin título)"
        con.execute(
            "INSERT INTO works (doi, title, year, type, canonical_key) VALUES (?,?,?,?,?)",
            (u["doi"], title, u["year"], u["type"], key))
        wid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
        id_de[key] = wid
        if u["doi"]:
            con.execute("INSERT INTO work_ids (work_id, scheme, value) VALUES (?,?,?)",
                        (wid, "doi", u["doi"]))
        if u["openalex_id"]:
            con.execute("INSERT INTO work_ids (work_id, scheme, value) VALUES (?,?,?)",
                        (wid, "openalex", u["openalex_id"]))
        for pid in u["portal_pub_ids"]:
            con.execute("INSERT INTO work_ids (work_id, scheme, value) VALUES (?,?,?)",
                        (wid, "portal", pid))
        if n % 5000 == 0:
            print(f"   works {n}/{len(union)}", flush=True)

    # author_work ORCID
    filas = []
    for rid, oid in orcid_pairs:
        key = by_openalex.get(oid)
        if key and key in id_de:
            filas.append((rid, id_de[key], "orcid_exacto", 1.0))
    con.executemany(
        "INSERT OR IGNORE INTO author_work (researcher_id, work_id, source, confidence) "
        "VALUES (?,?,?,?)", filas)
    print(f"   author_work ORCID: {len(filas)}", flush=True)

    # author_work portal
    filas = []
    for rid, pid in portal_pairs:
        key = by_portal.get(pid)
        if key and key in id_de:
            u = union[key]
            source = "portal_doi" if u["doi"] else "portal_publicacion"
            conf = 0.95 if u["doi"] else 0.90
            filas.append((rid, id_de[key], source, conf))
    con.executemany(
        "INSERT OR IGNORE INTO author_work (researcher_id, work_id, source, confidence) "
        "VALUES (?,?,?,?)", filas)
    print(f"   author_work portal: {len(filas)}", flush=True)

    con.execute("COMMIT")
    print("   COMMIT OK", flush=True)
except Exception as exc:
    con.execute("ROLLBACK")
    print(f"   ROLLBACK por error: {exc}", flush=True)
    raise
finally:
    con.close()

# ---------------------------------------------------------------- verificación
print("\n8. verificación...", flush=True)
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
for sql, etiqueta in [
    ("SELECT COUNT(*) c FROM researchers WHERE orcid IS NOT NULL", "investigadores con ORCID"),
    ("SELECT COUNT(*) c FROM works", "works"),
    ("SELECT COUNT(*) c FROM work_ids", "work_ids"),
    ("SELECT COUNT(*) c FROM author_work", "author_work"),
]:
    print(f"   {etiqueta}: {con.execute(sql).fetchone()['c']:,}")
print("   integrity_check:", con.execute("PRAGMA integrity_check").fetchone()[0])
print("   foreign_key_check:", len(list(con.execute("PRAGMA foreign_key_check"))), "incidencias")
print("\n   muestra:")
for r in con.execute("""SELECT r.name, r.orcid, r.orcid_source,
                               COUNT(aw.work_id) obras, COUNT(DISTINCT aw.source) fuentes
                        FROM researchers r JOIN author_work aw ON aw.researcher_id=r.id
                        WHERE r.orcid IS NOT NULL
                        GROUP BY r.id ORDER BY obras DESC LIMIT 5"""):
    print(f"     {r['name'][:34]:34} {r['orcid']} {r['orcid_source']:24} "
          f"{r['obras']:>4} obras · {r['fuentes']} fuentes")
con.close()
print("\nFIN", flush=True)
