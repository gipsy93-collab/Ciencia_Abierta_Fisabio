import os
from datetime import datetime

def generate_html_report(matches, pdf_filename, output_path):
    """
    Genera un reporte HTML agrupado por documento de origen, con enlaces corroborables.
    """
    # Agrupar coincidencias por PDF
    matches_by_pdf = {}
    for match in matches:
        source = match.get('source_pdf', pdf_filename)
        if source not in matches_by_pdf:
            matches_by_pdf[source] = []
        matches_by_pdf[source].append(match)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reporte de Impacto en Políticas</title>
        <style>
            :root {{
                --primary: #2c3e50;
                --secondary: #34495e;
                --accent: #3498db;
                --snowball: #9b59b6;
                --bg: #f8f9fa;
                --card-bg: #ffffff;
                --text: #333333;
                --border: #e2e8f0;
            }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: var(--text); max-width: 1000px; margin: 0 auto; padding: 20px; background-color: var(--bg); }}
            h1 {{ color: var(--primary); border-bottom: 3px solid var(--accent); padding-bottom: 10px; }}
            h2 {{ color: var(--secondary); margin-top: 40px; border-bottom: 1px solid var(--border); padding-bottom: 5px; }}
            a {{ color: var(--accent); text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .summary {{ background-color: var(--card-bg); padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 30px; border: 1px solid var(--border); }}
            .toc {{ background-color: var(--card-bg); padding: 20px; border-radius: 8px; margin-bottom: 30px; border: 1px solid var(--border); }}
            .toc ul {{ list-style-type: none; padding-left: 0; }}
            .toc li {{ margin-bottom: 10px; }}

            .pdf-section {{ margin-bottom: 50px; }}
            .match-card {{ background-color: var(--card-bg); padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 20px; border-left: 5px solid var(--accent); }}
            .match-card.snowball {{ border-left: 5px solid var(--snowball); }}

            .match-header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid var(--border); padding-bottom: 15px; margin-bottom: 15px; }}
            .match-title {{ font-size: 0.95em; color: var(--secondary); margin-top: 5px; }}

            .badges {{ display: flex; flex-direction: column; align-items: flex-end; gap: 8px; min-width: 180px; }}
            .badge {{ padding: 4px 10px; border-radius: 12px; font-size: 0.8em; font-weight: 600; text-align: center; display: inline-block; }}
            .badge-page {{ background-color: #2ecc71; color: white; }}
            .badge-type {{ background-color: #ecf0f1; color: #7f8c8d; border: 1px solid #bdc3c7; }}
            .badge-direct {{ background-color: var(--accent); color: white; }}
            .badge-indirect {{ background-color: var(--snowball); color: white; }}

            .relation-info {{ font-size: 0.85em; color: #e67e22; margin-top: 8px; display: block; background-color: #fff8f2; padding: 5px 10px; border-radius: 4px; border-left: 3px solid #e67e22; }}
            .snippet {{ background-color: #f8f9fa; padding: 15px; border-left: 3px solid #cbd5e1; font-style: italic; font-size: 0.9em; color: #475569; }}
            .pdf-link-btn {{ display: inline-block; margin-top: 10px; font-size: 0.85em; background-color: #f1f5f9; padding: 5px 12px; border-radius: 4px; border: 1px solid #cbd5e1; color: #334155; }}
            .pdf-link-btn:hover {{ background-color: #e2e8f0; text-decoration: none; }}
        </style>
    </head>
    <body>
        <h1>Reporte de Impacto en Políticas Públicas</h1>

        <div class="summary">
            <p><strong>Fecha de análisis:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p><strong>Documentos con menciones:</strong> {len(matches_by_pdf)}</p>
            <p><strong>Total de menciones encontradas:</strong> {len(matches)}</p>
        </div>
    """

    if not matches:
        html_content += "<p>No se encontraron menciones de los trabajos en este análisis.</p>"
    else:
        # Índice / Tabla de Contenidos
        html_content += """
        <div class="toc">
            <h3>Índice de Documentos</h3>
            <ul>
        """
        for i, (pdf_source, pdf_matches) in enumerate(matches_by_pdf.items()):
            html_content += f'<li><a href="#pdf-{i}">📄 {pdf_source}</a> <span style="color:#7f8c8d; font-size:0.9em;">({len(pdf_matches)} menciones)</span></li>'
        html_content += """
            </ul>
        </div>
        """

        # Secciones por PDF
        for i, (pdf_source, pdf_matches) in enumerate(matches_by_pdf.items()):
            pdf_path_relative = f"../data/{pdf_source}"

            html_content += f"""
            <div class="pdf-section" id="pdf-{i}">
                <h2>📄 {pdf_source}</h2>
                <a href="{pdf_path_relative}" target="_blank" class="pdf-link-btn">📁 Abrir PDF Original localmente</a>
                <br><br>
            """

            for match in pdf_matches:
                degree = match.get('degree', 1)
                is_snowball = degree == 2
                card_class = "match-card snowball" if is_snowball else "match-card"
                badge_class = "badge-indirect" if is_snowball else "badge-direct"
                degree_text = "Impacto 2º Grado (Bola de Nieve)" if is_snowball else "Impacto Directo"

                doi = match.get('doi', '')
                doi_link = f'<a href="https://doi.org/{doi}" target="_blank"><strong>{doi}</strong></a>' if doi else 'N/A'

                relation_html = ""
                if is_snowball:
                    parent_doi = match.get('parent_doi', '')
                    parent_link = f'<a href="https://doi.org/{parent_doi}" target="_blank">{parent_doi}</a>'
                    relation_html = f"<div class='relation-info'>↗ <strong>{match.get('relation_type')}</strong> del trabajo original: {parent_link}</div>"

                html_content += f"""
                <div class="{card_class}">
                    <div class="match-header">
                        <div style="flex: 1; padding-right: 15px;">
                            <div style="font-size: 1.1em;">DOI: {doi_link}</div>
                            <div class="match-title">{match.get('title', 'Sin título')}</div>
                            {relation_html}
                        </div>
                        <div class="badges">
                            <span class="badge {badge_class}">{degree_text}</span>
                            <span class="badge badge-page">Página {match['page_num']}</span>
                            <span class="badge badge-type">{match['match_type']}</span>
                        </div>
                    </div>
                    <div class="snippet">
                        "...{match['snippet']}..."
                    </div>
                </div>
                """
            html_content += "</div>"

    html_content += """
    </body>
    </html>
    """

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Reporte HTML generado en: {output_path}")
