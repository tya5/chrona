"""Neutral, schema-free tests for the #467 collision-aware lane allocator.

These tests exercise `allocate_lanes` directly with synthetic measured
footprints; they never touch View/Project resources. Schema and View-facing
behavior belongs to L1/L3.
"""
from __future__ import annotations

import pytest

from chrona.presentation.layout.lane_allocation import (
    LaneCandidate, LaneMark, LaneMember, allocate_lanes,
)
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment


def candidate(candidate_id: str, group_key: str, left: float, right: float, title_width: float = 30.0,
             delta_width: float | None = None, predecessors: tuple[tuple[str, str], ...] = (),
             order: tuple | None = None, footprints: tuple = (), group_order: tuple = ()) -> LaneCandidate:
    return LaneCandidate(candidate_id, group_key, order or (left, right, candidate_id, candidate_id),
                         LaneMark(left, right, footprints), title_width, delta_width, predecessors,
                         group_order)


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


def test_later_mark_cannot_cover_an_earlier_inline_name() -> None:
    # Exercise the same neutral working state used by allocate_lanes after an
    # inline label has been accepted by its finite ladder.
    first = candidate("a", "g", 0, 10, title_width=20)
    next_item = candidate("b", "g", 15, 25, title_width=5)
    from chrona.presentation.layout.lane_allocation import _Lane, LanePlacement
    lane = _Lane("test", "g", "a", 10, 10, 0, 0, 35)
    lane.accept(first, LanePlacement("a", "end", ObstacleRect(10, 0, 30, 10)))
    assert lane.try_place(next_item) is None


def test_point_glyph_and_actual_baseline_collisions_use_the_same_geometry() -> None:
    # A primary mark's supplemental actual/baseline/point geometry is not
    # approximated by its own planned interval.
    actual = ObstacleRect(25, 0, 30, 10)
    point = ObstacleSegment((27, 1), (27, 9), stroke_width=2)
    result = allocate_lanes([candidate("planned", "g", 0, 10, footprints=(actual, point)),
                             candidate("next", "g", 25, 35)],
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
    """The current 4wd Project allows the three-item chain to share a lane."""
    structure = candidate("structure", "g", 0, 10, title_width=50.0)
    avionics = candidate("avionics", "g", 10, 20, title_width=50.0, predecessors=(("r1", "structure"),))
    bus_test = candidate("bus-test", "g", 21, 30, title_width=50.0, predecessors=(("r2", "avionics"),))
    result = allocate_lanes([structure, avionics, bus_test], mark_row_height=10, label_row_height=10)
    assert result.lane_of("structure").lane_id == result.lane_of("avionics").lane_id
    assert result.lane_of("bus-test").lane_id == result.lane_of("avionics").lane_id


def test_third_stagger_row_is_reserved_after_inline_candidates_fail() -> None:
    result = allocate_lanes([
        candidate("a", "g", 10, 20, title_width=50),
        candidate("b", "g", 55, 65, title_width=50),
        candidate("c", "g", 70, 80, title_width=50),
    ], mark_row_height=10, label_row_height=10, canvas_left=0, canvas_right=100)
    assert len(result.lanes) == 1
    lane = result.lanes[0]
    assert lane.placements["c"].level == "label-row-3-end"
    assert lane.label_rows_used == 3
    assert lane.block_extent == 40


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
    assert lane.lane_id == f"lane:ggrp:{lane.representative_id}"
    assert lane.representative_id == "z"


def test_completed_placement_mapping_cannot_be_mutated() -> None:
    result = allocate_lanes([candidate("a", "g", 0, 10)])
    with pytest.raises(TypeError):
        result.lanes[0].placements["a"] = result.lanes[0].placements["a"]


def test_ungrouped_and_authored_group_keys_have_distinct_canonical_identities() -> None:
    result = allocate_lanes([candidate("a:b", "", 0, 10), candidate("a%3Ab", "u", 20, 30)])
    assert len({lane.lane_id for lane in result.lanes}) == 2


def test_group_order_is_declared_not_lexical() -> None:
    result = allocate_lanes([candidate("z", "z", 0, 10, group_order=(0,)),
                             candidate("a", "a", 0, 10, group_order=(1,))])
    assert tuple(lane.group_key for lane in result.lanes) == ("z", "a")


def test_candidate_id_is_required_and_empty_group_key_is_ungrouped() -> None:
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        LaneCandidate("", "g", (0,), LaneMark(0, 1), 1.0)
    assert allocate_lanes([candidate("a", "", 0, 1)]).lanes[0].lane_id == "lane:u:a"


def test_negative_measured_widths_are_rejected() -> None:
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        LaneCandidate("a", "g", (0,), LaneMark(0, 1), -1.0)
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        LaneCandidate("a", "g", (0,), LaneMark(0, 1), 0.0)


def test_duplicate_candidate_identity_and_out_of_band_mark_are_rejected() -> None:
    item = candidate("a", "g", 0, 1)
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        allocate_lanes([item, item])
    outside = candidate("outside", "g", 0, 1,
                        footprints=(ObstacleRect(2, -1, 3, 1),))
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_MARK_GEOMETRY"):
        allocate_lanes([outside], mark_row_height=10)


def test_mark_rect_requires_positive_width() -> None:
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_MARK_GEOMETRY"):
        LaneMark(10, 10)


def test_atomic_host_attached_point_and_comparison_keep_independent_required_labels() -> None:
    bundle = LaneCandidate(
        "host", "g", (0,), LaneMark(0, 20), 40.0,
        bundle=(
            LaneMember("host", LaneMark(0, 20), 40.0),
            LaneMember("host:comparison", LaneMark(0, 20), 50.0,
                       overlays=("host", "gate")),
            LaneMember("gate", LaneMark(8, 10), 30.0,
                       overlays=("host", "host:comparison")),
        ),
    )
    result = allocate_lanes([bundle], mark_row_height=10, label_row_height=10)
    lane = result.lanes[0]
    assert lane.members == ("host", "host:comparison", "gate")
    assert set(lane.placements) == {"host", "host:comparison", "gate"}
    assert all(not lane.placements[member].visible_overflow for member in lane.members)
    assert len({lane.placements[member].candidate_id for member in lane.members}) == 3


def test_atomic_bundle_uses_one_lane_when_a_child_mark_would_collide_in_prior_lane() -> None:
    prior = candidate("prior", "g", 8, 10, title_width=2)
    bundle = LaneCandidate(
        "host", "g", (1,), LaneMark(0, 20), 5.0,
        bundle=(LaneMember("host", LaneMark(0, 20), 5.0),
                    LaneMember("gate", LaneMark(8, 10), 5.0, overlays=("host",))),
    )
    result = allocate_lanes([prior, bundle], mark_row_height=10, label_row_height=10)
    assert result.lane_of("prior").lane_id != result.lane_of("host").lane_id
    assert result.lane_of("host").lane_id == result.lane_of("gate").lane_id


def test_bundle_overlay_exemption_must_be_explicit_and_member_ids_are_globally_unique() -> None:
    unexempted = LaneCandidate("host", "g", (0,), LaneMark(0, 20), 5.0,
                               bundle=(LaneMember("host", LaneMark(0, 20), 5.0),
                                       LaneMember("facet", LaneMark(0, 20), 5.0)))
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_BUNDLE_MARK_COLLISION"):
        allocate_lanes([unexempted], mark_row_height=10, label_row_height=10)
    duplicate = candidate("host", "g", 30, 40)
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        allocate_lanes([unexempted, duplicate])
