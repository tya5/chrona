"""Slide 16 declares a viewport wide enough for every relation and name (#760 item 1).

Owner decision: widen the declared viewport instead of detaching names. The slide is accepted only while
`shipment-campaign` is drawn, no name or relation is suppressed, and every name stays within the default
reach (2 em) of its own mark. The checks decide from the generated Scene only.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCENE = ROOT / "examples/halcyon-1/generated/16-gallery-editorial-lanes.scene.json"
DEFAULT_REACH_EM = 2.0


def _surface() -> tuple[dict, dict]:
    scene = json.loads(SCENE.read_text(encoding="utf-8"))
    return scene, scene["surfaces"][0]


def _rect(primitive: dict) -> tuple[float, float, float, float]:
    box = primitive["bounds"]
    return box["inline"], box["block"], box["inline"] + box["inlineSize"], box["block"] + box["blockSize"]


def _gap(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    dx = max(a[0] - b[2], b[0] - a[2], 0.0)
    dy = max(a[1] - b[3], b[1] - a[3], 0.0)
    return (dx * dx + dy * dy) ** 0.5


def test_slide_16_draws_shipment_campaign_without_losing_anything() -> None:
    scene, surface = _surface()
    primitives = {item["id"]: item for item in surface["primitives"]}
    dependencies = [item for item in primitives.values() if item.get("purpose") == "dependency"]
    assert any(item["sourceRef"] == "shipment-campaign" for item in dependencies)
    lost = [item for item in scene["diagnostics"]
            if item.startswith(("W_LAYOUT_RELATION_SUPPRESSED:", "W_LAYOUT_LABEL_SUPPRESSED:"))]
    assert lost == []
    labels = [item for item in primitives.values() if item.get("purpose") == "member-label"]
    assert len(labels) == len(surface["laneMembers"])


def test_slide_16_names_stay_within_the_default_reach_of_their_marks() -> None:
    _, surface = _surface()
    primitives = {item["id"]: item for item in surface["primitives"]}
    checked = 0
    for member in surface["laneMembers"]:
        emitted = [primitives[name] for name in member["emittedPrimitiveIds"]]
        label = next(item for item in emitted if item.get("purpose") == "member-label")
        marks = [_rect(item) for item in emitted if item.get("purpose") in {"planned", "actual"}]
        reach = DEFAULT_REACH_EM * label["textLayout"]["fontSize"]
        assert marks and min(_gap(_rect(label), mark) for mark in marks) <= reach, member["memberId"]
        checked += 1
    assert checked == len(surface["laneMembers"]) > 0
