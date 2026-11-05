from playwright.sync_api import sync_playwright
import sys

sys.stdout.reconfigure(encoding="utf-8")
URL = "https://gipsy93-collab.github.io/Ciencia_Abierta_Fisabio/"
errs = []
ok = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page(viewport={"width": 1440, "height": 900})
    page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(URL, wait_until="networkidle")
    ok.append(("redirección llega a la pieza", page.url.endswith("/taller-ciencia-participativa/Taller-Ciencia-Participativa.html")))
    ok.append(("título portada", page.locator(".page.active .title").inner_text().strip().startswith("Estamos")))
    ok.append(("5 zonas portada", page.locator(".page.active .hot").count() == 5))
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(400)
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(800)
    ok.append(("galería título", page.locator(".gtitle").inner_text() == "El taller, en imágenes"))
    ok.append(("5 fotos cargadas", page.evaluate("[...document.querySelectorAll('.shot img')].every(i => i.naturalWidth > 0)")))
    ok.append(("créditos", page.text_content(".gfoot .credits").strip() == "Fisabio · UPV · UV · FECYT"))
    page.evaluate("openModal('p2m1')")
    page.wait_for_timeout(200)
    ok.append(("conclusiones del informe", "voluntarismo individual" in page.locator("#mtext").inner_text()))
    ok.append(("sin editor", page.locator("#editbar").count() == 0))
    ok.append(("0 errores consola", len(errs) == 0))
    page.screenshot(path="C:/Users/gipsy/Documents/Obsidian Vault/03 Proyectos/FISABIO/Taller-Ciencia-Participativa/captura_web.png", full_page=False)
    page.close()
    b.close()

for n, c in ok:
    if not c:
        print("FALLO:", n)
        print("errores:", errs[:3])
        raise SystemExit(1)
print("WEB PÚBLICA TODO OK")
