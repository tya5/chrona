"""Scene projects source-proven window omissions without selecting dates or geometry."""
from copy import deepcopy
from dataclasses import replace

import pytest

from chrona.presentation.scene.model import (
    ContentFamilyCounts, InspectionScene, SceneLaneMember, SceneLaneWindowAbsence,
    SceneLaneObstacle, SceneLaneRectObstacle, SceneManifest, ScenePrimitive,
    SceneProvenance, SceneRow, SceneSlot, SceneSurface,
)
from chrona.presentation.scene.serialization import (
    SceneSerializationError, scene_document, serialize_scene, validate_scene_document,
)


def _absence(**changes):
    values = dict(placement_id="original:mark", instance_id="original:occurrence",
                  facet="planned", source_ref="/projection/rows/source/items/item",
                  source_kind="combined", semantic_role="planned")
    return SceneLaneWindowAbsence(**(values | changes))


def _scene(*, omitted=True):
    row = SceneRow("object", "group", (0, 0, 20, 12), "lane", 2)
    slot = SceneSlot("slot", "timeline", None, (0, 0, 20, 12))
    mark = ScenePrimitive("mark", "Rect", "object", "object", "planned", "planned",
                          (1, 2, 4, 2), slot_id="slot", lane_row_id="lane", lane_member_id="member")
    member = (SceneLaneMember("lane", "member", (), (), (_absence(),)) if omitted else
              SceneLaneMember("lane", "member", ("mark",), ("mark",)))
    obstacle = SceneLaneObstacle("facet", "mark", "lane", "member", "mark",
                                 SceneLaneRectObstacle(1, 2, 5, 4))
    surface = SceneSurface("s", (slot,), (row,), (), None, () if omitted else (mark,),
                           canvas_bounds=(0, 0, 20, 12), lane_mode="lanes",
                           lane_members=(member,), lane_obstacles=() if omitted else (obstacle,),
                           lane_clearance=0)
    manifest = SceneManifest("chrona/scene-manifest/v0.1", "test", (20, 12), (), (),
                             ContentFamilyCounts(0, 0, 0, 0, 0), ())
    return InspectionScene(SceneProvenance("draft", "test", ()), (20, 12), (), (surface,), manifest, ())


def test_wholly_omitted_member_has_no_fake_primitive_or_obstacle_and_selects_v07():
    scene = _scene()
    document = scene_document(scene)
    assert document["version"] == "chrona/scene/v0.7"
    surface = document["surfaces"][0]
    assert surface["primitives"] == surface["laneObstacles"] == []
    assert surface["laneMembers"] == [{
        "rowId": "lane", "memberId": "member", "emittedPrimitiveIds": [], "primaryMarkIds": [],
        "windowAbsences": [{"placementId": "original:mark", "instanceId": "original:occurrence",
            "facet": "planned", "sourceRef": "/projection/rows/source/items/item",
            "sourceKind": "combined", "semanticRole": "planned", "reason": "outside-window"}],
    }]
    validate_scene_document(document)
    assert serialize_scene(scene) == serialize_scene(scene)


def test_absent_metadata_keeps_existing_v06_document_and_strict_validation():
    scene = _scene(omitted=False)
    document = scene_document(scene)
    assert document["version"] == "chrona/scene/v0.6"
    assert "windowAbsences" not in document["surfaces"][0]["laneMembers"][0]
    validate_scene_document(document)
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        SceneLaneMember("lane", "member", (), ())


@pytest.mark.parametrize("field,value", [
    ("placement_id", ""), ("source_ref", ""), ("reason", "capacity"),
    ("facet", "label"), ("semantic_role", "actual"),
])
def test_malformed_omission_is_rejected_without_visibility_inference(field, value):
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        _absence(**{field: value})


def test_actual_absence_cannot_excuse_missing_primary_and_omission_cannot_also_be_emitted():
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        SceneLaneMember("lane", "member", (), (), (_absence(facet="actual", semantic_role="actual"),))
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        SceneLaneMember("lane", "member", ("original:mark",), ("original:mark",), (_absence(),))
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        SceneLaneMember("lane", "member", (), (), (_absence(), _absence(placement_id="other")))


@pytest.mark.parametrize("mutation", ["remove-proof", "actual-only", "duplicate", "wrong-reason", "v06"])
def test_raw_document_cannot_bypass_typed_omission_rules(mutation):
    document = deepcopy(scene_document(_scene()))
    member = document["surfaces"][0]["laneMembers"][0]
    if mutation == "remove-proof":
        del member["windowAbsences"]
    elif mutation == "actual-only":
        member["windowAbsences"][0].update(facet="actual", semanticRole="actual")
    elif mutation == "duplicate":
        member["windowAbsences"].append({**member["windowAbsences"][0], "placementId": "other"})
    elif mutation == "wrong-reason":
        member["windowAbsences"][0]["reason"] = "capacity"
    else:
        document["version"] = "chrona/scene/v0.6"
    with pytest.raises(SceneSerializationError):
        validate_scene_document(document)


@pytest.mark.parametrize("field", ["surfaces", "laneMembers"])
def test_malformed_container_keeps_scene_error_instead_of_python_type_error(field):
    document = scene_document(_scene())
    if field == "surfaces":
        document[field] = None
    else:
        document["surfaces"][0][field] = None
    with pytest.raises(SceneSerializationError):
        validate_scene_document(document)


def test_empty_obstacles_still_reject_visible_lane_geometry():
    surface = _scene(omitted=False).surfaces[0]
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        replace(surface, lane_obstacles=())
    document = scene_document(_scene(omitted=False))
    document["surfaces"][0]["laneObstacles"] = []
    with pytest.raises(SceneSerializationError):
        validate_scene_document(document)
