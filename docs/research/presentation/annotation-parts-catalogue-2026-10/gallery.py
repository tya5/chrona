#!/usr/bin/env python3
"""Render the two annotation-part glyphs at large and small scales."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CATALOGUE = ROOT / "src/chrona/resources/icons/chrona-annotation-parts-v2026-10-09.yaml"
FONT = ROOT / "src/chrona/resources/fonts/noto-sans-regular-v1.ttf"
THEMES = (("Paper", "#f4ead7", "#30251d"), ("Ink", "#17212c", "#f1c36a"))


def render() -> str:
    glyphs = json.loads(CATALOGUE.read_text(encoding="utf-8"))["body"]["glyphs"]
    if set(glyphs) != {"scroll-mounting", "scroll-rods"}:
        raise ValueError(f"unexpected annotation glyph inventory: {sorted(glyphs)}")
    width, height = 720, 390
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           f'<rect width="{width}" height="{height}" fill="#fafafa"/>',
           '<text x="24" y="32" font-family="Noto Sans" font-size="19" font-weight="700">chrona-annotation-parts-v2026-10-09</text>']
    for row, name in enumerate(sorted(glyphs)):
        top = 54 + row * 164
        out.append(f'<text x="24" y="{top + 16}" font-family="Noto Sans" font-size="13" font-weight="700">{name}</text>')
        for col, (theme, ground, ink) in enumerate(THEMES):
            x = 24 + col * 336
            y = top + 24
            out.append(f'<rect x="{x}" y="{y}" width="320" height="128" rx="5" fill="{ground}" stroke="#aaa"/>')
            entry = glyphs[name]
            for size, offset_x in ((64, 16), (20, 112)):
                scale = size / max(entry["viewport"].values())
                ox, oy = x + offset_x + (64 - 48 * scale) / 2, y + 8 + (64 - 64 * scale) / 2
                out.append(f'<g transform="translate({ox:.3f} {oy:.3f}) scale({scale:.5f})">')
                for part in entry["parts"]:
                    d = part["data"]
                    if part["paint"] == "fill":
                        out.append(f'<path d="{d}" fill="{ink}"/>')
                    else:
                        out.append(f'<path d="{d}" fill="none" stroke="{ink}" stroke-width="{part["strokeWidth"]}" stroke-linecap="{part["lineCap"]}" stroke-linejoin="{part["lineJoin"]}"/>')
                out.append("</g>")
            out.append(f'<text x="{x + 310}" y="{y + 14}" text-anchor="end" font-family="Noto Sans" font-size="10" fill="{ink}">{theme}</text>')
    out.append("</svg>\n")
    return "".join(out)


def main() -> None:
    svg = render()
    (HERE / "gallery.svg").write_text(svg, encoding="utf-8")
    import resvg_py
    png = resvg_py.svg_to_bytes(svg_string=svg, font_files=[str(FONT)], skip_system_fonts=True, background="#fafafa", dpi=96)
    (HERE / "gallery.png").write_bytes(bytes(png))
    print("wrote", HERE / "gallery.svg", HERE / "gallery.png")


if __name__ == "__main__":
    main()
