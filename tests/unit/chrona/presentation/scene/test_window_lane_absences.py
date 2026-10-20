"""Scene projects source-proven window omissions without selecting dates or geometry."""
from copy import deepcopy
from dataclasses import replace

import pytest

from chrona.presentation.scene.model import (
    ContentFamilyCounts, InspectionScene, SceneLaneMember, SceneLaneWindowAbsence,
    SceneLaneRowAbsence,
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


def _row_absence_scene(reason="outside-window"):
    scene = _scene()
    surface = replace(scene.surfaces[0], rows=(), lane_members=(
        SceneLaneMember("lane", "member", (), (),
                        (_absence(),) if reason == "outside-window" else (),
                        SceneLaneRowAbsence(reason)),
    ), lane_obstacles=())
    return replace(scene, surfaces=(surface,))


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


def test_omitted_row_keeps_source_member_without_geometry_and_round_trips_reason():
    scene = _scene()
    surface = replace(scene.surfaces[0], rows=(), lane_members=(
        SceneLaneMember("lane", "member", (), (), (),
                        SceneLaneRowAbsence("no-selected-temporal-facet")),
    ), lane_obstacles=())
    document = scene_document(replace(scene, surfaces=(surface,)))
    assert document["version"] == "chrona/scene/v0.7"
    value = document["surfaces"][0]
    assert value["rows"] == [] and value["primitives"] == value["laneObstacles"] == []
    assert value["laneMembers"] == [{
        "rowId": "lane", "memberId": "member", "emittedPrimitiveIds": [],
        "primaryMarkIds": [], "rowAbsence": {"reason": "no-selected-temporal-facet"},
    }]
    validate_scene_document(document)
    assert b'"rowAbsence":{"reason":"no-selected-temporal-facet"}' in serialize_scene(
        replace(scene, surfaces=(surface,)))


def test_row_absence_can_coexist_with_separate_expected_mark_absences():
    scene = _scene()
    surface = replace(scene.surfaces[0], rows=(), lane_members=(
        SceneLaneMember("lane", "member", (), (), (_absence(),),
                        SceneLaneRowAbsence("outside-window")),
    ), lane_obstacles=())
    document = scene_document(replace(scene, surfaces=(surface,)))
    validate_scene_document(document)
    member, = document["surfaces"][0]["laneMembers"]
    assert member["rowAbsence"] == {"reason": "outside-window"}
    assert len(member["windowAbsences"]) == 1


def test_mixed_present_and_omitted_rows_keep_only_present_member_geometry():
    scene = _scene(omitted=False)
    surface = scene.surfaces[0]
    omitted = SceneLaneMember("lane-omitted", "other", (), (), (_absence(),),
                              SceneLaneRowAbsence("outside-window"))
    mixed = replace(surface, lane_members=(surface.lane_members[0], omitted))
    document = scene_document(replace(scene, surfaces=(mixed,)))
    validate_scene_document(document)
    assert {row["id"] for row in document["surfaces"][0]["rows"]} == {"lane"}
    assert {member["rowId"] for member in document["surfaces"][0]["laneMembers"]} == {
        "lane", "lane-omitted",
    }


def test_omitted_row_cannot_own_obstacle_or_primitive():
    scene = _row_absence_scene()
    surface = scene.surfaces[0]
    obstacle = SceneLaneObstacle("facet", "ghost", "lane", "member", "mark",
                                 SceneLaneRectObstacle(1, 2, 5, 4))
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        replace(surface, lane_obstacles=(obstacle,))


@pytest.mark.parametrize("reason", ["capacity", "", None])
def test_invalid_row_absence_reason_is_rejected(reason):
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        SceneLaneRowAbsence(reason)


def test_row_absence_cannot_claim_a_rendered_row_or_emitted_geometry():
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        SceneLaneMember("lane", "member", ("mark",), ("mark",), (),
                        SceneLaneRowAbsence("outside-window"))
    scene = _scene()
    member = SceneLaneMember("lane", "member", (), (), (_absence(),),
                             SceneLaneRowAbsence("outside-window"))
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        replace(scene.surfaces[0], lane_members=(member,))


def test_row_absence_requires_consistent_reason_for_all_members_of_row():
    scene = _scene()
    members = (
        SceneLaneMember("lane", "one", (), (), (_absence(),), SceneLaneRowAbsence("outside-window")),
        SceneLaneMember("lane", "two", (), (), (),
                        SceneLaneRowAbsence("no-selected-temporal-facet")),
    )
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        replace(scene.surfaces[0], rows=(), lane_members=members, lane_obstacles=())


def test_outside_window_requires_row_group_mark_absence_but_preserves_actual_only_source():
    unaccounted = SceneLaneMember("lane", "member", (), (), (),
                                  SceneLaneRowAbsence("outside-window"))
    scene = _scene()
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        replace(scene.surfaces[0], rows=(), lane_members=(unaccounted,), lane_obstacles=())

    actual_only = _absence(facet="actual", source_kind="actual", semantic_role="actual")
    member = SceneLaneMember("lane", "member", (), (), (actual_only,),
                             SceneLaneRowAbsence("outside-window"))
    assert member.window_absences == (actual_only,)

    surface = replace(scene.surfaces[0], rows=(), lane_members=(member,), lane_obstacles=())
    validate_scene_document(scene_document(replace(scene, surfaces=(surface,))))

    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        SceneLaneMember("lane", "member", (), (), (actual_only, _absence()),
                        SceneLaneRowAbsence("outside-window"))


def test_outside_row_absence_allows_zero_expected_sibling_when_row_is_accounted():
    scene = _scene()
    expected = SceneLaneMember("lane", "expected", (), (), (_absence(),),
                               SceneLaneRowAbsence("outside-window"))
    zero_expected = SceneLaneMember("lane", "zero", (), (), (),
                                    SceneLaneRowAbsence("outside-window"))
    surface = replace(scene.surfaces[0], rows=(), lane_members=(expected, zero_expected),
                      lane_obstacles=())
    document = scene_document(replace(scene, surfaces=(surface,)))
    validate_scene_document(document)
    assert len(document["surfaces"][0]["laneMembers"]) == 2


def test_no_selected_temporal_facet_cannot_carry_window_mark_absences():
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        SceneLaneMember("lane", "member", (), (), (_absence(),),
                        SceneLaneRowAbsence("no-selected-temporal-facet"))


def test_absent_metadata_keeps_existing_v06_document_and_strict_validation():
    scene = _scene(omitted=False)
    document = scene_document(scene)
    assert document["version"] == "chrona/scene/v0.6"
    assert "windowAbsences" not in document["surfaces"][0]["laneMembers"][0]
    validate_scene_document(document)
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        SceneLaneMember("lane", "member", (), ())


def test_forecast_omission_is_primary_proof_and_round_trips_as_v07():
    scene = _scene()
    absence = _absence(facet="forecast", semantic_role="planned")
    member = SceneLaneMember("lane", "member", (), (), (absence,))
    forecast_scene = replace(scene.surfaces[0], lane_members=(member,))
    document = scene_document(replace(scene, surfaces=(forecast_scene,)))
    proof = document["surfaces"][0]["laneMembers"][0]["windowAbsences"][0]
    assert proof["facet"] == "forecast" and proof["semanticRole"] == "planned"
    validate_scene_document(document)


def test_forecast_primary_purpose_is_valid_in_lane_inventory():
    scene = _scene(omitted=False)
    surface = scene.surfaces[0]
    primitive = replace(surface.primitives[0], purpose="forecast", visual_role="planned")
    document = scene_document(replace(scene, surfaces=(replace(surface, primitives=(primitive,)),)))
    assert document["surfaces"][0]["laneMembers"][0]["primaryMarkIds"] == ["mark"]
    validate_scene_document(document)


def test_forecast_window_absence_requires_planned_semantic_role():
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        _absence(facet="forecast", semantic_role="snapshot")


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


@pytest.mark.parametrize("mutation", ["remove-proof", "actual-only", "forecast-wrong-role",
                                       "duplicate", "wrong-reason", "v06"])
def test_raw_document_cannot_bypass_typed_omission_rules(mutation):
    document = deepcopy(scene_document(_scene()))
    member = document["surfaces"][0]["laneMembers"][0]
    if mutation == "remove-proof":
        del member["windowAbsences"]
    elif mutation == "actual-only":
        member["windowAbsences"][0].update(facet="actual", semanticRole="actual")
    elif mutation == "forecast-wrong-role":
        member["windowAbsences"][0].update(facet="forecast", semanticRole="snapshot")
    elif mutation == "duplicate":
        member["windowAbsences"].append({**member["windowAbsences"][0], "placementId": "other"})
    elif mutation == "wrong-reason":
        member["windowAbsences"][0]["reason"] = "capacity"
    else:
        document["version"] = "chrona/scene/v0.6"
    with pytest.raises(SceneSerializationError):
        validate_scene_document(document)


@pytest.mark.parametrize("mutation", ["bad-reason", "row-present", "missing-row-proof",
                                       "outside-without-mark-proof", "no-facet-with-mark-proof",
                                       "invented-primitive", "conflicting-reason", "v06"])
def test_raw_document_cannot_bypass_typed_row_absence_rules(mutation):
    document = deepcopy(scene_document(_row_absence_scene()))
    surface = document["surfaces"][0]
    member = surface["laneMembers"][0]
    if mutation == "bad-reason":
        member["rowAbsence"]["reason"] = "capacity"
    elif mutation == "row-present":
        surface["rows"].append({"id": "lane", "groupId": "group",
                                "bounds": {"inline": 0, "block": 0,
                                           "inlineSize": 20, "blockSize": 12},
                                "laneMarkBandBlock": 2})
    elif mutation == "missing-row-proof":
        del member["rowAbsence"]
    elif mutation == "outside-without-mark-proof":
        member["windowAbsences"] = []
    elif mutation == "no-facet-with-mark-proof":
        member["rowAbsence"]["reason"] = "no-selected-temporal-facet"
    elif mutation == "invented-primitive":
        member["emittedPrimitiveIds"].append("mark")
        member["primaryMarkIds"].append("mark")
    elif mutation == "conflicting-reason":
        surface["laneMembers"].append({
            "rowId": "lane", "memberId": "another", "emittedPrimitiveIds": [],
            "primaryMarkIds": [], "rowAbsence": {"reason": "no-selected-temporal-facet"},
        })
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
