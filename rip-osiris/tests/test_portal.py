"""P1 — parser y cliente del portal FISABIO, sin red."""
import pathlib
import ssl
import tempfile
import unittest

from rip_osiris.anchor.cris import (
    PortalCris,
    PortalError,
    contexto_ssl,
    parsear_investigadores,
    parsear_perfil,
    parsear_publicaciones,
)
from rip_osiris.config import Config
from rip_osiris.corpus.store import Store

INVESTIGADORES_HTML = """
<ul class="results-list">
<li class="results-list__item">
  <h4 class="card__name text-400"><a href="https://fisabio.portalinvestigacion.com/investigadores/1815" class="tdn color-black"><span>Abel</span> Vicent Castillo</a></h4>
  <p class="style-italic text-350">Investigación osteomuscular</p>
  <p class="weight-bold text-350">Investigador/a</p>
</li>
<li class="results-list__item">
  <h4 class="card__name"><a href="/investigadores/1646"><span>Ainara</span> Mira Iglesias</a></h4>
  <p class="style-italic text-350">Epidemiología</p>
  <p class="weight-bold text-350">Investigador/a</p>
</li>
<li class="results-list__item">
  <h4 class="card__name"><a href="/investigadores/1815">Duplicado</a></h4>
</li>
</ul>
"""

PUBLICACIONES_HTML = """
<li class="results-list__item">
  <h4 class="results-list__title text-400"><a class="color-black" href="https://fisabio.portalinvestigacion.com/publicaciones/17086">Neoadjuvant &amp; adjuvant therapy</a></h4>
  <p>Conte P; <a href="/investigadores/1815">Vicent Castillo A</a>; Saura C</p>
  <p>Article. 10.1016/j.breast.2024.103742. 2024</p>
  <p>0960-9776. BREAST. Citas Recibidas en Web of Science: 5</p>
</li>
<li class="results-list__item">
  <h4 class="results-list__title"><a href="/publicaciones/2">Segunda obra</a></h4>
  <p>Sin enlaces</p>
  <p>Article. 10.1234/abc.2019. 2019</p>
</li>
"""

PERFIL_HTML = """
<h1 class="text-400">Ainara Mira Iglesias</h1>
<span><a href="https://orcid.org/0000-0001-6371-8229      ">0000-0001-6371-8229      </a></span>
"""


class _Respuesta:
    def __init__(self, content: bytes, status_code: int = 200, headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}


class _ClienteFalso:
    """Doble de httpx.Client: mapa {(método, fragmento): html}."""

    def __init__(self, mapa: dict):
        self.mapa = mapa
        self.llamadas: list[tuple] = []
        self.cerrado = False

    def _responder(self, metodo: str, url: str) -> _Respuesta:
        for (m, fragmento), contenido in self.mapa.items():
            if m == metodo and fragmento in url:
                return _Respuesta(contenido.encode("utf-8"))
        return _Respuesta(b"", status_code=404)

    def post(self, url, data=None, headers=None):
        self.llamadas.append(("POST", url, dict(data or {})))
        return self._responder("POST", url)

    def get(self, url, headers=None):
        self.llamadas.append(("GET", url, None))
        return self._responder("GET", url)

    def close(self):
        self.cerrado = True


class TestParseoPortal(unittest.TestCase):
    def test_investigadores_dedup_y_campos(self):
        perfiles = parsear_investigadores(INVESTIGADORES_HTML)
        self.assertEqual(len(perfiles), 2)
        self.assertEqual(perfiles[0].perfil_id, "1815")
        self.assertEqual(perfiles[0].nombre, "Abel Vicent Castillo")
        self.assertEqual(perfiles[0].area, "Investigación osteomuscular")
        self.assertEqual(perfiles[0].rol, "Investigador/a")
        self.assertEqual(perfiles[1].nombre, "Ainara Mira Iglesias")

    def test_publicaciones_doi_tipo_anio_autores(self):
        pubs = parsear_publicaciones(PUBLICACIONES_HTML)
        self.assertEqual(len(pubs), 2)
        primera = pubs[0]
        self.assertEqual(primera.pub_id, "17086")
        self.assertEqual(primera.titulo, "Neoadjuvant & adjuvant therapy")
        self.assertIn("10.1016/j.breast.2024.103742", primera.doi)
        self.assertEqual(primera.tipo, "Article")
        self.assertEqual(primera.anio, 2024)
        self.assertEqual(primera.autores_ids, ["1815"])
        self.assertEqual(pubs[1].doi, "10.1234/abc.2019")
        self.assertEqual(pubs[1].autores_ids, [])

    def test_perfil_orcid_con_espacios(self):
        perfil = parsear_perfil(PERFIL_HTML)
        self.assertEqual(perfil.nombre, "Ainara Mira Iglesias")
        self.assertEqual(perfil.orcid, "0000-0001-6371-8229")

    def test_perfil_sin_orcid(self):
        self.assertIsNone(parsear_perfil("<h1>Alguien</h1>").orcid)

    def test_titulo_entre_comillas_repetidas(self):
        html = (
            '<li><h4 class="results-list__title">'
            '<a href="/publicaciones/9">" Un título " "</a></h4>'
            "<p>Aut A</p><p>Article. 10.1000/x.2020. 2020</p></li>"
        )
        self.assertEqual(parsear_publicaciones(html)[0].titulo, "Un título")

    def test_area_vacia_no_captura_email(self):
        html = (
            '<li><h4 class="card__name"><a href="/investigadores/7">Ana Prueba</a></h4>'
            '<p class="style-italic text-350"></p>'
            '<p class="weight-bold text-350"></p>'
            '<p class="style-italic text-350 color-primary">correo</p></li>'
        )
        perfil = parsear_investigadores(html)[0]
        self.assertIsNone(perfil.area)
        self.assertIsNone(perfil.rol)


