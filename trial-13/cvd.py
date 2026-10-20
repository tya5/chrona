"""Machado et al. 2009 (severity 1.0) colour-vision-deficiency simulation, CIEDE2000, legend analysis."""
import json, re, sys, itertools
from pathlib import Path
import numpy as np
from PIL import Image

M = {
    "protan": np.array([[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]]),
    "deutan": np.array([[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]]),
    "tritan": np.array([[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]]),
}


def to_lin(c):
    c = np.asarray(c, dtype=float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


def simulate_rgb(rgb01, kind):
    if kind == "normal":
        return rgb01
    lin = to_lin(rgb01)
    return to_srgb(lin @ M[kind].T)


def simulate_png(src, dst, kind):
    im = Image.open(src).convert("RGBA")
    a = np.asarray(im).astype(float) / 255.0
    rgb = simulate_rgb(a[..., :3], kind)
    outa = np.concatenate([rgb, a[..., 3:]], axis=-1)
    Image.fromarray((outa * 255 + 0.5).astype(np.uint8), "RGBA").save(dst)


def rgb_to_lab(rgb01):
    lin = to_lin(rgb01)
    Mx = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ Mx.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def de2000(lab1, lab2):
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dLp = L2 - L1
    dCp = C2p - C1p
    if C1p * C2p == 0:
        dhp = 0
    else:
        dhp = h2p - h1p
        if dhp > 180: dhp -= 360
        elif dhp < -180: dhp += 360
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp / 2))
    Lbp = (L1 + L2) / 2
    Cbp = (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbp = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        hbp = (h1p + h2p + 360) / 2
    else:
        hbp = (h1p + h2p - 360) / 2
    T = 1 - 0.17 * np.cos(np.radians(hbp - 30)) + 0.24 * np.cos(np.radians(2 * hbp)) + 0.32 * np.cos(np.radians(3 * hbp + 6)) - 0.20 * np.cos(np.radians(4 * hbp - 63))
    dth = 30 * np.exp(-((hbp - 275) / 25) ** 2)
    Rc = 2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / np.sqrt(20 + (Lbp - 50) ** 2)
    Sc = 1 + 0.045 * Cbp
    Sh = 1 + 0.015 * Cbp * T
    Rt = -np.sin(np.radians(2 * dth)) * Rc
    return float(np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh)))


def hex01(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def legend_swatches(scene):
    surf = scene["surfaces"][0]
    page = (surf.get("canvasPaint") or {}).get("fill", "#FFFFFF")
    keys = {}
    labels = {}
    for p in surf["primitives"]:
        if p.get("purpose") == "legend-label" or (p.get("slotId") == "legend" and p.get("kind") == "Text"):
            labels[p["id"].split(":", 1)[1] if ":" in p["id"] else p["id"]] = p.get("text")
            continue
        if not (p.get("slotId") == "legend" or p.get("purpose") == "legend-swatch") or p.get("kind") == "Text":
            continue
        key = re.sub(r":part\d+$", "", p["id"]).replace("legend-swatch:", "")
        keys.setdefault(key, []).append(p)
    out = []
    for key, parts in keys.items():
        inks = []
        for p in parts:
            pa = p.get("paint") or {}
            for ch in ("fill", "stroke"):
                v = pa.get(ch)
                if isinstance(v, str) and v.startswith("#") and len(v) == 7 and v.upper() != page.upper():
                    inks.append((ch, v.upper()))
        # representative: fill unless it equals page / near-white, else stroke
        rep = None
        for ch, v in inks:
            if ch == "fill" and de2000(rgb_to_lab(hex01(v)), rgb_to_lab(hex01(page))) > 3:
                rep = v; break
        if rep is None and inks:
            rep = inks[0][1]
        shape = "+".join(sorted({p.get("kind") for p in parts}))
        dash = any((p.get("paint") or {}).get("dash") for p in parts)
        lab = labels.get(key) or labels.get(key.split(":")[0])
        if rep:
            out.append(dict(key=key, label=lab, colour=rep, shape=shape, dashed=dash, role=parts[0].get("visualRole")))
    return page, out


def analyse(pid, outdir):
    scene = json.load(open(outdir / f"{pid}.scene.json"))
    page, sw = legend_swatches(scene)
    res = {"preset": pid, "page": page, "swatches": sw, "worst": {}, "flagged": {}}
    for kind in ("normal", "deutan", "protan", "tritan"):
        labs = {s["key"]: rgb_to_lab(simulate_rgb(hex01(s["colour"]), kind)) for s in sw}
        pairs = []
        for a, b in itertools.combinations(sw, 2):
            d = de2000(labs[a["key"]], labs[b["key"]])
            pairs.append((d, a, b))
        pairs.sort(key=lambda t: t[0])
        if pairs:
            d, a, b = pairs[0]
            res["worst"][kind] = dict(de=round(d, 2), a=a["label"] or a["key"], b=b["label"] or b["key"], ca=a["colour"], cb=b["colour"])
        res["flagged"][kind] = [dict(de=round(d, 2), a=a["label"] or a["key"], b=b["label"] or b["key"], ca=a["colour"], cb=b["colour"],
                                     same_shape=(a["shape"] == b["shape"] and a["dashed"] == b["dashed"]))
                                for d, a, b in pairs if d < 10]
    return res


if __name__ == "__main__":
    outdir = Path(sys.argv[1])
    sim = outdir / "sim"
    sim.mkdir(exist_ok=True)
    results = []
    for pid in sys.argv[2:]:
        for kind in ("deutan", "protan", "tritan"):
            simulate_png(outdir / f"{pid}.png", sim / f"{pid}.{kind}.png", kind)
        results.append(analyse(pid, outdir))
    json.dump(results, open(outdir / "legend_de.json", "w"), indent=1)
    for r in results:
        print(r["preset"], {k: v["de"] for k, v in r["worst"].items()})
