"""Identity and expected-emission closure for lane Review projections."""
from datetime import date
from dataclasses import replace

import pytest

from chrona.presentation.layout.lane_projection import close_lane_projection
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.model.projection import ReviewItem, ReviewProjection, ReviewRowProjection
from chrona.presentation.model.projection import ObservationState


def _item(object_id, *, item_id=None, attached_to=None, source_kind="primary",
          actual=None, state=ObservationState.UNAVAILABLE):
    roles = ["planned"]
    if state == ObservationState.RECORDED:
        roles.append("actual")
    elif state == ObservationState.DUE_UNOBSERVED:
        roles.append("missing-actual")
    return ReviewItem(
        object_id=object_id, title=object_id, source_type="span",
        planned={"start": date(2026, 1, 1), "end": date(2026, 1, 3)},
        actual=actual, finish_delta=None, roles=tuple(roles), item_id=item_id or object_id,
        source_kind=source_kind, attached_to=attached_to,
        observation_state=state,
    )


def _projection(*rows):
    return ReviewProjection((), (date(2026, 1, 1), date(2026, 2, 1)), (), (), rows=tuple(rows))


def test_closure_returns_typed_instances_expected_ids_and_exact_attached_host():
    host = _item("host", item_id="host-view", source_kind="combined",
                 actual={"start": date(2026, 1, 1), "finish": date(2026, 1, 4)},
                 state=ObservationState.RECORDED)
    point = _item("gate", item_id="gate-view", attached_to="host")
    projection = _projection(ReviewRowProjection("row:one", "One", "g", "host", (host, point)))

    result = close_lane_projection(projection, as_of=None)

    assert [(mark.role, mark.placement_id) for mark in result.expected_marks] == [
        ("planned", "planned:row%3Aone:host-view"),
        ("actual", "actual:row%3Aone:host-view"),
        ("planned", "planned:row%3Aone:gate-view"),
    ]
    child, resolved_host = result.attached_hosts[0]
    assert (child.object_id, child.item_id) == ("gate", "gate-view")
    assert (resolved_host.object_id, resolved_host.item_id) == ("host", "host-view")


def test_closure_derives_expected_set_and_rejects_inconsistent_review_roles():
    item = _item("item", state=ObservationState.DUE_UNOBSERVED)
    projection = _projection(ReviewRowProjection("row", "Row", "g", "item", (item,)))
    result = close_lane_projection(projection, as_of=date(2026, 1, 3))
    assert [(mark.role, mark.purpose) for mark in result.expected_marks] == [
        ("planned", "planned"), ("missing-actual", "missing-actual"),
    ]
    invalid = replace(item, roles=("planned",))
    broken = _projection(ReviewRowProjection("row", "Row", "g", "item", (invalid,)))
    with pytest.raises(LayoutError):
        close_lane_projection(broken, as_of=date(2026, 1, 3))


def test_attached_host_must_resolve_to_exactly_one_selected_instance_in_same_row():
    child = _item("child", attached_to="host")
    projection = _projection(ReviewRowProjection("row", "Row", "g", "child", (child,)))
    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_ATTACHED_HOST_INVALID"):
        close_lane_projection(projection, as_of=None)

    duplicate_hosts = _projection(ReviewRowProjection(
        "row", "Row", "g", "child", (_item("host", item_id="host-a"),
                                          _item("host", item_id="host-b"), child)))
    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_ATTACHED_HOST_INVALID"):
        close_lane_projection(duplicate_hosts, as_of=None)


def test_folded_points_and_non_timeline_projection_fail_closed():
    folded = ReviewProjection((), (date(2026, 1, 1), date(2026, 2, 1)), (), (),
                              rows=(ReviewRowProjection("row", "Row", "g", "item", (_item("item"),)),),
                              folded_points=(object(),))
    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_PROJECTION_UNSUPPORTED"):
        close_lane_projection(folded, as_of=None)
    not_timeline = ReviewProjection((), (date(2026, 1, 1), date(2026, 2, 1)), (), (),
                                    rows=(ReviewRowProjection(
                                        "row", "Row", "g", "item", (_item("item"),)),),
                                    surface="dependency-network")
    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_PROJECTION_UNSUPPORTED"):
        close_lane_projection(not_timeline, as_of=None)


def test_lane_identity_encoding_is_unambiguous_for_separator_ids():
    left = _projection(ReviewRowProjection("a:b", "Left", "g", "c", (_item("c"),)))
    right = _projection(ReviewRowProjection("a", "Right", "g", "b:c", (_item("b:c"),)))
    left_mark = close_lane_projection(left, as_of=None).expected_marks[0]
    right_mark = close_lane_projection(right, as_of=None).expected_marks[0]
    assert left_mark.placement_id != right_mark.placement_id


