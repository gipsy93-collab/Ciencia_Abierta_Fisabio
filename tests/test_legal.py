"""Citas normativas: «Ley 14/1986» no es autor-año."""
import unittest

from rip_osiris.cascade.legal import claves_normativas, normalizar_source_id


class TestLegal(unittest.TestCase):
    def test_ley_numero_anio(self):
        citas = claves_normativas("según la Ley 14/1986, de 25 de abril")
        self.assertEqual(citas[0][1], "ley-14-1986")
        self.assertEqual(citas[0][0], "Ley 14/1986")

    def test_real_decreto_ley_con_guion(self):
        citas = claves_normativas("Real Decreto-ley 7/2018, de 27 de julio")
        self.assertEqual(citas[0][1], "real-decreto-ley-7-2018")

    def test_real_decreto_legislativo(self):
        citas = claves_normativas("Real Decreto Legislativo 1/1994")
        self.assertEqual(citas[0][1], "real-decreto-legislativo-1-1994")

    def test_orden_por_fecha(self):
        citas = claves_normativas("Orden de 21 de julio de 2001")
        self.assertEqual(citas[0][1], "orden-21-07-2001")

    def test_dedupe(self):
        citas = claves_normativas("Ley 14/1986 ... Ley 14/1986 ... Ley 14/1986")
        self.assertEqual(len(citas), 1)

    def test_no_confunde_anio_suelto(self):
        citas = claves_normativas("El año 1986 fue importante para 14 personas")
        self.assertEqual(citas, [])

    def test_varias_normas(self):
        texto = "La Ley 16/2003 y la Ley 14/1986 y el Real Decreto 63/1995"
        claves = [c for _, c in claves_normativas(texto)]
        self.assertIn("ley-16-2003", claves)
        self.assertIn("ley-14-1986", claves)
        self.assertIn("real-decreto-63-1995", claves)

    def test_normalizar_source_id(self):
        self.assertEqual(normalizar_source_id("ley-14-1986"), "ley-14-1986")
        self.assertEqual(normalizar_source_id("Ley 14/1986"), "ley-14-1986")
        self.assertEqual(normalizar_source_id("  BOE-A-2014-13612 "), "boe-a-2014-13612")

    def test_literal_es_exacto(self):
        texto = "según la Ley 14/1986, de 25 de abril, General de Sanidad"
        for literal, _ in claves_normativas(texto):
            self.assertIn(literal, texto)


if __name__ == "__main__":
    unittest.main()
