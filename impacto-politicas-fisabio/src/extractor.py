import pymupdf as fitz  # PyMuPDF
import os

def extract_text_with_pages(pdf_path):
    """
    Extrae texto de un documento PDF, manteniendo la referencia de la página.

    Args:
        pdf_path (str): Ruta al archivo PDF.

    Returns:
        list of dict: Una lista donde cada elemento representa una página y contiene
                      su número y el texto extraído.
    """
    extracted_data = []

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"No se encontró el archivo PDF en la ruta: {pdf_path}")

    try:
        # Abrir el documento PDF
        doc = fitz.open(pdf_path)

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text("text")

            extracted_data.append({
                "page_num": page_num + 1,  # Las páginas suelen indexarse desde 1 para humanos
                "text": text.strip()
            })

        doc.close()
    except Exception as e:
        print(f"Error procesando {pdf_path}: {e}")

    return extracted_data

if __name__ == "__main__":
    # Prueba rápida del extractor
    sample_pdf = os.path.join(os.path.dirname(__file__), '..', 'data', 'mock_policy_report.pdf')
    try:
        data = extract_text_with_pages(sample_pdf)
        print(f"Extraídas {len(data)} páginas.")
        for page in data:
            print(f"\n--- Página {page['page_num']} ---")
            # Imprimir un snippet pequeño de cada página
            print(page["text"][:100] + "...")
    except Exception as e:
        print(e)
