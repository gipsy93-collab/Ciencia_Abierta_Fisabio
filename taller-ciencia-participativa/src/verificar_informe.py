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

    check("portada: 4 páginas", page.locator(".page").count() == 4)
    check("portada: paginador 01/04", page.locator("#pager").inner_text().strip() == "01 / 04")
    check("portada: 5 zonas", page.locator(".page.active .hot").count() == 5)
    page.screenshot(path=str(shots / "p1_portada.png"))

    page.evaluate("showPage(1)")
    page.wait_for_timeout(500)
    check("p2: 2 zonas", page.locator(".page.active .hot").count() == 2)
    page.evaluate("showPage(2)")
    page.wait_for_timeout(700)
    check("p3: 5 fotos", page.locator(".page.active .shot").count() == 5)
    check("p3: fotos cargadas", page.evaluate("[...document.querySelectorAll('.page.active .shot img')].every(i => i.naturalWidth > 0)"))
    page.screenshot(path=str(shots / "p3_galeria.png"))

    page.evaluate("showPage(3)")
    page.wait_for_timeout(700)
    check("p4: 6 imágenes", page.locator(".page.active .shot").count() == 6)
    check("p4: imágenes cargadas", page.evaluate("[...document.querySelectorAll('.page.active .shot img')].every(i => i.naturalWidth > 0)"))
    check("p4: 2 logos", page.locator(".page.active .doclogos").count() == 2)
    check("p4: logos cargados", page.evaluate("[...document.querySelectorAll('.page.active .doclogos')].every(i => i.naturalWidth > 0)"))
    check("p4: título", page.locator(".page.active .gtitle").inner_text().strip() == "El diagnóstico, en imágenes")
    check("p4: sin desbordamiento", page.evaluate("""() => {
        const st = document.getElementById('stage').getBoundingClientRect();
        return [...document.querySelectorAll('.page.active .shot, .page.active .doclogos, .page.active .gfoot')]
          .every(n => { const r = n.getBoundingClientRect();
            return r.left >= st.left - 1 && r.top >= st.top - 1 && r.right <= st.right + 1 && r.bottom <= st.bottom + 1; });
    }"""))
    page.screenshot(path=str(shots / "p4_documental.png"))

    page.evaluate("openModal('m2')")
    page.wait_for_timeout(300)
    check("m2: texto 19 personas", "19 personas" in page.locator("#mtext").inner_text())
    page.locator("#mbody .plus").click()
    page.wait_for_timeout(200)
    check("m2: callout ponencia", "Orduña-Malea" in page.locator("#mbody .callout").first.inner_text())
    page.screenshot(path=str(shots / "m2_taller.png"))

    page.evaluate("openModal('m3')")
    page.wait_for_timeout(300)
    check("m3: texto 9 instituciones", "nueve instituciones" in page.locator("#mtext").inner_text())
    check("m3: botón listado", page.locator("#mbody .morebtn").inner_text().startswith("Ver las 19"))
    page.screenshot(path=str(shots / "m3_participantes.png"))
    page.locator("#mbody .morebtn").click()
    page.wait_for_timeout(300)
    check("m3b: tabla", page.locator("#mbody table").count() == 1)
    check("m3b: 22 filas", page.locator("#mbody table tbody tr").count() == 22)
    check("m3b: nombre", "Ana Peiró" in page.locator("#mbody table").inner_text())
    check("m3b: ponente", "Enrique Orduña-Malea" in page.locator("#mbody table").inner_text())
    check("m3b: sin cerebro", page.evaluate("getComputedStyle(document.getElementById('mbrain')).display === 'none'"))
    check("m3b: botón volver", page.locator("#mback").is_visible())
    check("m3b: tabla sin scroll", page.evaluate("(() => { const b=document.getElementById('mbody'); return b.scrollHeight <= b.clientHeight + 2; })()"))
    page.screenshot(path=str(shots / "m3b_tabla.png"))
    page.locator("#mback").click()
    page.wait_for_timeout(300)
    check("volver a m3", page.locator("#mtitle").inner_text().strip() == "Participantes")

    page.evaluate("openModal('m4')")
    page.wait_for_timeout(300)
    check("m4: texto 25 necesidades", "25 necesidades" in page.locator("#mtext").inner_text())
    check("m4: botón ranking", page.locator("#mbody .morebtn").inner_text().startswith("Ver el ranking"))
    page.locator("#mbody .morebtn").click()
    page.wait_for_timeout(300)
    check("m4b: tabla", page.locator("#mbody table").count() == 1)
    check("m4b: 13 filas", page.locator("#mbody table tbody tr").count() == 13)
    check("m4b: votos 19", "19" in page.locator("#mbody table").inner_text())
    check("m4b: 4 priorizadas", page.locator("#mbody table tr.prio").count() == 4)
    check("m4b: sin scroll", page.evaluate("(() => { const b=document.getElementById('mbody'); return b.scrollHeight <= b.clientHeight + 2; })()"))
    page.screenshot(path=str(shots / "m4b_ranking.png"))

    page.evaluate("openModal('m5')")
    page.wait_for_timeout(300)
    check("m5: texto prioridades", "13 quedaron priorizadas" in page.locator("#mtext").inner_text())
    page.locator("#mbody .plus").click()
    page.wait_for_timeout(250)
    check("m5: dos callouts", page.locator("#mbody .callout.show").count() == 2)
    check("m5: callout votos", "estrategia (19)" in page.locator("#mbody .callout").first.inner_text())
    page.screenshot(path=str(shots / "m5_prioridades.png"))

    page.evaluate("openModal('p2m1')")
    page.wait_for_timeout(300)
    check("p2m1: conclusiones", "financiación sostenible" in page.locator("#mtext").inner_text().lower())
    page.screenshot(path=str(shots / "p2m1_conclusiones.png"))

    page.evaluate("openModal('p2m2')")
    page.wait_for_timeout(300)
    check("p2m2: pasos", "codiseño" in page.locator("#mtext").inner_text())
    page.screenshot(path=str(shots / "p2m2_pasos.png"))

    page.evaluate("closeModal(); showPage(3)")
    page.wait_for_timeout(300)
    page.locator(".page.active .shot img").first.click()
    page.wait_for_timeout(250)
    check("lightbox: abierto", page.locator("#lightbox").evaluate("n => n.classList.contains('open')"))
    check("lightbox: imagen cargada", page.evaluate("document.getElementById('lbimg').naturalWidth > 0"))
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    check("lightbox: cerrado con Esc", page.locator("#lightbox").evaluate("n => !n.classList.contains('open')"))

    check("0 errores de consola", len(errs) == 0, str(errs[:2]))
    page.close()
    b.close()

fallos = [n for n, c in checks if not c]
print(f"\n{len(checks) - len(fallos)}/{len(checks)} OK")
if fallos:
    print("FALLOS:", ", ".join(fallos))
    raise SystemExit(1)
print("INFORME INTEGRADO TODO OK")
