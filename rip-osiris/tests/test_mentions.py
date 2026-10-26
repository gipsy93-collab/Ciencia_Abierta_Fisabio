"""Menciones institucionales: literal, sin solapes, sin inventar atribución."""
import pathlib
import tempfile
import unittest

from rip_osiris.config import Config
from rip_osiris.corpus.pages import guardar_mapa
from rip_osiris.corpus.store import Store
from rip_osiris.probe.mentions import buscar_entidades, procesar_documento_menciones

TEXTO = """Agradecimientos

Este informe se elaboró con datos del sistema centinela. El estudio fue
coordinado por FISABIO y por el Área de Investigación en Vacunas de la
Comunitat Valenciana, con la colaboración de varios hospitales.

Otra línea menciona a la Fundación para el Fomento de la Investigación
Sanitaria y Biomédica de la Comunitat Valenciana (FISABIO).
"""


class TestBusqueda(unittest.TestCase):
    def test_encuentra_fisabio(self):
        menciones = buscar_entidades(TEXTO)
        entidades = [m.entidad for m in menciones]
        self.assertIn("FISABIO", entidades)
        for m in menciones:
            self.assertIn(m.literal, TEXTO)

    def test_no_confunde_subcadena(self):
        texto = "La FISABIOLOGIA no es una institución."
        self.assertEqual([m for m in buscar_entidades(texto) if m.entidad == "FISABIO"], [])

    def test_variante_larga_gana_sin_solape(self):
        texto = "Coordinado por FISABIO-Public Health en 2024."
        menciones = buscar_entidades(texto)
        self.assertEqual(len(menciones), 1)
        self.assertIn("FISABIO", menciones[0].literal)

    def test_grupo(self):
        menciones = buscar_entidades(TEXTO)
        tipos = {m.tipo for m in menciones}
        self.assertIn("grupo", tipos)

    def test_sin_menciones(self):
        self.assertEqual(buscar_entidades("Un texto cualquiera sin instituciones."), [])


class TestPersistencia(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = Config(root=self.tmp.name)
        self.store = Store(pathlib.Path(self.tmp.name) / "test.sqlite")
        ruta = pathlib.Path(self.tmp.name) / "doc.txt"
        relleno = "Contexto previo de la recomendación. " * 12
        self.texto = relleno + "\n\n" + TEXTO
        ruta.write_text(self.texto, encoding="utf-8")
        self.doc_id = self.store.upsert_document(
            source="sanidad.gob.es",
            source_id="recomendaciones-2025",
            url="https://www.sanidad.gob.es/x.pdf",
            title="Recomendaciones de vacunación",
            doc_type="estrategia",
        )
        self.store.conn.execute(
            "UPDATE documents SET fulltext_path = ? WHERE id = ?", (str(ruta), self.doc_id)
        )
        self.store.conn.commit()
        guardar_mapa(self.cfg, self.doc_id, [0, len(relleno) + 5])

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_registra_mencion_con_pagina(self):
        resumen = procesar_documento_menciones(self.store, self.doc_id, self.cfg)
        self.assertGreaterEqual(resumen["nuevas"], 2)
        filas = self.store.conn.execute("SELECT * FROM mentions ORDER BY id").fetchall()
        self.assertTrue(filas)
        self.assertTrue(all(f["doc_id"] == self.doc_id for f in filas))
        self.assertEqual(filas[0]["page"], 2)
        self.assertIsNotNone(filas[0]["provenance_id"])

    def test_idempotente(self):
        procesar_documento_menciones(self.store, self.doc_id, self.cfg)
        segundo = procesar_documento_menciones(self.store, self.doc_id, self.cfg)
        self.assertEqual(segundo["nuevas"], 0)

    def test_no_crea_aristas_de_impacto(self):
        procesar_documento_menciones(self.store, self.doc_id, self.cfg)
        total = self.store.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        self.assertEqual(total, 0)


if __name__ == "__main__":
    unittest.main()
