"""Extracción de referencias: división de bloques sin numerar."""
import unittest

from rip_osiris.cascade import references

BLOQUE_APA = """REFERENCIAS BIBLIOGRÁFICAS
Abadal-Falgueras, E., Abad-García, F. y Santos-Hermosa, G.
(2023). Ciencia abierta en España 2023. Barcelona: Grupo Ciencia
Abierta. http://hdl.handle.net/2445/200020
Berens, P., Cranmer, K. y Montgomery, J. (2023). AI for Science:
An Emerging Agenda. http://arxiv.org/abs/2303.04217
CORDIS (2025). Repositorio de resultados de investigaciones de la
Unión Europea. https://cordis.europa.eu/es
"""

BLOQUE_NUMERADO = """Bibliografía
1. Conselleria de Sanitat. Plan de Salud de la Comunitat Valenciana
   2020. Valencia: Generalitat Valenciana; 2020.
2. Ministerio de Sanidad. Estrategia de Salud Mental 2021. Madrid; 2021.
"""


class TestReferences(unittest.TestCase):
    def test_detecta_inicio(self):
        ini = references.detectar_inicio_bibliografia(BLOQUE_APA)
        self.assertEqual(ini, 0)
        self.assertIsNone(references.detectar_inicio_bibliografia("Sin lista final."))

    def test_divide_bloque_apa_sin_numerar(self):
        refs = references.dividir_referencias(BLOQUE_APA)
        self.assertEqual(len(refs), 3)
        self.assertTrue(refs[0].startswith("Abadal-Falgueras"))
        self.assertTrue(refs[1].startswith("Berens"))
        self.assertTrue(refs[2].startswith("CORDIS"))

    def test_no_parte_autores_en_lineas_sueltas(self):
        refs = references.dividir_referencias(BLOQUE_APA)
        self.assertIn("Abad-García, F. y Santos-Hermosa, G.", refs[0])
        self.assertIn("Cranmer, K.", refs[1])

    def test_division_numerada(self):
        refs = references.dividir_referencias(BLOQUE_NUMERADO)
        self.assertEqual(len(refs), 2)
        self.assertTrue(refs[0].startswith("Conselleria"))
        self.assertTrue(refs[1].startswith("Ministerio"))

    def test_url_suelta_se_pega_a_la_anterior(self):
        bloque = (
            "Bibliografia\n"
            "Piñeiro-Naval, V. (2020). The content analysis methodology. "
            "Communication & Society, 33(3).\n"
            "https://tinyurl.com/3u4fk8fj\n"
            "Sierra-Caballero, F. (2022). Comunicología abierta. ThinkEPI.\n"
        )
        refs = references.dividir_referencias(bloque)
        self.assertEqual(len(refs), 2)
        self.assertIn("tinyurl.com/3u4fk8fj", refs[0])

    def test_ignora_cadenas_cortas(self):
        refs = references.dividir_referencias("Bibliografía\nAA\nBB\n")
        self.assertEqual(refs, [])

    def test_extraer_marca_seccion_y_offset(self):
        refs = references.extraer("Cuerpo del texto.\n\n" + BLOQUE_APA)
        self.assertTrue(refs)
        for r in refs:
            self.assertEqual(r.section, "bibliografia")
            self.assertGreaterEqual(r.offset, 0)

    def test_extraer_sin_bibliografia_usa_cuerpo(self):
        refs = references.extraer("Solo texto suelto sin lista final.")
        self.assertTrue(all(r.section == "cuerpo" for r in refs))

    def test_texto_vacio(self):
        self.assertEqual(references.extraer(""), [])

    def test_no_confunde_la_palabra_referencias_en_el_cuerpo(self):
        texto = (
            "Artículo 1. Las referencias que en esta ley se realizan a las "
            "competencias de las comunidades autónomas se entenderán hechas "
            "al Estado en relación con las Ciudades de Ceuta y Melilla, sin "
            "perjuicio de las competencias de dichas ciudades. " * 40
        )
        self.assertIsNone(references.detectar_inicio_bibliografia(texto))
        for r in references.extraer(texto):
            self.assertLessEqual(len(r.raw), references.MAX_LONGITUD_REF)

    def test_no_devuelve_el_documento_entero_como_referencia(self):
        texto = "Texto de una ley sin bibliografía. " * 200
        self.assertEqual(references.extraer(texto), [])

    def test_referencia_es_literal_en_la_fuente(self):
        from rip_osiris.guardian import contiene_literal

        texto = BLOQUE_APA
        for r in references.extraer(texto):
            self.assertTrue(
                contiene_literal(texto, r.raw),
                f"no literal: {r.raw[:60]!r}",
            )


if __name__ == "__main__":
    unittest.main()
