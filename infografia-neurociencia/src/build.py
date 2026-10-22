import os, io, re, base64
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
    "res_A": ("res_A.png", 92, None),
    "res_B": ("res_B.png", 92, None),
    "res_C": ("res_C.png", 92, None),
    "res_D": ("res_D.png", 92, None),
    "res_E": ("res_E.png", 92, None),
}

for token, (fn, q, mw) in items.items():
    uri = data_uri(os.path.join(assets, fn), q, mw, lossless=token.startswith("res_"))
    tpl = tpl.replace(f"@@{token}@@", uri)
    print(token, round(len(uri)/1024), "KB")

font = base64.b64encode(open(os.path.join(assets, "outfit.woff2"), "rb").read()).decode()
tpl = tpl.replace("@@FONT@@", "data:font/woff2;base64," + font)

left = re.findall(r"@@[A-Za-z_]+@@", tpl)
print("unresolved:", left)
out = os.path.join(base, "Infografia-Neurociencia.html")
open(out, "w", encoding="utf-8").write(tpl)
print("wrote", out, round(os.path.getsize(out)/1024), "KB")
