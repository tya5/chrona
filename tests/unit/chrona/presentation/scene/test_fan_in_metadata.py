"""Scene transports Layout-approved same-port fan-in without routing or inferring it."""

from __future__ import annotations

import json

import pytest

from chrona.presentation.layout.surface_quality import RelationFanIn
from chrona.presentation.layout.relation_terminals import marker_geometry
from chrona.presentation.scene.model import (
    ContentFamilyCounts, InspectionScene, SceneManifest, ScenePaint, ScenePrimitive,
    SceneProvenance, SceneSlot, SceneSurface,
)
from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.presentation.scene.serialization import scene_document, validate_scene_document


def _scene(*primitives):
    slot = SceneSlot("timeline", "timeline", None, (0, 0, 100, 100))
    surface = SceneSurface("timeline", (slot,), (), (), None, tuple(primitives),
        canvas_paint=ScenePaint("#ffffff", None, None, (), 1), canvas_bounds=(0, 0, 100, 100))
    manifest = SceneManifest("chrona/scene-manifest/v0.1", "test", (100, 100), (), (),
                             ContentFamilyCounts(1, 0, 0, 0, 0), ())
    return InspectionScene(SceneProvenance("draft", "test", ()), (100, 100), (), (surface,), manifest, ())


def _path(identifier, points, *, source, target, fan_in=None, marker=False, stroke="#000000"):
    marker_end = ({"outline": [{"kind": "move", "points": [[0, 0]]},
                                {"kind": "line", "points": [[6, 3]]}],
                   "headLength": 6, "headWidth": 6, "attachmentOffset": 1, "paintMode": "fill"}
                  if marker else None)
    value = {
        "id": identifier, "kind": "Path", "sourceKind": "relation", "sourceRef": identifier,
        "slotId": "timeline", "bounds": {"inline": 0, "block": 0, "inlineSize": 0, "blockSize": 0},
        "paint": {"stroke": stroke, "strokeWidth": 1, "opacity": 1}, "points": points,
        "fromInstanceId": source, "toInstanceId": target,
    }
    if fan_in is not None:
        value["fanIn"] = {"targetPortId": fan_in[0], "terminalOwnerId": fan_in[1]}
    if marker_end is not None:
        value["markerEnd"] = marker_end
    return value


def _diagnostic(reason="same-port-fan-in"):
    return "I_LAYOUT_RELATION_NODE_APPROACH_SHARED:" + json.dumps({
        "nodeInstanceId": "target", "relationIds": ["relation:a", "relation:b"], "reason": reason,
    }, separators=(",", ":"))


def _evaluate(*paths, diagnostic=None):
    document = {
        "version": "chrona/scene/v0.7", "kind": "scene",
        "surfaces": [{"id": "review", "slots": [{"id": "timeline", "bounds": {
            "inline": 0, "block": 0, "inlineSize": 100, "blockSize": 100}, "overflow": "fit"}],
            "canvasPaint": {"fill": "#ffffff", "opacity": 1}, "primitives": list(paths)}],
        "diagnostics": [diagnostic] if diagnostic else [],
    }
    return document, evaluate_scene_perceptibility(document)


def _valid_arrivals(*, head=True):
    claim = ("target-port", "relation:a")
    return (
        _path("relation:a", [[-10, 0], [0, 0]], source="left-a", target="target",
              fan_in=claim, marker=head),
        _path("relation:b", [[-6, 0], [0, 0]], source="left-b", target="target",
              fan_in=claim),
    )


def _typed_document():
    marker = marker_geometry({"shape": "triangle", "headLength": 6, "headWidth": 6,
                              "attachmentOffset": 1})
    owner = ScenePrimitive("relation:a", "Path", "a", "relation", "dependency-connector",
        "dependency-connector", (0, 0, 0, 0), slot_id="timeline", points=((-10, 0), (0, 0)),
        marker_end=marker, paint=ScenePaint(None, "#000000", 1, (), 1), from_instance_id="left-a",
        to_instance_id="target", fan_in=RelationFanIn("target-port", "relation:a"))
    nonowner = ScenePrimitive("relation:b", "Path", "b", "relation", "dependency-connector",
        "dependency-connector", (0, 0, 0, 0), slot_id="timeline", points=((-6, 0), (0, 0)),
        paint=ScenePaint(None, "#000000", 1, (), 1), from_instance_id="left-b", to_instance_id="target",
        fan_in=RelationFanIn("target-port", "relation:a"))
    return scene_document(_scene(owner, nonowner))


def test_scene_serializes_layout_fan_in_metadata_and_one_marker_owner():
    document = _typed_document()
    assert document["version"] == "chrona/scene/v0.7"
    first_primitive, second_primitive = document["surfaces"][0]["primitives"]
    assert first_primitive["fanIn"] == {"targetPortId": "target-port", "terminalOwnerId": "relation:a"}
    assert second_primitive["fanIn"] == first_primitive["fanIn"]
    assert "markerEnd" in first_primitive
    assert "markerEnd" not in second_primitive
    validate_scene_document(document)
    findings = evaluate_scene_perceptibility(document)
    assert not [finding for finding in findings if finding.code.endswith("FAN_IN_INVALID")]
    assert "E_SCENE_RELATION_NODE_APPROACH_SHARED" not in {finding.code for finding in findings}


