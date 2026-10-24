"""The six HALCYON-1 slides that draw calendar-closed bands key them as Non-working day (#1848)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

GENERATED = Path(__file__).resolve().parents[2] / "examples" / "halcyon-1" / "generated"
SLIDES = ("03-launch-campaign", "04-tvac-slip", "12-glyph-gates", "15-gallery-image-notes",
          "19-gallery-text-compression", "26-gates")
CODE = "W_LEGEND_ROLE_UNKEYED"


def _primitives(node):
    if isinstance(node, dict):
        if "purpose" in node:
            yield node
        for value in node.values():
            yield from _primitives(value)
    elif isinstance(node, list):
        for value in node:
            yield from _primitives(value)


@pytest.mark.parametrize("slide", SLIDES)
def test_calendar_closed_bands_are_keyed_once(slide):
    scene = json.loads((GENERATED / f"{slide}.scene.json").read_text(encoding="utf-8"))
    primitives = list(_primitives(scene))
    drawn = [item for item in primitives if item["purpose"] == "calendar-closed"]
    swatches = [item for item in primitives if item["purpose"] == "legend-swatch" and item["sourceRef"] == "calendar-closed"]
    labels = [item for item in primitives if item["purpose"] == "legend-label" and item["sourceRef"] == "calendar-closed"]

    assert drawn and len(swatches) == 1 and len(labels) == 1
    assert not [item for item in scene["diagnostics"] if str(item).startswith(CODE)]
