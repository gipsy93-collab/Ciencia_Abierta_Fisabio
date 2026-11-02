import json
import os
from extractor import extract_text_with_pages
from matcher import find_matches

def test():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    catalog_path = os.path.join(base_dir, 'data', 'hospital_elche_sample.json')
    pdf_path = os.path.join(base_dir, 'data', 'mock_policy_report.pdf')

    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    pages = extract_text_with_pages(pdf_path)
    matches = find_matches(catalog, pages)

    print(f"Se encontraron {len(matches)} coincidencias:")
    for m in matches:
        print(f"- [Pág {m['page_num']}] [{m['match_type']}] DOI: {m['doi']}")
        print(f"  Snippet: {m['snippet']}\n")

if __name__ == '__main__':
    test()
