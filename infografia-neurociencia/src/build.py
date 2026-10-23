import os, io, re, json, base64, shutil
from PIL import Image

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
assets = os.path.join(base, "assets")
tpl = open(os.path.join(base, "src", "template.html"), encoding="utf-8").read()

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

items = {
    "brain_cover": ("brain_cover.png", 92, None),
    "brain_p2": ("brain_p2.png", 92, None),
    "brain_m1": ("brain_m1.png", 92, None),
    "brain_m2": ("brain_m2.png", 92, None),
    "brain_m3": ("brain_m3.png", 92, None),
    "brain_m4": ("brain_m4.png", 92, None),
    "brain_m5": ("brain_m5.png", 92, None),
    "brain_p2m1": ("brain_p2m1.png", 92, None),
    "brain_p2m2": ("brain_p2m2.png", 92, None),
    "card_a": ("card_a.png", 82, 550),
    "card_b": ("card_b.png", 82, 550),
}

for token, (fn, q, mw) in items.items():
    uri = data_uri(os.path.join(assets, fn), q, mw, lossless=token.startswith("res_"))
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
out = os.path.join(base, "Infografia-Neurociencia.html")
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

out2 = os.path.join(dist, "Infografia-Neurociencia.html")
open(out2, "w", encoding="utf-8").write(public)
print("wrote", out2, round(os.path.getsize(out2)/1024), "KB")
