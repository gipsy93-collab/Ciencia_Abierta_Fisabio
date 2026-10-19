"""Exportación del expediente (Dublin Core Qualified / BibTeX)."""
from __future__ import annotations

from xml.sax.saxutils import escape


def dublincore(items: list[dict]) -> str:
    partes = ['<?xml version="1.0" encoding="UTF-8"?>', "<records>"]
    for it in items:
        doc = it.get("document") or {}
        partes += [
            "  <record>",
            f"    <dc:title>{escape(str(doc.get('title') or ''))}</dc:title>",
            f"    <dc:identifier>{escape(str(doc.get('url') or doc.get('doi') or ''))}</dc:identifier>",
            f"    <dc:date>{escape(str(doc.get('year') or ''))}</dc:date>",
            f"    <dc:type>{escape(str(doc.get('doc_type') or ''))}</dc:type>",
            f"    <rip:nivel>{escape(it.get('nivel', ''))}</rip:nivel>",
            "  </record>",
        ]
    partes.append("</records>")
    return "\n".join(partes)


def bibtex(items: list[dict]) -> str:
    salida = []
    for i, it in enumerate(items, 1):
        doc = it.get("document") or {}
        clave = f"rip{i}"
        titulo = str(doc.get("title") or "").replace("{", "").replace("}", "")
        salida.append(
            "\n".join(
                [
                    f"@misc{{{clave},",
                    f"  title = {{{titulo}}},",
                    f"  year = {{{doc.get('year') or ''}}},",
                    f"  note = {{{it.get('nivel', '')}}},",
                    f"  url = {{{doc.get('url') or ''}}}",
                    "}",
                ]
            )
        )
    return "\n\n".join(salida)
