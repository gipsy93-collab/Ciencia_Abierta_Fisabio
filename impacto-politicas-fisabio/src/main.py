import os
import json
from extractor import extract_text_with_pages
from matcher import find_matches
from report import generate_html_report
from tracker import Tracker

def main():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    data_dir = os.path.join(base_dir, 'data')
    catalog_path = os.path.join(data_dir, 'hospital_elche_sample.json')

    # Archivos locales de prueba
    mock_pdf_path = os.path.join(data_dir, 'mock_policy_report.pdf')

    print("1. Cargando catálogo de trabajos...")
    try:
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
        print(f"   Se cargaron {len(catalog)} trabajos.")
    except Exception as e:
        print(f"Error cargando el catálogo: {e}")
        return

    print("\n2. Rastreando e intentando descargar PDFs reales relacionados a los trabajos...")
    tracker = Tracker(data_dir)
    downloaded_pdfs = tracker.run_tracking(catalog)

    pdf_list = []
    if not downloaded_pdfs:
        print("   No se pudieron descargar PDFs reales. Usando mock_policy_report.pdf por defecto.")
        pdf_list.append(mock_pdf_path)
    else:
        print(f"   Se descargaron {len(downloaded_pdfs)} PDFs de fuentes externas.")
        pdf_list.extend(downloaded_pdfs)
        # Opcionalmente, agregar también el mock para asegurar que al menos haya resultados en la prueba
        pdf_list.append(mock_pdf_path)

    all_matches = []

    print("\n3. Extrayendo texto y buscando menciones...")
    for pdf_path in pdf_list:
        if not os.path.exists(pdf_path):
            continue

        print(f"   -> Analizando: {os.path.basename(pdf_path)}")
        pages = extract_text_with_pages(pdf_path)

        if not pages:
            continue

        # Umbral ajustado para matches parciales
        matches = find_matches(catalog, pages, threshold=60)

        # Añadir referencia al archivo PDF en el match
        for m in matches:
            m['source_pdf'] = os.path.basename(pdf_path)

        all_matches.extend(matches)

    print(f"\n   Total acumulado: Se encontraron {len(all_matches)} coincidencias a través de los documentos.")

    print("\n4. Generando reporte HTML consolidado...")
    report_path = os.path.join(base_dir, 'docs', 'reporte_impacto.html')
    generate_html_report(all_matches, f"Múltiples documentos ({len(pdf_list)} analizados)", report_path)

if __name__ == "__main__":
    main()
