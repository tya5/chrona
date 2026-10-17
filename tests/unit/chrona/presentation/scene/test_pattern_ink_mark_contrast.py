"""#1658: the mark gate judges a patterned fill by its strongest pattern ink against the ground."""
from __future__ import annotations

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast

PAPER = "#FFFDF5"
INK = "#1A1A1A"
BOX = {"inline": 10, "block": 10, "inlineSize": 22, "blockSize": 8}


def _hatch(ink):
    return {"tileInlineSize": 5.0, "tileBlockSize": 5.0, "angleDegrees": 45.0, "densityBasisPoints": 4000,
            "primitives": [{"kind": "path", "paint": "stroke", "strokeWidth": 2.0,
                            "lineCap": "round", "lineJoin": "round",
                            "commands": [{"kind": "move", "points": [2.5, 0.0]},
                                         {"kind": "line", "points": [2.5, 5.0]}]}],
            "origin": [10, 10], "regionBounds": dict(BOX), "clipBounds": dict(BOX), "cornerRadius": 2.0}


def _findings(ink):
    swatch = {"id": "legend-swatch:missing-actual", "kind": "Rect", "sourceRef": "missing-actual",
              "sourceKind": "legend", "purpose": "legend-swatch", "visualRole": "missing-actual",
              "paintOrder": 2, "bounds": dict(BOX), "cornerRadius": 2.0,
              "paint": {"fill": PAPER, "stroke": ink, "dash": [], "opacity": 1.0}, "pattern": _hatch(ink)}
    document = {"version": "chrona/scene/v0.7", "kind": "scene", "surfaces": [{
        "id": "s", "canvasPaint": {"fill": PAPER, "opacity": 1}, "primitives": [swatch],
        "decorationDispositions": []}]}
    return evaluate_scene_contrast(document)


def test_hatch_whose_ink_passes_on_the_ground_raises_no_mark_failure():
    findings = _findings(INK)
    assert findings and all(f.code == "E_SCENE_MARK_CONTRAST" for f in findings)
    assert {f.severity for f in findings} == {"info"}


def test_hatch_whose_ink_equals_the_ground_still_fails():
    findings = _findings(PAPER)
    assert any(f.code == "E_SCENE_MARK_CONTRAST" and f.severity != "info" for f in findings)