class TestClientePortal(unittest.TestCase):
    def test_contexto_ssl_exige_verificacion(self):
        self.assertEqual(contexto_ssl().verify_mode, ssl.CERT_REQUIRED)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = Config(root=pathlib.Path(self.tmp.name), rate_limit_s=0.0)
        self.mapa = {
            ("POST", "/get-researchers"): INVESTIGADORES_HTML,
            ("POST", "/get-publications"): PUBLICACIONES_HTML,
            ("GET", "/investigadores/1646"): PERFIL_HTML,
        }
        self.cliente = _ClienteFalso(self.mapa)
        self.portal = PortalCris(self.cfg, client=self.cliente)

    def tearDown(self):
        self.tmp.cleanup()

    def test_filtro_enviado(self):
        self.portal.listar_todos(limite=1080)
        metodo, url, datos = self.cliente.llamadas[0]
        self.assertEqual(metodo, "POST")
        self.assertIn("/get-researchers", url)
        self.assertEqual(datos["filter[limit]"], "1080")
        self.assertEqual(datos["filter[letter]"], "")

    def test_cache_evita_segunda_llamada(self):
        self.assertEqual(len(self.portal.listar_todos()), 2)
        self.assertEqual(len(self.portal.listar_todos()), 2)
        posts = [c for c in self.cliente.llamadas if c[0] == "POST"]
        self.assertEqual(len(posts), 1)
        self.assertTrue(any(l["cache"] for l in self.portal.llamadas))

    def test_perfil_por_id(self):
        perfil = self.portal.leer_perfil(1646)
        self.assertEqual(perfil.perfil_id, "1646")
        self.assertEqual(perfil.orcid, "0000-0001-6371-8229")
        self.assertEqual(self.portal.leer_orcid(1646), "0000-0001-6371-8229")

    def test_error_http_no_reintenta(self):
        portal = PortalCris(self.cfg, client=_ClienteFalso({}))
        with self.assertRaises(PortalError):
            portal.listar_todos()
        self.assertEqual(len(portal.client.llamadas), 1)
        self.assertEqual(len(portal.llamadas), 1)
        self.assertEqual(portal.llamadas[0]["status"], 404)


class TestStoreRoster(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(pathlib.Path(self.tmp.name) / "test.sqlite")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_researcher_idempotente_y_orcid(self):
        rid = self.store.upsert_researcher(
            portal_id="1815", name="Abel Vicent", area="Osteomuscular", role="Investigador/a"
        )
        mismo = self.store.upsert_researcher(
            portal_id="1815", name="Abel Vicent", orcid="0000-0001-6371-8229",
            orcid_source="portal",
        )
        self.assertEqual(rid, mismo)
        fila = self.store.conn.execute("SELECT * FROM researchers").fetchone()
        self.assertEqual(fila["area"], "Osteomuscular")
        self.assertEqual(fila["orcid"], "0000-0001-6371-8229")
        self.assertEqual(self.store.roster_coverage()["investigadores"], 1)
        self.assertEqual(self.store.roster_coverage()["con_orcid"], 1)

    def test_work_por_doi_y_por_clave_canonica(self):
        wid = self.store.upsert_work(
            title="Neoadjuvant & adjuvant therapy",
            doi="https://doi.org/10.1016/j.breast.2024.103742",
            year=2024,
            type="Article",
        )
        mismo = self.store.upsert_work(
            title="Neoadjuvant & adjuvant therapy", doi="10.1016/J.BREAST.2024.103742"
        )
        self.assertEqual(wid, mismo)
        sin_doi = self.store.upsert_work(title="Informe anual", year=2023)
        repetido = self.store.upsert_work(title="Informe   anual", year=2023)
        self.assertEqual(sin_doi, repetido)
        self.assertNotEqual(wid, sin_doi)
        self.assertEqual(self.store.roster_coverage()["obras"], 2)

    def test_vinculo_idempotente(self):
        rid = self.store.upsert_researcher(portal_id="1", name="A")
        wid = self.store.upsert_work(title="Obra", doi="10.1/x")
        self.assertTrue(self.store.link_author_work(rid, wid, source="portal"))
        self.assertFalse(self.store.link_author_work(rid, wid, source="portal"))
        self.assertEqual(self.store.roster_coverage()["vinculos_autor_obra"], 1)

    def test_presencia_upsert_y_log(self):
        wid = self.store.upsert_work(title="Obra", doi="10.1/x")
        self.store.upsert_presence(wid, "scopus", "no_comprobado")
        self.store.upsert_presence(wid, "scopus", "presente_exacto", method="doi")
        filas = self.store.conn.execute("SELECT * FROM presence").fetchall()
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["status"], "presente_exacto")
        self.assertEqual(filas[0]["method"], "doi")
        self.store.insert_crawl_log(
            url="u", method="POST", status=200, bytes=10, sha256="abc"
        )
        self.assertEqual(self.store.roster_coverage()["peticiones"], 1)


if __name__ == "__main__":
    unittest.main()
