#!/usr/bin/env python3
"""Render the gallery of the packaged `chrona-target-parts` catalogue (#718).

Reads the normalized catalogue the wheel ships, and draws every entry at two
sizes in two Themes. The part geometry never carries a colour: this script
stands in for a Theme and paints parts from two token sets, which is the
evidence that colour comes from the Theme and not from the catalogue.

    python docs/research/presentation/target-parts-catalogue-2026-10/render_gallery.py

writes `gallery.svg` and `gallery.png` next to this file. The PNG is produced
with the same pinned resvg route as chrona's own PNG adapter.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CATALOGUE = ROOT / "src/chrona/resources/icons/chrona-target-parts-v2026-10-09.yaml"
FONT = ROOT / "src/chrona/resources/fonts/noto-sans-regular-v1.ttf"
BOLD = ROOT / "src/chrona/resources/fonts/noto-sans-bold-v1.ttf"

# Two Themes, as role tokens. Nothing below this block names a colour.
THEMES = {
    "Hinoki": {"ground": "#EFE3C8", "substrate": "#EFE3C8", "ink": "#231A14", "muted": "#7A6A55", "panel": "#E4D5B3"},
    "Night": {"ground": "#101722", "substrate": "#101722", "ink": "#F2B84B", "muted": "#8E99AB", "panel": "#1A2433"},
}

GROUPS = [
    ("Gate glyphs", ["lantern", "lantern-outline", "hexagon", "hexagon-outline", "pin", "pin-outline", "star", "star-outline", "diamond", "diamond-outline"]),
    ("Frames and borders", ["scroll-frame", "clipping-edge", "bulb", "panel-corner", "hazard-tab"]),
    ("Marks", ["seal-risk", "seal-note"]),
    ("Patterns", ["hatch-fine", "hatch", "hatch-wide", "hazard-stripes", "ben-day-dots", "ben-day-dots-fine", "bulb-row", "hexagon-lattice", "hexagon-lattice-wide", "seigaiha"]),
]

COLUMNS = 6
CELL_W, CELL_H = 248, 172
TILE_W = 112
BIG, SMALL = 64, 20


def num(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def path_data(commands: list[dict]) -> str:
    letters = {"move": "M", "line": "L", "quadratic": "Q", "close": "Z"}
    return " ".join(letters[c["kind"]] + ("" if not c["points"] else " " + " ".join(num(v) for v in c["points"])) for c in commands)


def glyph_markup(entry: dict, box: float, token: dict, tx: float, ty: float) -> str:
    inline, block = entry["viewport"]["inlineSize"], entry["viewport"]["blockSize"]
    scale = box / max(inline, block)
    ox, oy = tx + (box - inline * scale) / 2, ty + (box - block * scale) / 2
    out = [f'<g transform="translate({num(ox)} {num(oy)}) scale({num(scale)})">']
    for part in entry["parts"]:
        if part["paint"] == "fill":
            out.append(f'<path d="{part["data"]}" fill="{token["ink"]}"/>')
        else:
            out.append(f'<path d="{part["data"]}" fill="none" stroke="{token["ink"]}" stroke-width="{num(part["strokeWidth"])}" '
                       f'stroke-linecap="{part["lineCap"]}" stroke-linejoin="{part["lineJoin"]}"/>')
    out.append("</g>")
    return "".join(out)


def pattern_def(pid: str, entry: dict, token: dict, scale: float) -> str:
    width, height = entry["tile"]["inlineSize"], entry["tile"]["blockSize"]
    # Clockwise rotation about the tile centre, then the display scale.
    transform = f'scale({num(scale)}) rotate({num(entry["angle"])} {num(width / 2)} {num(height / 2)})'
    body = [f'<rect width="{num(width)}" height="{num(height)}" fill="{token["substrate"]}"/>']
    for primitive in entry["primitives"]:
        if primitive["kind"] == "circle":
            channel = primitive.get("fillChannel", "ink")
            fill = {"ink": token["ink"], "substrate": token["substrate"], "none": "none"}[channel]
            stroke = f' stroke="{token["ink"]}" stroke-width="{num(primitive["strokeWidth"])}"' if "strokeWidth" in primitive else ""
            body.append(f'<circle cx="{num(primitive["cx"])}" cy="{num(primitive["cy"])}" r="{num(primitive["radius"])}" fill="{fill}"{stroke}/>')
        elif primitive["kind"] == "rect":
            body.append(f'<rect x="{num(primitive["x"])}" y="{num(primitive["y"])}" width="{num(primitive["inlineSize"])}" '
                        f'height="{num(primitive["blockSize"])}" fill="{token["ink"]}"/>')
        else:
            body.append(f'<path d="{path_data(primitive["commands"])}" fill="none" stroke="{token["ink"]}" '
                        f'stroke-width="{num(primitive["strokeWidth"])}" stroke-linecap="{primitive["lineCap"]}" '
                        f'stroke-linejoin="{primitive["lineJoin"]}"/>')
    return (f'<pattern id="{pid}" patternUnits="userSpaceOnUse" width="{num(width)}" height="{num(height)}" '
            f'patternTransform="{transform}">{"".join(body)}</pattern>')


def render() -> str:
    catalogue = json.loads(CATALOGUE.read_text(encoding="utf-8"))["body"]
    glyphs, patterns = catalogue["glyphs"], catalogue["patterns"]
    names = [name for _, group in GROUPS for name in group]
    missing = sorted((set(glyphs) | set(patterns)) - set(names))
    unknown = sorted(set(names) - (set(glyphs) | set(patterns)))
    if missing or unknown:
        raise SystemExit(f"gallery groups out of step with the catalogue: missing {missing}, unknown {unknown}")
    body: list[str] = []
    defs: list[str] = []
    y = 78
    for title, group in GROUPS:
        body.append(f'<text x="24" y="{y}" font-family="Noto Sans" font-weight="700" font-size="17" fill="#222">{title}</text>')
        body.append(f'<line x1="24" x2="{24 + COLUMNS * CELL_W - 16}" y1="{y + 8}" y2="{y + 8}" stroke="#bbb" stroke-width="1"/>')
        y += 20
        for index, name in enumerate(group):
            column, row = index % COLUMNS, index // COLUMNS
            cx, cy = 24 + column * CELL_W, y + row * CELL_H
            body.append(f'<text x="{cx}" y="{cy + 14}" font-family="Noto Sans" font-weight="700" font-size="12" fill="#222">{name}</text>')
            for tile_index, (theme_name, token) in enumerate(THEMES.items()):
                tx = cx + tile_index * (TILE_W + 8)
                ty = cy + 24
                body.append(f'<rect x="{tx}" y="{ty}" width="{TILE_W}" height="{CELL_H - 44}" rx="4" fill="{token["ground"]}" stroke="#bbb" stroke-width="0.8"/>')
                if name in glyphs:
                    big_x = tx + 8
                    body.append(glyph_markup(glyphs[name], BIG, token, big_x, ty + 10))
                    body.append(glyph_markup(glyphs[name], SMALL, token, tx + 8 + BIG + 12, ty + 10 + (BIG - SMALL) / 2))
                    wide = glyphs[name]["viewport"]
                    body.append(f'<text x="{tx + 8}" y="{ty + CELL_H - 52}" font-family="Noto Sans" font-size="9.5" fill="{token["muted"]}">'
                                f'{wide["inlineSize"]}x{wide["blockSize"]} · {len(glyphs[name]["parts"])} parts</text>')
                else:
                    entry = patterns[name]
                    for size_index, scale in enumerate((1, 2)):
                        pid = f"p-{name}-{theme_name.lower()}-{scale}"
                        defs.append(pattern_def(pid, entry, token, scale))
                        px = tx + 8 + size_index * 50
                        body.append(f'<rect x="{px}" y="{ty + 20}" width="46" height="{CELL_H - 44 - 20 - 26}" fill="url(#{pid})" stroke="{token["muted"]}" stroke-width="0.6"/>')
                    body.append(f'<text x="{tx + 8}" y="{ty + CELL_H - 52}" font-family="Noto Sans" font-size="9.5" fill="{token["muted"]}">'
                                f'{num(entry["tile"]["inlineSize"])}x{num(entry["tile"]["blockSize"])} · {num(entry["angle"])}° · '
                                f'{entry["densityBasisPoints"] / 100:g}%</text>')
                body.append(f'<text x="{tx + TILE_W - 6}" y="{ty + 13}" text-anchor="end" font-family="Noto Sans" font-size="8.5" fill="{token["muted"]}">{theme_name}</text>')
        y += math.ceil(len(group) / COLUMNS) * CELL_H + 18
    height = y + 24
    width = 24 + COLUMNS * CELL_W + 8
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'role="img" aria-label="chrona-target-parts catalogue: every glyph and pattern at two sizes in two Themes">')
    title = (f'<rect width="{width}" height="{height}" fill="#fafafa"/>'
             f'<text x="24" y="34" font-family="Noto Sans" font-weight="700" font-size="22" fill="#111">chrona-target-parts-v2026-10-09</text>'
             f'<text x="24" y="56" font-family="Noto Sans" font-size="12.5" fill="#444">{len(glyphs)} glyphs and {len(patterns)} patterns, MIT. '
             f'Glyphs are drawn at 64 and 20 px, patterns at 1x and 2x, each in two Themes; the catalogue carries no colour, the Theme tokens supply ink and substrate.</text>')
    return head + title + "<defs>" + "".join(defs) + "</defs>" + "".join(body) + "</svg>\n"


def main() -> None:
    svg = render()
    (HERE / "gallery.svg").write_text(svg, encoding="utf-8")
    import resvg_py
    png = resvg_py.svg_to_bytes(svg_string=svg, font_files=[str(FONT), str(BOLD)], skip_system_fonts=True, background="#fafafa", dpi=96)
    (HERE / "gallery.png").write_bytes(bytes(png))
    print("wrote", HERE / "gallery.svg", HERE / "gallery.png")


if __name__ == "__main__":
    sys.exit(main())
