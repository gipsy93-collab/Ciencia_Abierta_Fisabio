"""La cascada (rama c): el matcher in-corpus y su regla de oro."""
import unittest

from rip_osiris.cascade.match import CorpusIndex, Doc
from rip_osiris.config import Config


class TestMatcher(unittest.TestCase):
    def setUp(self):
        self.cfg = Config(root=".")
        self.corpus = [
            Doc(
                doc_id=1,
                title="Plan de Salud de la Comunitat Valenciana 2020",
                org="Conselleria de Sanitat",
                year=2020,
            ),
            Doc(
                doc_id=2,
                title="Estrategia de Salud Digital de la Unión Europea",
                org="Comisión Europea",
                year=2022,
            ),
        ]
        self.index = CorpusIndex(self.corpus)

    def test_match_exacto(self):
        ref = (
            "Conselleria de Sanitat. Plan de Salud de la Comunitat Valenciana "
            "2020. Valencia: Generalitat Valenciana; 2020."
        )
        m = self.index.match(ref, self.cfg)
        self.assertIsNotNone(m)
        self.assertEqual(m.doc_id, 1)
        self.assertGreaterEqual(m.score, self.cfg.match_min_score)

    def test_sin_anio_no_hay_arista(self):
        ref = "Conselleria de Sanitat. Plan de Salud de la Comunitat Valenciana."
        self.assertIsNone(self.index.match(ref, self.cfg))

    def test_anio_distinto_no_hay_arista(self):
        ref = (
            "Conselleria de Sanitat. Plan de Salud de la Comunitat Valenciana "
            "2019. Valencia; 2019."
        )
        self.assertIsNone(self.index.match(ref, self.cfg))

    def test_org_ausente_no_hay_arista(self):
        ref = "Plan de Salud de la Comunitat Valenciana 2020. Valencia; 2020."
        self.assertIsNone(self.index.match(ref, self.cfg))

    def test_titulo_parcial_bajo_umbral(self):
        ref = "Conselleria de Sanitat. Plan de Salud 2020."
        self.assertIsNone(self.index.match(ref, self.cfg))

    def test_referencia_ajena(self):
        ref = "Ministerio de Sanidad. Estrategia de Salud Mental 2021. Madrid; 2021."
        self.assertIsNone(self.index.match(ref, self.cfg))

    def test_sin_org_y_anio_si_se_configura(self):
        cfg = Config(root=".", require_org_and_year=False)
        ref = "Plan de Salud de la Comunitat Valenciana 2020. Valencia; 2020."
        m = self.index.match(ref, cfg)
        self.assertIsNotNone(m)
        self.assertEqual(m.doc_id, 1)

    def test_referencia_vacia(self):
        self.assertIsNone(self.index.match("", self.cfg))


if __name__ == "__main__":
    unittest.main()
