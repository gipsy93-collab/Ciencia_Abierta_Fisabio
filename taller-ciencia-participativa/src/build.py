import os, io, re, json, base64, shutil
from PIL import Image

import compone_cerebro

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
assets = os.path.join(base, "assets")
tpl = open(os.path.join(base, "src", "template.html"), encoding="utf-8").read()

# el arte del cerebro (SVG con la línea original de Genially) se recompone antes
compone_cerebro.main(verboso=False)

def data_uri(path, quality=90, maxw=None, lossless=False):
    src = Image.open(path)
    im = src.convert("RGBA") if src.mode in ("RGBA","LA","P") else src.convert("RGB")
    if maxw and im.width > maxw:
        h = round(im.height * maxw / im.width)
        im = im.resize((maxw, h), Image.LANCZOS)
    buf = io.BytesIO()
    if lossless:
        im.save(buf, "WEBP", lossless=True, quality=100, method=6)
    else:
        im.save(buf, "WEBP", quality=quality, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()

def svg_uri(path):
    with open(path, "rb") as f:
        return "data:image/svg+xml;base64," + base64.b64encode(f.read()).decode()

items = {
    "card_a": ("card_a.png", 82, 550),
    "card_b": ("card_b.png", 82, 550),
}

for token, (fn, q, mw) in items.items():
    uri = data_uri(os.path.join(assets, fn), q, mw, lossless=token.startswith("res_"))
    tpl = tpl.replace(f"@@{token}@@", uri)
    print(token, round(len(uri)/1024), "KB")

# láminas del cerebro: SVG vectorial + línea original
for token, _, _ in compone_cerebro.LAMINAS:
    uri = svg_uri(os.path.join(assets, "cerebro", token + ".svg"))
    tpl = tpl.replace(f"@@{token}@@", uri)
    print(token, round(len(uri)/1024), "KB")

font = base64.b64encode(open(os.path.join(assets, "outfit.woff2"), "rb").read()).decode()
tpl = tpl.replace("@@FONT@@", "data:font/woff2;base64," + font)

# textos.json: exportado desde el editor de la propia pieza (boton "Exportar textos.json")
# se incrusta en el HTML final para que los cambios dejen de depender del navegador.
over_path = os.path.join(base, "src", "textos.json")
if os.path.exists(over_path):
    with open(over_path, encoding="utf-8-sig") as f:
        over = json.load(f)
    print("textos.json:", len(over), "claves")
else:
    over = {}
    print("textos.json: no existe (se compila con los textos del template)")
tpl = tpl.replace("@@OVERRIDES@@", json.dumps(over, ensure_ascii=False))

left = re.findall(r"@@[A-Za-z_]+@@", tpl)
print("unresolved:", left)
out = os.path.join(base, "Taller-Ciencia-Participativa.html")
open(out, "w", encoding="utf-8").write(tpl)
print("wrote", out, round(os.path.getsize(out)/1024), "KB")

# Version publicable: mismo HTML sin el editor (se quita el bloque marcado como
# EDITOR:INICIO ... EDITOR:FIN) con los textos de textos.json ya incrustados.
mark = re.compile(r"(?:/\*\s*EDITOR:INICIO\s*\*/|<!--\s*EDITOR:INICIO\s*-->)[\s\S]*?"
                  r"(?:/\*\s*EDITOR:FIN\s*\*/|<!--\s*EDITOR:FIN\s*-->)")
public = mark.sub("", tpl)
if "EDITOR:INICIO" in public or "id=\"editbar\"" in public:
    raise SystemExit("quedan restos del editor en la version publica")
dist = os.path.join(base, "dist")
os.makedirs(dist, exist_ok=True)

# fotos referenciadas (no incrustadas): se copian junto a dist para que el HTML
# publicable las encuentre en assets/fotos/
fotos_src = os.path.join(assets, "fotos")
if os.path.isdir(fotos_src):
    fotos_dst = os.path.join(dist, "assets", "fotos")
    os.makedirs(fotos_dst, exist_ok=True)
    copied = 0
    for fn in sorted(os.listdir(fotos_src)):
        s, d = os.path.join(fotos_src, fn), os.path.join(fotos_dst, fn)
        if not os.path.exists(d) or os.path.getsize(s) != os.path.getsize(d):
            shutil.copy2(s, d)
            copied += 1
    print("fotos:", len(os.listdir(fotos_dst)), "en dist/assets/fotos/", f"({copied} copiadas)")

# imágenes del informe (página 4): se copian junto a dist para que el HTML
# publicable las encuentre en assets/informe/
informe_src = os.path.join(assets, "informe")
if os.path.isdir(informe_src):
    informe_dst = os.path.join(dist, "assets", "informe")
    os.makedirs(informe_dst, exist_ok=True)
    copied = 0
    for fn in sorted(os.listdir(informe_src)):
        s, d = os.path.join(informe_src, fn), os.path.join(informe_dst, fn)
        if not os.path.exists(d) or os.path.getsize(s) != os.path.getsize(d):
            shutil.copy2(s, d)
            copied += 1
    print("informe:", len(os.listdir(informe_dst)), "en dist/assets/informe/", f"({copied} copiadas)")

out2 = os.path.join(dist, "Taller-Ciencia-Participativa.html")
open(out2, "w", encoding="utf-8").write(public)
print("wrote", out2, round(os.path.getsize(out2)/1024), "KB")
