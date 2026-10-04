"""Published Editorial Scene safety and name association.

The #1114 owner decision accepts route suppression caused by primary-mark
safety; all omitted dependencies must remain diagnosed. Visible names retain
the default 2 em reach of their own mark (#760). No generated resource edits.
"""
from __future__ import annotations

import json
from pathlib import Path

from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility

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


def test_slide_16_routes_are_mark_safe_and_every_omission_is_diagnosed() -> None:
    scene, surface = _surface()
    primitives = {item["id"]: item for item in surface["primitives"]}
    dependencies = {item["id"] for item in primitives.values()
                    if item.get("purpose") == "dependency" and item.get("sourceKind") == "relation"
                    and item["id"].startswith("relation:")}
    suppressed = [item.removeprefix("W_LAYOUT_RELATION_SUPPRESSED:") for item in scene["diagnostics"]
                  if item.startswith("W_LAYOUT_RELATION_SUPPRESSED:")]
    assert len(suppressed) == len(set(suppressed)), "each omitted relation is diagnosed once"
    assert dependencies.isdisjoint(suppressed), "a suppressed relation must not be drawn"
    assert len(dependencies) + len(suppressed) == scene["manifest"]["contentFamilyCounts"]["relations"]
    assert dependencies, "safety cannot pass by suppressing every dependency"
    assert not [item for item in evaluate_scene_perceptibility(scene)
                if item.code == "E_SCENE_RELATION_THROUGH_MARK"]


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
