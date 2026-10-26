"""Ingesta: URL -> documento, texto, huella sha256 y mapa de páginas."""
import pathlib
import tempfile
import unittest

from rip_osiris.config import Config
from rip_osiris.corpus.pages import cargar_mapa, pagina_de
from rip_osiris.corpus.store import Store
from rip_osiris.ingest import inferir_doc_type, ingerir_urls, leer_urls, titulo_probable

HTML = b"""<html><head><title>x</title><style>.a{}</style></head>
<body><h1>Plan de Salud de la Comunitat Valenciana 2024</h1>
<p>Este plan se apoya en la evidencia disponible sobre gripe y vacunacion.
La estrategia prioriza la vigilancia centinela, la caracterizacion de virus
circulantes y la evaluacion de la efectividad vacunal en poblacion mayor de
sesenta y cinco anos, con especial atencion a los ambitos de mayor riesgo.</p>
</body></html>"""


class _FetcherFalso:
    def __init__(self, datos=HTML, content_type="text/html"):
        self.datos = datos
        self.content_type = content_type
        self.llamadas = []

    def obtener(self, url):
        self.llamadas.append(url)
        import hashlib

        return self.datos, {
            "url": url,
            "sha256": hashlib.sha256(self.datos).hexdigest(),
            "bytes": len(self.datos),
            "cache": False,
            "content_type": self.content_type,
        }


class TestIngesta(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = Config(root=self.tmp.name)
        self.store = Store(pathlib.Path(self.tmp.name) / "test.sqlite")
        self.fetcher = _FetcherFalso()

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_url_a_documento(self):
        resumen = ingerir_urls(
            self.store,
            self.cfg,
            ["https://www.san.gva.es/documents/plan-salud-2024.pdf"],
            fetcher=self.fetcher,
        )
        self.assertEqual(len(resumen.documentos), 1)
        doc = resumen.documentos[0]
        self.assertEqual(doc.doc_type, "plan")
        self.assertEqual(doc.paginas, 1)
        self.assertGreater(doc.caracteres, 200)
        fila = self.store.conn.execute("SELECT * FROM documents WHERE id = ?", (doc.doc_id,)).fetchone()
        self.assertIsNotNone(fila["sha256"])
        self.assertTrue(pathlib.Path(fila["fulltext_path"]).exists())
        self.assertEqual(cargar_mapa(self.cfg, doc.doc_id), [0])
        self.assertEqual(pagina_de(self.cfg, doc.doc_id, 10), 1)

    def test_idempotente(self):
        url = "https://www.san.gva.es/documents/plan-salud-2024.pdf"
        ingerir_urls(self.store, self.cfg, [url], fetcher=self.fetcher)
        segundo = ingerir_urls(self.store, self.cfg, [url], fetcher=self.fetcher)
        self.assertEqual(segundo.documentos, [])
        self.assertEqual(segundo.existentes, [url])
        self.assertEqual(len(self.fetcher.llamadas), 1)

    def test_registra_crawl_log_y_cobertura(self):
        ingerir_urls(self.store, self.cfg, ["https://www.san.gva.es/a.pdf"], fetcher=self.fetcher)
        self.assertEqual(self.store.conn.execute("SELECT COUNT(*) FROM crawl_log").fetchone()[0], 1)
        self.assertEqual(len(self.store.coverage()), 1)

    def test_texto_insuficiente_es_error(self):
        corto = _FetcherFalso(b"<html><body>vacio</body></html>")
        resumen = ingerir_urls(self.store, self.cfg, ["https://x.org/a"], fetcher=corto)
        self.assertEqual(resumen.documentos, [])
        self.assertEqual(len(resumen.errores), 1)

    def test_inferir_doc_type(self):
        self.assertEqual(inferir_doc_type("https://www.boe.es/buscar/pdf/2018/a.pdf"), "normativa")
        self.assertEqual(inferir_doc_type("https://www.ecdc.europa.eu/x.pdf"), "informe_agencia")
        self.assertEqual(inferir_doc_type("https://www.san.gva.es/documents/guia-x.pdf"), "gpc")
        self.assertEqual(inferir_doc_type("https://ejemplo.org/otra-cosa.pdf"), "informe")

    def test_leer_urls_ignora_comentarios(self):
        ruta = pathlib.Path(self.tmp.name) / "urls.txt"
        ruta.write_text("# cabecera\nhttps://a.org/1.pdf\n\n  https://b.org/2.pdf  # nota\n", encoding="utf-8")
        self.assertEqual(leer_urls(ruta), ["https://a.org/1.pdf", "https://b.org/2.pdf"])

    def test_titulo_probable(self):
        self.assertEqual(
            titulo_probable("Página 1\n\nPlan de Salud 2024 de la Comunitat"), "Plan de Salud 2024 de la Comunitat"
        )


if __name__ == "__main__":
    unittest.main()
