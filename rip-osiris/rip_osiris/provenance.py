"""Acta de procedencia — el «por qué» de cada hallazgo.

Convierte una arista en algo defendible ante evaluador (CoARA/DORA).
Cada fila lleva el fragmento LITERAL, el método, la fuente y la fecha.
"""
from __future__ import annotations

import datetime
import hashlib
import json


def ahora() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _hash(acta: dict) -> str:
    canon = json.dumps(
        {k: v for k, v in acta.items() if k != "id"},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def nueva_acta(
    *,
    kind: str,
    literal: str,
    method: str,
    source: str,
    confidence: float | None = None,
    extra: dict | None = None,
) -> dict:
    acta = {
        "kind": kind,
        "literal": literal,
        "method": method,
        "source": source,
        "fetched_at": ahora(),
        "confidence": confidence,
        "extra": extra or {},
    }
    acta["id"] = _hash(acta)
    return acta
