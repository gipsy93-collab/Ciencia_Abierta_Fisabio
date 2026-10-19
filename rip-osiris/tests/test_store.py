"""Invariantes del almacén: sin literal no hay arista ni referencia."""
import pathlib
import tempfile
import unittest

from rip_osiris.corpus.store import Store
from rip_osiris.provenance import nueva_acta


class TestStoreInvariantes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(pathlib.Path(self.tmp.name) / "test.sqlite")
        self.doc_a = self.store.upsert_document(
            source="test", source_id="a", title="Estrategia de Salud 2024", org="GVA", year=2024
        )
        self.doc_b = self.store.upsert_document(
            source="test", source_id="b", title="Plan de Salud 2020", org="GVA", year=2020
        )

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_arista_sin_literal_falla(self):
        with self.assertRaises(ValueError):
            self.store.insert_edge(
                src_kind="document",
                src_id=self.doc_a,
                dst_kind="document",
                dst_id=self.doc_b,
                edge_type="cascade",
                evidence_literal="",
            )

    def test_arista_literal_no_presente_falla(self):
        with self.assertRaises(ValueError):
            self.store.insert_edge(
                src_kind="document",
                src_id=self.doc_a,
                dst_kind="document",
                dst_id=self.doc_b,
                edge_type="cascade",
                evidence_literal="Plan de Salud 2020",
                texto_fuente="texto donde no aparece la cita",
            )

    def test_arista_valida(self):
        literal = "Plan de Salud de la Comunitat Valenciana 2020"
        texto = f"Como establece el {literal}, se prioriza la prevención."
        self.store.insert_edge(
            src_kind="document",
            src_id=self.doc_a,
            dst_kind="document",
            dst_id=self.doc_b,
            edge_type="cascade",
            evidence_literal=literal,
            texto_fuente=texto,
            method="corpus_match",
            confidence=0.91,
            acta=nueva_acta(
                kind="edge",
                literal=literal,
                method="corpus_match",
                source="test",
                confidence=0.91,
            ),
        )
        filas = self.store.conn.execute("SELECT * FROM edges").fetchall()
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["edge_type"], "cascade")
        self.assertIsNotNone(filas[0]["provenance_id"])

    def test_ref_sin_cadena_falla(self):
        with self.assertRaises(ValueError):
            self.store.insert_ref(self.doc_a, "   ")

    def test_upsert_output_idempotente_por_doi(self):
        primero = self.store.upsert_output(doi="10.1111/irv.70069", title="A", year=2025)
        segundo = self.store.upsert_output(doi="10.1111/irv.70069", title="A", year=2025)
        self.assertEqual(primero, segundo)
        total = self.store.conn.execute("SELECT COUNT(*) FROM outputs").fetchone()[0]
        self.assertEqual(total, 1)

    def test_upsert_document_idempotente(self):
        otro = self.store.upsert_document(source="test", source_id="a", title="Cambiado")
        self.assertEqual(otro, self.doc_a)
        total = self.store.conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        self.assertEqual(total, 2)

    def test_coverage_se_declara(self):
        self.store.set_coverage("orcid", "works/x", hits=0, declared="no medido")
        fila = self.store.coverage()[0]
        self.assertEqual(fila["declared"], "no medido")
        self.assertEqual(fila["hits"], 0)


if __name__ == "__main__":
    unittest.main()
