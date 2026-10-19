"""Recorrido del grafo y expediente tipado N1-N6."""
import pathlib
import tempfile
import unittest

from rip_osiris.cascade import graph
from rip_osiris.corpus.store import Store
from rip_osiris.dossier import expediente


class TestGrafoYExpediente(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(pathlib.Path(self.tmp.name) / "test.sqlite")
        self.out = self.store.upsert_output(
            doi="10.1016/s2214-109x(20)30393-4",
            title="Global burden of acute lower respiratory infection",
            year=2020,
            source="orcid",
        )
        self.doc1 = self.store.upsert_document(
            source="test",
            source_id="d1",
            title="Plan de Salud 2020",
            org="GVA",
            year=2020,
            doc_type="plan_salud",
        )
        self.doc2 = self.store.upsert_document(
            source="test",
            source_id="d2",
            title="Estrategia de Salud 2024",
            org="GVA",
            year=2024,
            doc_type="estrategia",
        )
        self._arista("output", self.out, "document", self.doc1, "impact", "cita 1")
        self._arista("document", self.doc1, "document", self.doc2, "cascade", "cita 2")

    def _arista(self, sk, si, dk, di, tipo, literal):
        self.store.insert_edge(
            src_kind=sk,
            src_id=si,
            dst_kind=dk,
            dst_id=di,
            edge_type=tipo,
            evidence_literal=literal,
        )

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_recorrido_dos_saltos(self):
        filas = graph.recorrer(self.store.conn, "output", self.out, 3)
        tipos = {f["edge_type"] for f in filas}
        self.assertEqual(tipos, {"impact", "cascade"})
        self.assertEqual(len(filas), 2)

    def test_recorrido_un_salto(self):
        filas = graph.recorrer(self.store.conn, "output", self.out, 1)
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["edge_type"], "impact")

    def test_recorrido_sin_aristas(self):
        self.assertEqual(graph.recorrer(self.store.conn, "output", 999, 3), [])

    def test_expediente_clasifica_niveles(self):
        exp = expediente.construir(self.store, self.out, 3)
        self.assertEqual(exp["output"]["id"], self.out)
        self.assertEqual(len(exp["items"]), 2)
        niveles = {it["nivel"] for it in exp["items"]}
        self.assertEqual(niveles, {"N3"})
        self.assertTrue(all(it["document"] for it in exp["items"]))

    def test_expediente_output_inexistente(self):
        with self.assertRaises(KeyError):
            expediente.construir(self.store, 999, 3)


if __name__ == "__main__":
    unittest.main()
