"""Parser robusto de la lista de publicaciones del portal (get-publications)."""
from __future__ import annotations

import re
import sys


def limpiar(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parsear(html: str) -> list[dict]:
    # cada publicación es un <li class="pad-top-600 ...">; los <li> internos
    # (métricas) no llevan pad-top-600, así que el corte es seguro.
    bloques = re.split(r'<li class="pad-top-600[^"]*">', html)[1:]
    salida = []
    for b in bloques:
        m_tit = re.search(
            r'<h4 class="results-list__title[^"]*">\s*<a[^>]*href="([^"]*?/publicaciones/(\d+))"[^>]*>(.*?)</a>',
            b, re.S)
        if not m_tit:
            continue
        url, pid, titulo = m_tit.group(1), m_tit.group(2), limpiar(m_tit.group(3))

        parrafos = re.findall(r"<p>(.*?)</p>", b, re.S)
        autores = limpiar(parrafos[0]) if parrafos else ""
        tipo = doi = anio = issn = revista = ""
        citas = None
        if len(parrafos) > 1:
            p2 = limpiar(parrafos[1])
            m_doi = re.search(r"\b(10\.\d{4,9}/[^\s<]+)", p2)
            doi = m_doi.group(1).rstrip(".") if m_doi else ""
            m_anio = re.search(r"\b(19|20)\d{2}\b", p2)
            anio = m_anio.group(0) if m_anio else ""
            tipo = p2.split(".")[0].strip() if "." in p2 else p2
        if len(parrafos) > 2:
            p3 = limpiar(parrafos[2])
            m_issn = re.match(r"([0-9Xx-]{8,9})\.\s*(.*)", p3)
            if m_issn:
                issn = m_issn.group(1)
                resto = m_issn.group(2)
                m_cit = re.search(r"Citas Recibidas en Web of Science:\s*(\d+)", resto)
                if m_cit:
                    citas = int(m_cit.group(1))
                    resto = resto[:m_cit.start()]
                revista = resto.strip(" .")
            else:
                revista = p3

        anio_i = int(anio) if anio else None
        salida.append({
            "portal_pub_id": pid,
            "url": url,
            "titulo": titulo,
            "autores": autores,
            "tipo": tipo,
            "doi": doi,
            "anio": anio_i,
            "issn": issn,
            "revista": revista,
            "citas_wos": citas,
            "anio_sospechoso": bool(anio_i and (anio_i < 1900 or anio_i > 2027)),
        })
    return salida


if __name__ == "__main__":
    from pathlib import Path
    for f in ["pub_2186_ajax.html", "pub_1928.html"]:
        html = Path(rf"C:\Users\gipsy\AppData\Local\Temp\opencode\{f}").read_text(encoding="utf-8")
        pubs = parsear(html)
        print(f"{f}: {len(pubs)} publicaciones · "
              f"{sum(bool(p['doi']) for p in pubs)} con DOI · "
              f"{sum(p['anio_sospechoso'] for p in pubs)} años sospechosos")
