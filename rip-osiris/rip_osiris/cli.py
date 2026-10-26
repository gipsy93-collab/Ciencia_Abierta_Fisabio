"""CLI de RIP-OSIRIS (`python -m rip_osiris <verbo>`).

Esqueleto: los verbos de red delegan en conectores aún no implementados;
`coverage` y `graph` ya funcionan sobre la base local.
"""
from __future__ import annotations

import argparse
import json
import pathlib

from .config import Config
from .corpus.store import Store


def _store(cfg: Config) -> Store:
    return Store(cfg.db_path)


def cmd_coverage(cfg: Config, args) -> int:
    store = _store(cfg)
    try:
        print(json.dumps(store.coverage(), ensure_ascii=False, indent=2))
    finally:
        store.close()
    return 0


def cmd_graph(cfg: Config, args) -> int:
    from .cascade import graph

    store = _store(cfg)
    try:
        filas = graph.recorrer(store.conn, args.kind, args.id, args.hops)
        print(json.dumps(filas, ensure_ascii=False, indent=2))
    finally:
        store.close()
    return 0


def cmd_expediente(cfg: Config, args) -> int:
    from .dossier import expediente

    store = _store(cfg)
    try:
        print(
            json.dumps(
                expediente.construir(store, args.output, args.hops),
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
    finally:
        store.close()
    return 0


def cmd_anchor(cfg: Config, args) -> int:
    from .anchor.orcid import OrcidClient

    cliente = OrcidClient(cfg)
    obras = cliente.obras(args.orcid)
    store = _store(cfg)
    try:
        ids = [
            store.upsert_output(
                doi=obra.doi,
                orcid=args.orcid,
                ror=args.ror,
                title=obra.titulo,
                year=obra.anio,
                source="orcid",
            )
            for obra in obras
        ]
        store.set_coverage(
            "orcid",
            f"works/{args.orcid}",
            hits=len(obras),
            declared="cubierta",
        )
    finally:
        store.close()

    print(
        json.dumps(
            {
                "orcid": args.orcid,
                "obras": len(obras),
                "con_doi": sum(1 for o in obras if o.doi),
                "outputs_guardados": len(ids),
                "db": str(cfg.db_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_fulltext(cfg: Config, args) -> int:
    from .corpus.fetch import Fetcher
    from .corpus.fulltext import extraer_texto_archivo, extraer_texto_bytes

    store = _store(cfg)
    try:
        if args.doc is not None:
            filas = store.conn.execute(
                "SELECT id, source, source_id, url FROM documents WHERE id = ?",
                (args.doc,),
            ).fetchall()
        else:
            filas = store.conn.execute(
                "SELECT id, source, source_id, url FROM documents "
                "WHERE fulltext_path IS NULL ORDER BY id"
            ).fetchall()

        cfg.corpus_dir.mkdir(parents=True, exist_ok=True)
        fetcher = None if args.pdf else Fetcher(cfg)
        hechos, fallos = [], []
        for f in filas:
            try:
                if args.pdf:
                    texto = extraer_texto_archivo(args.pdf)
                else:
                    if not f["url"]:
                        fallos.append({"doc_id": f["id"], "error": "sin PDF ni URL"})
                        continue
                    datos, meta = fetcher.obtener(f["url"])
                    texto = extraer_texto_bytes(datos, meta.get("content_type", ""))
            except Exception as exc:
                fallos.append({"doc_id": f["id"], "error": f"{type(exc).__name__}: {exc}"})
                continue
            destino = cfg.corpus_dir / f"{f['id']}.txt"
            destino.write_text(texto, encoding="utf-8")
            store.conn.execute(
                "UPDATE documents SET fulltext_path = ? WHERE id = ?",
                (str(destino), f["id"]),
            )
            hechos.append(
                {"doc_id": f["id"], "txt": str(destino), "caracteres": len(texto)}
            )
        store.conn.commit()
        fuente_de = {f["id"]: f["source"] for f in filas}
        por_fuente: dict[str, int] = {}
        for h in hechos:
            fuente = fuente_de[h["doc_id"]]
            por_fuente[fuente] = por_fuente.get(fuente, 0) + 1
        for fuente, cuantos in por_fuente.items():
            store.set_coverage(fuente, "fulltext", hits=cuantos, declared="cubierta")
        store.conn.commit()
        print(
            json.dumps(
                {"extraidos": hechos, "fallos": fallos},
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        store.close()
    return 0


def cmd_cascade(cfg: Config, args) -> int:
    from .cascade import pipeline
    from .harvest.crossref import CrossrefClient, CrossrefNulo

    store = _store(cfg)
    try:
        crossref = (
            CrossrefNulo() if args.sin_red else CrossrefClient.desde_config(cfg)
        )
        try:
            if args.texto:
                texto = pathlib.Path(args.texto).read_text(
                    encoding="utf-8", errors="replace"
                )
                resumen = pipeline.procesar_documento(
                    store, args.doc, cfg, crossref=crossref, texto=texto
                )
            else:
                resumen = pipeline.procesar_documento(
                    store, args.doc, cfg, crossref=crossref
                )
        except (KeyError, ValueError) as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
            return 2
        print(json.dumps(resumen.como_dict(), ensure_ascii=False, indent=2))
    finally:
        store.close()
    return 0


def cmd_roster(cfg: Config, args) -> int:
    from .anchor.cris import PortalCris

    store = _store(cfg)
    try:
        portal = PortalCris(cfg, cache_dir=args.cache)
        perfiles = portal.listar_todos(args.limite)
        ids: dict[str, int] = {}
        for perfil in perfiles:
            ids[perfil.perfil_id] = store.upsert_researcher(
                portal_id=perfil.perfil_id,
                name=perfil.nombre,
                area=perfil.area,
                role=perfil.rol,
            )

        errores: list[dict] = []
        if not args.sin_perfiles:
            for perfil in perfiles:
                try:
                    orcid = portal.leer_orcid(perfil.perfil_id)
                except Exception as exc:  # red o HTML inesperado
                    errores.append(
                        {
                            "portal_id": perfil.perfil_id,
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )
                    continue
                if orcid:
                    store.upsert_researcher(
                        portal_id=perfil.perfil_id,
                        name=perfil.nombre,
                        orcid=orcid,
                        orcid_source="portal",
                    )

        obras = 0
        vinculos = 0
        if not args.sin_publicaciones:
            for pub in portal.publicaciones(args.limite_publicaciones):
                wid = store.upsert_work(
                    title=pub.titulo, doi=pub.doi, year=pub.anio, type=pub.tipo
                )
                obras += 1
                for portal_id in pub.autores_ids:
                    rid = ids.get(portal_id)
                    if rid is None:
                        continue
                    if store.link_author_work(rid, wid, source="portal"):
                        vinculos += 1

        for llamada in portal.llamadas:
            store.insert_crawl_log(**llamada)

        store.set_coverage(
            "portal_fisabio", "researchers", hits=len(perfiles), declared="cubierta"
        )
        if not args.sin_perfiles:
            store.set_coverage(
                "portal_fisabio",
                "orcid_profiles",
                hits=store.roster_coverage()["con_orcid"],
                declared="cubierta",
            )
        if not args.sin_publicaciones:
            store.set_coverage(
                "portal_fisabio", "publications", hits=obras, declared="cubierta"
            )

        print(
            json.dumps(
                {
                    "investigadores": len(perfiles),
                    "obras": obras,
                    "vinculos_autor_obra": vinculos,
                    "errores": len(errores),
                    "muestra_errores": errores[:5],
                    "cobertura": store.roster_coverage(),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        store.close()
    return 0


def cmd_demo(cfg: Config, args) -> int:
    """Slice vertical: semilla -> ingesta -> rastreo -> informe."""
    from .cascade import pipeline
    from .dossier import html as dossier_html
    from .harvest.crossref import CrossrefClient, CrossrefNulo
    from .ingest import ingerir_urls, leer_urls
    from .probe import titles as titulos
    from .seed.openalex import OpenAlexClient, OpenAlexError, guardar_semilla

    store = _store(cfg)
    resumen: dict = {}
    try:
        if not args.sin_red:
            cliente = OpenAlexClient.desde_config(cfg, per_page=cfg.openalex_per_page)
            try:
                if args.dois:
                    obras = cliente.por_dois([d for d in args.dois.split(",") if d.strip()])
                else:
                    obras = cliente.obras(args.muestra, buscar=args.buscar, orden=args.orden)
            except OpenAlexError as exc:
                print(json.dumps({"error": f"OpenAlex: {exc}"}, ensure_ascii=False, indent=2))
                return 2
            ids = guardar_semilla(store, obras)
            resumen["semilla"] = {
                "obras": len(obras),
                "outputs": len(ids),
                "con_doi": sum(1 for o in obras if o.doi),
                "peticiones": len(cliente.llamadas),
            }

            urls = leer_urls(args.corpus) if args.corpus else []
            if args.limite_corpus:
                urls = urls[: args.limite_corpus]
            if urls:
                ingesta = ingerir_urls(store, cfg, urls)
                resumen["ingesta"] = ingesta.como_dict()
        else:
            resumen["semilla"] = {"saltada": True}
            resumen["ingesta"] = {"saltada": True}

        crossref = CrossrefNulo() if (args.sin_red or not args.crossref) else CrossrefClient.desde_config(cfg)
        docs = [int(f["id"]) for f in store.conn.execute("SELECT id FROM documents ORDER BY id")]
        rastreo = {"documentos": 0, "referencias": 0, "impactos_doi": 0,
                   "impactos_cuerpo": 0, "impactos_titulo": 0, "titulos": 0,
                   "descartadas": 0, "errores": []}
        for doc_id in docs:
            try:
                r = pipeline.procesar_documento(store, doc_id, cfg, crossref=crossref)
                t = titulos.procesar_documento_titulos(store, doc_id, cfg)
            except (KeyError, ValueError) as exc:
                rastreo["errores"].append({"doc_id": doc_id, "error": f"{type(exc).__name__}: {exc}"})
                continue
            rastreo["documentos"] += 1
            rastreo["referencias"] += r.referencias
            rastreo["impactos_doi"] += r.aristas_impact
            rastreo["impactos_cuerpo"] += r.impactos_por_mencion
            rastreo["titulos"] += t["coincidencias"]
            rastreo["impactos_titulo"] += t["aristas_nuevas"]
            rastreo["descartadas"] += r.aristas_descartadas + t["descartadas"]
        resumen["rastreo"] = rastreo

        resumen["informe"] = dossier_html.generar(store, args.out, args.titulo)
    finally:
        store.close()

    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    return 0


def cmd_no_implementado(cfg: Config, args) -> int:
    raise SystemExit(
        f"'{args.verbo}' es un stub del esqueleto: se implementa en la fase indicada en el diseño."
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rip_osiris", description="RIP-OSIRIS (esqueleto)")
    p.add_argument("--home", default=None, help="raíz del proyecto (por defecto, la del paquete)")
    sub = p.add_subparsers(dest="verbo", required=True)

    sub.add_parser("coverage", help="qué fuentes se consultaron y qué se declara")
    r = sub.add_parser("roster", help="P1: roster del portal FISABIO + ORCID")
    r.add_argument("--limite", type=int, default=2000, help="tope de perfiles a pedir")
    r.add_argument(
        "--limite-publicaciones",
        type=int,
        default=12000,
        dest="limite_publicaciones",
        help="tope de publicaciones del portal",
    )
    r.add_argument(
        "--sin-perfiles",
        action="store_true",
        dest="sin_perfiles",
        help="no visita cada perfil individual (más rápido, sin ORCID)",
    )
    r.add_argument(
        "--sin-publicaciones",
        action="store_true",
        dest="sin_publicaciones",
        help="no pide el listado de publicaciones del portal",
    )
    r.add_argument("--cache", default=None, help="directorio de caché del portal")
    a = sub.add_parser("anchor", help="Capa 0: ORCID -> obras -> DOI")
    a.add_argument("--orcid", required=True, help="ORCID de la autora/investigador")
    a.add_argument("--ror", default=None, help="ROR de la institución (opcional)")
    sub.add_parser("harvest", help="[stub] Capa 1: traer documentos")
    f = sub.add_parser("fulltext", help="PDF -> texto y fulltext_path")
    f.add_argument("--doc", type=int, default=None, help="solo este documento")
    f.add_argument(
        "--pdf", default=None, help="ruta local del PDF (si no, usa la URL del documento)"
    )
    c = sub.add_parser("cascade", help="referencias + resolución + aristas")
    c.add_argument("--doc", type=int, required=True, help="id del documento en el corpus")
    c.add_argument(
        "--texto",
        default=None,
        help="ruta a un .txt con el texto completo (si no, usa fulltext_path)",
    )
    c.add_argument(
        "--sin-red",
        action="store_true",
        help="no consulta Crossref (solo DOI inline + corpus)",
    )
    sub.add_parser("export", help="[stub] Dublin Core / BibTeX")

    g = sub.add_parser("graph", help="recorrer el grafo desde un nodo")
    g.add_argument("--kind", default="output", choices=["output", "document"])
    g.add_argument("--id", type=int, required=True)
    g.add_argument("--hops", type=int, default=3)

    e = sub.add_parser("expediente", help="expediente N1-N6 de una salida")
    e.add_argument("--output", type=int, required=True)
    e.add_argument("--hops", type=int, default=3)

    d = sub.add_parser("demo", help="slice: semilla, ingesta, rastreo e informe")
    d.add_argument("--muestra", type=int, default=None, help="nº de obras FISABIO (por defecto, config)")
    d.add_argument("--dois", default=None, help="lista de DOI separada por comas (en vez de muestra)")
    d.add_argument("--buscar", default=None, help="términos de búsqueda en OpenAlex (p. ej. 'influenza|vaccine')")
    d.add_argument("--orden", default="cited_by_count:desc", help="orden de la muestra (OpenAlex)")
    d.add_argument("--corpus", default=None, help="fichero con una URL de documento por línea")
    d.add_argument("--limite-corpus", type=int, default=None, dest="limite_corpus")
    d.add_argument("--out", default="docs/demo.html", help="ruta del informe HTML")
    d.add_argument("--titulo", default=None, help="título del informe")
    d.add_argument("--crossref", action="store_true", help="verificar DOIs contra Crossref (lento)")
    d.add_argument("--sin-red", action="store_true", dest="sin_red", help="no toca la red: usa la base local")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = Config.load(args.home)

    despacho = {
        "coverage": cmd_coverage,
        "roster": cmd_roster,
        "anchor": cmd_anchor,
        "fulltext": cmd_fulltext,
        "cascade": cmd_cascade,
        "graph": cmd_graph,
        "expediente": cmd_expediente,
        "demo": cmd_demo,
    }
    if args.verbo in despacho:
        return despacho[args.verbo](cfg, args)
    return cmd_no_implementado(cfg, args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
