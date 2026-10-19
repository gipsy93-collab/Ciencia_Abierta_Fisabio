"""Fetcher: robots.txt, caché y descarga (sin red real)."""
import pathlib
import tempfile
import unittest

import httpx

from rip_osiris.config import Config
from rip_osiris.corpus.fetch import FetchError, Fetcher, SinRed


def _resp(status: int, cuerpo: bytes = b"", texto: str = "", cabeceras=None):
    datos = cuerpo if cuerpo else texto.encode("utf-8")
    return httpx.Response(
        status,
        content=datos,
        headers=cabeceras or {},
        request=httpx.Request("GET", "https://example.org/x"),
    )


class _ClienteFalso(httpx.Client):
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = []

    def get(self, url, headers=None):
        self.llamadas.append(url)
        if not self.respuestas:
            raise AssertionError(f"llamada inesperada a {url}")
        r = self.respuestas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def close(self):
        pass


class TestFetcher(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = Config(root=self.tmp.name, rate_limit_s=0.0)
        self.cfg.respetar_robots = True

    def tearDown(self):
        self.tmp.cleanup()

    def _fetcher(self, respuestas):
        falso = _ClienteFalso(respuestas)
        return Fetcher(self.cfg, self.tmp.name, client=falso), falso

    def test_robots_permite(self):
        robots = "User-agent: *\nAllow: /\n"
        f, _ = self._fetcher([_resp(200, texto=robots)])
        self.assertTrue(f.permitido("https://example.org/doc.pdf"))

    def test_robots_prohibe(self):
        robots = "User-agent: *\nDisallow: /privado/\n"
        f, _ = self._fetcher([_resp(200, texto=robots)])
        self.assertFalse(f.permitido("https://example.org/privado/doc.pdf"))

    def test_robots_404_permite(self):
        f, _ = self._fetcher([_resp(404)])
        self.assertTrue(f.permitido("https://example.org/doc.pdf"))

    def test_robots_se_cachea_por_dominio(self):
        robots = "User-agent: *\nAllow: /\n"
        f, falso = self._fetcher([_resp(200, texto=robots)])
        f.permitido("https://example.org/a")
        f.permitido("https://example.org/b")
        self.assertEqual(len(falso.llamadas), 1)

    def test_robots_desactivado(self):
        self.cfg.respetar_robots = False
        f, falso = self._fetcher([])
        self.assertTrue(f.permitido("https://example.org/privado/x"))
        self.assertEqual(falso.llamadas, [])

    def test_obtener_descarga_y_cachea(self):
        robots = "User-agent: *\nAllow: /\n"
        f, falso = self._fetcher(
            [
                _resp(200, texto=robots),
                _resp(200, cuerpo=b"%PDF-1.4 contenido", cabeceras={"content-type": "application/pdf"}),
            ]
        )
        datos, meta = f.obtener("https://example.org/doc.pdf")
        self.assertEqual(datos, b"%PDF-1.4 contenido")
        self.assertFalse(meta["cache"])
        self.assertEqual(meta["bytes"], len(datos))
        self.assertEqual(len(meta["sha256"]), 64)

        datos2, meta2 = f.obtener("https://example.org/doc.pdf")
        self.assertEqual(datos2, datos)
        self.assertTrue(meta2["cache"])
        self.assertEqual(meta2["sha256"], meta["sha256"])
        self.assertEqual(len(falso.llamadas), 2)

    def test_obtener_bloqueado_por_robots(self):
        robots = "User-agent: *\nDisallow: /privado/\n"
        f, _ = self._fetcher([_resp(200, texto=robots)])
        with self.assertRaises(FetchError):
            f.obtener("https://example.org/privado/doc.pdf")

    def test_obtener_http_error(self):
        robots = "User-agent: *\nAllow: /\n"
        f, _ = self._fetcher([_resp(200, texto=robots), _resp(500)])
        with self.assertRaises(FetchError):
            f.obtener("https://example.org/doc.pdf")

    def test_obtener_vacio(self):
        robots = "User-agent: *\nAllow: /\n"
        f, _ = self._fetcher([_resp(200, texto=robots), _resp(200, cuerpo=b"")])
        with self.assertRaises(FetchError):
            f.obtener("https://example.org/doc.pdf")

    def test_sin_red(self):
        f = SinRed(self.cfg, self.tmp.name)
        self.assertFalse(f.permitido("https://example.org/x"))
        with self.assertRaises(FetchError):
            f.obtener("https://example.org/x")


if __name__ == "__main__":
    unittest.main()
