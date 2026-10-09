#!/usr/bin/env python3
"""Reproduce the authored source for the annotation-parts icon catalogue."""
from __future__ import annotations

from pathlib import Path
import sys

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ICONS = ROOT / "src/chrona/resources/icons"
SOURCE = ICONS / "chrona-annotation-parts-v2026-10-09.source.yaml"
NOTICE = ICONS / "chrona-annotation-parts.NOTICE"

RODS = [
    {"paint": "fill", "d": "M 4.2 7 L 43.8 7 Q 46 7 46 9.2 L 46 9.2 Q 46 11.4 43.8 11.4 L 4.2 11.4 Q 2 11.4 2 9.2 L 2 9.2 Q 2 7 4.2 7 Z"},
    {"paint": "fill", "d": "M 4.4 57.2 L 43.6 57.2 Q 46 57.2 46 59.6 L 46 59.6 Q 46 62 43.6 62 L 4.4 62 Q 2 62 2 59.6 L 2 59.6 Q 2 57.2 4.4 57.2 Z"},
    {"paint": "fill", "d": "M 5.2 59.6 Q 5.2 60.12 5 60.59 Q 4.8 61.07 4.44 61.44 Q 4.07 61.8 3.59 62 Q 3.12 62.2 2.6 62.2 Q 2.08 62.2 1.61 62 Q 1.13 61.8 0.76 61.44 Q 0.4 61.07 0.2 60.59 Q 0 60.12 0 59.6 Q 0 59.08 0.2 58.61 Q 0.4 58.13 0.76 57.76 Q 1.13 57.4 1.61 57.2 Q 2.08 57 2.6 57 Q 3.12 57 3.59 57.2 Q 4.07 57.4 4.44 57.76 Q 4.8 58.13 5 58.61 Q 5.2 59.08 5.2 59.6 Z"},
    {"paint": "fill", "d": "M 48 59.6 Q 48 60.12 47.8 60.59 Q 47.6 61.07 47.24 61.44 Q 46.87 61.8 46.39 62 Q 45.92 62.2 45.4 62.2 Q 44.88 62.2 44.41 62 Q 43.93 61.8 43.56 61.44 Q 43.2 61.07 43 60.59 Q 42.8 60.12 42.8 59.6 Q 42.8 59.08 43 58.61 Q 43.2 58.13 43.56 57.76 Q 43.93 57.4 44.41 57.2 Q 44.88 57 45.4 57 Q 45.92 57 46.39 57.2 Q 46.87 57.4 47.24 57.76 Q 47.6 58.13 47.8 58.61 Q 48 59.08 48 59.6 Z"},
]
MOUNTING = [
    {"paint": "stroke", "strokeWidth": 1.1, "lineCap": "round", "lineJoin": "round", "d": "M 15 7 L 24 1.6 L 33 7"},
    {"paint": "fill", "d": "M 4.5 12.6 L 43.5 12.6 L 43.5 56.2 L 4.5 56.2 Z M 8.2 16.3 L 8.2 52.5 L 39.8 52.5 L 39.8 16.3 Z"},
]


def render_source() -> str:
    notice = NOTICE.read_text(encoding="utf-8")
    document = {
        "version": "chrona/theme-asset-source/v0.2",
        "kind": "theme-asset-source",
        "id": "chrona-annotation-parts-v2026-10-09",
        "body": {
            "set": "chrona-annotation-parts",
            "aliases": ["annotation-parts"],
            "license": {"spdx": "MIT", "notice": notice},
            "glyphs": {
                "scroll-mounting": {"viewport": {"inlineSize": 48, "blockSize": 64}, "parts": MOUNTING},
                "scroll-rods": {"viewport": {"inlineSize": 48, "blockSize": 64}, "parts": RODS},
            },
            "patterns": {},
        },
    }
    return yaml.safe_dump(document, sort_keys=False, allow_unicode=True, width=10000)


def main() -> int:
    text = render_source()
    if "--write" in sys.argv:
        SOURCE.write_text(text, encoding="utf-8")
        print("wrote", SOURCE)
        return 0
    same = SOURCE.read_text(encoding="utf-8") == text
    print("source is reproduced exactly" if same else "source differs from formulas (use --write)")
    return 0 if same else 1


if __name__ == "__main__":
    raise SystemExit(main())
