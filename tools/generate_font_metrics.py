"""Generate a deterministic Chrona font-metrics table from one explicit font file."""
from __future__ import annotations

import argparse
from pathlib import Path

from chrona.presentation.fonts.importer import _axes, _metrics
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("font", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--family", required=True)
    parser.add_argument("--weight", required=True, type=int)
    parser.add_argument("--axis", action="append", default=[], metavar="TAG=VALUE",
                        help="Instantiate one variable-font axis before measuring.")
    args = parser.parse_args()

    payload = args.font.read_bytes()
    font = TTFont(args.font)
    axes = _axes(tuple(args.axis))
    if axes:
        font = instantiateVariableFont(font, axes, inplace=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(_metrics(font, payload, args.family, args.weight))


if __name__ == "__main__":
    main()
