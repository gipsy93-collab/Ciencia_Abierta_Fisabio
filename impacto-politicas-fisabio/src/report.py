import os
import json
from datetime import datetime

def generate_html_report(matches, pdf_filename, output_path):
    """
    Genera un reporte HTML con los resultados de las coincidencias.
    """
    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reporte de Impacto en Políticas</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 900px; margin: 0 auto; padding: 20px; background-color: #f5f7fa; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            .summary {{ background-color: #fff; padding: 15px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; }}
            .match-card {{ background-color: #fff; padding: 20px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; border-left: 5px solid #3498db; }}
            .match-header {{ display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 10px; }}
            .doi {{ font-weight: bold; color: #e74c3c; }}
            .match-type {{ background-color: #ecf0f1; padding: 3px 8px; border-radius: 12px; font-size: 0.85em; color: #7f8c8d; }}
            .snippet {{ background-color: #f9f9f9; padding: 15px; border-left: 3px solid #bdc3c7; font-style: italic; margin-top: 10px; }}
            .page-badge {{ background-color: #2ecc71; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.85em; }}
        </style>
    </head>
    <body>
        <h1>Reporte de Impacto en Políticas Públicas</h1>

        <div class="summary">
            <p><strong>Fecha de análisis:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p><strong>Documento analizado:</strong> {pdf_filename}</p>
            <p><strong>Total de menciones encontradas:</strong> {len(matches)}</p>
        </div>
    """

    if not matches:
        html_content += "<p>No se encontraron menciones de los trabajos en este documento.</p>"
    else:
        for match in matches:
            html_content += f"""
            <div class="match-card">
                <div class="match-header">
                    <div>
                        <span class="doi">DOI: {match.get('doi', 'N/A')}</span>
                        <br>
                        <small>{match.get('title', 'Sin título')}</small>
                    </div>
                    <div>
                        <span class="page-badge">Página {match['page_num']}</span>
                        <span class="match-type">{match['match_type']}</span>
                    </div>
                </div>
                <div class="snippet">
                    "{match['snippet']}"
                </div>
            </div>
            """

    html_content += """
    </body>
    </html>
    """

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Reporte HTML generado en: {output_path}")

if __name__ == "__main__":
    # Prueba de generación de reporte con datos ficticios
    dummy_matches = [
        {
            "doi": "10.1038/s41591-023-02465-7",
            "title": "Zolbetuximab plus CAPOX in first-line treatment...",
            "page_num": 2,
            "match_type": "DOI (Exacto)",
            "snippet": "...Como se menciona en la literatura reciente (DOI: 10.1038/s41591-023-02465-7), el uso de Zolbetuximab plus CAPOX ha mostrado resultados prometedores..."
        }
    ]
    report_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'test_reporte.html')
    generate_html_report(dummy_matches, "mock_policy_report.pdf", report_path)
