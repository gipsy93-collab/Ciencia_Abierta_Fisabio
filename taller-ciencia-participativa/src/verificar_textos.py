from playwright.sync_api import sync_playwright
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")

base = pathlib.Path(__file__).parent.parent
files = {
    "taller": base / "Taller-Ciencia-Participativa.html",
    "dist": base / "dist" / "Taller-Ciencia-Participativa.html",
}

resultado = []
fallos = []


def check(nombre, cond, detalle=""):
    (resultado if cond else fallos).append(f"[{'OK ' if cond else 'FALLO'}] {nombre} {detalle}")


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    for nombre, f in files.items():
        errs = []
        page = b.new_page()
        page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(f.as_uri())
        page.wait_for_timeout(500)
        n_al_arranque = page.evaluate("document.querySelectorAll('[data-edit]').length")
        ce_al_arranque = page.evaluate("document.querySelectorAll('[contenteditable]').length")

        check(f"{nombre}: portada", page.locator(".page.active .cover-title").inner_text().strip().startswith("Estamos"))
        check(f"{nombre}: 5 accesos en portada", page.locator(".page.active .idx").count() == 5)
        if nombre == "taller":
            check(f"{nombre}: título editable", page.locator('[data-edit="cover.title"]').count() == 1)

        page.evaluate("openModal('p2m1')")
        page.wait_for_timeout(250)
        texto = page.locator("#mtext").inner_text()
        check(f"{nombre}: conclusiones text", "financiación sostenible" in texto, "→ " + texto[:60])
        check(f"{nombre}: conclusions title", page.locator("#mtitle").inner_text() == "Comentarios y conclusiones")
        pills = page.locator("#mbody .pill.small")
        check(f"{nombre}: 4 píldoras", pills.count() == 4, f"({pills.count()})")
        check(f"{nombre}: píldora 1", "Financiación sostenible" in page.locator("#mbody .pill").nth(0).inner_text())
        check(f"{nombre}: píldora 3", "Infraestructuras compartidas" in page.locator("#mbody .pill").nth(2).inner_text())
        check(f"{nombre}: píldora 4", "Gobernanza inclusiva" in page.locator("#mbody .pill").nth(3).inner_text())
        page.locator("#mbody .plus").click()
        page.wait_for_timeout(200)
        check(f"{nombre}: callout conclusiones", "interrelacionadas" in page.locator("#mbody .callout").first.inner_text())

        page.locator("#close").click()
        page.wait_for_timeout(150)
        page.evaluate("openModal('p2m2')")
        page.wait_for_timeout(200)
        check(f"{nombre}: pasos text", "codiseño" in page.locator("#mtext").inner_text())
        check(f"{nombre}: píldora pasos 3", "Definir estrategia y hoja de ruta" in page.locator("#mbody .pill").nth(2).inner_text())
        page.locator("#mbody .plus").click()
        page.wait_for_timeout(200)
        check(f"{nombre}: callout pasos", "El diagnóstico es la base" in page.locator("#mbody .callout").first.inner_text())

        page.locator("#close").click()
        page.wait_for_timeout(150)
        page.evaluate("openModal('m2')")
        page.wait_for_timeout(200)
        check(f"{nombre}: m2 metodología", page.locator("#mtitle").inner_text().strip() == "Metodología y diagnóstico de necesidades")
        page.locator("#mbody .plus").click()
        page.wait_for_timeout(200)
        tabla = page.locator("#mbody table")
        check(f"{nombre}: m2 cuadro", tabla.count() == 1)
        check(f"{nombre}: m2 6 ejes", page.locator("#mbody table tbody tr").count() == 6)
        check(f"{nombre}: m2 gobernanza", "Gobernanza y cultura" in tabla.inner_text())

        page.locator("#close").click()
        page.wait_for_timeout(150)
        page.evaluate("openModal('m3')")
        page.wait_for_timeout(200)
        check(f"{nombre}: m3 sin botón listado", page.locator("#mbody .morebtn").count() == 0)
        page.locator("#mbody .plus").click()
        page.wait_for_timeout(300)
        check(f"{nombre}: m3 tabla 22", page.locator("#mbody table tbody tr").count() == 22)
        check(f"{nombre}: m3 foto grupo", page.locator("#mbody .mphoto img").count() == 1)
        check(f"{nombre}: m3 foto cargada", page.evaluate("document.querySelector('#mbody .mphoto img').naturalWidth > 0"))

        page.locator("#close").click()
        page.wait_for_timeout(150)
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(500)
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(600)
        check(f"{nombre}: título galería", page.locator(".page.active .gtitle").inner_text() == "El taller, en imágenes")
        check(f"{nombre}: 5 fotos", page.locator(".page.active .shot").count() == 5)
        cargadas = page.evaluate("[...document.querySelectorAll('.page.active .shot img')].every(i => i.naturalWidth > 0)")
        check(f"{nombre}: 5 fotos cargadas (referenciadas)", cargadas)
        caps = page.evaluate("[...document.querySelectorAll('.page.active .shot figcaption')].map(f => f.textContent)")
        check(f"{nombre}: caption N15", any("N15" in c for c in caps))
        check(f"{nombre}: caption pizarra", any("25 necesidades" in c for c in caps))
        check(f"{nombre}: cierre con créditos", page.text_content(".page.active .gfoot .credits").strip() == "Fisabio · UPV · UV · FECYT")
        check(f"{nombre}: paginador visible en galería", page.evaluate("getComputedStyle(document.getElementById('pager')).opacity") != "0")

        check(f"{nombre}: 0 errores consola", len(errs) == 0, " ".join(errs[:3]))

        if nombre == "dist":
            check("dist: sin editbar", page.locator("#editbar").count() == 0)
            check("dist: sin contenteditable", ce_al_arranque == 0)
        else:
            check("taller: editables suficientes", n_al_arranque >= 30, f"({n_al_arranque})")
            check("taller: portada editable", page.locator('[data-edit="cover.kicker"]').count() == 1 and page.locator('[data-edit="cover.lede"]').count() == 1)
        page.close()
    b.close()

print("\n".join(resultado))
if fallos:
    print("\n".join(fallos))
    raise SystemExit(1)
print(f"\nTODO OK ({len(resultado)} comprobaciones)")
