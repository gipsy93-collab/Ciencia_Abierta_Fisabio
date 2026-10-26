"""Informe HTML del rastreo (autocontenido, sin peticiones externas).

Rescata la idea del `report.py` del intento de Jules —agrupar por documento,
índice, tarjetas— pero leyendo el **expediente real** (`edges` con literal
verificado) en lugar de una lista de coincidencias difusas.

Cada hallazgo muestra: DOI, título, método, página, confianza y el fragmento
literal del documento. Sin literal no hay tarjeta, porque sin literal no hay
arista.
"""
from __future__ import annotations

import html
import json
import pathlib
from datetime import datetime

from ..dossier import classify

_CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#1f2933;--muted:#66788a;--line:#e3e8ee;
--accent:#1d4ed8;--ok:#0f766e;--warn:#b45309;--chip:#eef2f7}
*{box-sizing:border-box}
body{margin:0;padding:32px 20px 60px;background:var(--bg);color:var(--ink);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
main{max-width:1040px;margin:0 auto}
h1{font-size:1.6rem;margin:0 0 4px}
h2{font-size:1.15rem;margin:36px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:1rem;margin:0}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.sub{color:var(--muted);margin:0 0 24px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:20px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.card b{display:block;font-size:1.6rem;line-height:1.2}
.card span{color:var(--muted);font-size:.85rem}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden;font-size:.9rem}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--chip);font-weight:600}
tr:last-child td{border-bottom:0}
.mono{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.82rem}
.doc{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px;margin:0 0 18px}
.doc header{display:flex;flex-wrap:wrap;gap:10px;align-items:baseline;justify-content:space-between;margin-bottom:12px}
.meta{color:var(--muted);font-size:.82rem}
.hit{border-left:4px solid var(--accent);background:#fbfcfe;border-radius:6px;padding:12px 14px;margin:12px 0}
.hit .top{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between}
.chip{background:var(--chip);border-radius:999px;padding:2px 10px;font-size:.75rem;color:var(--muted)}
.chip.n{background:#e7f5f2;color:var(--ok)}
.chip.p{background:#fef3e2;color:var(--warn)}
blockquote{margin:10px 0 0;padding:10px 14px;background:#fff;border-left:3px solid var(--line);
color:#334155;font-size:.9rem;white-space:pre-wrap}
.note{background:#fff8e6;border:1px solid #f0d9a8;border-radius:8px;padding:12px 16px;color:#7c5a12;font-size:.88rem}
.empty{background:var(--card);border:1px dashed var(--line);border-radius:10px;padding:24px;color:var(--muted);text-align:center}
footer{margin-top:40px;color:var(--muted);font-size:.8rem}
"""


def _esc(valor) -> str:
    return html.escape("" if valor is None else str(valor))


def _pagina(payload_json: str | None) -> int | None:
    if not payload_json:
        return None
    try:
        extra = (json.loads(payload_json) or {}).get("extra") or {}
        valor = extra.get("page")
        return int(valor) if valor is not None else None
    except (ValueError, TypeError):
        return None


def _menciones(store) -> list[dict]:
    """Menciones institucionales agrupadas por documento (Capa 2, N6)."""
    filas = store.conn.execute(
        """
        SELECT m.doc_id, m.entidad, m.tipo, m.literal, m.page,
               d.title AS doc_title, d.url, d.doc_type
        FROM mentions m
        JOIN documents d ON d.id = m.doc_id
        ORDER BY m.doc_id, m.page, m.id
        """
    ).fetchall()

    grupos: dict[int, dict] = {}
    orden: list[int] = []
    for f in filas:
        did = int(f["doc_id"])
        if did not in grupos:
            grupos[did] = {
                "doc_id": did,
                "titulo": f["doc_title"],
                "url": f["url"],
                "doc_type": f["doc_type"],
                "menciones": [],
            }
            orden.append(did)
        grupos[did]["menciones"].append(
            {
                "entidad": f["entidad"],
                "tipo": f["tipo"],
                "literal": f["literal"],
                "page": f["page"],
            }
        )
    return [grupos[i] for i in orden]


def _documentos(store) -> list[dict]:
    filas = store.conn.execute(
        """
        SELECT d.id AS doc_id, d.source, d.title, d.url, d.doc_type, d.org,
               d.year, d.sha256, d.license,
               COUNT(DISTINCT e.src_id) AS hits,
               COUNT(e.id) AS menciones
        FROM documents d
        LEFT JOIN edges e
               ON e.dst_kind = 'document' AND e.dst_id = d.id
              AND e.edge_type = 'impact' AND e.src_kind = 'output'
        GROUP BY d.id
        ORDER BY hits DESC, menciones DESC, d.id
        """
    ).fetchall()
    return [dict(f) for f in filas]


def _hallazgos(store, doc_id: int) -> list[dict]:
    """Una ficha por salida, con todas sus evidencias (DOI y/o título)."""
    filas = store.conn.execute(
        """
        SELECT e.id, e.method, e.confidence, e.evidence_literal,
               o.id AS output_id, o.doi, o.title AS output_title,
               o.year AS output_year, p.payload_json
        FROM edges e
        JOIN outputs o ON o.id = e.src_id
        LEFT JOIN provenance p ON p.id = e.provenance_id
        WHERE e.src_kind = 'output' AND e.dst_kind = 'document'
          AND e.dst_id = ? AND e.edge_type = 'impact'
        ORDER BY e.id
        """,
        (doc_id,),
    ).fetchall()

    grupos: dict[int, dict] = {}
    orden: list[int] = []
    for f in filas:
        oid = int(f["output_id"])
        if oid not in grupos:
            grupos[oid] = {
                "output_id": oid,
                "doi": f["doi"],
                "titulo": f["output_title"],
                "anio": f["output_year"],
                "metodos": [],
                "paginas": [],
                "confianza": None,
                "evidencias": [],
            }
            orden.append(oid)
        grupo = grupos[oid]
        if f["method"] not in grupo["metodos"]:
            grupo["metodos"].append(f["method"])
        if f["confidence"] is not None:
            grupo["confianza"] = max(grupo["confianza"] or 0.0, float(f["confidence"]))
        pagina = _pagina(f["payload_json"])
        if pagina and pagina not in grupo["paginas"]:
            grupo["paginas"].append(pagina)
        grupo["evidencias"].append(
            {"literal": f["evidence_literal"], "method": f["method"], "page": pagina}
        )
    return [grupos[i] for i in orden]


def generar(store, salida: str | pathlib.Path, titulo: str | None = None) -> dict:
    documentos = _documentos(store)
    menciones_inst = _menciones(store)
    total_menciones_inst = sum(len(m["menciones"]) for m in menciones_inst)
    total = sum(d["hits"] for d in documentos)
    menciones = sum(d["menciones"] for d in documentos)
    con_hallazgos = sum(1 for d in documentos if d["hits"])
    salidas_con_impacto = store.conn.execute(
        "SELECT COUNT(DISTINCT src_id) FROM edges "
        "WHERE src_kind = 'output' AND dst_kind = 'document' AND edge_type = 'impact'"
    ).fetchone()[0]

    partes: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="es"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        f"<title>{_esc(titulo or 'Rastreo de impacto en políticas')}</title>",
        f"<style>{_CSS}</style></head><body><main>",
        f"<h1>{_esc(titulo or 'Rastreo de impacto en políticas públicas')}</h1>",
        f'<p class="sub">Generado el {datetime.now().strftime("%Y-%m-%d %H:%M")} · '
        "solo se cuenta lo que tiene fragmento literal en el documento.</p>",
        '<div class="cards">',
        f'<div class="card"><b>{len(documentos)}</b><span>documentos analizados</span></div>',
        f'<div class="card"><b>{con_hallazgos}</b><span>con al menos un hallazgo</span></div>',
        f'<div class="card"><b>{total}</b><span>salidas citadas</span></div>',
        f'<div class="card"><b>{menciones}</b><span>evidencias literales</span></div>',
        f'<div class="card"><b>{total_menciones_inst}</b><span>menciones institucionales (N6)</span></div>',
        "</div>",
        '<div class="note">0 hallazgos no significa «sin impacto»: significa que en '
        "este corpus no aparece. La cobertura se declara por fuente más abajo. "
        "Este informe no incluye citas académicas de OpenAlex (fase 2).</div>",
    ]

    if documentos:
        partes += ["<h2>Documentos analizados</h2>", "<table>", "<tr>"
                   "<th>#</th><th>Documento</th><th>Tipo</th><th>Fuente</th>"
                   "<th>Hallazgos</th><th>sha256</th></tr>"]
        for d in documentos:
            nivel = classify.nivel(d["doc_type"])
            url = d["url"] or ""
            enlace = (
                f'<a href="{_esc(url)}" target="_blank" rel="noopener">{_esc(d["title"] or url)}</a>'
                if url
                else _esc(d["title"] or "(sin título)")
            )
            partes.append(
                "<tr>"
                f'<td class="mono">{d["doc_id"]}</td>'
                f"<td>{enlace}</td>"
                f"<td>{_esc(d['doc_type'] or '—')} <span class=\"chip n\">{nivel}</span></td>"
                f'<td>{_esc(d["source"])}</td>'
                f'<td><b>{d["hits"]}</b></td>'
                f'<td class="mono">{_esc((d["sha256"] or "—")[:12])}</td>'
                "</tr>"
            )
        partes.append("</table>")

    con_hits = [d for d in documentos if d["hits"]]
    if not con_hits:
        partes.append(
            '<div class="empty">Ningún hallazgo literal en este corpus.<br>'
            "El pipeline ha corrido: revisa la cobertura y amplía documentos.</div>"
        )
    else:
        partes.append("<h2>Hallazgos por documento</h2>")
        for d in con_hits:
            nivel = classify.nivel(d["doc_type"])
            partes += [
                '<section class="doc">',
                "<header><h3>"
                + _esc(d["title"] or f"Documento {d['doc_id']}")
                + "</h3>"
                f'<span class="chip n">{nivel} · {_esc(classify.descripcion(nivel))}</span>'
                "</header>",
                '<p class="meta">'
                + (
                    f'<a href="{_esc(d["url"])}" target="_blank" rel="noopener">{_esc(d["url"])}</a> · '
                    if d["url"]
                    else ""
                )
                + f'sha256 <span class="mono">{_esc((d["sha256"] or "—")[:16])}</span> · '
                f'{_esc(d["hits"])} salida(s) citada(s), {_esc(d["menciones"])} evidencia(s)</p>',
            ]
            for h in _hallazgos(store, d["doc_id"]):
                doi = h["doi"]
                doi_html = (
                    f'<a href="https://doi.org/{_esc(doi)}" target="_blank" rel="noopener">'
                    f"{_esc(doi)}</a>"
                    if doi
                    else "<em>sin DOI</em>"
                )
                paginas = (
                    f'<span class="chip">pág. {", ".join(str(p) for p in h["paginas"])}</span>'
                    if h["paginas"]
                    else ""
                )
                conf = (
                    f'<span class="chip">conf. {h["confianza"]:.2f}</span>'
                    if h["confianza"] is not None
                    else ""
                )
                metodos = "".join(
                    f'<span class="chip p">{_esc(m)}</span>' for m in h["metodos"]
                )
                evidencias = "".join(
                    f"<blockquote>{_esc(e['literal'])}</blockquote>" for e in h["evidencias"]
                )
                partes += [
                    '<div class="hit"><div class="top">',
                    f"<div><b>{_esc(h['titulo'] or doi)}</b><br>"
                    f'<span class="mono">{doi_html}</span></div>',
                    f"<div>{metodos}{paginas}{conf}</div>",
                    "</div>",
                    evidencias,
                    "</div>",
                ]
            partes.append("</section>")

    if menciones_inst:
        partes += [
            "<h2>Menciones institucionales (N6)</h2>",
            '<div class="note">La institución nombrada no se atribuye a una salida concreta: '
            "se declara aparte como N6 y <b>no</b> se suma al recuento de salidas citadas.</div>",
        ]
        for grupo in menciones_inst:
            nivel = classify.nivel(grupo["doc_type"])
            partes += [
                '<section class="doc">',
                "<header><h3>"
                + _esc(grupo["titulo"] or f"Documento {grupo['doc_id']}")
                + "</h3>"
                f'<span class="chip n">{nivel}</span>'
                "</header>",
            ]
            for m in grupo["menciones"]:
                pagina = (
                    f'<span class="chip">pág. {m["page"]}</span>' if m["page"] else ""
                )
                partes += [
                    '<div class="hit"><div class="top">',
                    f"<div><b>{_esc(m['entidad'])}</b></div>",
                    f"<div><span class=\"chip p\">{_esc(m['tipo'])}</span>{pagina}</div>",
                    "</div>",
                    f"<blockquote>{_esc(m['literal'])}</blockquote>",
                    "</div>",
                ]
            partes.append("</section>")

    cobertura = store.coverage()
    if cobertura:
        partes += ["<h2>Cobertura declarada</h2>", "<table>",
                   "<tr><th>Fuente</th><th>Consulta</th><th>Resultados</th>"
                   "<th>Declaración</th><th>Medido</th></tr>"]
        for c in cobertura:
            partes.append(
                "<tr>"
                f'<td>{_esc(c["source"])}</td>'
                f'<td class="mono">{_esc(c["query"])}</td>'
                f'<td>{_esc(c["hits"])}</td>'
                f'<td>{_esc(c["declared"] or "")}</td>'
                f'<td class="mono">{_esc((c["measured_at"] or "")[:10])}</td>'
                "</tr>"
            )
        partes.append("</table>")

    partes += [
        "<footer>RIP-OSIRIS · cada hallazgo lleva fragmento literal y huella del "
        "documento; sin eso no se registra.</footer>",
        "</main></body></html>",
    ]

    destino = pathlib.Path(salida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(partes), encoding="utf-8")

    return {
        "salida": str(destino),
        "documentos": len(documentos),
        "con_hallazgos": con_hallazgos,
        "hallazgos": total,
        "menciones": menciones,
        "menciones_institucionales": total_menciones_inst,
        "salidas_con_impacto": int(salidas_con_impacto),
    }
