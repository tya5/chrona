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


def _logical_relation_ids(scene: dict, surface: dict) -> set[str]:
    relation_paths = {item["id"]: item for item in surface["primitives"]
                      if item.get("kind") == "Path" and item.get("purpose") == "dependency"
                      and item.get("sourceKind") == "relation" and item["id"].startswith("relation:")}
    fragment_to_relation: dict[str, str] = {}
    stub_relations: set[str] = set()
    for diagnostic in scene["diagnostics"]:
        prefix = "I_LAYOUT_RELATION_RESOLUTION:"
        if not diagnostic.startswith(prefix):
            continue
        payload = json.loads(diagnostic[len(prefix):])
        if payload.get("surfaceId") != surface["id"] or payload.get("stage") != "stub":
            continue
        fragment_ids = payload.get("fragmentIds")
        assert (set(payload) == {"surfaceId", "relationId", "stage", "critical", "fragmentIds"}
                and isinstance(payload.get("relationId"), str) and payload["relationId"]
                and isinstance(payload.get("critical"), bool)
                and isinstance(fragment_ids, list) and len(fragment_ids) == 2
                and all(isinstance(item, str) and item for item in fragment_ids)
                and fragment_ids[0] != fragment_ids[1])
        relation_id = payload["relationId"]
        assert relation_id not in stub_relations
        stub_relations.add(relation_id)
        for fragment_id in fragment_ids:
            assert fragment_id in relation_paths
            assert fragment_id not in fragment_to_relation
            fragment_to_relation[fragment_id] = relation_id
    return {fragment_to_relation.get(path_id, path_id) for path_id in relation_paths}


def test_paired_stub_fragment_receipt_counts_one_logical_relation() -> None:
    relation_id = "relation:logical-stub"
    fragment_ids = ["relation:opaque-fragment-a", "relation:opaque-fragment-b"]
    surface = {"id": "table-timeline", "primitives": [
        {"id": fragment_id, "kind": "Path", "purpose": "dependency", "sourceKind": "relation"}
        for fragment_id in fragment_ids]}
    scene = {"diagnostics": ["I_LAYOUT_RELATION_RESOLUTION:" + json.dumps({
        "surfaceId": "table-timeline", "relationId": relation_id, "stage": "stub",
        "critical": False, "fragmentIds": fragment_ids}, separators=(",", ":"))]}

    assert _logical_relation_ids(scene, surface) == {relation_id}


def test_slide_16_routes_are_mark_safe_and_every_omission_is_diagnosed() -> None:
    scene, surface = _surface()
    logical_routes = _logical_relation_ids(scene, surface)
    suppressed = [item.removeprefix("W_LAYOUT_RELATION_SUPPRESSED:") for item in scene["diagnostics"]
                  if item.startswith("W_LAYOUT_RELATION_SUPPRESSED:")]
    assert len(suppressed) == len(set(suppressed)), "each omitted relation is diagnosed once"
    assert logical_routes.isdisjoint(suppressed), "a suppressed relation must not be drawn"
    assert len(logical_routes) + len(suppressed) == scene["manifest"]["contentFamilyCounts"]["relations"]
    assert logical_routes, "safety cannot pass by suppressing every dependency"
    assert not [item for item in evaluate_scene_perceptibility(scene)
                if item.code == "E_SCENE_RELATION_THROUGH_MARK"]


def test_slide_16_names_stay_within_the_default_reach_of_their_marks() -> None:
    scene, surface = _surface()
    primitives = {item["id"]: item for item in surface["primitives"]}
    checked = 0
    for member in surface["laneMembers"]:
        emitted = [primitives[name] for name in member["emittedPrimitiveIds"]]
        labels = [item for item in emitted if item.get("purpose") == "member-label"]
        if not labels:
            # First-fit gives routes priority; an absent name must be diagnosed.
            assert f'W_LAYOUT_LABEL_SUPPRESSED:member-label:{member["rowId"]}:{member["memberId"]}' in scene["diagnostics"]
            checked += 1
            continue
        assert len(labels) == 1
        label = labels[0]
        marks = [_rect(item) for item in emitted if item.get("purpose") in {"planned", "actual"}]
        reach = DEFAULT_REACH_EM * label["textLayout"]["fontSize"]
        assert marks and min(_gap(_rect(label), mark) for mark in marks) <= reach, member["memberId"]
        checked += 1
    assert checked == len(surface["laneMembers"]) > 0
