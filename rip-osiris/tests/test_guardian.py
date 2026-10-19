"""Invariantes del guardián de fidelidad (protocolo S69).

Sin literal en la fuente no hay hallazgo; se admite la variante desguionizada
por los cortes de línea del PDF.
"""
import unittest

from rip_osiris.guardian import contiene_literal, desguionizar, exigir_literal


class TestGuardian(unittest.TestCase):
    def test_literal_exacto(self):
        texto = "El plan de salud contempla la vacunación infantil."
        self.assertTrue(contiene_literal(texto, "vacunación infantil"))

    def test_no_literal(self):
        texto = "El plan de salud contempla la vacunación infantil."
        self.assertFalse(contiene_literal(texto, "vacunación de adultos"))

    def test_espacios_colapsados(self):
        texto = "El plan   de salud\ncontempla la vacunación."
        self.assertTrue(contiene_literal(texto, "plan de salud contempla"))

    def test_desguionizado(self):
        texto = "La efectividad vacu-\nnacional fue alta."
        self.assertTrue(contiene_literal(texto, "vacunacional fue alta"))

    def test_desguionizar_une_palabras(self):
        self.assertEqual(desguionizar("vacu-\nnacional"), "vacunacional")

    def test_exigir_literal_lanza(self):
        with self.assertRaises(ValueError):
            exigir_literal("texto fuente", "fragmento inventado")

    def test_vacio_no_es_literal(self):
        self.assertFalse(contiene_literal("", "algo"))
        self.assertFalse(contiene_literal("texto", ""))


if __name__ == "__main__":
    unittest.main()
