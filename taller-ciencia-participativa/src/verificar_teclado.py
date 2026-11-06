from playwright.sync_api import sync_playwright
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding="utf-8")
base = Path(r"C:\Users\gipsy\Documents\Obsidian Vault\03 Proyectos\FISABIO\Taller-Ciencia-Participativa")
url = (base / "dist" / "Ciencia-abierta.html").as_uri()

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
    page.wait_for_timeout(600)

    def active_page():
        return page.locator(".page.active").get_attribute("data-page")

    check("modal inert al arranque", page.evaluate("document.getElementById('modal').inert"))

    page.keyboard.press("d")
    page.wait_for_timeout(200)
    check("D: página siguiente", active_page() == "2")
    page.keyboard.press("a")
    page.wait_for_timeout(200)
    check("A: página anterior", active_page() == "1")
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(200)
    check("→: página siguiente", active_page() == "2")
    page.keyboard.press("ArrowLeft")
    page.wait_for_timeout(200)
    check("←: página anterior", active_page() == "1")
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(200)
    page.keyboard.press("x")
    page.wait_for_timeout(200)
    check("X: volver de página", active_page() == "1")

    page.keyboard.press("ArrowDown")
    page.wait_for_timeout(150)
    check("↓: foco en el primer hotspot", page.evaluate("document.activeElement && document.activeElement.dataset.open") == "m1")
    page.keyboard.press("ArrowDown")
    page.wait_for_timeout(150)
    check("↓: foco en el segundo hotspot", page.evaluate("document.activeElement && document.activeElement.dataset.open") == "m2")
    page.keyboard.press("w")
    page.wait_for_timeout(400)
    check("W: abre el hotspot enfocado", page.locator("#mtitle").inner_text().strip() == "Metodología y diagnóstico de necesidades")
    check("foco dentro del modal", page.evaluate("document.activeElement && document.activeElement.closest('#modal') !== null"))
    page.keyboard.press("x")
    page.wait_for_timeout(300)
    check("X: cierra el modal", page.evaluate("!document.getElementById('modal').classList.contains('open')"))
    check("modal inerte tras cerrar", page.evaluate("document.getElementById('modal').inert"))

    page.keyboard.press("w")
    page.wait_for_timeout(400)
    check("W sin foco: abre el primer hotspot", page.locator("#mtitle").inner_text().strip() == "El taller")
    page.keyboard.press("Escape")
    page.wait_for_timeout(250)
    check("Esc: cierra el modal", page.evaluate("!document.getElementById('modal').classList.contains('open')"))

    page.evaluate("openModal('m5a')")
    page.wait_for_timeout(450)
    check("m5a: foco en volver", page.evaluate("document.activeElement && document.activeElement.id === 'mback'"))
    check("m5a: cuatro cuadrantes", page.locator("#mbody .dimcell").count() == 4)
    page.keyboard.press("d")
    page.wait_for_timeout(200)
    check("D en m5a: no rompe", page.locator("#mtitle").inner_text().strip() == "Estrategia institucional")
    page.keyboard.press("x")
    page.wait_for_timeout(300)
    check("X: vuelve a m5", page.locator("#mtitle").inner_text().strip() == "Temáticas priorizadas")
    page.keyboard.press("x")
    page.wait_for_timeout(250)
    check("X: cierra m5", page.evaluate("!document.getElementById('modal').classList.contains('open')"))

    page.evaluate("openModal('m5')")
    page.wait_for_timeout(450)
    check("m5: foco en categoría", page.evaluate("document.activeElement && document.activeElement.dataset.open") == "m5a")
    page.keyboard.press("d")
    page.wait_for_timeout(200)
    check("D: siguiente categoría", page.evaluate("document.activeElement && document.activeElement.dataset.open") == "m5d")
    page.keyboard.press("w")
    page.wait_for_timeout(350)
    check("W: abre la categoría enfocada", page.locator("#mtitle").inner_text().strip() == "Financiación estable")
    page.keyboard.press("x")
    page.wait_for_timeout(250)
    page.keyboard.press("x")
    page.wait_for_timeout(250)

    page.evaluate("openModal('m5')")
    page.wait_for_timeout(450)
    inside = True
    for _ in range(16):
        page.keyboard.press("Tab")
        page.wait_for_timeout(40)
        if not page.evaluate("document.activeElement && document.activeElement.closest('#modal') !== null"):
            inside = False
            break
    check("Tab: foco atrapado en el modal", inside)
    page.keyboard.press("x")
    page.wait_for_timeout(250)
    page.keyboard.press("x")
    page.wait_for_timeout(250)

    page.evaluate("openModal('m2')")
    page.wait_for_timeout(450)
    page.keyboard.press("w")
    page.wait_for_timeout(250)
    check("W: despliega el cuadro de m2", page.locator("#mbody table").count() == 1)
    page.keyboard.press("Tab")
    page.wait_for_timeout(150)
    check("Tab: llega al botón de galería", page.evaluate("document.activeElement && document.activeElement.className") == "morebtn")
    page.keyboard.press("w")
    page.wait_for_timeout(400)
    check("W: abre la galería m2b", page.locator("#mtitle").inner_text().strip() == "El proceso, en imágenes")
    check("m2b: foco en foto", page.evaluate("document.activeElement && document.activeElement.tagName === 'IMG'"))
    page.keyboard.press("w")
    page.wait_for_timeout(300)
    check("W: abre el lightbox", page.evaluate("document.getElementById('lightbox').classList.contains('open')"))
    page.keyboard.press("x")
    page.wait_for_timeout(250)
    check("X: cierra el lightbox", page.evaluate("!document.getElementById('lightbox').classList.contains('open')"))
    page.keyboard.press("x")
    page.wait_for_timeout(300)
    check("X: vuelve de m2b", page.locator("#mtitle").inner_text().strip() == "Metodología y diagnóstico de necesidades")
    page.keyboard.press("x")
    page.wait_for_timeout(250)

    check("0 errores de consola", len(errs) == 0, str(errs[:2]))
    page.close()
    b.close()

fallos = [n for n, c in checks if not c]
print(f"\n{len(checks) - len(fallos)}/{len(checks)} OK")
if fallos:
    print("FALLOS:", ", ".join(fallos))
    raise SystemExit(1)
print("TECLADO TODO OK")
