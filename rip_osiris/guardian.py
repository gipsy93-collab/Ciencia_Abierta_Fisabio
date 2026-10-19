"""Guardián de fidelidad (heredado de Thinkuy / protocolo S69).

Regla de oro: un hallazgo solo se acepta si el fragmento aparece
LITERALMENTE en el texto fuente (o en su variante desguionizada por los
cortes de línea del PDF). Sin literal -> se descarta y se declara.

Ubicación: top-level (no en `mentions/`) para que `corpus.store` lo use sin
depender de `mentions`. El diseño §3 lo situaba en `mentions/`; se eleva por
conveniencia de importación y `mentions` lo reexporta.
"""
from __future__ import annotations


def _ws(s: str) -> str:
    return " ".join(s.split())


def desguionizar(s: str) -> str:
    """Une palabras partidas por guion de fin de línea (PDF)."""
    return s.replace("-\r\n", "").replace("-\n", "").replace("\u00ad", "")


def contiene_literal(texto: str, fragmento: str, *, deshyphen: bool = True) -> bool:
    if not texto or not fragmento:
        return False
    frag = _ws(fragmento)
    if frag in _ws(texto):
        return True
    if deshyphen:
        if frag in _ws(desguionizar(texto)):
            return True
    return False


def exigir_literal(texto: str, fragmento: str, *, deshyphen: bool = True) -> None:
    """Lanza ValueError si el fragmento no está literalmente en el texto."""
    if not contiene_literal(texto, fragmento, deshyphen=deshyphen):
        raise ValueError(f"fragmento no literal en la fuente: {fragmento!r}")
