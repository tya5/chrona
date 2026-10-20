"""Deadline review sheets from out_dl: 4 visions, crop around gate/deadline area (bottom rows) and one task deadline."""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw
from cvd import simulate_png

out = Path("out_dl")
(out / "sim").mkdir(exist_ok=True)
(out / "review").mkdir(exist_ok=True)
V = ("normal", "deutan", "protan", "tritan")
for pid in sys.argv[1:]:
    for v in V[1:]:
        simulate_png(out / f"{pid}.png", out / "sim" / f"{pid}.{v}.png", v)
    s = json.load(open(out / f"{pid}.scene.json"))
    marks = [p for p in s["surfaces"][0]["primitives"] if p.get("purpose") == "deadline-mark"]
    W, H = Image.open(out / f"{pid}.png").size
    # centre on the go-no-go / launch region: the last marks (gates), else max x
    m = max(marks, key=lambda p: p["bounds"]["block"])
    cx, cy = m["bounds"]["inline"], m["bounds"]["block"]
    x0 = int(max(0, min(W - 800, cx - 500)))
    y0 = int(max(0, min(H - 400, cy - 300)))
    sheet = Image.new("RGB", (1600, 840), "white")
    d = ImageDraw.Draw(sheet)
    for i, v in enumerate(V):
        im = Image.open(out / f"{pid}.png" if v == "normal" else out / "sim" / f"{pid}.{v}.png").convert("RGB")
        sheet.paste(im.crop((x0, y0, x0 + 800, y0 + 400)), ((i % 2) * 800, (i // 2) * 420 + 20))
        d.text(((i % 2) * 800 + 4, (i // 2) * 420 + 4), v, fill="black")
    sheet.save(out / "review" / f"{pid}.deadline.png")
print("ok")
