"""Re-parsea las respuestas cacheadas de get-publications y completa año/tipo.

No hace peticiones: reconstruye la clave de caché de cada investigador y lee
el `.frag` correspondiente. Actualiza `data/portal_publicaciones.jsonl`.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\Users\gipsy\repos\Ciencia_Acabierta_Fisabio\rip-osiris") if False else Path(
    r"C:\Users\gipsy\repos\Ciencia_Abierta_Fisabio\rip-osiris")
sys.path.insert(0, str(ROOT))

from rip_osiris.anchor.cris import PortalCris, parsear_publicaciones  # noqa: E402
from rip_osiris.config import Config  # noqa: E402

ENTRADA = ROOT / "data" / "portal_publicaciones.jsonl"
BACKUP = ROOT / "data" / "portal_publicaciones.backup-2026-11-02.jsonl"
CACHE = ROOT / "data" / "portal"
cfg = Config(root=ROOT)

filas = [json.loads(l) for l in ENTRADA.open(encoding="utf-8")]
if not BACKUP.exists():
    shutil.copy2(ENTRADA, BACKUP)
    print(f"backup: {BACKUP.name}")

antes_anio = sum(1 for f in filas for p in f["pubs"] if p.get("anio"))
antes_tipo = sum(1 for f in filas for p in f["pubs"] if p.get("tipo"))

sin_cache = 0
nuevos_anio = 0
nuevos_tipo = 0
for f in filas:
    datos = PortalCris._filtro(
        min(max(f["declaradas"], 20), 2000),
        avanzado=("participant", str(f["portal_id"]), ""))
    url = f"{cfg.portal_base}/get-publications"
    clave = hashlib.sha256(
        f"POST {url} {sorted(datos.items())}".encode("utf-8")).hexdigest()[:32]
    cache_file = CACHE / f"{clave}.frag"
    if not cache_file.exists():
        sin_cache += 1
        continue
    html = cache_file.read_text(encoding="utf-8", errors="replace")
    nuevas = {p.pub_id: p for p in parsear_publicaciones(html)}
    for p in f["pubs"]:
        n = nuevas.get(p["pub_id"])
        if not n:
            continue
        if not p.get("anio") and n.anio:
            p["anio"] = n.anio
            nuevos_anio += 1
        if not p.get("tipo") and n.tipo:
            p["tipo"] = n.tipo
            nuevos_tipo += 1
        if not p.get("doi") and n.doi:
            p["doi"] = n.doi
        if not p.get("autores") and n.autores:
            p["autores"] = n.autores
        if not p.get("autores_ids") and n.autores_ids:
            p["autores_ids"] = n.autores_ids

despues_anio = sum(1 for f in filas for p in f["pubs"] if p.get("anio"))
despues_tipo = sum(1 for f in filas for p in f["pubs"] if p.get("tipo"))

with ENTRADA.open("w", encoding="utf-8") as fh:
    for f in filas:
        fh.write(json.dumps(f, ensure_ascii=False) + "\n")

print(f"investigadores: {len(filas)} · sin caché: {sin_cache}")
print(f"con año:   {antes_anio} → {despues_anio}  (+{nuevos_anio})")
print(f"con tipo:  {antes_tipo} → {despues_tipo}  (+{nuevos_tipo})")
print(f"escrito {ENTRADA}")
