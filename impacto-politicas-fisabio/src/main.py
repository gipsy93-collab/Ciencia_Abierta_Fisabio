import os
import json
from extractor import extract_text_with_pages
from matcher import find_matches
from report import generate_html_report

def main():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    catalog_path = os.path.join(base_dir, 'data', 'hospital_elche_sample.json')
    pdf_path = os.path.join(base_dir, 'data', 'mock_policy_report.pdf')
    report_path = os.path.join(base_dir, 'docs', 'reporte_impacto.html')

    print("1. Cargando catálogo de trabajos...")
    try:
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
        print(f"   Se cargaron {len(catalog)} trabajos.")
    except Exception as e:
        print(f"Error cargando el catálogo: {e}")
        return

    print(f"\n2. Extrayendo texto del documento PDF ({os.path.basename(pdf_path)})...")
    pages = extract_text_with_pages(pdf_path)
    if not pages:
        print("No se pudo extraer texto del PDF.")
        return

    print("\n3. Buscando menciones de los trabajos en el texto...")
    # Usamos un umbral de 60 para que capture el fuzzy match parcial de los títulos en la bibliografía
    matches = find_matches(catalog, pages, threshold=60)
    print(f"   Se encontraron {len(matches)} coincidencias.")

    print("\n4. Generando reporte HTML...")
    generate_html_report(matches, os.path.basename(pdf_path), report_path)

if __name__ == "__main__":
    main()
