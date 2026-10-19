"""Normalización de DOI, años y tokens para el matcher."""
import unittest

from rip_osiris.cascade.normalize import (
    extraer_anio,
    extraer_doi,
    normalizar_doi,
    normalizar_texto,
    tokens,
)


class TestNormalize(unittest.TestCase):
    def test_doi_desde_url(self):
        self.assertEqual(
            normalizar_doi("https://doi.org/10.1016/S2214-109X(20)30393-4"),
            "10.1016/s2214-109x(20)30393-4",
        )

    def test_doi_con_prefijo(self):
        self.assertEqual(normalizar_doi("doi: 10.1111/irv.70069"), "10.1111/irv.70069")

    def test_doi_sin_doi(self):
        self.assertIsNone(normalizar_doi("un texto cualquiera"))
        self.assertIsNone(normalizar_doi(None))

    def test_extraer_doi_en_frase(self):
        frase = "Véase doi.org/10.2807/1560-7917.ES.2019.24.31.1800461."
        self.assertEqual(
            extraer_doi(frase), "10.2807/1560-7917.es.2019.24.31.1800461"
        )

    def test_anio_ultimo(self):
        self.assertEqual(extraer_anio("Plan 2015, revisado en 2020"), 2020)
        self.assertIsNone(extraer_anio("sin año"))

    def test_tokens_sin_acentos_ni_puntuacion(self):
        self.assertEqual(
            tokens("Plan de Salud, Comunitat Valenciana (2020)"),
            ["plan", "salud", "comunitat", "valenciana", "2020"],
        )

    def test_normalizar_texto(self):
        self.assertEqual(normalizar_texto("  Estrategia   de SALUD  "), "estrategia de salud")


if __name__ == "__main__":
    unittest.main()
