"""The six HALCYON-1 slides that draw calendar-closed bands key them as Non-working day (#1848)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from chrona.usecases.materialize import materialize

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "halcyon-1"
SLIDES = {"launch-campaign": "03-launch-campaign", "tvac-slip": "04-tvac-slip", "glyph-gates": "12-glyph-gates",
          "gallery-image-notes": "15-gallery-image-notes", "gallery-text-compression": "19-gallery-text-compression",
          "gates": "26-gates"}
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


@pytest.mark.parametrize("slide", tuple(SLIDES))
def test_calendar_closed_bands_are_keyed_once(slide, tmp_path):
    # Render from source in a scratch copy: the committed generated/ files are derived-owned and not read here.
    example = tmp_path / "halcyon-1"
    shutil.copytree(EXAMPLE, example, ignore=shutil.ignore_patterns("generated"))
    (example / "generated").mkdir()
    materialize(example / "manifest.yaml", slide, tmp_path / "out", write=True)
    scene = json.loads((example / "generated" / f"{SLIDES[slide]}.scene.json").read_text(encoding="utf-8"))
    primitives = list(_primitives(scene))
    drawn = [item for item in primitives if item["purpose"] == "calendar-closed"]
    swatches = [item for item in primitives if item["purpose"] == "legend-swatch" and item["sourceRef"] == "calendar-closed"]
    labels = [item for item in primitives if item["purpose"] == "legend-label" and item["sourceRef"] == "calendar-closed"]

    assert drawn and len(swatches) == 1 and len(labels) == 1
    assert not [item for item in scene["diagnostics"] if str(item).startswith(CODE)]
