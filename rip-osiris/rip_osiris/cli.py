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


def cmd_no_implementado(cfg: Config, args) -> int:
    raise SystemExit(
        f"'{args.verbo}' es un stub del esqueleto: se implementa en la fase indicada en el diseño."
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rip_osiris", description="RIP-OSIRIS (esqueleto)")
    p.add_argument("--home", default=None, help="raíz del proyecto (por defecto, la del paquete)")
    sub = p.add_subparsers(dest="verbo", required=True)

    sub.add_parser("coverage", help="qué fuentes se consultaron y qué se declara")
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
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = Config.load(args.home)

    despacho = {
        "coverage": cmd_coverage,
        "anchor": cmd_anchor,
        "fulltext": cmd_fulltext,
        "cascade": cmd_cascade,
        "graph": cmd_graph,
        "expediente": cmd_expediente,
    }
    if args.verbo in despacho:
        return despacho[args.verbo](cfg, args)
    return cmd_no_implementado(cfg, args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
