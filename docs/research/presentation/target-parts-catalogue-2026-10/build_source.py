#!/usr/bin/env python3
"""Write the `theme-asset-source/v0.2` document of the `chrona-target-parts` catalogue (#718/#849).

The paths in the source YAML are drawn by the formulas below, from the structure of the hand-drawn target pages in
the sibling folders (the Yuya lantern and scroll, the Title Card hexagon and hazard tab, the Tenth Frame pin, the
Sunday star and dots, the Marquee bulb). They are original geometry; no font outline or third-party artwork is
used. The seal characters are monoline skeletons fitted into a frame.

    python docs/research/presentation/target-parts-catalogue-2026-10/build_source.py          # check, prints a diff summary
    python docs/research/presentation/target-parts-catalogue-2026-10/build_source.py --write  # rewrite the source

The committed source is the authority; this script keeps the numbers reproducible. After a change, run
`chrona icon-catalog import --theme-assets SOURCE --output CATALOG`, refresh the manifest hashes, and render the gallery.
"""
from __future__ import annotations

import math
import re

# ---------------------------------------------------------------- formatting


def n(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def P(cmds: list) -> str:
    """cmds: list of (letter, *numbers) -> path string with explicit absolute M/L/Q/Z."""
    out = []
    for c in cmds:
        out.append(c[0] + (" " + " ".join(n(v) for v in c[1:]) if len(c) > 1 else ""))
    return " ".join(out)


def poly(points, close=True):
    cmds = [("M", *points[0])] + [("L", *p) for p in points[1:]]
    if close:
        cmds.append(("Z",))
    return cmds


def rect(x, y, w, h, reverse=False):
    pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    if reverse:
        pts = [pts[0], pts[3], pts[2], pts[1]]
    return poly(pts)


def rrect(x, y, w, h, r, reverse=False):
    if not reverse:
        return [("M", x + r, y), ("L", x + w - r, y), ("Q", x + w, y, x + w, y + r), ("L", x + w, y + h - r),
                ("Q", x + w, y + h, x + w - r, y + h), ("L", x + r, y + h), ("Q", x, y + h, x, y + h - r),
                ("L", x, y + r), ("Q", x, y, x + r, y), ("Z",)]
    return [("M", x + r, y), ("Q", x, y, x, y + r), ("L", x, y + h - r), ("Q", x, y + h, x + r, y + h),
            ("L", x + w - r, y + h), ("Q", x + w, y + h, x + w, y + h - r), ("L", x + w, y + r),
            ("Q", x + w, y, x + w - r, y), ("Z",)]


def arc_quads(cx, cy, r, a0, a1, step=22.5):
    """Quadratic chain along a circle arc from angle a0 to a1 (degrees, screen-clockwise, 0 = +x). Returns Q cmds."""
    total = a1 - a0
    k = max(1, math.ceil(abs(total) / step))
    d = total / k
    cmds = []
    for i in range(k):
        s = math.radians(a0 + i * d)
        e = math.radians(a0 + (i + 1) * d)
        m = (s + e) / 2
        rc = r / math.cos((e - s) / 2)
        cmds.append(("Q", cx + rc * math.cos(m), cy + rc * math.sin(m), cx + r * math.cos(e), cy + r * math.sin(e)))
    return cmds


def circle(cx, cy, r, reverse=False):
    if not reverse:
        return [("M", cx + r, cy)] + arc_quads(cx, cy, r, 0, 360) + [("Z",)]
    return [("M", cx + r, cy)] + arc_quads(cx, cy, r, 0, -360) + [("Z",)]


def cubic_to_quads(p0, c1, c2, p3, n_seg=4):
    cmds = []

    def pt(t):
        u = 1 - t
        return (u ** 3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t ** 3 * p3[0],
                u ** 3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t ** 3 * p3[1])

    def d(t):
        u = 1 - t
        return (3 * u * u * (c1[0] - p0[0]) + 6 * u * t * (c2[0] - c1[0]) + 3 * t * t * (p3[0] - c2[0]),
                3 * u * u * (c1[1] - p0[1]) + 6 * u * t * (c2[1] - c1[1]) + 3 * t * t * (p3[1] - c2[1]))

    for i in range(n_seg):
        t0, t1 = i / n_seg, (i + 1) / n_seg
        a, b = pt(t0), pt(t1)
        da, db = d(t0), d(t1)
        # intersection of tangents; fall back to midpoint
        det = da[0] * db[1] - da[1] * db[0]
        if abs(det) < 1e-9:
            q = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        else:
            s = ((b[0] - a[0]) * db[1] - (b[1] - a[1]) * db[0]) / det
            q = (a[0] + s * da[0], a[1] + s * da[1])
        cmds.append(("Q", q[0], q[1], b[0], b[1]))
    return cmds


def clip_poly(points, x0, y0, x1, y1):
    def clip(pts, inside, inter):
        out = []
        for i, cur in enumerate(pts):
            prev = pts[i - 1]
            if inside(cur):
                if not inside(prev):
                    out.append(inter(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(inter(prev, cur))
        return out

    def ix(xv):
        return lambda a, b: (xv, a[1] + (b[1] - a[1]) * (xv - a[0]) / (b[0] - a[0]))

    def iy(yv):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (yv - a[1]) / (b[1] - a[1]), yv)

    pts = points
    for inside, inter in ((lambda p: p[0] >= x0, ix(x0)), (lambda p: p[0] <= x1, ix(x1)),
                          (lambda p: p[1] >= y0, iy(y0)), (lambda p: p[1] <= y1, iy(y1))):
        if not pts:
            break
        pts = clip(pts, inside, inter)
    return pts


def fit(points_cmds_strokes, box, margin):
    """Scale-and-center helper for skeleton strokes: returns transformed strokes."""
    xs = [p[0] for s in points_cmds_strokes for p in s]
    ys = [p[1] for s in points_cmds_strokes for p in s]
    bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
    w, h = bx1 - bx0, by1 - by0
    avail = box - 2 * margin
    k = min(avail / w, avail / h)
    ox = margin + (avail - w * k) / 2 - bx0 * k
    oy = margin + (avail - h * k) / 2 - by0 * k
    return [[(x * k + ox, y * k + oy) for x, y in s] for s in points_cmds_strokes]


# ------------------------------------------------------------------ glyphs

GLYPHS: dict[str, dict] = {}


def glyph(name, vw, vh, parts):
    GLYPHS[name] = {"vw": vw, "vh": vh, "parts": parts}


def fill(cmds):
    return {"paint": "fill", "d": P(cmds)}


def stroke(cmds, w, cap="round", join="round"):
    return {"paint": "stroke", "d": P(cmds), "strokeWidth": w, "lineCap": cap, "lineJoin": join}


# --- lantern (Yuya): caps, ribbed body as four bands, gaps stand for the rib lines
def band(cx, cy, r, ya, yb):
    """Region of a circle between horizontal lines ya < yb, as a closed quadratic path (clockwise)."""
    def ang(y):
        return math.degrees(math.asin(max(-1, min(1, (y - cy) / r))))
    a_top, a_bot = ang(ya), ang(yb)
    cmds = []
    # right side from top chord down to bottom chord: angles a_top -> a_bot (clockwise on screen)
    cmds.append(("M", cx + r * math.cos(math.radians(a_top)), ya))
    cmds += arc_quads(cx, cy, r, a_top, a_bot, step=15)
    # bottom chord to left side
    cmds.append(("L", cx - r * math.cos(math.radians(a_bot)), yb))
    # left side bottom -> top: angles 180 - a_bot -> 180 - a_top, going clockwise means decreasing? left side:
    cmds += arc_quads(cx, cy, r, 180 - a_bot, 180 - a_top, step=15)
    cmds.append(("Z",))
    return cmds


def lantern():
    cx, cy, r = 12, 12, 8
    caps = [fill(rrect(6.2, 0.8, 11.6, 2.4, 0.7)), fill(rrect(6.2, 20.8, 11.6, 2.4, 0.7))]
    top, bot = cy - r, cy + r
    ribs = [cy - 4, cy, cy + 4]
    g = 0.5
    edges = [top] + sum(([rb - g, rb + g] for rb in ribs), []) + [bot]
    bands = [fill(band(cx, cy, r, edges[i], edges[i + 1])) for i in range(0, len(edges), 2)]
    return caps + bands


glyph("lantern", 24, 24, lantern())


def lantern_outline():
    return [stroke([("M", 6.6, 2), ("L", 17.4, 2)], 1.4), stroke([("M", 6.6, 22), ("L", 17.4, 22)], 1.4),
            stroke(circle(12, 12, 7.3), 1.4)]


glyph("lantern-outline", 24, 24, lantern_outline())


# --- hexagon (Title Card): flat-top hexagon, regular
def hexpts(cx, cy, r, rot=0):
    return [(cx + r * math.cos(math.radians(60 * k + rot)), cy + r * math.sin(math.radians(60 * k + rot))) for k in range(6)]


glyph("hexagon", 24, 24, [fill(poly(hexpts(12, 12, 11)))])
glyph("hexagon-outline", 24, 24, [stroke(poly(hexpts(12, 12, 10.2)), 1.6, join="miter")])


# --- pin (Tenth Frame): bowling pin silhouette, two stripe knockouts
def pin_outline_cmds(sx, ox, oy, reverse=False):
    # target path, y up from -8 (top) to 8 (bottom), x symmetric
    def T(x, y):
        return (ox + x * sx, oy + y * sx)
    segs = [
        ((0, -8), (2.4, -8), (2.6, -5.2), (1.6, -3.2)),
        ((1.6, -3.2), (1.2, -2.2), (1.4, -1.4), (2.6, 0)),
        ((2.6, 0), (4.6, 2.2), (4.2, 6), (2.2, 8)),
    ]
    right = [("M", *T(0, -8))]
    for a, b, c, d in segs:
        right += cubic_to_quads(T(*a), T(*b), T(*c), T(*d), 3)
    right.append(("L", *T(-2.2, 8)))
    left_segs = [
        ((-2.2, 8), (-4.2, 6), (-4.6, 2.2), (-2.6, 0)),
        ((-2.6, 0), (-1.4, -1.4), (-1.2, -2.2), (-1.6, -3.2)),
        ((-1.6, -3.2), (-2.6, -5.2), (-2.4, -8), (0, -8)),
    ]
    for a, b, c, d in left_segs:
        right += cubic_to_quads(T(*a), T(*b), T(*c), T(*d), 3)
    right.append(("Z",))
    return right


def pin_parts():
    s = 1.38
    body = pin_outline_cmds(s, 12, 12)
    # stripes (holes): reverse winding relative to body. Body path is clockwise-ish (top -> right -> bottom -> left) on screen.
    def T(x, y):
        return (12 + x * s, 12 + y * s)
    st1 = rect(*T(-1.9, -3.4), 3.8 * s, 1.3 * s, reverse=True)
    st2 = rect(*T(-1.7, -1.6), 3.4 * s, 1.1 * s, reverse=True)
    return [fill(body + st1 + st2)]


glyph("pin", 24, 24, pin_parts())
glyph("pin-outline", 24, 24, [stroke(pin_outline_cmds(1.3, 12, 12), 1.5)])


# --- star (Sunday): five-point, 10-vertex star, inner ratio .45
def starpts(cx, cy, r, ratio=0.45):
    return [(cx + (r if k % 2 == 0 else r * ratio) * math.cos(math.radians(-90 + 36 * k)),
             cy + (r if k % 2 == 0 else r * ratio) * math.sin(math.radians(-90 + 36 * k))) for k in range(10)]


glyph("star", 24, 24, [fill(poly(starpts(12, 12.8, 11.4)))])
glyph("star-outline", 24, 24, [stroke(poly(starpts(12, 12.8, 10.4)), 1.5)])

# --- diamond (Marquee, Title card): plain and with a faceted inner cut
glyph("diamond", 24, 24, [fill(poly([(12, 1), (23, 12), (12, 23), (1, 12)]))])
glyph("diamond-outline", 24, 24, [stroke(poly([(12, 2), (22, 12), (12, 22), (2, 12)]), 1.6, join="miter")])

# ----------------------------------------------------------- frames, marks


# hanging-scroll mounting (Yuya)
def scroll_frame():
    parts = [stroke([("M", 15, 7), ("L", 24, 1.6), ("L", 33, 7)], 1.1)]
    parts.append(fill(rrect(2, 7, 44, 4.4, 2.2)))                         # top rod
    parts.append(fill(rect(4.5, 12.6, 39, 43.6) + rect(8.2, 16.3, 31.6, 36.2, reverse=True)))  # mounting ring
    parts.append(fill(rrect(2, 57.2, 44, 4.8, 2.4)))                       # bottom rod
    parts.append(fill(circle(2.6, 59.6, 2.6)))                             # knob left
    parts.append(fill(circle(45.4, 59.6, 2.6)))                            # knob right
    return parts


glyph("scroll-frame", 48, 64, scroll_frame())


# newspaper-clipping edge (Marquee): deckled ragged torn-paper line
def clipping_edge():
    low = [(0.6, 5), (3.4, 6.4), (6, 4.4), (9.6, 6.8), (12.6, 4.8), (15.4, 6.2), (19, 4.2), (22.2, 6.6), (26, 4.9),
           (29.4, 6.9), (33, 4.4), (36.4, 6.3), (40, 4.1), (43.4, 6.7), (47, 5), (50.2, 6.9), (54, 4.6), (57.2, 6.3),
           (60.6, 4.9), (63.4, 6.1)]
    up = [(x, y - 3.4) for x, y in low]
    return [fill(poly(up + low[::-1]))]


glyph("clipping-edge", 64, 8, clipping_edge())


# bulb border element (Marquee): lit core with a glass ring; glow is a Theme treatment, not a part
glyph("bulb", 16, 16, [fill(circle(8, 8, 3.2)), stroke(circle(8, 8, 5.6), 1)])

# inked panel corner (Sunday): heavy L-bracket plus a fine inner rule
glyph("panel-corner", 16, 16, [
    fill(poly([(0, 0), (16, 0), (16, 3), (3, 3), (3, 16), (0, 16)])),
    fill(poly([(5.4, 5.4), (16, 5.4), (16, 6.4), (6.4, 6.4), (6.4, 16), (5.4, 16)])),
])


# hazard tab (Title Card kind corner): outlined tab with 45-degree stripes
def hazard_tab():
    parts = [stroke(rect(0.6, 0.6, 54.8, 22.8), 1.2, join="miter")]
    H = 24
    x = -H
    while x < 56:
        pts = [(x, H), (x + 6, H), (x + 6 + H, 0), (x + H, 0)]
        c = clip_poly(pts, 1.2, 1.2, 54.8, 22.8)
        if len(c) >= 3:
            parts.append(fill(poly(c)))
        x += 12
    return parts


glyph("hazard-tab", 56, 24, hazard_tab())


# ------------------------------------------------------------------ seals

# monoline skeletons in a free coordinate space; fitted into the seal at build time
KIKEN = [  # 危
    [(35, 8), (8, 40)],
    [(64, 12), (51, 32)],
    [(42, 32.5), (94, 32.5)],
    [(27, 36), (24, 55), (21, 72), (7, 97)],
    [(37, 48), (37, 92), (40, 94), (84, 94), (90, 92), (91, 86), (94, 75)],
    [(37, 50), (80, 50), (80, 72), (56, 72)],
]
KI = [  # 記
    [(12, 12), (36, 12)],
    [(5, 25.5), (42, 25.5)],
    [(11, 39), (36, 39)],
    [(11, 52), (36, 52)],
    [(11, 65), (38, 65), (38, 95), (11, 95), (11, 65)],
    [(49, 13), (88, 13), (88, 56)],
    [(50, 46), (88, 46)],
    [(52, 46), (52, 92), (55, 95), (84, 95), (89, 92), (90, 76)],
]


def seal(strokes):
    fitted = fit(strokes, 32, 8.2)
    parts = [stroke(rrect(1.6, 1.6, 28.8, 28.8, 3.4), 1.8, join="round")]
    for s in fitted:
        parts.append(stroke(poly(s, close=False), 1.5))
    return parts


glyph("seal-risk", 32, 32, seal(KIKEN))
glyph("seal-note", 32, 32, seal(KI))

# ---------------------------------------------------------------- patterns

PATTERNS: dict[str, dict] = {}


def pattern(name, w, h, angle, prims):
    PATTERNS[name] = {"w": w, "h": h, "angle": angle, "prims": prims}


def line(x1, y1, x2, y2, sw):
    return {"kind": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "strokeWidth": sw}


def circ(cx, cy, r):
    return {"kind": "circle", "cx": cx, "cy": cy, "radius": r}


def seigaiha_circle(cx, cy, radius, fill_channel):
    return {"kind": "circle", "cx": cx, "cy": cy, "radius": radius,
            "fillChannel": fill_channel, "strokeWidth": 0.8}


# hatch family: one centred stripe per tile, 45 degrees (a stripe on the tile edge would be clipped to half width)
pattern("hatch-fine", 4, 4, 45, [line(2, 0, 2, 4, 1.3)])
pattern("hatch", 5, 5, 45, [line(2.5, 0, 2.5, 5, 2)])
pattern("hatch-wide", 6, 6, 45, [line(3, 0, 3, 6, 2)])
# hazard stripes: half of a 12 unit tile is ink, 45 degrees
pattern("hazard-stripes", 12, 12, 45, [{"kind": "rect", "x": 0, "y": 0, "inlineSize": 6, "blockSize": 12}])
# Ben-Day dots, 20 degrees
pattern("ben-day-dots", 6, 6, 20, [circ(3, 3, 1.35)])
pattern("ben-day-dots-fine", 5, 5, 20, [circ(2.5, 2.5, 1.1)])
# bulb row: one lit bulb per 14 unit cell
pattern("bulb-row", 14, 14, 0, [circ(7, 7, 3)])


def hexlattice(name, r, sw):
    w = round(math.sqrt(3) * r, 2)
    h = 3 * r
    a = [
        (w / 2, 0.5 * r, w, r), (w, r, w, 2 * r), (w, 2 * r, w / 2, 2.5 * r), (w / 2, 2.5 * r, 0, 2 * r),
        (0, 2 * r, 0, r), (0, r, w / 2, 0.5 * r), (w / 2, 0, w / 2, 0.5 * r), (w / 2, 2.5 * r, w / 2, h),
    ]
    pattern(name, w, h, 0, [line(round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2), sw) for x1, y1, x2, y2 in a])


hexlattice("hexagon-lattice", 7, 0.9)
hexlattice("hexagon-lattice-wide", 16, 0.8)
pattern("seigaiha", 20, 10, 0, [
    seigaiha_circle(0, 10, 10, "substrate"),
    seigaiha_circle(0, 10, 7, "none"),
    seigaiha_circle(0, 10, 4, "none"),
    seigaiha_circle(20, 10, 10, "substrate"),
    seigaiha_circle(20, 10, 7, "none"),
    seigaiha_circle(20, 10, 4, "none"),
    seigaiha_circle(10, 5, 10, "substrate"),
    seigaiha_circle(10, 5, 7, "none"),
    seigaiha_circle(10, 5, 4, "none"),
])


# ------------------------------------------------------------------- output

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
ICONS = ROOT / "src/chrona/resources/icons"
SOURCE = ICONS / "chrona-target-parts-v2026-10-09.source.yaml"
NOTICE = ICONS / "chrona-target-parts.NOTICE"


def _density(entry: dict) -> int:
    from chrona.presentation.icons.normalizer import IconNormalizationError, normalize_pattern_entry
    value = {"tile": {"inlineSize": entry["w"], "blockSize": entry["h"]}, "angle": entry["angle"],
             "densityBasisPoints": 1, "primitives": entry["prims"]}
    try:
        return normalize_pattern_entry(value)["densityBasisPoints"]
    except IconNormalizationError as error:
        found = re.search(r"derived=(\d+)", getattr(error, "detail", "") or str(error))
        if not found:
            raise
        return int(found.group(1))


def _num(value) -> str:
    return n(value) if isinstance(value, float) else str(value)


def render_source() -> str:
    glyph_lines = []
    for name in sorted(GLYPHS):
        entry = GLYPHS[name]
        glyph_lines += [f"    {name}:", f"      viewport: {{inlineSize: {entry['vw']}, blockSize: {entry['vh']}}}", "      parts:"]
        for part in entry["parts"]:
            items = [f"paint: {part['paint']}"]
            if part["paint"] == "stroke":
                items += [f"strokeWidth: {_num(part['strokeWidth'])}", f"lineCap: {part['lineCap']}", f"lineJoin: {part['lineJoin']}"]
            items.append(f'd: "{part["d"]}"')
            glyph_lines.append("        - {" + ", ".join(items) + "}")
    pattern_lines = []
    for name in sorted(PATTERNS):
        entry = PATTERNS[name]
        pattern_lines += [f"    {name}:", f"      tile: {{inlineSize: {_num(entry['w'])}, blockSize: {_num(entry['h'])}}}",
                          f"      angle: {_num(entry['angle'])}", f"      densityBasisPoints: {_density(entry)}", "      primitives:"]
        for primitive in entry["prims"]:
            pattern_lines.append("        - {" + ", ".join(f"{k}: {_num(v)}" for k, v in primitive.items()) + "}")
    notice = NOTICE.read_text(encoding="utf-8").rstrip("\n").split("\n")
    notice_block = "\n".join(("      " + line) if line else "" for line in notice)
    return ("version: chrona/theme-asset-source/v0.2\nkind: theme-asset-source\nid: chrona-target-parts-v2026-10-09\nbody:\n"
            "  set: chrona-target-parts\n  aliases: [target-parts]\n  license:\n    spdx: MIT\n    notice: |\n"
            f"{notice_block}\n  glyphs:\n" + "\n".join(glyph_lines) + "\n  patterns:\n" + "\n".join(pattern_lines) + "\n")


def main() -> int:
    text = render_source()
    if "--write" in sys.argv:
        SOURCE.write_text(text, encoding="utf-8")
        print("wrote", SOURCE)
        return 0
    same = SOURCE.read_text(encoding="utf-8") == text
    print("source is reproduced exactly" if same else "source differs from the formulas (run with --write to rewrite it)")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
