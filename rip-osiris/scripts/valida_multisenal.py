"""Validación multiseñal de los 102 candidatos ORCID.

Señales:
  1. nombre (nombre de pila + apellidos + ratio)
  2. afiliación en el registro ORCID
  3. solapamiento entre los DOIs del portal y las obras del ORCID
  4. apoyo (nº de obras de OpenAlex con ese ORCID)
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
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
MAIL = os.environ.get("OPENALEX_MAILTO", "rip-osiris@localhost")
SALIDA = ROOT / "data" / "orcid_reverso_multisenal.csv"


def tokens(s: str) -> list[str]:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z ]", " ", s.lower())
    return [t for t in s.split() if len(t) > 1]


def normalizar_doi(valor: str | None) -> str:
    doi = (valor or "").strip().lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"^doi:\s*", "", doi)
    return doi.rstrip(" .,;)")


def normalizar_orcid(valor: str) -> str:
    return re.sub(r"^https?://(www\.)?orcid\.org/", "", (valor or "").strip()).upper()


def score_nombre(portal: str, orcid: str) -> dict:
    a, b = tokens(portal), tokens(orcid)
    if not a or not b:
        return {"ratio": 0.0, "given": False, "surname": False, "nivel": "rechazado"}
    ga, gb = set(a[:2]), set(b[:2])
    sa, sb = set(a[-2:]), set(b[-2:])
    given, surname = bool(ga & gb), bool(sa & sb)
    ratio = difflib.SequenceMatcher(None, " ".join(a), " ".join(b)).ratio()
    nivel = ("alto" if given and surname and ratio >= 0.80 else
             "medio" if given and surname and ratio >= 0.60 else
             "bajo" if given and surname else "rechazado")
    return {"ratio": round(ratio, 2), "given": given, "surname": surname, "nivel": nivel}


def get_json(url: str) -> dict | None:
    req = urllib.request.Request(url, headers={
        "User-Agent": f"rip-osiris/0.1 (mailto:{MAIL})", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.load(r)
    except Exception:
        return None


def dois_del_orcid(orcid: str) -> set[str]:
    d = get_json(f"https://pub.orcid.org/v3.0/{orcid}/works")
    out = set()
    for grupo in (d or {}).get("group") or []:
        for resumen in grupo.get("work-summary") or []:
            for ext in ((resumen.get("external-ids") or {}).get("external-id") or []):
                if (ext.get("external-id-type") or "").lower() == "doi":
                    v = normalizar_doi(ext.get("external-id-value"))
                    if v:
                        out.add(v)
    return out


# publicaciones del portal por researcher_id
portal = {}
for linea in (ROOT / "data" / "portal_publicaciones.jsonl").open(encoding="utf-8"):
    f = json.loads(linea)
    portal[f["researcher_id"]] = {
        normalizar_doi(p.get("doi"))
        for p in f["pubs"] if p.get("doi")
    }

filas = list(csv.DictReader((ROOT / "data" / "orcid_reverso_validado.csv").open(encoding="utf-8-sig")))
print(f"candidatos: {len(filas)}", flush=True)

con = __import__("sqlite3").connect(ROOT / "data" / "rip_osiris.sqlite")
con.row_factory = __import__("sqlite3").Row
orcid_owner = {}
for owner_id, owner_orcid in con.execute(
    "SELECT id, orcid FROM researchers WHERE orcid IS NOT NULL AND orcid != ''"
):
    ident = normalizar_orcid(owner_orcid)
    orcid_owner.setdefault(ident, set()).add(int(owner_id))
con.close()

salida = []
t0 = time.monotonic()
for i, r in enumerate(filas, 1):
    rid = int(r["researcher_id"])
    orcid = r["orcid_candidato"]
    sn = score_nombre(r["nombre"], r["nombre_orcid"])
    dois_orcid = dois_del_orcid(orcid)
    dois_portal = portal.get(rid, set())
    solapan = dois_portal & dois_orcid
    ratio_solape = len(solapan) / max(1, len(dois_portal))
    afiliacion = r.get("afiliacion_coincide") == "True"
    apoyo = int(r["apoyo"])

    if len(solapan) >= 2 and ratio_solape >= 0.5:
        estado = "confirmado_doi"
    elif sn["nivel"] == "alto" and afiliacion and len(solapan) >= 1:
        estado = "confirmado_nombre_afiliacion"
    elif sn["nivel"] == "alto" and (afiliacion or apoyo >= 2):
        estado = "probable"
    elif len(solapan) >= 1 and sn["nivel"] in ("alto", "medio"):
        estado = "probable"
    elif sn["nivel"] == "rechazado" and len(solapan) == 0:
        estado = "rechazado"
    else:
        estado = "revisar"

    ident = normalizar_orcid(orcid)
    propietarios = orcid_owner.get(ident, set()) - {rid}
    if propietarios and estado in ("confirmado_doi", "confirmado_nombre_afiliacion"):
        estado = "revisar"

    salida.append({
        "researcher_id": rid,
        "portal_id": r["portal_id"],
        "nombre": r["nombre"],
        "orcid": orcid,
        "nombre_orcid": r["nombre_orcid"],
        "apoyo": apoyo,
        "nivel_nombre": sn["nivel"],
        "ratio_nombre": sn["ratio"],
        "afiliacion_coincide": afiliacion,
        "n_dois_portal": len(dois_portal),
        "n_dois_orcid": len(dois_orcid),
        "n_solape": len(solapan),
        "ratio_solape": round(ratio_solape, 2),
        "ejemplos_solape": ";".join(sorted(solapan)[:3]),
        "estado_final": estado,
        "otros_propietarios_orcid": ";".join(str(x) for x in sorted(propietarios)),
    })
    if i % 20 == 0:
        print(f"  {i}/{len(filas)} · {(time.monotonic()-t0)/i:.2f} s/cand", flush=True)
    time.sleep(0.35)

# No autoasignar una identidad cuando varias candidaturas de la misma persona
# o del mismo ORCID superan el umbral; se conserva la evidencia para revisión.
por_persona = defaultdict(list)
por_orcid = defaultdict(list)
for fila in salida:
    if fila["estado_final"] in ("confirmado_doi", "confirmado_nombre_afiliacion"):
        por_persona[fila["researcher_id"]].append(fila)
        por_orcid[normalizar_orcid(fila["orcid"])].append(fila)
ambiguos = set()
for grupo in (*por_persona.values(), *por_orcid.values()):
    if len(grupo) > 1:
        ambiguos.update(id(f) for f in grupo)
for fila in salida:
    if id(fila) in ambiguos:
        fila["estado_final"] = "revisar"
        fila["motivo_revision"] = "más de un candidato supera el umbral"
    elif fila["otros_propietarios_orcid"]:
        fila["motivo_revision"] = "ORCID ya asignado a otra persona del roster"
    else:
        fila["motivo_revision"] = ""

with SALIDA.open("w", newline="", encoding="utf-8-sig") as fh:
    campos = list(salida[0].keys()) if salida else [
        "researcher_id", "portal_id", "nombre", "orcid", "nombre_orcid",
        "apoyo", "nivel_nombre", "ratio_nombre", "afiliacion_coincide",
        "n_dois_portal", "n_dois_orcid", "n_solape", "ratio_solape",
        "ejemplos_solape", "estado_final", "otros_propietarios_orcid",
        "motivo_revision",
    ]
    w = csv.DictWriter(fh, fieldnames=campos)
    w.writeheader()
    w.writerows(salida)

print("\n=== ESTADOS FINALES ===")
print(Counter(r["estado_final"] for r in salida))
for estado in ("confirmado_doi", "confirmado_nombre_afiliacion", "probable", "revisar", "rechazado"):
    print(f"\n-- {estado} --")
    for r in salida:
        if r["estado_final"] == estado:
            print(f"  {r['nombre'][:34]:34} → {r['nombre_orcid'][:28]:28} "
                  f"nombre {r['nivel_nombre']:8} solape {r['n_solape']:>2}/{r['n_dois_portal']:<2} "
                  f"apoyo {r['apoyo']:>2}  {r['orcid']}")
print(f"\nescrito {SALIDA}")
