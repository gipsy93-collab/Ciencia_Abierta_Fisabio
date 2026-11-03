"""Refresca los metadatos EHDS de los 6 conjuntos del catálogo CKAN.

Corrige dos defectos de la primera carga:
  1. `access_rights` se quedó en 'unknown' en 3 casos porque CKAN expone el
     cierre en `isopen`, no en `access_rights`.
  2. `license` guardaba el literal «License not specified», que no es licencia.

También reclasifica `health_category_propuesta` con el patrón corregido.
No toca `health_category` (lo declarado): sigue vacío a propósito.

Uso:
    python scripts/actualiza_datasets_ckan.py            # dry-run
    python scripts/actualiza_datasets_ckan.py --write
"""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
import sys
import unicodedata
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from backup_util import siguiente_backup  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "rip_osiris.sqlite"
BASE = "https://health-dcat.fisabio.san.gva.es"
UA = {"User-Agent": "OSIRIS-research (mailto:gipsy93@gmail.com)"}

CATEGORIAS = [
    (r"\bpadchest\b|\bbimcv\b|\bcovid|x-?ray|radiogra|imagen(es)? medic|\bimaging\b|\bprostate\b|\bmri\b|resonancia|\bct\b", "Medical imaging"),
    (r"retina|retinopat|oftalm|\bdhr\b|distrofia", "Electronic health records"),
    (r"genom|sequenc|microbiom|mutano|bacteri|streptoc|pseudomon", "Genomic and molecular data"),
    (r"\bregistry\b|\bregistro\b|\bcohort", "Health data from registries"),
    (r"\btrial\b|\bensayo\b", "Clinical trial data"),
]


def get(url: str) -> dict:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in s if not unicodedata.combining(c))).strip()


def clasifica(titulo: str) -> str | None:
    t = norm(titulo)
    for patron, categoria in CATEGORIAS:
        if re.search(patron, t):
            return categoria
    return None


def acceso(d: dict) -> str:
    """Solo `access_rights` es declaración. `isopen` no sirve: es False en los 6.

    Y vacío NO es abierto: es «sin declarar». La web del catálogo lo pinta como
    «Abierto» por defecto, lo que en datos de salud es un default engañoso.
    """
    v = (d.get("access_rights") or "").strip().lower()
    if v == "public":
        return "public"
    if v == "restricted":
        return "restricted"
    if v in ("non-public", "non_public"):
        return "non_public"
    return "unknown"


def main(write: bool) -> None:
    ids = get(BASE + "/api/3/action/package_list")["result"]
    cambios = []
    for i in ids:
        p = get(f"{BASE}/api/3/action/package_show?id={i}")["result"]
        lic = (p.get("license_title") or p.get("license_id") or "").strip()
        lic = None if lic.lower() in ("license not specified", "notspecified", "") else lic
        cambios.append({
            "pid": f"ckan:{i}",
            "access_rights": acceso(p),
            "license": lic,
            "holder": (p.get("organization") or {}).get("title"),
            "nota": "CKAN: licencia no especificada" if lic is None else None,
        })

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    print(f"{'pid':28} {'acceso':12} licencia            tenedor")
    for c in cambios:
        print(f"{c['pid']:28} {c['access_rights']:12} {str(c['license']):18} {c['holder']}")

    # Reclasificación de todos los registros
    reclasificados = []
    for r in con.execute("SELECT id, title, health_category_propuesta FROM datasets"):
        nueva = clasifica(r["title"])
        if nueva != r["health_category_propuesta"]:
            reclasificados.append((nueva, r["id"], r["health_category_propuesta"], r["title"]))
    print(f"\nreclasificaciones de categoría propuesta: {len(reclasificados)}")
    for nueva, _, vieja, titulo in reclasificados[:6]:
        print(f"  {str(vieja):28} → {str(nueva):28} {titulo[:40]}")

    if not write:
        print("\nDRY-RUN. Para escribir: python scripts/actualiza_datasets_ckan.py --write")
        con.close()
        return

    backup = siguiente_backup(DB)
    shutil.copy2(DB, backup)
    print(f"\nbackup: {backup.name}")

    try:
        con.execute("BEGIN IMMEDIATE")
        for c in cambios:
            con.execute(
                """UPDATE datasets SET access_rights=?, license=?, holder=?,
                   notes = CASE WHEN ? IS NULL THEN notes ELSE ? END
                   WHERE pid=?""",
                (c["access_rights"], c["license"], c["holder"],
                 c["nota"], c["nota"], c["pid"]))
        for nueva, rid, _, _ in reclasificados:
            con.execute("UPDATE datasets SET health_category_propuesta=? WHERE id=?", (nueva, rid))
        con.execute("COMMIT")
    except Exception as exc:  # noqa: BLE001
        con.execute("ROLLBACK")
        print(f"ERROR, rollback: {exc}")
        raise

    print("por acceso:")
    for r in con.execute("SELECT access_rights, COUNT(*) n FROM datasets GROUP BY access_rights"):
        print(f"  {str(r['access_rights']):12} {r['n']}")
    print("con licencia declarada:", con.execute(
        "SELECT COUNT(*) FROM datasets WHERE license IS NOT NULL").fetchone()[0])
    print("integridad:", con.execute("PRAGMA integrity_check").fetchone()[0])
    con.close()


if __name__ == "__main__":
    main(write="--write" in sys.argv[1:])
