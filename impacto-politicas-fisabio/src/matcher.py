import re
from fuzzywuzzy import fuzz

def find_matches(catalog, extracted_pages, threshold=80):
    """
    Busca menciones del catálogo dentro del texto extraído de los PDFs.

    Args:
        catalog (list of dict): Lista de trabajos (diccionarios con 'doi', 'title', etc.).
        extracted_pages (list of dict): Lista de páginas extraídas (diccionarios con 'page_num', 'text').
        threshold (int): Umbral para la coincidencia difusa (Fuzzy Match).

    Returns:
        list of dict: Lista de coincidencias encontradas con detalles.
    """
    matches = []

    for page in extracted_pages:
        text = page['text']
        page_num = page['page_num']

        # Limpiar texto para mejor matching (quitar saltos de línea extra)
        clean_text = " ".join(text.split())

        for item in catalog:
            doi = item.get('doi', '')
            title = item.get('title', '')

            match_found = False
            match_type = ""

            # 1. Búsqueda exacta por DOI
            if doi and doi.lower() in clean_text.lower():
                match_found = True
                match_type = "DOI (Exacto)"

            # 2. Búsqueda por Título (Fuzzy)
            if not match_found and title:
                # Usar partial_ratio para ver si el título está "dentro" del texto de la página
                score = fuzz.partial_ratio(title.lower(), clean_text.lower())
                if score >= threshold:
                    match_found = True
                    match_type = f"Título (Fuzzy, score={score})"

            if match_found:
                # Extraer un "snippet" o fragmento del contexto
                snippet = extract_snippet(clean_text, doi, title, match_type)

                matches.append({
                    "doi": doi,
                    "title": title,
                    "page_num": page_num,
                    "match_type": match_type,
                    "snippet": snippet,
                    "degree": item.get('degree', 1),
                    "relation_type": item.get('relation_type', 'Original'),
                    "parent_doi": item.get('parent_doi', doi)
                })

    return matches

def extract_snippet(text, doi, title, match_type, context_length=150):
    """
    Extrae un fragmento de texto alrededor de la coincidencia.
    """
    lower_text = text.lower()
    start_index = -1

    if "DOI" in match_type:
        start_index = lower_text.find(doi.lower())
    else:
        # Para Fuzzy, buscamos la primera aparición de las primeras palabras del título
        first_words = " ".join(title.split()[:3]).lower()
        start_index = lower_text.find(first_words)

    if start_index == -1:
        # Fallback si no encuentra el índice exacto
        return text[:context_length] + "..."

    # Calcular límites del snippet
    start_snippet = max(0, start_index - context_length // 2)
    end_snippet = min(len(text), start_index + len(doi if "DOI" in match_type else title) + context_length // 2)

    snippet = text[start_snippet:end_snippet]
    if start_snippet > 0:
        snippet = "..." + snippet
    if end_snippet < len(text):
        snippet = snippet + "..."

    return snippet
