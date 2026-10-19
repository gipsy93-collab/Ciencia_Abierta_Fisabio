"""Configuración de RIP-OSIRIS.

Todos los umbrales y las rutas viven aquí (diseño D1/D5/D7).
Nada de constantes dispersas por el código.
"""
from __future__ import annotations

import os
import pathlib
from dataclasses import dataclass, field


def _raiz_por_defecto() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[1]


@dataclass
class Config:
    """Parámetros operativos. Los umbrales se documentan en el diseño §2 y §5."""

    root: pathlib.Path = field(default_factory=_raiz_por_defecto)
    db_path: pathlib.Path | None = None
    corpus_dir: pathlib.Path | None = None
    pdf_dir: pathlib.Path | None = None

    # --- Crossref ---
    crossref_mailto: str = "rip-osiris@localhost"
    user_agent: str = "rip-osiris/0.1 (+mailto:rip-osiris@localhost)"

    # --- matcher in-corpus (rama c = LA CASCADA) ---
    match_min_score: float = 0.60
    match_min_title_tokens: float = 0.70
    require_org_and_year: bool = True

    # --- resolución de referencias (confianza por rama) ---
    conf_doi_inline: float = 1.00
    conf_doi_inline_sin_verificar: float = 0.80
    conf_crossref_query: float = 0.95

    # --- grafo ---
    max_hops: int = 3

    # --- red ---
    rate_limit_s: float = 1.0
    http_timeout_s: float = 30.0

    # --- respeto legal (robots / RISP / art. 67 LPI) ---
    respetar_robots: bool = True
    domain_whitelist: tuple[str, ...] = (
        "boe.es",
        "dogv.gva.es",
        "eur-lex.europa.eu",
        "dadesobertes.gva.es",
        "san.gva.es",
        "who.int",
        "paho.org",
    )

    def __post_init__(self) -> None:
        self.root = pathlib.Path(self.root)
        if self.db_path is None:
            self.db_path = self.root / "data" / "rip_osiris.sqlite"
        if self.corpus_dir is None:
            self.corpus_dir = self.root / "data" / "corpus"
        if self.pdf_dir is None:
            self.pdf_dir = self.root / "data" / "pdf"

    @classmethod
    def load(cls, root: pathlib.Path | str | None = None) -> "Config":
        env = os.environ.get("RIP_OSIRIS_HOME")
        base = pathlib.Path(root or env) if (root or env) else None
        return cls(root=base) if base else cls()
