"""Neutral, schema-free tests for the #467 collision-aware lane allocator.

These tests exercise `allocate_lanes` directly with synthetic measured
footprints; they never touch View/Project resources. Schema and View-facing
behavior belongs to L1/L3.
"""
from __future__ import annotations

import pytest

from chrona.presentation.layout.lane_allocation import (
    LaneCandidate, LaneMark, allocate_lanes,
)


def candidate(candidate_id: str, group_key: str, left: float, right: float, title_width: float = 30.0,
             delta_width: float | None = None, predecessors: tuple[tuple[str, str], ...] = (),
             order: tuple | None = None) -> LaneCandidate:
    return LaneCandidate(candidate_id, group_key, order or (left, right, candidate_id, candidate_id),
                         LaneMark(left, right), title_width, delta_width, predecessors)


def test_two_non_touching_items_share_one_lane_via_staggered_label_rows() -> None:
    result = allocate_lanes([candidate("a", "g", 0, 10), candidate("b", "g", 11, 20)],
                            mark_row_height=10, label_row_height=10)
    assert len(result.lanes) == 1
    lane = result.lanes[0]
    assert set(lane.members) == {"a", "b"}
    assert lane.label_rows_used >= 1


def test_overlapping_marks_never_share_a_lane() -> None:
    # b's mark overlaps a's mark; no label ladder level changes the mark row.
    result = allocate_lanes([candidate("a", "g", 0, 10), candidate("b", "g", 5, 15)],
                            mark_row_height=10, label_row_height=10)
    assert len(result.lanes) == 2
    assert result.lane_of("a").lane_id != result.lane_of("b").lane_id


def test_touching_marks_are_not_a_collision() -> None:
    # a ends exactly where b starts: a legal touch, not an overlap.
    result = allocate_lanes([candidate("a", "g", 0, 10), candidate("b", "g", 10, 20)],
                            mark_row_height=10, label_row_height=10)
    assert len(result.lanes) == 1


def test_point_glyph_and_actual_baseline_collisions_use_the_same_geometry() -> None:
    # A zero-width "point" is modeled as a small finite mark; two adjacent
    # points still collide when their marks overlap, exactly like spans.
    result = allocate_lanes([candidate("planned", "g", 10, 12), candidate("actual", "g", 11, 13)],
                            mark_row_height=10, label_row_height=10)
    assert len(result.lanes) == 2


def test_label_staggering_prefers_two_label_rows_over_same_level_end_start() -> None:
    """The L0 ladder correction: staggered label rows are tried before
    same-level end/start, because end/start extend a lane's inline footprint
    and force extra lanes on dense fixtures."""
    wide_title = candidate("a", "g", 0, 10, title_width=100.0)
    # b's mark starts right after a's label-row-1/label-row-2 footprint would
    # end inline, but well within where an "end" placement of a's title would
    # have landed (0..110). b must NOT be pushed to a new lane merely because
    # a's title is wide; the ladder tries label rows above the mark first.
    tight_neighbor = candidate("b", "g", 50, 60, title_width=10.0)
    result = allocate_lanes([wide_title, tight_neighbor], mark_row_height=10, label_row_height=10)
    assert len(result.lanes) == 1
    lane = result.lanes[0]
    assert lane.placements["a"].level in ("label-row-1", "label-row-2")


def test_chain_preference_shares_a_lane_when_marks_do_not_overlap() -> None:
    """Reproduces the L0 feasibility record: structure -> avionics share a
    lane (they touch); avionics -> bus-test cannot (the actual finish
    overlaps the successor's planned start), so bus-test opens a new lane."""
    structure = candidate("structure", "g", 0, 10, title_width=50.0)
    avionics = candidate("avionics", "g", 10, 20, title_width=50.0, predecessors=(("r1", "structure"),))
    bus_test = candidate("bus-test", "g", 19, 30, title_width=50.0, predecessors=(("r2", "avionics"),))
    result = allocate_lanes([structure, avionics, bus_test], mark_row_height=10, label_row_height=10)
    assert result.lane_of("structure").lane_id == result.lane_of("avionics").lane_id
    assert result.lane_of("bus-test").lane_id != result.lane_of("avionics").lane_id


