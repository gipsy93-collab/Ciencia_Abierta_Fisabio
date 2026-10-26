import requests
import os
import time
import uuid
from duckduckgo_search import DDGS
from urllib.parse import urlparse

class Tracker:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.downloaded_pdfs = set()

        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def run_tracking(self, catalog):
        """
        Inicia el rastreo para cada trabajo en el catálogo.
        Retorna la lista de rutas a los PDFs descargados.
        """
        all_downloaded = []
        for item in catalog:
            doi = item.get('doi')
            if not doi:
                continue

            print(f"Rastreando DOI: {doi} ...")
            urls = set()

            # 1. Búsqueda web directa
            web_urls = self.search_web_for_pdf(doi)
            urls.update(web_urls)

            # 2. Consultar OpenAlex (para citas que podrían incluir URLs)
            openalex_urls = self.search_openalex(doi)
            urls.update(openalex_urls)

            # 3. Consultar OpenAIRE
            openaire_urls = self.search_openaire(doi)
            urls.update(openaire_urls)

            # Descargar los PDFs encontrados
            for url in urls:
                pdf_path = self.download_pdf(url)
                if pdf_path and pdf_path not in all_downloaded:
                    all_downloaded.append(pdf_path)

            time.sleep(2) # Respetar límites de rate limiting

        return all_downloaded

    def search_web_for_pdf(self, doi):
        urls = []
        try:
            # Buscar el DOI explícitamente en formato PDF
            query = f'"{doi}" ext:pdf'
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                for r in results:
                    url = r.get('href', '')
                    if url.lower().endswith('.pdf'):
                        urls.append(url)
        except Exception as e:
            print(f"  [Web Search] Error buscando {doi}: {e}")
        return urls

    def search_openalex(self, doi):
        urls = []
        try:
            # Buscar trabajos que citen a este DOI
            # Primero necesitamos encontrar el ID de OpenAlex del DOI
            doi_url = f"https://api.openalex.org/works/https://doi.org/{doi}"
            response = requests.get(doi_url, timeout=10)
            if response.status_code == 200:
                work_data = response.json()
                work_id = work_data.get('id')

                if work_id:
                    # Buscar citas a este trabajo
                    citations_url = f"https://api.openalex.org/works?filter=cites:{work_id}&per-page=5"
                    c_resp = requests.get(citations_url, timeout=10)
                    if c_resp.status_code == 200:
                        c_data = c_resp.json()
                        for result in c_data.get('results', []):
                            # Intentar encontrar una URL de acceso abierto en formato PDF
                            open_access = result.get('open_access', {})
                            oa_url = open_access.get('oa_url')
                            if oa_url and oa_url.lower().endswith('.pdf'):
                                urls.append(oa_url)
        except Exception as e:
            print(f"  [OpenAlex] Error buscando {doi}: {e}")
        return urls

    def search_openaire(self, doi):
        urls = []
        try:
            # Endpoint público de OpenAIRE para buscar publicaciones por DOI
            api_url = f"https://api.openaire.eu/search/publications?doi={doi}&format=json"
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = data.get('response', {}).get('results', {}).get('result', [])
                if not isinstance(results, list):
                    results = [results]

                for res in results:
                    # OpenAIRE retorna una estructura XML convertida a JSON algo compleja
                    metadata = res.get('metadata', {}).get('oaf:entity', {}).get('oaf:result', {})
                    instances = metadata.get('children', {}).get('instance', [])
                    if not isinstance(instances, list):
                        instances = [instances]

                    for inst in instances:
                        webresources = inst.get('webresource', [])
                        if not isinstance(webresources, list):
                            webresources = [webresources]
                        for wr in webresources:
                            url = wr.get('url', '')
                            if isinstance(url, dict):
                                url = url.get('$', '')
                            if isinstance(url, str) and url.lower().endswith('.pdf'):
                                urls.append(url)
        except Exception as e:
             print(f"  [OpenAIRE] Error buscando {doi}: {e}")
        return urls

    def download_pdf(self, url):
        if url in self.downloaded_pdfs:
            return None

        try:
            # Añadir headers básicos para evitar ser bloqueados por algunos servidores
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            print(f"  -> Descargando: {url}")
            response = requests.get(url, stream=True, timeout=15, headers=headers)

            if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', '').lower():
                # Generar nombre de archivo único
                filename = f"tracked_{uuid.uuid4().hex[:8]}.pdf"
                filepath = os.path.join(self.data_dir, filename)

                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                self.downloaded_pdfs.add(url)
                print(f"     Guardado como: {filename}")
                return filepath
            else:
                 print(f"     No es un PDF válido o error HTTP {response.status_code}")
        except Exception as e:
            print(f"     Error al descargar {url}: {e}")

        return None
