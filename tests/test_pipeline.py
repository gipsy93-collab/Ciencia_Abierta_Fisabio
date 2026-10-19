"""El pipeline completo: de texto a aristas con literal verificado."""
import pathlib
import tempfile
import unittest

from rip_osiris.cascade import pipeline
from rip_osiris.config import Config
from rip_osiris.corpus.store import Store
from rip_osiris.harvest.crossref import CrossrefNulo

TEXTO = """ESTRATEGIA DE SALUD 2024

La presente estrategia se apoya en el marco previo de la Comunitat.

Referencias

1. Conselleria de Sanitat. Plan de Salud de la Comunitat Valenciana 2020.
   Valencia: Generalitat Valenciana; 2020.

2. Mira-Iglesias A, Lopez-Lacort M. Accuracy of ICD Influenza Discharge
   Diagnosis Codes in Hospitalized Adults From the Valencia Region, Spain.
   Influenza Other Respir Viruses. 2025. doi:10.1111/irv.70069

3. Ministerio de Sanidad. Estrategia de Salud Mental 2021. Madrid; 2021.
"""


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = Config(root=self.tmp.name)
        self.store = Store(pathlib.Path(self.tmp.name) / "test.sqlite")

        self.plan = self.store.upsert_document(
            source="gva",
            source_id="plan-2020",
            title="Plan de Salud de la Comunitat Valenciana 2020",
            org="Conselleria de Sanitat",
            year=2020,
            doc_type="plan_salud",
        )
        self.estrategia = self.store.upsert_document(
            source="gva",
            source_id="estrategia-2024",
            title="Estrategia de Salud 2024",
            org="Conselleria de Sanitat",
            year=2024,
            doc_type="estrategia",
        )
        self.salida = self.store.upsert_output(
            doi="10.1111/irv.70069",
            title="Accuracy of ICD Influenza Discharge Diagnosis Codes",
            year=2025,
            orcid="0000-0001-6371-8229",
        )

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _procesar(self, crossref=None):
        return pipeline.procesar_documento(
            self.store,
            self.estrategia,
            self.cfg,
            crossref=crossref or CrossrefNulo(),
            texto=TEXTO,
        )

    def test_extrae_referencias(self):
        r = self._procesar()
        self.assertGreaterEqual(r.referencias, 3)

    def test_crea_arista_cascade(self):
        r = self._procesar()
        self.assertEqual(r.por_corpus, 1)
        self.assertEqual(r.aristas_cascade, 1)
        filas = self.store.conn.execute(
            "SELECT * FROM edges WHERE edge_type = 'cascade'"
        ).fetchall()
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["src_id"], self.estrategia)
        self.assertEqual(filas[0]["dst_id"], self.plan)
        self.assertIn("Plan de Salud", filas[0]["evidence_literal"])

    def test_crea_arista_impact_por_doi(self):
        r = self._procesar()
        self.assertGreaterEqual(r.aristas_impact, 1)
        filas = self.store.conn.execute(
            "SELECT * FROM edges WHERE edge_type = 'impact'"
        ).fetchall()
        self.assertTrue(filas)
        self.assertEqual(filas[0]["src_kind"], "output")
        self.assertEqual(filas[0]["src_id"], self.salida)

    def test_referencia_ajena_queda_sin_resolver(self):
        r = self._procesar()
        self.assertEqual(r.sin_resolver, 1)

    def test_todas_las_aristas_tienen_literal(self):
        self._procesar()
        filas = self.store.conn.execute("SELECT * FROM edges").fetchall()
        self.assertTrue(filas)
        for f in filas:
            self.assertTrue(f["evidence_literal"].strip())
            self.assertIsNotNone(f["provenance_id"])

    def test_aristas_son_idempotentes(self):
        primera = self._procesar()
        antes = self.store.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        refs_antes = self.store.conn.execute("SELECT COUNT(*) FROM refs").fetchone()[0]
        segunda = self._procesar()
        despues = self.store.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        refs_despues = self.store.conn.execute("SELECT COUNT(*) FROM refs").fetchone()[0]
        self.assertEqual(antes, despues)
        self.assertEqual(refs_antes, refs_despues)
        self.assertGreater(segunda.aristas_existentes, 0)
        self.assertEqual(segunda.aristas_cascade, 0)

    def test_expediente_tras_pipeline(self):
        from rip_osiris.dossier import expediente

        self._procesar()
        exp = expediente.construir(self.store, self.salida, 3)
        self.assertEqual(exp["output"]["id"], self.salida)
        niveles = [it["nivel"] for it in exp["items"]]
        self.assertIn("N3", niveles)

    def test_texto_desde_archivo(self):
        ruta = pathlib.Path(self.tmp.name) / "doc.txt"
        ruta.write_text(TEXTO, encoding="utf-8")
        r = pipeline.procesar_documento(
            self.store, self.estrategia, self.cfg, crossref=CrossrefNulo(), texto=TEXTO
        )
        self.assertEqual(r.aristas_cascade, 1)

    def test_texto_desde_fulltext_path(self):
        ruta = pathlib.Path(self.tmp.name) / "fulltext.txt"
        ruta.write_text(TEXTO, encoding="utf-8")
        self.store.conn.execute(
            "UPDATE documents SET fulltext_path = ? WHERE id = ?",
            (str(ruta), self.estrategia),
        )
        self.store.conn.commit()
        r = pipeline.procesar_documento(
            self.store, self.estrategia, self.cfg, crossref=CrossrefNulo()
        )
        self.assertEqual(r.referencias, 3)
        self.assertEqual(r.aristas_cascade, 1)

    def test_documento_sin_fulltext_falla(self):
        with self.assertRaises(ValueError):
            pipeline.procesar_documento(
                self.store, self.estrategia, self.cfg, crossref=CrossrefNulo()
            )

    def test_documento_inexistente(self):
        with self.assertRaises(KeyError):
            pipeline.procesar_documento(
                self.store, 999, self.cfg, crossref=CrossrefNulo(), texto=TEXTO
            )


