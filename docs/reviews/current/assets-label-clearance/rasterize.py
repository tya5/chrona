"""Rasterize one review SVG with resvg_py and the repository's bundled font directories (#1848).

Run: python docs/reviews/current/assets-label-clearance/rasterize.py <worktree> <in.svg> <out.png> [<zoom>]
"""
from __future__ import annotations

import sys
from pathlib import Path

import resvg_py


def main(argv: list[str]) -> int:
    root, source, target = Path(argv[0]), argv[1], Path(argv[2])
    zoom = float(argv[3]) if len(argv) > 3 else 1.0
    fonts = [root / "src" / "chrona" / "resources" / "fonts",
             root / "packages" / "chrona-fonts-noto-cjk" / "src" / "chrona_fonts_noto_cjk" / "fonts"]
    target.write_bytes(bytes(resvg_py.svg_to_bytes(svg_path=source, zoom=zoom,
                                                   font_dirs=[str(item) for item in fonts])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
