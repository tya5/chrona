"""The five affected HALCYON bindings retain their declared content (#1109).

CI supplies the shared public-materializer snapshot; these checks inspect both
completed Scene and serialized SVG instead of re-rendering the corpus.
"""
from __future__ import annotations

import json
from math import hypot
from pathlib import Path
from xml.etree import ElementTree

import pytest
import yaml

from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility


EXAMPLE = Path(__file__).resolve().parents[2] / "examples/halcyon-1"
CONTEXTS = (
    "02-programme-board", "11-overlay-briefing", "12-glyph-gates",
    "19-gallery-text-compression", "20-gallery-vertical-group-tags",
)


def _rect(item: dict) -> tuple[float, float, float, float]:
    box = item["bounds"]
    return (box["inline"], box["block"], box["inline"] + box["inlineSize"],
            box["block"] + box["blockSize"])


def _gap(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return hypot(max(a[0] - b[2], b[0] - a[2], 0),
                 max(a[1] - b[3], b[1] - a[3], 0))


@pytest.mark.parametrize("context_name", CONTEXTS)
def test_lane_binding_draws_all_selected_relations_and_attached_names(context_name):
    context = yaml.safe_load((EXAMPLE / "contexts" / f"{context_name}.yaml").read_text())
    view = yaml.safe_load((EXAMPLE / context["body"]["view"]["address"]).read_text())
    project = yaml.safe_load((EXAMPLE / "project.yaml").read_text())
    selected = set(view["body"]["selection"]["include"]["ids"])
    expected = {item["id"] for item in project["relations"]
                if item["type"] == "dependency"
                and item["from"]["object"] in selected
                and item["to"]["object"] in selected}
    scene = json.loads((EXAMPLE / "generated" / f"{context_name}.scene.json").read_text())
    surface = scene["surfaces"][0]
    primitives = {item["id"]: item for item in surface["primitives"]}
    paths = {item["sourceRef"] for item in primitives.values()
             if item.get("purpose") == "dependency" and item["kind"] == "Path"}
    assert paths == expected
    assert "launch-leop" in paths
    assert not any(item.startswith(("W_LAYOUT_RELATION_SUPPRESSED:",
                                    "W_LAYOUT_LABEL_SUPPRESSED:",
                                    "W_LAYOUT_RELATION_LABEL_SUPPRESSED:"))
                   for item in scene["diagnostics"])
    assert {member["memberId"] for member in surface["laneMembers"]} == selected
    for member in surface["laneMembers"]:
        emitted = [primitives[name] for name in member["emittedPrimitiveIds"]]
        labels = [item for item in emitted if item.get("purpose") == "member-label"]
        assert len(labels) == 1, member["memberId"]
        label = labels[0]
        assert project["objects"][member["memberId"]]["title"] in label["text"]
        marks = [_rect(item) for item in emitted if item.get("purpose") in {"planned", "actual"}]
        assert marks and min(_gap(_rect(label), mark) for mark in marks) <= (
            2 * label["textLayout"]["fontSize"]), member["memberId"]
    assert not [finding for finding in evaluate_scene_perceptibility(scene)
                if finding.severity in {"error", "warning"}]
    expected_indices = {
        "02-programme-board": {"window-note", "tvac-note"},
        "11-overlay-briefing": set(),
        "12-glyph-gates": {"window-note", "tvac-note"},
        "19-gallery-text-compression": {"window-note", "tvac-note"},
        "20-gallery-vertical-group-tags": {"tvac-note"},
    }
    observed_indices = {item["sourceRef"] for item in primitives.values()
                        if item.get("purpose") == "note-index"}
    assert expected_indices[context_name] <= observed_indices
    svg = ElementTree.parse(EXAMPLE / "generated" / f"{context_name}.svg")
    serialized_paths = {element.get("data-source-ref") for element in svg.iter()
                        if element.get("data-purpose") == "dependency"
                        and element.tag.rsplit("}", 1)[-1] == "path"}
    assert serialized_paths == expected
    serialized_names = {element.get("data-source-ref") for element in svg.iter()
                        if element.get("data-purpose") == "member-label"
                        and element.tag.rsplit("}", 1)[-1] == "text"}
    assert serialized_names == selected
    for element in svg.iter():
        if element.get("data-purpose") == "member-label" and element.tag.rsplit("}", 1)[-1] == "text":
            title = project["objects"][element.get("data-source-ref")]["title"]
            assert title in " ".join("".join(element.itertext()).split())
