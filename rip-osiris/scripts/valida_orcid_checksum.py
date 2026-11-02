"""Valida el dígito de control de los ORCID de la base (ISO 7064 mod 11-2)."""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\Users\gipsy\repos\Ciencia_Abierta_Fisabio\rip-osiris")
DB = ROOT / "data" / "rip_osiris.sqlite"


def normalizar(o: str) -> str:
    o = re.sub(r"^https?://(www\.)?orcid\.org/", "", (o or "").strip()).upper()
    return o


def valido(orcid: str) -> tuple[bool, str]:
    s = orcid.replace("-", "")
    if len(s) != 16:
        return False, "longitud"
    if not re.fullmatch(r"\d{15}[\dX]", s):
        return False, "formato"
    total = 0
    for c in s[:15]:
        total = (total + int(c)) * 2
    resto = total % 11
    control = (12 - resto) % 11
    esperado = "X" if control == 10 else str(control)
    if s[15] != esperado:
        return False, f"dígito {s[15]}≠{esperado}"
    return True, ""


con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
filas = list(con.execute(
    "SELECT id, name, orcid, orcid_source FROM researchers "
    "WHERE orcid IS NOT NULL AND orcid != '' ORDER BY orcid_source, name"))
con.close()

validos = invalidos = 0
por_fuente = {}
malos = []
for r in filas:
    o = normalizar(r["orcid"])
    ok, motivo = valido(o)
    fuente = r["orcid_source"]
    por_fuente.setdefault(fuente, {"ok": 0, "mal": 0})
    if ok:
        validos += 1
        por_fuente[fuente]["ok"] += 1
    else:
        invalidos += 1
        por_fuente[fuente]["mal"] += 1
        malos.append((r["id"], r["name"], o, fuente, motivo))

print(f"ORCID totales: {len(filas)}")
print(f"  válidos:   {validos}")
print(f"  inválidos: {invalidos}")
print("\npor fuente:")
for fuente, c in sorted(por_fuente.items()):
    print(f"  {fuente:28} {c['ok']:>4} ok · {c['mal']:>2} mal")
if malos:
    print("\ninválidos:")
    for rid, nombre, o, fuente, motivo in malos:
        print(f"  {rid:>4} {nombre[:36]:36} {o:19} {fuente:28} {motivo}")
else:
    print("\nTodos los ORCID pasan el dígito de control.")
