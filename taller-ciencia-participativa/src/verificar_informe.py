from playwright.sync_api import sync_playwright
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding="utf-8")
base = Path(r"C:\Users\gipsy\Documents\Obsidian Vault\03 Proyectos\FISABIO\Taller-Ciencia-Participativa")
url = (base / "dist" / "Taller-Ciencia-Participativa.html").as_uri()
shots = base / "capturas_informe"
shots.mkdir(exist_ok=True)

errs = []
checks = []


def check(name, cond, extra=""):
    checks.append((name, bool(cond)))
    print(("OK  " if cond else "FALLO ") + name + (f"  [{extra}]" if extra else ""))


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page(viewport={"width": 1440, "height": 900})
    page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(url, wait_until="networkidle")

    check("portada: 3 páginas", page.locator(".page").count() == 3)
    check("portada: paginador 01/03", page.locator("#pager").inner_text().strip() == "01 / 03")
    check("portada: 5 zonas", page.locator(".page.active .hot").count() == 5)
    check("portada: 5 accesos", page.locator(".page.active .idx").count() == 5)
    check("portada: título", "Estamos pensando" in page.locator(".cover-title").inner_text())
    check("portada: cerebro cargado", page.evaluate("document.querySelector('.cover-brain').naturalWidth > 0"))
    check("portada: logos cargados", page.evaluate("[...document.querySelectorAll('.cover-logos img')].every(i => i.naturalWidth > 0)"))
    check("portada: sinapsis animadas", page.locator(".syn path.flow").count() >= 7)
    check("portada: sin desbordamiento", page.evaluate("""() => {
        const st = document.getElementById('stage').getBoundingClientRect();
        return [...document.querySelectorAll('.cover-title, .cover-lede, .cover-index, .cover-logos')]
          .every(n => { const r = n.getBoundingClientRect();
            return r.left >= st.left - 1 && r.top >= st.top - 1 && r.right <= st.right + 1 && r.bottom <= st.bottom + 1; });
    }"""))
    page.screenshot(path=str(shots / "p1_portada.png"))

    page.evaluate("showPage(1)")
    page.wait_for_timeout(500)
    check("p2: 2 zonas", page.locator(".page.active .hot").count() == 2)
    page.evaluate("showPage(2)")
    page.wait_for_timeout(700)
    check("p3: cierre", page.locator(".page.active .closing h2").inner_text().strip() == "Gracias")
    check("p3: agradecimientos", page.locator(".page.active .close-kicker").inner_text().strip().lower() == "agradecimientos")
    check("p3: 2 logos", page.locator(".page.active .closelogos img").count() == 2)
    check("p3: logos cargados", page.evaluate("[...document.querySelectorAll('.page.active .closelogos img')].every(i => i.naturalWidth > 0)"))
    check("p3: paginador oculto", page.evaluate("getComputedStyle(document.getElementById('pager')).opacity") == "0")
    check("p3: sin desbordamiento", page.evaluate("""() => {
        const st = document.getElementById('stage').getBoundingClientRect();
        return [...document.querySelectorAll('.page.active .closing, .page.active .closelogos, .page.active .close-lede')]
          .every(n => { const r = n.getBoundingClientRect();
            return r.left >= st.left - 1 && r.top >= st.top - 1 && r.right <= st.right + 1 && r.bottom <= st.bottom + 1; });
    }"""))
    page.screenshot(path=str(shots / "p3_agradecimientos.png"))

    page.evaluate("openModal('m1')")
    page.wait_for_timeout(300)
    check("m1: título El taller", page.locator("#mtitle").inner_text().strip() == "El taller")
    check("m1: objetivo general", "diagnóstico compartido" in page.locator("#mtext").inner_text())
    check("m1: 4 objetivos específicos", page.locator("#mbody .pill").count() == 4)
    check("m1: foto del proceso", page.locator("#mbody .photobtn").count() == 1)
    check("m1: foto cargada", page.evaluate("getComputedStyle(document.querySelector('#mbody .photobtn')).backgroundImage.includes('mapa-relevancia')"))
    page.locator("#mbody .photobtn").click()
    page.wait_for_timeout(300)
    check("m1: lightbox del proceso", page.locator("#lightbox").evaluate("n => n.classList.contains('open')"))
    check("m1: imagen del proceso cargada", page.evaluate("document.getElementById('lbimg').naturalWidth > 0"))
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    page.screenshot(path=str(shots / "m1_taller.png"))
    page.evaluate("closeModal()")

    page.evaluate("openModal('m2')")
    page.wait_for_timeout(300)
    check("m2: metodología", "validación y priorización" in page.locator("#mtext").inner_text())
    check("m2: 4 pasos", page.locator("#mbody .pill").count() == 4)
    page.locator("#mbody .plus").click()
    page.wait_for_timeout(250)
    check("m2: cuadro de categorías", page.locator("#mbody table").count() == 1)
    check("m2: 6 ejes", page.locator("#mbody table tbody tr").count() == 6)
    check("m2: gobernanza", "Gobernanza y cultura" in page.locator("#mbody table").inner_text())
    check("m2: participación", "Participación ciudadana" in page.locator("#mbody table").inner_text())
    page.screenshot(path=str(shots / "m2_taller.png"))

    page.locator("#mbody .morebtn").click()
    page.wait_for_timeout(400)
    check("m2b: galería del proceso", page.locator("#mbody .pcell").count() == 5)
    check("m2b: fotos cargadas", page.evaluate("[...document.querySelectorAll('#mbody .pcell img')].every(i => i.naturalWidth > 0)"))
    check("m2b: pies", page.locator("#mbody .pcell figcaption").count() == 5)
    check("m2b: tarjeta N15", "N15" in page.locator("#mbody .pcell figcaption").nth(1).inner_text())
    page.screenshot(path=str(shots / "m2b_proceso.png"))
    page.locator("#mbody .pcell img").first.click()
    page.wait_for_timeout(300)
    check("m2b: lightbox", page.locator("#lightbox").evaluate("n => n.classList.contains('open')"))
    check("m2b: imagen lightbox", page.evaluate("document.getElementById('lbimg').naturalWidth > 0"))
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    page.locator("#mback").click()
    page.wait_for_timeout(300)
    check("m2b: volver a m2", page.locator("#mtitle").inner_text().strip() == "Metodología y diagnóstico de necesidades")
    page.evaluate("closeModal()")

    page.evaluate("openModal('m3')")
    page.wait_for_timeout(300)
    check("m3: texto 9 instituciones", "nueve instituciones" in page.locator("#mtext").inner_text())
    check("m3: sin botón listado", page.locator("#mbody .morebtn").count() == 0)
    check("m3: sin callout", page.locator("#mbody .callout").count() == 0)
    page.screenshot(path=str(shots / "m3_participantes.png"))
    page.locator("#mbody .plus").click()
    page.wait_for_timeout(300)
    check("m3b: tabla", page.locator("#mbody table").count() == 1)
    check("m3b: 22 filas", page.locator("#mbody table tbody tr").count() == 22)
    check("m3b: nombre", "Ana Peiró" in page.locator("#mbody table").inner_text())
    check("m3b: ponente", "Enrique Orduña-Malea" in page.locator("#mbody table").inner_text())
    check("m3b: sin cerebro", page.evaluate("getComputedStyle(document.getElementById('mbrain')).display === 'none'"))
    check("m3b: botón volver", page.locator("#mback").is_visible())
    check("m3b: foto del grupo", page.locator("#mbody .mphoto img").count() == 1)
    check("m3b: foto cargada", page.evaluate("document.querySelector('#mbody .mphoto img').naturalWidth > 0"))
    check("m3b: tabla sin scroll", page.evaluate("(() => { const b=document.getElementById('mbody'); return b.scrollHeight <= b.clientHeight + 2; })()"))
    page.screenshot(path=str(shots / "m3b_tabla.png"))
    page.locator("#mback").click()
    page.wait_for_timeout(300)
    check("volver a m3", page.locator("#mtitle").inner_text().strip() == "Participantes")

    page.evaluate("openModal('m4')")
    page.wait_for_timeout(300)
    check("m4: texto 25 necesidades", "25 necesidades" in page.locator("#mtext").inner_text())
    check("m4: sin botón ranking", page.locator("#mbody .morebtn").count() == 0)
    check("m4: sin callout", page.locator("#mbody .callout").count() == 0)
    check("m4: 6 recuadros", page.locator("#mbody .pill").count() == 6)
    check("m4: recuadros sin solape", page.evaluate("""() => {
        const r = [...document.querySelectorAll('#mbody .pill')].map(n => n.getBoundingClientRect());
        for (let i = 0; i < r.length; i++) for (let j = i + 1; j < r.length; j++) {
            if (r[i].left < r[j].right - 1 && r[j].left < r[i].right - 1 &&
                r[i].top < r[j].bottom - 1 && r[j].top < r[i].bottom - 1) return false;
        }
        return true;
    }"""))
    page.screenshot(path=str(shots / "m4_necesidades.png"))
    page.locator("#mbody .plus").click()
    page.wait_for_timeout(300)
    check("m4b: tabla", page.locator("#mbody table").count() == 1)
    check("m4b: 13 filas", page.locator("#mbody table tbody tr").count() == 13)
    check("m4b: votos 19", "19" in page.locator("#mbody table").inner_text())
    check("m4b: 4 priorizadas", page.locator("#mbody table tr.prio").count() == 4)
    check("m4b: foto del panel", page.locator("#mbody .mphoto img").count() == 1)
    check("m4b: foto cargada", page.evaluate("document.querySelector('#mbody .mphoto img').naturalWidth > 0"))
    check("m4b: sin scroll", page.evaluate("(() => { const b=document.getElementById('mbody'); return b.scrollHeight <= b.clientHeight + 2; })()"))
    page.screenshot(path=str(shots / "m4b_ranking.png"))

    page.evaluate("openModal('m5')")
    page.wait_for_timeout(300)
    check("m5: texto prioridades", "cuatro dimensiones" in page.locator("#mtext").inner_text())
    check("m5: sin plus", page.locator("#mbody .plus").count() == 0)
    check("m5: sin callouts", page.locator("#mbody .callout").count() == 0)
    check("m5: 4 categorías", page.locator("#mbody .pill.link").count() == 4)
    check("m5: accesos correctos", page.evaluate("[...document.querySelectorAll('#mbody .pill.link')].map(n => n.dataset.open).join(',')") == "m5a,m5d,m5b,m5c")
    check("m5: categorías sin solape", page.evaluate("""() => {
        const r = [...document.querySelectorAll('#mbody .pill')].map(n => n.getBoundingClientRect());
        for (let i = 0; i < r.length; i++) for (let j = i + 1; j < r.length; j++) {
            if (r[i].left < r[j].right - 1 && r[j].left < r[i].right - 1 &&
                r[i].top < r[j].bottom - 1 && r[j].top < r[i].bottom - 1) return false;
        }
        return true;
    }"""))
    page.screenshot(path=str(shots / "m5_prioridades.png"))

    page.locator("#mbody .pill.link").first.click()
    page.wait_for_timeout(350)
    check("m5a: título", page.locator("#mtitle").inner_text().strip() == "Estrategia institucional")
    check("m5a: 4 dimensiones", page.locator("#mbody .dimtab").count() == 4)
    check("m5a: diagnóstico", "ENCA" in page.locator("#mbody .dimcontent p[data-edit]").inner_text())
    check("m5a: pregunta", "¿Qué está pasando?" in page.locator("#mbody .dq").inner_text())
    check("m5a: foto plantilla", page.evaluate("document.querySelector('#mbody .mphoto img').naturalWidth > 0"))
    page.locator("#mbody .dimtab").nth(2).click()
    page.wait_for_timeout(250)
    check("m5a: pestaña transformación", "Transformación requerida" in page.locator("#mbody .dimcontent h3").inner_text())
    check("m5a: texto transformación", "intercambio" in page.locator("#mbody .dimcontent p[data-edit]").inner_text())
    page.screenshot(path=str(shots / "m5a_estrategia.png"))
    page.locator("#mback").click()
    page.wait_for_timeout(300)
    check("m5a: volver a m5", page.locator("#mtitle").inner_text().strip() == "Temáticas priorizadas")

    for key, title, needle in [
        ("m5b", "Gobernanza compartida", "asociaciones"),
        ("m5c", "Infraestructuras tecnológicas", "esfuerzos aislados"),
        ("m5d", "Financiación estable", "partidas"),
    ]:
        page.evaluate(f"openModal('{key}')")
        page.wait_for_timeout(250)
        check(f"{key}: título", page.locator("#mtitle").inner_text().strip() == title)
        check(f"{key}: 4 dimensiones", page.locator("#mbody .dimtab").count() == 4)
        check(f"{key}: diagnóstico", needle in page.locator("#mbody .dimcontent p[data-edit]").inner_text())
        check(f"{key}: foto", page.evaluate("document.querySelector('#mbody .mphoto img').naturalWidth > 0"))
        page.evaluate("closeModal()")
        page.wait_for_timeout(150)

    page.evaluate("openModal('p2m1')")
    page.wait_for_timeout(300)
    check("p2m1: conclusiones", "financiación sostenible" in page.locator("#mtext").inner_text().lower())
    page.screenshot(path=str(shots / "p2m1_conclusiones.png"))

    page.evaluate("openModal('p2m2')")
    page.wait_for_timeout(300)
    check("p2m2: pasos", "codiseño" in page.locator("#mtext").inner_text())
    page.screenshot(path=str(shots / "p2m2_pasos.png"))

    check("0 errores de consola", len(errs) == 0, str(errs[:2]))
    page.close()
    b.close()

fallos = [n for n, c in checks if not c]
print(f"\n{len(checks) - len(fallos)}/{len(checks)} OK")
if fallos:
    print("FALLOS:", ", ".join(fallos))
    raise SystemExit(1)
print("INFORME INTEGRADO TODO OK")

