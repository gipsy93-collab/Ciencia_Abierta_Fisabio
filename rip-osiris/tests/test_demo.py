"""Bucle completo sin red: DOI en el cuerpo, título literal e informe HTML."""
import pathlib
import tempfile
import unittest

from rip_osiris.cascade import pipeline
from rip_osiris.config import Config
from rip_osiris.corpus.store import Store
from rip_osiris.dossier import html as dossier_html
from rip_osiris.harvest.crossref import CrossrefNulo
from rip_osiris.probe import titles as titulos

TITULO_LARGO = (
    "Accuracy of ICD Influenza Discharge Diagnosis Codes in Hospitalized Adults "
    "From the Valencia Region Spain"
)

DOC_CON_DOI = """Estrategia de vigilancia de la gripe 2025

La evidencia que sustenta este apartado procede de un estudio previo
(doi:10.1111/irv.70069) realizado en la Comunitat Valenciana.

Referencias

1. Mira-Iglesias A, et al. Accuracy of ICD Influenza Discharge Diagnosis
   Codes in Hospitalized Adults From the Valencia Region, Spain.
   Influenza Other Respir Viruses. 2025. doi:10.1111/irv.70069
"""

DOC_SIN_DOI = """Plan de respuesta frente a la gripe 2024

Entre los trabajos considerados destaca: Accuracy of ICD Influenza Discharge
Diagnosis Codes in Hospitalized Adults From the Valencia Region Spain, que
aporta evidencia local sobre la codificación de altas hospitalarias.
"""


class TestBucleCompleto(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = Config(root=self.tmp.name)
        self.store = Store(pathlib.Path(self.tmp.name) / "test.sqlite")
        self.output_id = self.store.upsert_output(
            doi="10.1111/irv.70069", title=TITULO_LARGO, year=2025
        )
        self.doc_doi = self._documento("gva", "estrategia-2025", DOC_CON_DOI, "estrategia")
        self.doc_titulo = self._documento(
            "gva", "plan-2024", DOC_SIN_DOI, "plan", titulo="<script>alert(1)</script> Plan de gripe"
        )

    def _documento(self, source, source_id, texto, doc_type, titulo=None) -> int:
        ruta = pathlib.Path(self.tmp.name) / f"{source_id}.txt"
        ruta.write_text(texto, encoding="utf-8")
        doc_id = self.store.upsert_document(
            source=source,
            source_id=source_id,
            url=f"https://san.gva.es/{source_id}.pdf",
            title=titulo or f"Documento {source_id}",
            doc_type=doc_type,
        )
        self.store.conn.execute(
            "UPDATE documents SET fulltext_path = ?, sha256 = ? WHERE id = ?",
            (str(ruta), "a" * 64, doc_id),
        )
        self.store.conn.commit()
        return doc_id

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_doi_en_cuerpo_genera_impacto(self):
        resumen = pipeline.procesar_documento(
            self.store, self.doc_doi, self.cfg, crossref=CrossrefNulo()
        )
        self.assertGreaterEqual(resumen.aristas_impact, 1)
        filas = self.store.conn.execute(
            "SELECT * FROM edges WHERE dst_id = ? AND edge_type = 'impact'", (self.doc_doi,)
        ).fetchall()
        self.assertTrue(filas)
        self.assertIn("10.1111/irv.70069", filas[0]["evidence_literal"].lower())

    def test_titulo_sin_doi_genera_impacto(self):
        resumen = titulos.procesar_documento_titulos(self.store, self.doc_titulo, self.cfg)
        self.assertEqual(resumen["aristas_nuevas"], 1)

    def test_informe_deduplica_salida_citada_por_doi_y_titulo(self):
        # El mismo documento cita la salida de las dos formas: una ficha,
        # dos evidencias (una por vía), no dos "hallazgos".
        pipeline.procesar_documento(self.store, self.doc_doi, self.cfg, crossref=CrossrefNulo())
        titulos.procesar_documento_titulos(self.store, self.doc_doi, self.cfg)

        info = dossier_html.generar(self.store, pathlib.Path(self.tmp.name) / "d.html")
        self.assertEqual(info["documentos"], 2)
        self.assertEqual(info["hallazgos"], 1)  # una salida citada en doc_doi
        self.assertGreaterEqual(info["menciones"], 2)  # DOI + título

    def test_informe_agrupa_y_no_pide_recursos_externos(self):
        pipeline.procesar_documento(self.store, self.doc_doi, self.cfg, crossref=CrossrefNulo())
        titulos.procesar_documento_titulos(self.store, self.doc_titulo, self.cfg)

        salida = pathlib.Path(self.tmp.name) / "docs" / "demo.html"
        info = dossier_html.generar(self.store, salida, "Prueba de rastreo")

        self.assertTrue(salida.exists())
        self.assertEqual(info["documentos"], 2)
        self.assertEqual(info["con_hallazgos"], 2)
        self.assertGreaterEqual(info["hallazgos"], 2)

        html = salida.read_text(encoding="utf-8")
        self.assertIn("Accuracy of ICD Influenza", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)  # escapado
        self.assertNotIn("<script src=", html)
        self.assertNotIn('<link rel="stylesheet"', html)
        self.assertIn("0 hallazgos no significa", html)
        self.assertIn("a" * 12, html)


class TestEscapado(unittest.TestCase):
    def test_escapa_html(self):
        self.assertEqual(dossier_html._esc("<b>&</b>"), "&lt;b&gt;&amp;&lt;/b&gt;")
        self.assertEqual(dossier_html._esc(None), "")


if __name__ == "__main__":
    unittest.main()
