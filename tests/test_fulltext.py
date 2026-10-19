"""fulltext y html_a_texto: conversión de HTML del BOE sin perder literales."""
import unittest

from rip_osiris.corpus.fulltext import html_a_texto


HTML_BOE = """<html><head><style>body{color:red}</style>
<script>var x = 1;</script></head>
<body><p>Ley&nbsp;16/2003, de 28 de mayo, de cohesi&oacute;n</p>
<p>La <b>Ley 14/1986</b>, de 25 de abril, General de Sanidad.</p></body></html>"""


class TestHtml(unittest.TestCase):
    def test_quita_etiquetas_y_scripts(self):
        t = html_a_texto(HTML_BOE)
        self.assertNotIn("<", t)
        self.assertNotIn("var x", t)
        self.assertNotIn("color:red", t)

    def test_decodifica_entidades(self):
        t = html_a_texto(HTML_BOE)
        self.assertIn("cohesión", t)

    def test_conserva_literal_normativo(self):
        t = html_a_texto(HTML_BOE)
        self.assertIn("Ley 14/1986", t)
        self.assertIn("Ley 16/2003", t)

    def test_espacios_colapsados(self):
        t = html_a_texto("<p>a</p>\n\n<p>b</p>")
        self.assertEqual(t, "a b")

    def test_vacio(self):
        self.assertEqual(html_a_texto(""), "")

    def test_entidad_numerica(self):
        self.assertIn("ñ", html_a_texto("a&#241;o"))


if __name__ == "__main__":
    unittest.main()
