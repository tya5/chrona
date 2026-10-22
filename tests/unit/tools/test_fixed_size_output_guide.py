"""The fixed-size guide states how to fit a slide or page, and its page-size table is the registry's (#1870)."""
from __future__ import annotations

import re
from pathlib import Path

from chrona.presentation.layout.paper_size import PAGE_SIZE_NAMES, viewport_for_page_size

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
GUIDE = ROOT / "docs/guides/fixed-size-output.md"


def test_guide_says_the_viewport_is_a_minimum_and_what_is_not_supported():
    prose = " ".join(GUIDE.read_text(encoding="utf-8").split())
    assert "is a **minimum**" in prose
    for statement in ("**No fit-to-page.**", "**No pagination.**", "W_LAYOUT_CANVAS_EXCEEDS_VIEWPORT",
                      "`selection.include`", "Chrona has no separate `--page-size` option"):
        assert statement in prose, statement


def test_guide_page_size_table_matches_the_named_page_registry():
    text = GUIDE.read_text(encoding="utf-8")
    rows = re.findall(r"^\| (?P<name>A3|A4|A5|Letter|Legal) landscape / portrait \| `(?P<land>\d+x\d+)` / `(?P<port>\d+x\d+)` \|$",
                      text, re.MULTILINE)
    assert len(rows) == 5
    for name, landscape, portrait in rows:
        key = name.lower()
        assert f"{key}-landscape" in PAGE_SIZE_NAMES
        assert landscape == "x".join(map(str, viewport_for_page_size(f"{key}-landscape")))
        assert portrait == "x".join(map(str, viewport_for_page_size(f"{key}-portrait")))