def test_open_actual_is_bound_to_selected_cutoff_and_incomplete_payload_is_typed_absence():
    start = date(2026, 1, 3)
    item = _item("item", source_kind="combined", actual={"start": start, "openUntil": "asOf"},
                 state=ObservationState.RECORDED)
    projection = _projection(ReviewRowProjection("row", "Row", "g", "item", (item,)))
    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_AS_OF_REQUIRED"):
        close_lane_projection(projection, as_of=None)
    absence = close_lane_projection(projection, as_of=start).intentional_absences
    assert [(entry.role, entry.reason) for entry in absence] == [
        ("actual", "open-actual-empty-at-cutoff"),
    ]
    missing_start = replace(item, actual={"openUntil": "asOf"})
    missing_start_projection = _projection(ReviewRowProjection(
        "row", "Row", "g", "item", (missing_start,)))
    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_AS_OF_REQUIRED"):
        close_lane_projection(missing_start_projection, as_of=None)


def test_in_progress_span_expects_the_missing_actual_mark_in_place_of_the_actual_mark():
    start = date(2026, 1, 3)
    item = replace(_item("item", source_kind="combined", actual={"start": start},
                         state=ObservationState.RECORDED), missing_actual_mark="in-progress")
    projection = _projection(ReviewRowProjection("row", "Row", "g", "item", (item,)))
    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_AS_OF_REQUIRED"):
        close_lane_projection(projection, as_of=None)
    closure = close_lane_projection(projection, as_of=date(2026, 1, 10))
    assert [(mark.role, mark.purpose) for mark in closure.expected_marks] == [
        ("planned", "planned"), ("missing-actual", "missing-actual")]
    assert closure.expected_marks[1].placement_id.startswith("missing-actual:")
    assert not closure.intentional_absences
    empty = close_lane_projection(projection, as_of=start)
    assert [(entry.role, entry.reason) for entry in empty.intentional_absences] == [
        ("missing-actual", "in-progress-empty-at-cutoff")]
    # Without the in-progress mark the same Actual stays an incomplete payload, as before.
    unmarked = _projection(ReviewRowProjection("row", "Row", "g", "item", (replace(item, missing_actual_mark="due-end"),)))
    assert [(entry.role, entry.reason) for entry in close_lane_projection(unmarked, as_of=date(2026, 1, 10)).intentional_absences] == [
        ("actual", "incomplete-actual-payload")]


def test_primary_recorded_actual_is_an_explicit_absence():
    item = _item("item", actual={"start": date(2026, 1, 1), "finish": date(2026, 1, 2)},
                 state=ObservationState.RECORDED)
    result = close_lane_projection(_projection(ReviewRowProjection(
        "row", "Row", "g", "item", (item,))), as_of=None)
    assert [(mark.role, mark.purpose) for mark in result.expected_marks] == [("planned", "planned")]
    assert [(absence.role, absence.reason) for absence in result.intentional_absences] == [
        ("actual", "actual-owned-by-selected-source"),
    ]


def test_actual_source_complete_payload_emits_actual_and_not_planned():
    item = _item("item", source_kind="actual",
                 actual={"start": date(2026, 1, 1), "finish": date(2026, 1, 2)},
                 state=ObservationState.RECORDED)
    result = close_lane_projection(_projection(ReviewRowProjection(
        "row", "Row", "g", "item", (item,))), as_of=None)
    assert [(mark.role, mark.purpose) for mark in result.expected_marks] == [("actual", "actual")]
    assert [(absence.role, absence.reason) for absence in result.intentional_absences] == [
        ("planned", "actual-source-only"),
    ]


def test_incomplete_recorded_actual_is_typed_absence_and_state_conflicts_fail():
    incomplete = _item("item", source_kind="combined", actual={"start": date(2026, 1, 1)},
                       state=ObservationState.RECORDED)
    result = close_lane_projection(_projection(ReviewRowProjection(
        "row", "Row", "g", "item", (incomplete,))), as_of=None)
    assert [(absence.role, absence.reason) for absence in result.intentional_absences] == [
        ("actual", "incomplete-actual-payload"),
    ]
    contradictory = replace(incomplete, observation_state=ObservationState.UNAVAILABLE,
                             roles=("planned",))
    projection = _projection(ReviewRowProjection("row", "Row", "g", "item", (contradictory,)))
    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_EXPECTED_MARK_SET_INVALID"):
        close_lane_projection(projection, as_of=None)


def test_duplicate_review_row_ids_fail_closed():
    rows = (
        ReviewRowProjection("row", "First", "g", "one", (_item("one"),)),
        ReviewRowProjection("row", "Second", "g", "two", (_item("two"),)),
    )
    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_PROJECTION_INVALID"):
        close_lane_projection(_projection(*rows), as_of=None)
