"""Utilidades de escritura segura sobre la base RIP-OSIRIS."""
from __future__ import annotations

from datetime import date
from pathlib import Path


def siguiente_backup(db: Path) -> Path:
    """Primer nombre de backup libre para hoy: ...-AAAA-MM-DD[-b|-c...].sqlite."""
    hoy = date.today().isoformat()
    base = db.parent / f"rip_osiris.backup-{hoy}.sqlite"
    if not base.exists():
        return base
    for letra in "bcdefghijklmnopqrstuvwxyz":
        cand = db.parent / f"rip_osiris.backup-{hoy}-{letra}.sqlite"
        if not cand.exists():
            return cand
    raise SystemExit("no queda hueco de backup para hoy")
