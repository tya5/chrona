#!/usr/bin/env python3
"""Every `gallerySet` the builtin preset library names is a gallery set that exists (#1403).

A set is `docs/gallery/sets/<name>.md`. `chrona preset list` reports the name, so a name with no page sends a user nowhere.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
import sys

from chrona.resources import safe_load

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "src" / "chrona" / "resources" / "presets" / "library.yaml"
SETS = ROOT / "docs" / "gallery" / "sets"


def unknown_gallery_sets(entries: Iterable[Mapping[str, object]], sets: Path = SETS) -> list[str]:
    """`<preset id>: <set name>` for every entry naming a set that has no page under `sets`."""
    known = {path.stem for path in sets.glob("*.md")}
    return [f"{entry['id']}: {entry['gallerySet']}" for entry in entries if "gallerySet" in entry and entry["gallerySet"] not in known]


def main() -> int:
    entries = safe_load(LIBRARY.read_bytes())["entries"]
    unknown = unknown_gallery_sets(entries)
    for item in unknown:
        print(f"E_PRESET_GALLERY_SET_UNKNOWN: {item}", file=sys.stderr)
    return 1 if unknown else 0


if __name__ == "__main__":
    raise SystemExit(main())
