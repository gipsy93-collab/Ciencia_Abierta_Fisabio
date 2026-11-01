"""Pipeline completo: portal -> publicaciones -> DOI -> OpenAlex -> ORCID inverso.

Etapas:
  1. Cosechar publicaciones de cada investigador (resumible, JSONL).
  2. Enlazar DOI -> obra OpenAlex + authorships.
  3. Recuperar ORCID inverso (convergencia >= 2 obras).
  4. Validar candidatos contra el registro ORCID.

No escribe en la base: deja artefactos en data/ para revisión.
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
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rip_osiris.anchor.cris import PortalCris, parsear_publicaciones  # noqa: E402
from rip_osiris.config import Config  # noqa: E402

MAIL = os.environ.get("OPENALEX_MAILTO", "rip-osiris@localhost")
PUB_JSONL = ROOT / "data" / "portal_publicaciones.jsonl"
DOI_JSON = ROOT / "data" / "portal_doi_openalex.json"
REVERSO_CSV = ROOT / "data" / "orcid_reverso_candidatos.csv"
VALIDADO_CSV = ROOT / "data" / "orcid_reverso_validado.csv"

cfg = Config(root=ROOT)
portal = PortalCris(cfg)


def norm_tokens(s: str) -> list[str]:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z ]", " ", s.lower())
    return [t for t in s.split() if len(t) > 1]


def compatible(a: str, b: str) -> bool:
    ta, tb = set(norm_tokens(a)), set(norm_tokens(b))
    if not ta or not tb:
        return False
    inter = ta & tb
    return len(inter) >= 2 and len(inter) / min(len(ta), len(tb)) >= 0.5


# Variantes Valenciano/Castellano y formas abreviadas que aparecen en ORCID.
ALIASES_ORG = {
    "elx": "elche",
    "doctor": "dr",
    "sant": "san",
    "joan": "juan",
    "alcoi": "alcoy",
    "castello": "castellon",
    "sagunt": "sagunto",
    "universitari": "universitario",
    "universitaria": "universitario",
    "transfusiones": "transfusion",
    "transfusio": "transfusion",
    "investigacio": "investigacion",
    "comunitat": "comunidad",
}

GENERICOS_ORG = {
    "hospital", "general", "universitario", "de", "del", "la", "el",
    "los", "las", "centro", "atencion", "primaria", "salud", "publica",
    "servicio", "clinica", "comarcal", "virgen", "doctor", "dr",
    "fundacion", "fomento", "investigacion", "sanitaria", "biomedica",
    "comunitat", "comunidad", "valenciana", "valencia",
}


def normalizar_org(nombre: str) -> list[str]:
    return [ALIASES_ORG.get(t, t) for t in norm_tokens(nombre)]


def _raiz(token: str) -> str:
    return token[:6] if len(token) >= 6 else token


def _coincide_token(a: str, b: str) -> bool:
    if a == b:
        return True
    ra, rb = _raiz(a), _raiz(b)
    return len(ra) >= 4 and ra == rb


def afiliacion_fisabio(afiliaciones: list[str], centros: set[str]) -> str | None:
    """Acepta FISABIO explícito o el centro del portal, con alias y raíces.

    No acepta «hospital» por sí solo: exige al menos un token distintivo
    (ciudad, apellido o nombre propio del centro) y una palabra de salud.
    """
    for afiliacion in afiliaciones:
        tokens_af = set(normalizar_org(afiliacion))
        if "fisabio" in tokens_af or (
            "fomento" in tokens_af
            and "investigacion" in tokens_af
            and "sanitaria" in tokens_af
        ):
            return afiliacion
        norm_af = " ".join(normalizar_org(afiliacion))
        for centro in centros:
            tokens_ce = set(normalizar_org(centro))
            if not tokens_ce:
                continue
            norm_ce = " ".join(normalizar_org(centro))
            corto, largo = ((norm_af, norm_ce) if len(tokens_af) <= len(tokens_ce)
                            else (norm_ce, norm_af))
            if corto and corto in largo and len(corto.split()) >= 3:
                return afiliacion
            distintivos = tokens_ce - GENERICOS_ORG
            if (
                any(_coincide_token(d, t) for d in distintivos for t in tokens_af)
                and tokens_af & {"hospital", "centro", "salud", "clinica", "universitario"}
            ):
                return afiliacion
    return None


def get_json(url: str, intentos: int = 3) -> dict | None:
    for i in range(intentos):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": f"rip-osiris/0.1 (mailto:{MAIL})",
                              "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except Exception as exc:
            if i < intentos - 1:
                time.sleep(2 ** (i + 1))
                continue
            print(f"   fallo: {exc} · {url[:100]}", flush=True)
            return None
    return None


# ------------------------------------------------------------------ etapa 1
def etapa1():
    con = sqlite3.connect(ROOT / "data" / "rip_osiris.sqlite")
    con.row_factory = sqlite3.Row
    gente = [dict(r) for r in con.execute(
        "SELECT id, portal_id, name FROM researchers ORDER BY id")]
    hechos = set()
    if PUB_JSONL.exists():
        for linea in PUB_JSONL.open(encoding="utf-8"):
            try:
                fila = json.loads(linea)
                # Las filas históricas vacías tras un fallo no cuentan como
                # cosechadas: se vuelven a intentar en la siguiente ejecución.
                if fila.get("completa") is False or (
                    int(fila.get("declaradas") or 0) > 0 and not fila.get("pubs")
                ):
                    continue
                hechos.add(fila["researcher_id"])
            except Exception:
                pass
    pendientes = [g for g in gente if g["id"] not in hechos]
    print(f"[1] roster {len(gente)} · hechos {len(hechos)} · pendientes {len(pendientes)}", flush=True)

    re_conteo = lambda pid: re.compile(
        rf'/investigadores/{pid}/publicaciones"[^>]*>Publicaciones\s*<span[^>]*>(\d+)</span>')

    fh = PUB_JSONL.open("a", encoding="utf-8")
    t0 = time.monotonic()
    errores = 0
    for i, g in enumerate(pendientes, 1):
        pid = g["portal_id"]
        try:
            perfil = portal._solicitar("GET", f"/investigadores/{pid}")
            m = re_conteo(pid).search(perfil)
            if m:
                declaradas = int(m.group(1))
            elif f'/investigadores/{pid}/publicaciones"' in perfil:
                # Perfil legítimo sin publicaciones: el portal muestra el
                # enlace «Publicaciones» pero no el contador.
                declaradas = 0
            else:
                raise ValueError("ficha sin sección de publicaciones")
            errores = 0
        except Exception as exc:
            print(f"   ERROR perfil {g['name'][:30]}: {exc}", flush=True)
            errores += 1
            if errores >= 8:
                print("[1] aborto por errores seguidos", flush=True)
                break
            continue

        pubs = []
        if declaradas:
            datos = PortalCris._filtro(
                min(max(declaradas, 20), 2000),
                avanzado=("participant", str(pid), ""))
            try:
                html = portal._solicitar("POST", "/get-publications", datos)
                pubs = parsear_publicaciones(html)
                if not pubs:
                    raise ValueError("la lista declaró publicaciones, pero el parser no encontró ninguna")
                if len(pubs) < declaradas:
                    raise ValueError(
                        f"parser incompleto: {len(pubs)} de {declaradas} publicaciones declaradas"
                    )
                errores = 0
            except Exception as exc:
                print(f"   ERROR pubs {g['name'][:30]}: {exc}", flush=True)
                errores += 1
                if errores >= 8:
                    print("[1] aborto por errores seguidos", flush=True)
                    break
                # No se escribe una fila incompleta como si fueran cero obras.
                continue

        fila = {
            "researcher_id": g["id"],
            "portal_id": pid,
            "nombre": g["name"],
            "declaradas": declaradas,
            "pubs": [{
                "pub_id": p.pub_id, "titulo": p.titulo, "doi": p.doi,
                "tipo": p.tipo, "anio": p.anio, "autores": p.autores,
                "autores_ids": p.autores_ids,
            } for p in pubs],
        }
        fh.write(json.dumps(fila, ensure_ascii=False) + "\n")
        fh.flush()
        if i % 25 == 0 or i == len(pendientes):
            ritmo = (time.monotonic() - t0) / i
            falta = (len(pendientes) - i) * ritmo
            print(f"   {i:>4}/{len(pendientes)}  {ritmo:.2f} s/inv  faltan {falta/60:.0f} min  "
                  f"| {g['name'][:32]}", flush=True)
    fh.close()


# ------------------------------------------------------------------ etapa 2
def etapa2():
    if not PUB_JSONL.exists():
        print("[2] falta", PUB_JSONL)
        return
    dois = set()
    for linea in PUB_JSONL.open(encoding="utf-8"):
        fila = json.loads(linea)
        for p in fila["pubs"]:
            if p.get("doi"):
                d = p["doi"].strip().lower()
                d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
                dois.add(d)
    dois = sorted(dois)
    print(f"[2] DOIs únicos: {len(dois)}", flush=True)

    salida = {}
    if DOI_JSON.exists():
        try:
            salida = json.loads(DOI_JSON.read_text(encoding="utf-8"))
        except Exception:
            salida = {}
    pendientes = [d for d in dois if d not in salida]
    print(f"[2] ya resueltos: {len(salida)} · pendientes: {len(pendientes)}", flush=True)

    for i in range(0, len(pendientes), 50):
        lote = pendientes[i:i + 50]
        url = ("https://api.openalex.org/works?filter=doi:" + "|".join(lote)
               + "&select=id,doi,authorships&per-page=50" + f"&mailto={MAIL}")
        d = get_json(url)
        if not d:
            continue
        for w in d.get("results") or []:
            doi = (w.get("doi") or "").replace("https://doi.org/", "").lower()
            salida[doi] = {
                "openalex_id": w.get("id"),
                "authorships": [{
                    "name": (a.get("author") or {}).get("display_name"),
                    "orcid": (a.get("author") or {}).get("orcid"),
                    "institutions": [x.get("display_name") for x in (a.get("institutions") or [])],
                } for a in (w.get("authorships") or [])],
            }
        DOI_JSON.write_text(json.dumps(salida, ensure_ascii=False), encoding="utf-8")
        if (i // 50 + 1) % 10 == 0:
            print(f"   lotes {i//50+1}/{(len(pendientes)+49)//50} · resueltos {len(salida)}", flush=True)
        time.sleep(0.12)
    print(f"[2] total resueltos: {len(salida)}", flush=True)


# ------------------------------------------------------------------ etapa 3
def etapa3():
    if not PUB_JSONL.exists() or not DOI_JSON.exists():
        print("[3] faltan artefactos")
        return
    obras = json.loads(DOI_JSON.read_text(encoding="utf-8"))
    filas = [json.loads(l) for l in PUB_JSONL.open(encoding="utf-8")]
    con_orcid = {
        int(f["researcher_id"])
        for f in csv.DictReader((ROOT / "data" / "cosecha_orcid.csv").open(encoding="utf-8-sig"))
        if f["orcid"]
    }

    salida = []
    for f in filas:
        if f["researcher_id"] in con_orcid:
            continue
        candidatos = defaultdict(list)
        for p in f["pubs"]:
            doi = (p.get("doi") or "").strip().lower()
            doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
            if not doi or doi not in obras:
                continue
            for a in obras[doi]["authorships"]:
                if a.get("orcid") and compatible(f["nombre"], a.get("name") or ""):
                    candidatos[a["orcid"]].append({
                        "doi": doi,
                        "openalex": obras[doi]["openalex_id"],
                        "nombre_openalex": a.get("name"),
                        "instituciones": a.get("institutions"),
                    })
        orden = sorted(candidatos.items(), key=lambda x: -len(x[1]))
        for orcid, ev in orden:
            salida.append({
                "researcher_id": f["researcher_id"],
                "portal_id": f["portal_id"],
                "nombre": f["nombre"],
                "n_pubs_portal": len(f["pubs"]),
                "orcid_candidato": orcid.replace("https://orcid.org/", ""),
                "apoyo": len(ev),
                "evidencia": json.dumps(ev[:5], ensure_ascii=False),
            })
    campos = ["researcher_id", "portal_id", "nombre", "n_pubs_portal",
              "orcid_candidato", "apoyo", "evidencia"]
    with REVERSO_CSV.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(salida)
    unicos = len({r["researcher_id"] for r in salida})
    convergentes = len({r["researcher_id"] for r in salida if r["apoyo"] >= 2})
    print(f"[3] candidatos: {len(salida)} · investigadores con candidato: {unicos} · "
          f"convergentes (>=2 obras): {convergentes}", flush=True)


# ------------------------------------------------------------------ etapa 4
def etapa4():
    if not REVERSO_CSV.exists():
        print("[4] falta", REVERSO_CSV)
        return
    filas = list(csv.DictReader(REVERSO_CSV.open(encoding="utf-8-sig")))
    # Validar todos los candidatos. Elegir el máximo de apoyo antes de mirar
    # DOI y afiliación descarta alternativas y resuelve empates arbitrariamente.
    por_persona = defaultdict(list)
    for r in filas:
        por_persona[int(r["researcher_id"])].append(r)

    con = sqlite3.connect(ROOT / "data" / "rip_osiris.sqlite")
    centros = defaultdict(set)
    for rid, nombre in con.execute(
        """SELECT ra.researcher_id, o.name FROM researcher_affiliations ra
           JOIN orgs o ON o.id=ra.org_id WHERE ra.affiliation_type='centro'"""
    ):
        centros[int(rid)].add(nombre)
    con.close()

    salida = []
    cache_orcid = {}
    for i, r in enumerate(filas, 1):
        orcid = r["orcid_candidato"]
        if orcid not in cache_orcid:
            cache_orcid[orcid] = (
                get_json(f"https://pub.orcid.org/v3.0/{orcid}/person"),
                get_json(f"https://pub.orcid.org/v3.0/{orcid}/employments"),
            )
        person, emp = cache_orcid[orcid]
        nombre_orcid = ""
        afiliaciones = []
        if person:
            n = person.get("name") or {}
            nombre_orcid = " ".join(x for x in [
                ((n.get("given-names") or {}).get("value") or ""),
                ((n.get("family-name") or {}).get("value") or ""),
            ] if x)
        if emp:
            for g in emp.get("affiliation-group") or []:
                for s in g.get("summaries") or []:
                    e = s.get("employment-summary") or {}
                    org = (e.get("organization") or {}).get("name")
                    if org:
                        afiliaciones.append(org)
        nombre_ok = compatible(r["nombre"], nombre_orcid) if nombre_orcid else False
        centro_persona = centros.get(int(r["researcher_id"]), set())
        afiliacion_match = afiliacion_fisabio(afiliaciones, centro_persona)
        afiliacion_ok = afiliacion_match is not None
        n_candidatos = len(por_persona[int(r["researcher_id"])])
        estado = ("validado" if nombre_ok and afiliacion_ok else
                  "nombre_coincide" if nombre_ok else
                  "afiliacion_coincide" if afiliacion_ok else "sin_validar")
        salida.append({
            **r,
            "nombre_orcid": nombre_orcid,
            "afiliaciones_orcid": " | ".join(sorted(set(afiliaciones)))[:300],
            "centros_portal": " | ".join(sorted(centro_persona)),
            "afiliacion_match": afiliacion_match or "",
            "nombre_coincide": nombre_ok,
            "afiliacion_coincide": afiliacion_ok,
            "n_candidatos": n_candidatos,
            "estado": estado,
        })
        if i % 25 == 0:
            print(f"   {i}/{len(filas)} validados", flush=True)
        time.sleep(0.3)

    campos = list(salida[0].keys()) if salida else []
    with VALIDADO_CSV.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(salida)
    from collections import Counter
    print(f"[4] candidatos evaluados: {len(salida)} · personas: {len(por_persona)}", flush=True)
    print("[4] estados:", Counter(r["estado"] for r in salida), flush=True)


if __name__ == "__main__":
    etapa = sys.argv[1] if len(sys.argv) > 1 else "all"
    if etapa in ("1", "all"):
        etapa1()
    if etapa in ("2", "all"):
        etapa2()
    if etapa in ("3", "all"):
        etapa3()
    if etapa in ("4", "all"):
        etapa4()
    print("FIN", flush=True)
