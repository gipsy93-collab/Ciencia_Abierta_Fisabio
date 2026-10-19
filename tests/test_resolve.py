"""Orden de resolución y marca de verificación (diseño §5)."""
import unittest

from rip_osiris.cascade.match import CorpusIndex, Doc
from rip_osiris.cascade.resolve import resolver
from rip_osiris.config import Config
from rip_osiris.harvest.crossref import CrossrefNulo


class _CrossrefFalso:
    disponible = True

    def __init__(self, existentes=(), hallazgos=None):
        self.existentes = set(existentes)
        self.hallazgos = hallazgos or {}
        self.consultas = []

    def existe(self, doi):
        return doi in self.existentes

    def query_bibliographic(self, texto):
        self.consultas.append(texto)
        return self.hallazgos.get(texto)


class TestResolve(unittest.TestCase):
    def setUp(self):
        self.cfg = Config(root=".")
        self.index = CorpusIndex(
            [Doc(7, "Plan de Salud de la Comunitat Valenciana 2020", "Conselleria de Sanitat", 2020)]
        )

    def test_doi_inline_verificado(self):
        cr = _CrossrefFalso(existentes=["10.1111/irv.70069"])
        r = resolver("Mira A. Articulo. 2025. doi:10.1111/irv.70069", self.index, cr, self.cfg)
        self.assertEqual(r.method, "doi_inline")
        self.assertTrue(r.verificado)
        self.assertEqual(r.confidence, self.cfg.conf_doi_inline)
        self.assertEqual(cr.consultas, [])

    def test_doi_inline_inexistente_cae_a_crossref(self):
        cita = "cita doi:10.1111/irv.70069"
        cr = _CrossrefFalso(hallazgos={cita: "10.9999/otro"})
        r = resolver(cita, self.index, cr, self.cfg)
        self.assertEqual(r.method, "crossref_query")
        self.assertEqual(r.doi, "10.9999/otro")

    def test_doi_inline_sin_red_se_acepta_marcado(self):
        r = resolver("cita doi:10.1111/irv.70069", self.index, CrossrefNulo(), self.cfg)
        self.assertEqual(r.method, "doi_inline")
        self.assertEqual(r.doi, "10.1111/irv.70069")
        self.assertFalse(r.verificado)
        self.assertEqual(r.confidence, self.cfg.conf_doi_inline_sin_verificar)

    def test_corpus_match_sin_doi(self):
        r = resolver(
            "Conselleria de Sanitat. Plan de Salud de la Comunitat Valenciana 2020. Valencia; 2020.",
            self.index,
            CrossrefNulo(),
            self.cfg,
        )
        self.assertEqual(r.method, "corpus_match")
        self.assertEqual(r.doc_id, 7)

    def test_sin_resolver(self):
        r = resolver("Ministerio de Sanidad. Estrategia de Salud Mental 2021. Madrid; 2021.", self.index, CrossrefNulo(), self.cfg)
        self.assertEqual(r.method, "unresolved")
        self.assertIsNone(r.doc_id)
        self.assertIsNone(r.doi)


if __name__ == "__main__":
    unittest.main()
