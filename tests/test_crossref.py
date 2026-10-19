"""CrossrefClient: umbrales, cachÃ© y polÃ­tica de fallo (sin red real)."""
import unittest

import httpx

from rip_osiris.harvest.crossref import (
    CrossrefClient,
    CrossrefError,
    CrossrefNulo,
    USER_AGENT,
    coincidencia_titulo,
)


def _respuesta(status: int, cuerpo: dict | None = None) -> httpx.Response:
    return httpx.Response(
        status,
        json=cuerpo or {},
        request=httpx.Request("GET", "https://api.crossref.org/works"),
    )


class _ClienteFalso(httpx.Client):
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = []

    def get(self, url, params=None, headers=None):
        self.llamadas.append((url, params, headers))
        if not self.respuestas:
            raise AssertionError("respuesta inesperada")
        r = self.respuestas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def close(self):
        pass


def _cliente(respuestas, **kw):
    falso = _ClienteFalso(respuestas)
    cli = CrossrefClient("test@example.org", client=falso, **kw)
    return cli, falso


class TestCrossref(unittest.TestCase):
    def test_existe_200(self):
        cli, falso = _cliente([_respuesta(200, {"message": {"DOI": "10.1234/x"}})])
        self.assertTrue(cli.existe("10.1234/x"))
        self.assertEqual(len(falso.llamadas), 1)

    def test_existe_404_no_es_error(self):
        cli, _ = _cliente([_respuesta(404)])
        self.assertFalse(cli.existe("10.1234/no-existe"))

    def test_existe_normaliza_doi(self):
        cli, falso = _cliente([_respuesta(200)])
        cli.existe("https://doi.org/10.1111/IRV.70069")
        self.assertIn("10.1111/irv.70069", falso.llamadas[0][0])

    def test_existe_cachea(self):
        cli, falso = _cliente([_respuesta(200)])
        self.assertTrue(cli.existe("10.1234/x"))
        self.assertTrue(cli.existe("10.1234/x"))
        self.assertEqual(len(falso.llamadas), 1)

    def test_existe_doi_invalido(self):
        cli, falso = _cliente([])
        self.assertFalse(cli.existe("no es un doi"))
        self.assertEqual(falso.llamadas, [])

    def test_existe_500_lanza(self):
        cli, _ = _cliente([_respuesta(500)] * 3)
        with self.assertRaises(CrossrefError):
            cli.existe("10.1234/x")

    def test_query_elige_candidato_valido(self):
        cuerpo = {
            "message": {
                "items": [
                    {
                        "DOI": "10.1111/IRV.70069",
                        "title": [
                            "Accuracy of ICD Influenza Discharge Diagnosis Codes "
                            "in Hospitalized Adults"
                        ],
                        "score": 82.0,
                    }
                ]
            }
        }
        cli, _ = _cliente([_respuesta(200, cuerpo)])
        ref = (
            "LÃ³pez-Lacort M, Mira-Iglesias A. Accuracy of ICD Influenza Discharge "
            "Diagnosis Codes in Hospitalized Adults. Influenza Other Respir Viruses. "
            "2025."
        )
        self.assertEqual(cli.query_bibliographic(ref), "10.1111/irv.70069")

    def test_query_rechaza_score_bajo(self):
        cuerpo = {
            "message": {
                "items": [
                    {
                        "DOI": "10.1234/bajo",
                        "title": ["Accuracy of ICD Influenza Discharge Diagnosis Codes"],
                        "score": 12.0,
                    }
                ]
            }
        }
        cli, _ = _cliente([_respuesta(200, cuerpo)])
        ref = "Accuracy of ICD Influenza Discharge Diagnosis Codes in Hospitalized Adults"
        self.assertIsNone(cli.query_bibliographic(ref))

    def test_query_rechaza_titulo_distinto(self):
        cuerpo = {
            "message": {
                "items": [
                    {
                        "DOI": "10.1234/otro",
                        "title": ["Memoria sobre la situaciÃ³n socioeconÃ³mica"],
                        "score": 95.0,
                    }
                ]
            }
        }
        cli, _ = _cliente([_respuesta(200, cuerpo)])
        ref = "Accuracy of ICD Influenza Discharge Diagnosis Codes in Hospitalized Adults"
        self.assertIsNone(cli.query_bibliographic(ref))

    def test_query_sin_resultados(self):
        cli, _ = _cliente([_respuesta(200, {"message": {"items": []}})])
        self.assertIsNone(cli.query_bibliographic("una referencia inventada"))

    def test_query_texto_vacio(self):
        cli, falso = _cliente([])
        self.assertIsNone(cli.query_bibliographic("   "))
        self.assertEqual(falso.llamadas, [])

    def test_query_cachea_negativo(self):
        cli, falso = _cliente([_respuesta(200, {"message": {"items": []}})])
        cli.query_bibliographic("x y z")
        cli.query_bibliographic("x y z")
        self.assertEqual(len(falso.llamadas), 1)

    def test_cabeceras_llevan_mailto(self):
        cli, falso = _cliente([_respuesta(200)])
        cli.existe("10.1234/x")
        self.assertEqual(falso.llamadas[0][2]["User-Agent"], USER_AGENT.format(mailto="test@example.org"))

    def test_reintenta_tras_503(self):
        cli, falso = _cliente(
            [_respuesta(503), _respuesta(200)],
            max_reintentos=1,
        )
        cli.max_reintentos = 1
        self.assertTrue(cli.existe("10.1234/x"))
        self.assertEqual(len(falso.llamadas), 2)

    def test_nulo_no_resuelve(self):
        nulo = CrossrefNulo()
        self.assertFalse(nulo.existe("10.1234/x"))
        self.assertIsNone(nulo.query_bibliographic("algo"))


class TestCoincidenciaTitulo(unittest.TestCase):
    TITULO = (
        "Accuracy of ICD Influenza Discharge Diagnosis Codes in Hospitalized "
        "Adults From the Valencia Region, Spain"
    )

    def test_cita_trunca_el_subtitulo_es_prefijo(self):
        ref = (
            "Accuracy of ICD Influenza Discharge Diagnosis Codes in "
            "Hospitalized Adults. Influenza Other Respir Viruses. 2025."
        )
        cobertura, prefijo = coincidencia_titulo(self.TITULO, ref)
        self.assertTrue(prefijo)
        self.assertLess(cobertura, 1.0)

    def test_titulo_completo_cobertura_alta(self):
        cobertura, prefijo = coincidencia_titulo(self.TITULO, self.TITULO)
        self.assertAlmostEqual(cobertura, 1.0)
        self.assertTrue(prefijo)

    def test_titulo_ajeno_no_es_prefijo(self):
        cobertura, prefijo = coincidencia_titulo(
            self.TITULO, "Memoria sobre la situación socioeconómica de la Comunitat"
        )
        self.assertFalse(prefijo)
        self.assertEqual(cobertura, 0.0)

    def test_titulo_vacio(self):
        self.assertEqual(coincidencia_titulo("", "algo"), (0.0, False))
        self.assertEqual(coincidencia_titulo("algo", ""), (0.0, False))

    def test_prefijo_corto_no_basta(self):
        cobertura, prefijo = coincidencia_titulo(self.TITULO, "Accuracy of ICD")
        self.assertFalse(prefijo)
        self.assertGreater(cobertura, 0.0)


if __name__ == "__main__":
    unittest.main()
