"""Semilla OpenAlex: deduplicaciÃ³n, filtro por ROR y cortesÃ­a (sin red)."""
import unittest

import httpx

from rip_osiris.seed.openalex import (
    OpenAlexClient,
    Obra,
    _mejor_por_doi,
    parsear,
    ror_corto,
)


def _respuesta(status: int, cuerpo: dict | None = None) -> httpx.Response:
    return httpx.Response(
        status,
        json=cuerpo or {},
        request=httpx.Request("GET", "https://api.openalex.org/works"),
    )


class _ClienteFalso:
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = []

    def get(self, url, params=None, headers=None):
        self.llamadas.append((url, dict(params or {})))
        if not self.respuestas:
            raise AssertionError("respuesta inesperada")
        return self.respuestas.pop(0)

    def close(self):
        pass


def _item(oid: str, doi: str | None, titulo: str = "T", refs: int = 0) -> dict:
    return {
        "id": f"https://openalex.org/{oid}",
        "doi": doi,
        "title": titulo,
        "publication_year": 2024,
        "type": "article",
        "cited_by_count": 3,
        "referenced_works_count": refs,
    }


class TestParseo(unittest.TestCase):
    def test_ror_corto(self):
        self.assertEqual(ror_corto("https://ror.org/0116vew40"), "0116vew40")
        self.assertEqual(ror_corto("ror.org/0116vew40"), "0116vew40")

    def test_dedupe_por_doi_conserva_el_rico(self):
        obras = parsear(
            {"results": [_item("W1", "https://doi.org/10.1234/X", refs=0), _item("W2", "https://doi.org/10.1234/x", refs=9)]}
        )
        self.assertEqual(len(obras), 2)  # dos registros, mismo DOI
        mejores = _mejor_por_doi(obras)
        self.assertEqual(len(mejores), 1)
        self.assertEqual(mejores[0].openalex_id, "W2")
        self.assertEqual(mejores[0].doi, "10.1234/x")

    def test_sin_doi_se_conserva_por_id(self):
        obras = parsear({"results": [_item("W1", None), _item("W2", None)]})
        self.assertEqual(len(obras), 2)

    def test_sin_titulo_se_descarta(self):
        obras = parsear({"results": [_item("W1", "10.1234/x", titulo="")]})
        self.assertEqual(obras, [])


class TestCliente(unittest.TestCase):
    def test_obras_pide_filtro_ror_y_mailto(self):
        falso = _ClienteFalso([_respuesta(200, {"results": [_item("W1", "10.1234/x")], "meta": {}})])
        cli = OpenAlexClient("0116vew40", mailto="yo@example.org", client=falso)
        obras = cli.obras(5)
        self.assertEqual(len(obras), 1)
        _, params = falso.llamadas[0]
        self.assertIn("authorships.institutions.ror:0116vew40", params["filter"])
        self.assertIn("has_doi:true", params["filter"])
        self.assertEqual(params["mailto"], "yo@example.org")

    def test_paginacion_por_cursor(self):
        falso = _ClienteFalso(
            [
                _respuesta(200, {"results": [_item("W1", "10.1234/a")], "meta": {"next_cursor": "abc"}}),
                _respuesta(200, {"results": [_item("W2", "10.1234/b")], "meta": {}}),
            ]
        )
        cli = OpenAlexClient("0116vew40", client=falso, per_page=1)
        obras = cli.obras(2)
        self.assertEqual([o.openalex_id for o in obras], ["W1", "W2"])
        self.assertEqual(falso.llamadas[1][1]["cursor"], "abc")

    def test_por_dois_usa_or(self):
        falso = _ClienteFalso([_respuesta(200, {"results": [_item("W1", "10.1234/a")], "meta": {}})])
        cli = OpenAlexClient("0116vew40", client=falso)
        cli.por_dois(["https://doi.org/10.1234/A", "10.1234/b"])
        _, params = falso.llamadas[0]
        self.assertEqual(params["filter"], "doi:10.1234/a|10.1234/b")

    def test_404_es_ausencia(self):
        falso = _ClienteFalso([_respuesta(404)])
        cli = OpenAlexClient("0116vew40", client=falso)
        self.assertEqual(cli.obras(3), [])

    def test_500_tras_reintentos_lanza(self):
        from rip_osiris.seed.openalex import OpenAlexError

        falso = _ClienteFalso([_respuesta(500)] * 3)
        cli = OpenAlexClient("0116vew40", client=falso, max_reintentos=2)
        with self.assertRaises(OpenAlexError):
            cli.obras(3)

    def test_buscar_anade_default_search(self):
        falso = _ClienteFalso([_respuesta(200, {"results": [], "meta": {}})])
        cli = OpenAlexClient("0116vew40", client=falso)
        cli.obras(3, buscar="influenza vaccine")
        _, params = falso.llamadas[0]
        self.assertIn("default.search:influenza vaccine", params["filter"])


if __name__ == "__main__":
    unittest.main()
