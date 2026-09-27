"""Fixed lane membership with Layout-owned internal mark subtracks."""
from __future__ import annotations

import pytest

from chrona.presentation.layout.lane_subtracks import (
    LaneItemFootprints,
    assign_lane_subtracks,
)
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment
from chrona.presentation.review.lane_membership import (
    Lane,
    LaneAssignment,
    LaneMembership,
)


def membership(*entries: tuple[str, str, str, str, str]) -> LaneMembership:
    """Build ordered (item, lane, group, rule, source) assignments."""
    lane_members: dict[tuple[str, str], list[str]] = {}
    assignments = []
    for item_id, lane_id, group_id, rule, source_id in entries:
        lane_members.setdefault((lane_id, group_id), []).append(item_id)
        assignments.append(LaneAssignment(item_id, lane_id, group_id, rule, source_id))
    lanes = tuple(Lane(lane_id, group_id, tuple(members))
                  for (lane_id, group_id), members in lane_members.items())
    return LaneMembership(lanes, tuple(assignments))


def footprints(*entries: tuple[str, tuple[ObstacleRect | ObstacleSegment, ...]]) -> tuple[LaneItemFootprints, ...]:
    return tuple(LaneItemFootprints(item_id, geometries) for item_id, geometries in entries)


def test_explicitly_overlapping_items_keep_membership_and_get_internal_tracks() -> None:
    source = membership(("a", "authored", "g", "explicit", "hardware"),
                        ("b", "authored", "g", "explicit", "hardware"))
    result = assign_lane_subtracks(source, footprints(
        ("a", (ObstacleRect(0, 0, 10, 10),)),
        ("b", (ObstacleRect(5, 0, 15, 10),)),
    ), mark_band_size=10)

    assert source.lanes[0].lane_id == "authored"
    assert source.lanes[0].member_item_ids == ("a", "b")
    assert [(item.item_id, item.lane_id, item.track_index) for item in result.items] == [
        ("a", "authored", 0), ("b", "authored", 1),
    ]
    assert result.lanes[0].subtrack_count == 2
    assert result.lanes[0].pitch == 10


def test_touching_visible_marks_share_a_subtrack() -> None:
    source = membership(("a", "lane", "g", "dates", "first-compatible:lane"),
                        ("b", "lane", "g", "dates", "first-compatible:lane"))
    result = assign_lane_subtracks(source, footprints(
        ("a", (ObstacleRect(0, 0, 10, 10),)),
        ("b", (ObstacleRect(10, 0, 20, 10),)),
    ), mark_band_size=10)

    assert [item.track_index for item in result.items] == [0, 0]
    assert result.lanes[0].subtrack_count == 1


def test_ungrouped_fixed_lane_is_valid() -> None:
    source = membership(("a", "ungrouped-lane", "", "single", "a"))
    result = assign_lane_subtracks(source, footprints(
        ("a", (ObstacleRect(0, 0, 10, 10),)),
    ), mark_band_size=10)

    assert result.lanes[0].lane_id == "ungrouped-lane"
    assert result.item("a").track_index == 0


def test_attached_bundle_shares_track_even_when_its_facets_overlap() -> None:
    source = membership(("host", "lane", "g", "explicit", "key"),
                        ("child", "lane", "g", "attached", "host"),
                        ("other", "lane", "g", "explicit", "key"))
    same_mark = ObstacleRect(0, 0, 10, 10)
    result = assign_lane_subtracks(source, footprints(
        ("host", (same_mark,)),
        ("child", (same_mark,)),
        ("other", (ObstacleRect(5, 0, 15, 10),)),
    ), mark_band_size=10)

    tracks = {item.item_id: item.track_index for item in result.items}
    assert tracks == {"host": 0, "child": 0, "other": 1}
    assert result.lanes[0].subtrack_count == 2


def test_protruding_stroked_icon_footprint_controls_pitch_and_offset() -> None:
    source = membership(("a", "lane", "g", "explicit", "key"),
                        ("b", "lane", "g", "explicit", "key"))
    result = assign_lane_subtracks(source, footprints(
        ("a", (ObstacleRect(0, 0, 10, 10), ObstacleSegment((5, -2), (5, 12), 2))),
        ("b", (ObstacleRect(5, 0, 15, 10),)),
    ), mark_band_size=10)

    lane = result.lanes[0]
    assert lane.offset == 3  # the stroked segment reaches y=-3
    assert lane.pitch == 16  # visible vertical envelope [-3, 13) plus band extent
    assert lane.block_extent == 32
    assert result.item("a").block_offset == 3
    assert result.item("b").block_offset == 19


def test_theme_geometry_can_change_tracks_without_mutating_membership() -> None:
    source = membership(("a", "lane", "g", "explicit", "key"),
                        ("b", "lane", "g", "explicit", "key"))
    narrow = assign_lane_subtracks(source, footprints(
        ("a", (ObstacleRect(0, 0, 4, 10),)),
        ("b", (ObstacleRect(5, 0, 10, 10),)),
    ), mark_band_size=10)
    wide = assign_lane_subtracks(source, footprints(
        ("a", (ObstacleRect(0, 0, 7, 10),)),
        ("b", (ObstacleRect(5, 0, 12, 10),)),
    ), mark_band_size=10)

    assert [item.track_index for item in narrow.items] == [0, 0]
    assert [item.track_index for item in wide.items] == [0, 1]
    assert narrow.lanes[0].lane_id == wide.lanes[0].lane_id == source.lanes[0].lane_id
    assert source.lanes[0].member_item_ids == ("a", "b")


@pytest.mark.parametrize(("mark_band_size", "clearance"), [(0, 0), (float("nan"), 0), (10, -1), (True, 0)])
def test_rejects_invalid_metrics(mark_band_size: float, clearance: float) -> None:
    source = membership(("a", "lane", "g", "explicit", "key"))
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_SUBTRACK_INPUT"):
        assign_lane_subtracks(source, footprints(("a", (ObstacleRect(0, 0, 1, 1),)),),
                              mark_band_size=mark_band_size, clearance=clearance)


def test_rejects_incomplete_or_empty_footprint_inventory() -> None:
    source = membership(("a", "lane", "g", "explicit", "key"))
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_SUBTRACK_INPUT"):
        assign_lane_subtracks(source, (), mark_band_size=10)
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_SUBTRACK_INPUT"):
        assign_lane_subtracks(source, (LaneItemFootprints("a", ()),), mark_band_size=10)


def test_rejects_attached_assignment_without_same_lane_host() -> None:
    source = membership(("child", "lane", "g", "attached", "missing"))
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_SUBTRACK_INPUT"):
        assign_lane_subtracks(source, footprints(("child", (ObstacleRect(0, 0, 1, 1),)),),
                              mark_band_size=10)


def test_clearance_is_applied_by_canonical_collision_predicate() -> None:
    source = membership(("a", "lane", "g", "explicit", "key"),
                        ("b", "lane", "g", "explicit", "key"))
    no_clearance = assign_lane_subtracks(source, footprints(
        ("a", (ObstacleRect(0, 0, 10, 10),)),
        ("b", (ObstacleRect(10.5, 0, 20, 10),)),
    ), mark_band_size=10)
    with_clearance = assign_lane_subtracks(source, footprints(
        ("a", (ObstacleRect(0, 0, 10, 10),)),
        ("b", (ObstacleRect(10.5, 0, 20, 10),)),
    ), mark_band_size=10, clearance=1)

    assert [item.track_index for item in no_clearance.items] == [0, 0]
    assert [item.track_index for item in with_clearance.items] == [0, 1]
