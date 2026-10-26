"""Mención por título literal: exacta, tolerante a acentos y a guiones de línea."""
import pathlib
import tempfile
import unittest

from rip_osiris.config import Config
from rip_osiris.corpus.pages import guardar_mapa
from rip_osiris.corpus.store import Store
from rip_osiris.probe.titles import (
    buscar_titulos,
    normalizar_con_mapa,
    procesar_documento_titulos,
)

TITULO_CORTO = "Efectividad de la vacunación antigripal en personas mayores de 65 años"

TEXTO_CORTO = """Referencias

12. Autores varios. Efectividad de la vacunación antigripal en personas
mayores de 65 años. Rev Esp Salud Publica. 2024;98:e1-e10.
"""

TITULO_LARGO = (
    "Accuracy of ICD Influenza Discharge Diagnosis Codes in Hospitalized Adults "
    "From the Valencia Region Spain"
)

TEXTO_LARGO = """Referencias

8. Mira-Iglesias A, et al. Accuracy of ICD Influen-
za Discharge Diagnosis Codes in Hospitalized Adults From the
Valencia Region, Spain. Influenza Other Respir Viruses. 2025.
"""


class TestNormalizacion(unittest.TestCase):
    def test_acentos_y_mayusculas(self):
        norm, _ = normalizar_con_mapa("Vacunación ANTIGRIPAL")
        self.assertEqual(norm, "vacunacion antigripal")

    def test_guion_de_fin_de_linea_no_separa(self):
        norm, _ = normalizar_con_mapa("Influen-\nza y gripe")
        self.assertEqual(norm, "influenza y gripe")

    def test_mapa_devuelve_offset_original(self):
        texto = "xx\n\nEfectividad"
        norm, mapa = normalizar_con_mapa(texto)
        pos = norm.index("efectividad")
        self.assertEqual(texto[mapa[pos] : mapa[pos] + 4], "Efec")


class TestBusqueda(unittest.TestCase):
    def test_encuentra_titulo_corto_con_umbral_bajo(self):
        hits = buscar_titulos(TEXTO_CORTO, [(1, TITULO_CORTO)], min_tokens=6)
        self.assertEqual(len(hits), 1)
        self.assertIn(hits[0].literal, TEXTO_CORTO)
        self.assertIn("vacunación", hits[0].literal)
        self.assertEqual(TEXTO_CORTO[hits[0].offset : hits[0].offset + 10], hits[0].literal[:10])

    def test_umbral_por_defecto_no_acepta_titulo_corto(self):
        self.assertEqual(buscar_titulos(TEXTO_CORTO, [(1, TITULO_CORTO)]), [])

    def test_titulo_cruzando_guion_y_salto(self):
        hits = buscar_titulos(TEXTO_LARGO, [(2, TITULO_LARGO)])
        self.assertEqual(len(hits), 1)
        self.assertIn("Influen-\nza", hits[0].literal)
        self.assertIn(hits[0].literal, TEXTO_LARGO)

    def test_titulo_parcial_no_es_mencion(self):
        parcial = " ".join(TITULO_LARGO.split()[:6])
        self.assertEqual(buscar_titulos(TEXTO_LARGO, [(2, parcial)]), [])

    def test_titulo_ausente(self):
        self.assertEqual(buscar_titulos("texto sin nada", [(1, TITULO_LARGO)]), [])


class TestPersistencia(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = Config(root=self.tmp.name)
        self.store = Store(pathlib.Path(self.tmp.name) / "test.sqlite")
        self.output_id = self.store.upsert_output(
            doi="10.1111/irv.70069", title=TITULO_CORTO, year=2024
        )
        relleno = "Contenido previo de la estrategia. " * 20
        self.texto = relleno + "\n\n" + TEXTO_CORTO
        ruta = pathlib.Path(self.tmp.name) / "doc.txt"
        ruta.write_text(self.texto, encoding="utf-8")
        self.doc_id = self.store.upsert_document(
            source="gva", source_id="estrategia-2024", title="Estrategia", doc_type="estrategia"
        )
        self.store.conn.execute(
            "UPDATE documents SET fulltext_path = ? WHERE id = ?", (str(ruta), self.doc_id)
        )
        self.store.conn.commit()
        guardar_mapa(self.cfg, self.doc_id, [0, len(relleno) + 5])

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_inserta_arista_con_pagina(self):
        resumen = procesar_documento_titulos(
            self.store, self.doc_id, self.cfg, min_tokens=6
        )
        self.assertEqual(resumen["aristas_nuevas"], 1)
        fila = self.store.conn.execute("SELECT * FROM edges").fetchone()
        self.assertEqual(fila["edge_type"], "impact")
        self.assertEqual(fila["method"], "titulo_literal")
        self.assertEqual(fila["src_id"], self.output_id)
        import json

        payload = self.store.conn.execute(
            "SELECT payload_json FROM provenance WHERE id = ?", (fila["provenance_id"],)
        ).fetchone()
        self.assertEqual(json.loads(payload["payload_json"])["extra"]["page"], 2)


if __name__ == "__main__":
    unittest.main()
