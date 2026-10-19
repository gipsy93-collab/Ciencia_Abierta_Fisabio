"""Texto completo de un documento: PDF (PyMuPDF) o HTML (BOE/GVA).

Los documentos de política llegan en dos formatos: PDF (planes, estrategias)
y HTML (normas del BOE, portales institucionales). Ambos se reducen al mismo
contrato: una cadena de texto que después atraviesa `references`/`guardian`.
"""
from __future__ import annotations

import pathlib
import re
import tempfile

_RE_BLOQUES_MUERTOS = re.compile(r"(?is)<(script|style|noscript).*?</\1>")
_RE_ETIQUETAS = re.compile(r"(?s)<[^>]+>")
_RE_ENTIDADES = re.compile(r"&[a-zA-Z]+;|&#\d+;")

_ENTIDADES = {
    "&nbsp;": " ",
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&apos;": "'",
    "&aacute;": "á",
    "&eacute;": "é",
    "&iacute;": "í",
    "&oacute;": "ó",
    "&uacute;": "ú",
    "&ntilde;": "ñ",
    "&Aacute;": "Á",
    "&Eacute;": "É",
    "&Iacute;": "Í",
    "&Oacute;": "Ó",
    "&Uacute;": "Ú",
    "&Ntilde;": "Ñ",
    "&uuml;": "ü",
    "&laquo;": "«",
    "&raquo;": "»",
    "&ordf;": "ª",
    "&ordm;": "º",
}


def extraer_texto(pdf_path: str | pathlib.Path) -> str:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise RuntimeError("PyMuPDF no instalado: pip install pymupdf") from exc

    doc = fitz.open(str(pdf_path))
    try:
        return "\n".join(page.get_text("text") for page in doc)
    finally:
        doc.close()


def html_a_texto(html: str) -> str:
    """Reduce HTML a texto plano conservando el orden y los literales."""
    texto = _RE_BLOQUES_MUERTOS.sub(" ", html)

    def _entidad(m: re.Match) -> str:
        cruda = m.group(0)
        if cruda in _ENTIDADES:
            return _ENTIDADES[cruda]
        if cruda.startswith("&#"):
            try:
                return chr(int(cruda[2:-1]))
            except ValueError:
                return " "
        return " "

    texto = _RE_ENTIDADES.sub(_entidad, texto)
    texto = _RE_ETIQUETAS.sub(" ", texto)
    return " ".join(texto.split())


def extraer_texto_archivo(ruta: str | pathlib.Path) -> str:
    """Extrae texto según la extensión: `.pdf` -> PyMuPDF, resto -> HTML."""
    p = pathlib.Path(ruta)
    if p.suffix.lower() == ".pdf":
        return extraer_texto(p)
    crudo = p.read_bytes()
    return html_a_texto(crudo.decode("utf-8", errors="replace"))


def extraer_texto_bytes(datos: bytes, content_type: str = "") -> str:
    """Extrae texto de una descarga recién hecha, sin escribir a disco."""
    if "pdf" in content_type.lower() or datos[:5] == b"%PDF-":
        with tempfile.TemporaryDirectory() as tmp:
            ruta = pathlib.Path(tmp) / "doc.pdf"
            ruta.write_bytes(datos)
            return extraer_texto(ruta)
    return html_a_texto(datos.decode("utf-8", errors="replace"))