TEXTO_NORMA = """LEY DE COHESION

La presente ley desarrolla la Ley 14/1986, de 25 de abril, General de Sanidad.
"""


class TestPipelineNormas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = Config(root=self.tmp.name)
        self.store = Store(pathlib.Path(self.tmp.name) / "test.sqlite")
        self.general = self.store.upsert_document(
            source="boe",
            source_id="ley-14-1986",
            title="Ley 14/1986, de 25 de abril, General de Sanidad",
            org="Jefatura del Estado",
            year=1986,
            doc_type="ley",
        )
        self.cohesion = self.store.upsert_document(
            source="boe",
            source_id="ley-16-2003",
            title="Ley 16/2003, de 28 de mayo, de cohesion y calidad del SNS",
            org="Jefatura del Estado",
            year=2003,
            doc_type="ley",
        )

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_arista_por_cita_normativa(self):
        r = pipeline.procesar_documento(
            self.store, self.cohesion, self.cfg,
            crossref=CrossrefNulo(), texto=TEXTO_NORMA,
        )
        self.assertEqual(r.aristas_norma, 1)
        fila = self.store.conn.execute(
            "SELECT * FROM edges WHERE edge_type = 'cascade'"
        ).fetchone()
        self.assertEqual(fila["src_id"], self.cohesion)
        self.assertEqual(fila["dst_id"], self.general)
        self.assertEqual(fila["method"], "cita_normativa")
        self.assertEqual(fila["evidence_literal"], "Ley 14/1986")

    def test_no_se_autocita(self):
        r = pipeline.procesar_documento(
            self.store, self.general, self.cfg,
            crossref=CrossrefNulo(),
            texto="La Ley 14/1986, de 25 de abril, General de Sanidad.",
        )
        self.assertEqual(r.aristas_norma, 0)

    def test_cita_normativa_idempotente(self):
        for _ in range(2):
            pipeline.procesar_documento(
                self.store, self.cohesion, self.cfg,
                crossref=CrossrefNulo(), texto=TEXTO_NORMA,
            )
        n = self.store.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        self.assertEqual(n, 1)


if __name__ == "__main__":
    unittest.main()
