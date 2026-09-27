from __future__ import annotations

from copy import deepcopy

import pytest

from chrona.presentation.scene.lane_audit import (
    SceneLaneAuditError, audit_serialized_lane_surface,
)


def _surface() -> dict:
    rows = [
        {"id": "g-a", "groupId": "g", "laneMarkBandBlock": 10},
        {"id": "g-b", "groupId": "g", "laneMarkBandBlock": 30},
        {"id": "g-c", "groupId": "g", "laneMarkBandBlock": 50},
        {"id": "h-a", "groupId": "h", "laneMarkBandBlock": 70},
    ]
    members = [
        {"rowId": row_id, "memberId": member_id,
         "emittedPrimitiveIds": [primitive_id], "primaryMarkIds": [primitive_id]}
        for row_id, member_id, primitive_id in (
            ("g-a", "m1", "p1"), ("g-b", "m2", "p2"),
            ("g-c", "m3", "p3"), ("h-a", "m4", "p4"),
        )
    ]
    obstacles = [
        {"facetId": f"f-{primitive_id}", "primitiveId": primitive_id,
         "rowId": row_id, "memberId": member_id, "class": "mark",
         "geometry": {"kind": "rect", "left": left, "top": top,
                      "right": right, "bottom": top + 2}}
        for row_id, member_id, primitive_id, left, right, top in (
            ("g-a", "m1", "p1", 0, 5, 10),
            ("g-b", "m2", "p2", 5, 10, 30),
            ("g-c", "m3", "p3", 4, 6, 50),
            ("h-a", "m4", "p4", 20, 22, 70),
        )
    ]
    # A required label creates concrete full-footprint witnesses for g-a/g-c
    # and g-b/g-c without changing primary-mark concurrency.
    members[2]["emittedPrimitiveIds"].append("label-c")
    obstacles.append({"facetId": "f-label-c", "primitiveId": "label-c", "rowId": "g-c",
                      "memberId": "m3", "class": "required-label",
                      "geometry": {"kind": "stroked-segment", "start": [2, 51],
                                   "end": [12, 51], "strokeWidth": 1}})
    primitives = [
        {"id": primitive_id, "laneRowId": member["rowId"], "laneMemberId": member["memberId"]}
        for member in members for primitive_id in member["emittedPrimitiveIds"]
    ]
    return {"laneMode": "lanes", "laneClearance": 0,
            "rows": rows, "laneMembers": members, "laneObstacles": obstacles,
            "primitives": primitives}


def test_audit_uses_group_local_bidirectional_scene_witnesses_and_reports_gap():
    audit = audit_serialized_lane_surface(_surface())

    group_g = next(item for item in audit.groups if item.group_id == "g")
    assert (group_g.lane_count, group_g.primary_mark_lower_bound,
            group_g.full_footprint_inline_concurrency, group_g.lane_gap) == (3, 2, 2, 1)
    assert len(group_g.gap_witnesses) == 4
    assert {item.source_class for item in group_g.gap_witnesses} == {"mark", "required-label"}
    assert len(audit.lane_pairs) == 3  # only the three pairs in group g
    a_b, a_c, b_c = audit.lane_pairs
    assert (a_b.a_into_b, a_b.b_into_a) == (None, None)
    assert a_c.a_into_b is not None and a_c.b_into_a is not None
    assert a_c.a_into_b.source_member_id == "m1"
    assert a_c.b_into_a.source_member_id == "m3"
    assert (a_c.a_into_b.source_lane_id, a_c.a_into_b.target_lane_id) == ("g-a", "g-c")
    assert (a_c.b_into_a.source_lane_id, a_c.b_into_a.target_lane_id) == ("g-c", "g-a")
    assert b_c.a_into_b is not None and b_c.b_into_a is not None
    assert not audit.non_redundant


def test_primary_mark_endpoint_sweep_is_half_open_and_counts_members_once():
    surface = _surface()
    surface["rows"] = surface["rows"][:2]
    surface["laneMembers"] = surface["laneMembers"][:2]
    surface["laneObstacles"] = surface["laneObstacles"][:2]
    surface["primitives"] = surface["primitives"][:2]
    audit = audit_serialized_lane_surface(surface)
    group = audit.groups[0]
    # [0,5) and [5,10) touch; they do not overlap.
    assert group.primary_mark_lower_bound == 1
    assert group.lane_count == 2


def test_full_footprint_concurrency_reports_label_pressure_beyond_mark_bound():
    surface = _surface()
    surface["rows"] = surface["rows"][:2]
    surface["laneMembers"] = surface["laneMembers"][:2]
    surface["laneObstacles"] = surface["laneObstacles"][:2]
    surface["primitives"] = surface["primitives"][:2]

    surface["laneMembers"][0]["emittedPrimitiveIds"].append("label-a")
    surface["laneObstacles"].append({
        "facetId": "f-label-a", "primitiveId": "label-a", "rowId": "g-a",
        "memberId": "m1", "class": "required-label",
        "geometry": {"kind": "rect", "left": 0, "top": 11, "right": 10, "bottom": 12},
    })
    surface["primitives"].append({"id": "label-a", "laneRowId": "g-a", "laneMemberId": "m1"})

    group = audit_serialized_lane_surface(surface).groups[0]
    assert group.primary_mark_lower_bound == 1
    assert group.full_footprint_inline_concurrency == 2
    assert group.lane_gap == 1


def test_audit_rejects_missing_or_malformed_serialized_obstacle_evidence():
    missing = _surface()
    missing["laneObstacles"] = missing["laneObstacles"][:-1]
    with pytest.raises(SceneLaneAuditError, match="E_SCENE_LANE_AUDIT_INVALID"):
        audit_serialized_lane_surface(missing)

    malformed = deepcopy(_surface())
    malformed["laneObstacles"][0]["geometry"]["left"] = "zero"
    with pytest.raises(SceneLaneAuditError, match="E_SCENE_LANE_AUDIT_INVALID"):
        audit_serialized_lane_surface(malformed)


@pytest.mark.parametrize("broken", ["missing-primitive", "wrong-lane-tag", "untagged-member-purpose"])
def test_audit_requires_exact_primitive_emission_and_lane_tags(broken):
    surface = deepcopy(_surface())
    if broken == "missing-primitive":
        surface["primitives"] = [item for item in surface["primitives"] if item["id"] != "p2"]
    elif broken == "wrong-lane-tag":
        next(item for item in surface["primitives"] if item["id"] == "p2")["laneMemberId"] = "m1"
    else:
        surface["primitives"].append({"id": "untagged", "kind": "Text", "purpose": "member-label"})
    with pytest.raises(SceneLaneAuditError, match="E_SCENE_LANE_AUDIT_INVALID"):
        audit_serialized_lane_surface(surface)
