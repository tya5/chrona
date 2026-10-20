"""Review sheets: for each preset, a 2x2 crop around the as-of line (normal/deutan/protan/tritan) and stacked legend strips."""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw

outdir = Path(sys.argv[1])
sim = outdir / "sim"
rev = outdir / "review"
rev.mkdir(exist_ok=True)
VIS = ("normal", "deutan", "protan", "tritan")


def img(pid, v):
    return Image.open(outdir / f"{pid}.png" if v == "normal" else sim / f"{pid}.{v}.png").convert("RGB")


for pid in sys.argv[2:]:
    scene = json.load(open(outdir / f"{pid}.scene.json"))
    surf = scene["surfaces"][0]
    prims = surf["primitives"]
    asof = next((p for p in prims if p.get("visualRole") == "as-of" and p.get("purpose") == "as-of"), None)
    W, H = img(pid, "normal").size
    sx = W / scene["viewport"]["width"] if "width" in scene.get("viewport", {}) else 1.0
    x = (asof["bounds"]["inline"] * sx) if asof else W * 0.6
    # crop: 800 x 560 starting at top data rows, centred on as-of
    rows = surf.get("rows") or []
    top = int(min((r["bounds"]["block"] for r in rows), default=100) * sx)
    x0 = int(max(0, min(W - 800, x - 450)))
    y0 = int(max(0, min(H - 560, top + (H - top) * 0.15)))
    sheet = Image.new("RGB", (1600, 1140), "white")
    d = ImageDraw.Draw(sheet)
    for i, v in enumerate(VIS):
        c = img(pid, v).crop((x0, y0, x0 + 800, y0 + 560))
        sheet.paste(c, ((i % 2) * 800, (i // 2) * 580 + 20))
        d.text(((i % 2) * 800 + 4, (i // 2) * 580 + 4), v, fill="black")
    sheet.save(rev / f"{pid}.crop.png")
    # legend strip
    leg = [p for p in prims if p.get("slotId") == "legend"]
    if leg:
        ly0 = int(min(p["bounds"]["block"] for p in leg) * sx) - 6
        ly1 = int(max(p["bounds"]["block"] + p["bounds"]["blockSize"] for p in leg) * sx) + 6
        lx0 = int(min(p["bounds"]["inline"] for p in leg) * sx) - 6
        lx1 = int(max(p["bounds"]["inline"] + p["bounds"]["inlineSize"] for p in leg) * sx) + 6
        lx0, ly0 = max(0, lx0), max(0, ly0)
        lx1, ly1 = min(W, lx1), min(H, ly1)
        h = ly1 - ly0
        strip = Image.new("RGB", (lx1 - lx0 + 70, (h + 4) * 4), "white")
        ds = ImageDraw.Draw(strip)
        for i, v in enumerate(VIS):
            strip.paste(img(pid, v).crop((lx0, ly0, lx1, ly1)), (70, i * (h + 4)))
            ds.text((2, i * (h + 4) + h // 2 - 5), v, fill="black")
        if strip.width > 1600:
            strip = strip.resize((1600, int(strip.height * 1600 / strip.width)))
        strip.save(rev / f"{pid}.legend.png")
print("ok")