def test_dependency_preference_never_overrides_collision() -> None:
    """A predecessor lane is only *tried first*; if the successor's mark
    collides there it still opens/uses another lane instead of overlapping."""
    a = candidate("a", "g", 0, 10)
    b = candidate("b", "g", 5, 15, predecessors=(("r1", "a"),))
    result = allocate_lanes([a, b], mark_row_height=10, label_row_height=10)
    assert result.lane_of("a").lane_id != result.lane_of("b").lane_id


def test_group_isolation_no_lane_crosses_a_group_boundary() -> None:
    result = allocate_lanes([candidate("a", "g1", 0, 10), candidate("b", "g2", 0, 10)],
                            mark_row_height=10, label_row_height=10)
    assert len(result.lanes) == 2
    assert result.lane_of("a").group_key == "g1"
    assert result.lane_of("b").group_key == "g2"
    assert result.lane_of("a").lane_id != result.lane_of("b").lane_id


def test_deterministic_first_fit_is_stable_across_insertion_of_an_unrelated_item() -> None:
    """A later unrelated item's insertion does not reorder or rename a lane
    whose own members and predecessor closure are unchanged."""
    a = candidate("a", "g", 0, 10)
    b = candidate("b", "g", 50, 60)
    baseline = allocate_lanes([a, b], mark_row_height=10, label_row_height=10)
    unrelated = candidate("c", "g", 100, 110)
    with_insertion = allocate_lanes([a, b, unrelated], mark_row_height=10, label_row_height=10)

    def lane_shape(result, candidate_id):
        lane = result.lane_of(candidate_id)
        return lane.lane_id, lane.representative_id

    assert lane_shape(baseline, "a") == lane_shape(with_insertion, "a")
    assert lane_shape(baseline, "b") == lane_shape(with_insertion, "b")


def test_required_name_and_delta_are_reserved_as_one_measured_footprint() -> None:
    result = allocate_lanes([candidate("a", "g", 0, 10, title_width=40.0, delta_width=15.0)],
                            mark_row_height=10, label_row_height=10)
    lane = result.lanes[0]
    placement = lane.placements["a"]
    assert placement.rect.right - placement.rect.left == pytest.approx(55.0)
    assert not placement.visible_overflow


def test_no_fitting_candidate_anywhere_uses_terminal_visible_overflow_not_a_drop() -> None:
    """Even alone in a fresh lane, an absurdly wide label has nowhere to go;
    the item is still placed (never suppressed), flagged as visible-overflow."""
    huge = candidate("a", "g", 0, 1, title_width=1e12)
    result = allocate_lanes([huge], mark_row_height=1, label_row_height=1,
                            canvas_left=0.0, canvas_right=100.0)
    lane = result.lanes[0]
    placement = lane.placements["a"]
    assert placement.visible_overflow
    assert placement.level == "visible-overflow"
    assert "a" in lane.members


def test_explicit_row_track_allocation_reuses_the_same_primitive_via_group_isolation() -> None:
    """Explicit rows opt into collision packing per-row (#467 design, `explicit`
    successor); modeling one authored row as its own group key reuses the
    identical collision algorithm without a second code path."""
    shared_row = "row:fw-qualification"
    result = allocate_lanes([
        candidate("snapshot-plan", shared_row, 0, 10),
        candidate("current-plan", shared_row, 20, 30),
    ], mark_row_height=10, label_row_height=10)
    assert len(result.lanes) == 1
    assert result.lanes[0].group_key == shared_row


def test_stable_lane_and_representative_identity_naming() -> None:
    result = allocate_lanes([candidate("z", "grp", 0, 10), candidate("y", "grp", 11, 20)],
                            mark_row_height=10, label_row_height=10)
    lane = result.lanes[0]
    assert lane.lane_id == f"lane:grp:{lane.representative_id}"
    assert lane.representative_id == "z"


def test_candidate_id_and_group_key_are_required() -> None:
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        LaneCandidate("", "g", (0,), LaneMark(0, 1), 1.0)
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        LaneCandidate("a", "", (0,), LaneMark(0, 1), 1.0)


def test_negative_measured_widths_are_rejected() -> None:
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        LaneCandidate("a", "g", (0,), LaneMark(0, 1), -1.0)


def test_mark_rect_requires_positive_width() -> None:
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_MARK_GEOMETRY"):
        LaneMark(10, 10)
