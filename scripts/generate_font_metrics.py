"""Generate a deterministic Chrona font-metrics table from one explicit font file."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from fontTools.ttLib import TTFont


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("font", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--family", required=True)
    parser.add_argument("--weight", required=True, type=int)
    args = parser.parse_args()

    payload = args.font.read_bytes()
    font = TTFont(args.font)
    cmap = font.getBestCmap() or {}
    hmtx = font["hmtx"].metrics
    units = int(font["head"].unitsPerEm)
    table = {
        "version": "chrona/font-metrics/v1",
        "family": args.family,
        "weight": args.weight,
        "sourceContentIdentity": "sha256:" + sha256(payload).hexdigest(),
        "unitsPerEm": units,
        "ascent": int(font["hhea"].ascent),
        "descent": int(font["hhea"].descent),
        "defaultAdvance": int(hmtx.get(".notdef", (units, 0))[0]),
        "advances": {str(code): int(hmtx[name][0]) for code, name in sorted(cmap.items()) if name in hmtx},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(table, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