@pytest.mark.parametrize("mutate", [
    lambda doc: doc["surfaces"][0]["primitives"][1]["fanIn"].update(targetPortId="other-port"),
    lambda doc: doc["surfaces"][0]["primitives"][1]["fanIn"].update(terminalOwnerId="missing-owner"),
    lambda doc: doc["surfaces"][0]["primitives"][1].update(
        markerEnd=doc["surfaces"][0]["primitives"][0]["markerEnd"]),
])
def test_scene_reference_validation_rejects_bad_port_owner_or_duplicate_marker(mutate):
    document = _typed_document()
    mutate(document)
    with pytest.raises(ValueError, match="E_SCENE_SERIALIZATION"):
        validate_scene_document(document)


def test_scene_reference_validation_rejects_owner_in_a_different_surface():
    document = _typed_document()
    other = json.loads(json.dumps(document["surfaces"][0]))
    other["id"] = "other-surface"
    other["primitives"] = [other["primitives"][0]]
    document["surfaces"][0]["primitives"] = document["surfaces"][0]["primitives"][1:]
    document["surfaces"].append(other)
    with pytest.raises(ValueError, match="E_SCENE_SERIALIZATION"):
        validate_scene_document(document)


def test_fan_in_model_requires_a_resolved_relation_path():
    base = ScenePrimitive("relation:a", "Path", "a", "relation", "dependency-connector",
        "dependency-connector", (0, 0, 0, 0), slot_id="timeline", points=((-1, 0), (0, 0)),
        from_instance_id="left", to_instance_id="target")
    claim = RelationFanIn("target-port", "relation:a")
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        ScenePrimitive(**{**base.__dict__, "to_instance_id": None, "from_instance_id": None,
                          "fan_in": claim})
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        ScenePrimitive(**{**base.__dict__, "source_kind": "annotation", "fan_in": claim})


def test_valid_headless_fan_in_claim_can_have_no_terminal_marker():
    _, findings = _evaluate(*_valid_arrivals(head=False))
    assert not [finding for finding in findings if finding.code.endswith("FAN_IN_INVALID")]
    assert "E_SCENE_RELATION_NODE_APPROACH_SHARED" not in {finding.code for finding in findings}


@pytest.mark.parametrize("mutate,reason", [
    (lambda a, b: (a, {**b, "fanIn": {"targetPortId": "other-port", "terminalOwnerId": "relation:a"}}),
     "fan-in-needs-multiple-arrivals"),
    (lambda a, b: ({**a, "fanIn": {"targetPortId": "target-port", "terminalOwnerId": "relation:missing"}},
                    {**b, "fanIn": {"targetPortId": "target-port", "terminalOwnerId": "relation:missing"}}),
     "terminal-owner-not-a-member"),
    (lambda a, b: (a, {**b, "markerEnd": a["markerEnd"]}), "multiple-terminal-markers"),
])
def test_malformed_or_mismatched_fan_in_is_reported_and_diagnostic_cannot_authorize_it(mutate, reason):
    a, b = mutate(*_valid_arrivals())
    _, findings = _evaluate(a, b, diagnostic=_diagnostic())
    invalid = [finding for finding in findings if finding.code == "E_SCENE_RELATION_FAN_IN_INVALID"]
    assert invalid
    assert reason in {dict(finding.measured_facts).get("reason") for finding in invalid}
    assert "E_SCENE_RELATION_NODE_APPROACH_SHARED" in {finding.code for finding in findings}


def test_arrival_departure_overlap_cannot_claim_same_port_fan_in():
    arrival = _path("relation:a", [[-10, 0], [0, 0]], source="left", target="target",
        fan_in=("target-port", "relation:a"), marker=True)
    departure = _path("relation:b", [[0, 0], [-6, 0]], source="target", target="left-b",
        fan_in=("target-port", "relation:a"))
    _, findings = _evaluate(arrival, departure, diagnostic=_diagnostic())
    assert "E_SCENE_RELATION_FAN_IN_INVALID" in {finding.code for finding in findings}
    assert "E_SCENE_RELATION_NODE_APPROACH_SHARED" in {finding.code for finding in findings}
    assert "I_SCENE_RELATION_NODE_APPROACH_SHARED" not in {finding.code for finding in findings}


def test_ordinary_unannotated_overlap_still_requires_its_existing_diagnostic():
    first = _path("relation:a", [[-10, 0], [0, 0]], source="left-a", target="target")
    second = _path("relation:b", [[-6, 0], [0, 0]], source="left-b", target="target")
    _, findings = _evaluate(first, second)
    assert "E_SCENE_RELATION_NODE_APPROACH_SHARED" in {finding.code for finding in findings}
    _, diagnosed = _evaluate(first, second, diagnostic=_diagnostic("terminal-corridor-shared"))
    assert "I_SCENE_RELATION_NODE_APPROACH_SHARED" in {finding.code for finding in diagnosed}
