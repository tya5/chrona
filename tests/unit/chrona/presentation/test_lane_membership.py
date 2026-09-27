from datetime import date

import pytest

from chrona.presentation.review.lane_membership import (
    LaneItem,
    LaneMembershipError,
    LanePackingInput,
    PlannedPoint,
    PlannedSpan,
    SelectedFSRelation,
    derive_lane_membership,
)


def d(day: int) -> date:
    return date(2026, 4, day)


def item(item_id, object_id, planned, *, key=None, host=None, group="g"):
    return LaneItem(item_id, object_id, group, planned, key, host)


def test_chain_uses_selected_fs_fact_across_a_gap():
    predecessor = item("i-a", "a", PlannedSpan(d(1), d(3)))
    successor = item("i-b", "b", PlannedSpan(d(3), d(5)))
    result = derive_lane_membership(LanePackingInput(
        (predecessor, successor), ("chain",),
        (SelectedFSRelation("rel-a-b", "a", "b"),),
    ))
    assert result.assignment_for("i-a").lane_id == result.assignment_for("i-b").lane_id
    assert result.assignment_for("i-b").rule == "chain"
    assert result.assignment_for("i-b").source_id == "rel-a-b"


def test_halcyon_02_named_chain_stays_together_across_planned_gap():
    structure = item("row-structure", "structure", PlannedSpan(date(2026, 4, 1), date(2026, 4, 10)), group="")
    avionics = item("row-avionics", "avionics", PlannedSpan(date(2026, 4, 10), date(2026, 4, 27)), group="")
    bus_test = item("row-bus-test", "bus-test", PlannedSpan(date(2026, 5, 3), date(2026, 5, 17)), group="")
    result = derive_lane_membership(LanePackingInput(
        (structure, avionics, bus_test), ("chain",),
        (SelectedFSRelation("structure-avionics", "structure", "avionics"),
         SelectedFSRelation("avionics-bustest", "avionics", "bus-test")),
    ))
    ids = {result.assignment_for(row.item_id).lane_id for row in (structure, avionics, bus_test)}
    assert len(ids) == 1
    assert next(iter(result.lanes)).group_id == ""


def test_chain_checks_every_interval_already_in_predecessor_lane():
    predecessor = item("pred", "pred", PlannedSpan(d(1), d(3)), key="authored")
    other_authored_member = item("other", "other", PlannedSpan(d(5), d(7)), key="authored")
    successor = item("succ", "succ", PlannedSpan(d(6), d(8)))
    result = derive_lane_membership(LanePackingInput(
        (predecessor, other_authored_member, successor), ("explicit", "chain"),
        (SelectedFSRelation("pred-succ", "pred", "succ"),),
    ))
    assert result.assignment_for("pred").lane_id == result.assignment_for("other").lane_id
    assert result.assignment_for("succ").lane_id != result.assignment_for("pred").lane_id


def test_dates_allows_touching_half_open_spans():
    result = derive_lane_membership(LanePackingInput((
        item("a", "a", PlannedSpan(d(1), d(3))),
        item("b", "b", PlannedSpan(d(3), d(5))),
    ), ("dates",)))
    assert result.assignment_for("a").lane_id == result.assignment_for("b").lane_id


def test_same_day_points_overlap_but_point_at_span_end_only_touches():
    point_a = item("p-a", "p-a", PlannedPoint(d(3)))
    point_b = item("p-b", "p-b", PlannedPoint(d(3)))
    end_point = item("p-end", "p-end", PlannedPoint(d(5)))
    span = item("span", "span", PlannedSpan(d(3), d(5)))
    result = derive_lane_membership(LanePackingInput((point_a, point_b, end_point, span), ("dates",)))
    assert result.assignment_for("p-a").lane_id != result.assignment_for("p-b").lane_id
    assert result.assignment_for("p-end").lane_id != result.assignment_for("span").lane_id


def test_explicit_key_precedes_chain_and_dates_for_overlapping_items():
    result = derive_lane_membership(LanePackingInput((
        item("a", "a", PlannedSpan(d(1), d(5)), key="work"),
        item("b", "b", PlannedSpan(d(2), d(4)), key="work"),
        item("c", "c", PlannedSpan(d(2), d(4)), key="other"),
    ), ("explicit", "chain", "dates"),
        (SelectedFSRelation("rel-a-b", "a", "b"),)))
    assert result.assignment_for("a").lane_id == result.assignment_for("b").lane_id
    assert result.assignment_for("a").lane_id != result.assignment_for("c").lane_id
    assert result.assignment_for("a").rule == "explicit"
    assert result.assignment_for("b").rule == "explicit"


def test_attached_point_inherits_host_lane_and_key_and_conflict_fails_closed():
    host = item("host", "host-object", PlannedSpan(d(1), d(8)), key="host-key")
    child = item("milestone", "milestone-object", PlannedPoint(d(4)), host="host", key="host-key")
    result = derive_lane_membership(LanePackingInput((child, host)))
    assert result.assignment_for("milestone").lane_id == result.assignment_for("host").lane_id
    assert result.assignment_for("milestone").rule == "attached"
    assert "milestone" in next(lane for lane in result.lanes if lane.lane_id == result.assignment_for("host").lane_id).member_item_ids

    conflict = item("milestone", "milestone-object", PlannedPoint(d(4)), host="host", key="different")
    with pytest.raises(LaneMembershipError, match="E_REVIEW_LANE_KEY_CONFLICT"):
        derive_lane_membership(LanePackingInput((host, conflict)))


def test_keys_have_no_effect_and_no_conflict_without_explicit_rule():
    result = derive_lane_membership(LanePackingInput((
        item("host", "host", PlannedSpan(d(1), d(8)), key="a"),
        item("child", "child", PlannedPoint(d(4)), host="host", key="b"),
    ), ("attached",)))
    assert result.assignment_for("host").lane_id == result.assignment_for("child").lane_id


def test_inserting_unrelated_item_preserves_existing_lane_ids():
    original = (
        item("a", "a", PlannedSpan(d(1), d(2))),
        item("b", "b", PlannedSpan(d(1), d(2))),
    )
    baseline = derive_lane_membership(LanePackingInput(original))
    extended = derive_lane_membership(LanePackingInput((
        item("z-new", "z-new", PlannedSpan(d(1), d(2))), *original,
    )))
    assert {entry.item_id: entry.lane_id for entry in baseline.assignments} == {
        key: value for key, value in ((entry.item_id, entry.lane_id) for entry in extended.assignments)
        if key in {"a", "b"}
    }


def test_duplicate_objects_in_group_are_rejected_for_relation_resolution():
    with pytest.raises(LaneMembershipError, match="E_REVIEW_LANE_DUPLICATE_OBJECT"):
        derive_lane_membership(LanePackingInput((
            item("row-1", "same-object", PlannedSpan(d(1), d(2))),
            item("row-2", "same-object", PlannedSpan(d(3), d(4))),
        )))
