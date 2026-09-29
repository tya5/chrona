"""Fixed lane membership with per-instance, source-keyed mark subtracks."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from chrona.presentation.layout.lane_projection import LaneProjectionInstance
from chrona.presentation.layout.lane_subtracks import (
    LaneFacetFootprint,
    LaneItemFootprints,
    assign_lane_subtracks,
)
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment
from chrona.presentation.layout.presentation import RowPlacement
from chrona.presentation.layout.surface_lanes import _LaneLayoutRow
from chrona.presentation.layout.surface_composer import (
    _lane_label_candidates,
    _place_lane_mark_tracks,
)
from chrona.presentation.review.lane_membership import (
    Lane,
    LaneAssignment,
    LaneMembership,
)


def membership(*entries: tuple[str, str, str, str, str]) -> LaneMembership:
    lane_members: dict[tuple[str, str], list[str]] = {}
    assignments = []
    for item_id, lane_id, group_id, rule, source_id in entries:
        lane_members.setdefault((lane_id, group_id), []).append(item_id)
        assignments.append(LaneAssignment(item_id, lane_id, group_id, rule, source_id))
    lanes = tuple(Lane(lane_id, group_id, tuple(members))
                  for (lane_id, group_id), members in lane_members.items())
    return LaneMembership(lanes, tuple(assignments))


def unit(item_id: str, *facets: tuple[str, ObstacleRect | ObstacleSegment, tuple[str, ...]],
         source_kind: str = "primary") -> LaneItemFootprints:
    instance = LaneProjectionInstance("row", item_id, item_id, source_kind)
    return LaneItemFootprints(item_id, instance, tuple(
        LaneFacetFootprint(facet_id, geometry, overlays)
        for facet_id, geometry, overlays in facets
    ))


def rect(facet_id: str, left: float, top: float, right: float, bottom: float,
         overlays: tuple[str, ...] = ()):
    return facet_id, ObstacleRect(left, top, right, bottom), overlays


def tracks(result):
    return {item.item_id: item.track_index for item in result.items}


@pytest.mark.parametrize(("side", "fallback", "preferred", "expected"), [
    ("auto", (), None, ("end", "start")),
    ("inside", ("inside", "end", "suppress"), None, ("inside", "end")),
    ("above", ("inside", "end", "suppress"), None, ("above", "inside", "end")),
    ("auto", ("start", "suppress", "end"), None, ("start",)),
    ("auto", (), "inside", ("inside", "end", "start")),
])
def test_lane_label_candidates_preserve_authored_order_and_terminal_suppression(side, fallback, preferred, expected):
    assert _lane_label_candidates(side, fallback, preferred) == expected


def test_explicitly_overlapping_members_keep_membership_and_get_internal_tracks():
    source = membership(("a", "authored", "g", "explicit", "hardware"),
                        ("b", "authored", "g", "explicit", "hardware"))
    result = assign_lane_subtracks(source, (
        unit("a", rect("a-mark", 0, 0, 10, 10)),
        unit("b", rect("b-mark", 5, 0, 15, 10)),
    ), mark_band_size=10)

    assert source.lanes[0].member_item_ids == ("a", "b")
    assert tracks(result) == {"a": 0, "b": 1}
    assert result.lanes[0].subtrack_count == 2
    assert result.lanes[0].pitch == 10


def test_touching_visible_marks_share_a_subtrack():
    source = membership(("a", "lane", "g", "dates", "first-compatible:lane"),
                        ("b", "lane", "g", "dates", "first-compatible:lane"))
    result = assign_lane_subtracks(source, (
        unit("a", rect("a-mark", 0, 0, 10, 10)),
        unit("b", rect("b-mark", 10, 0, 20, 10)),
    ), mark_band_size=10)

    assert tracks(result) == {"a": 0, "b": 0}
    assert result.lanes[0].subtrack_count == 1


def test_attached_children_try_host_track_but_sibling_collision_is_not_exempt():
    source = membership(("host", "lane", "g", "explicit", "key"),
                        ("child-one", "lane", "g", "attached", "host"),
                        ("child-two", "lane", "g", "attached", "host"))
    host = rect("host-mark", 0, 0, 10, 10, ("child-one-mark", "child-two-mark"))
    one = rect("child-one-mark", 0, 0, 10, 10, ("host-mark",))
    two = rect("child-two-mark", 0, 0, 10, 10, ("host-mark",))
    result = assign_lane_subtracks(source, (
        unit("host", host),
        unit("child-one", one),
        unit("child-two", two),
    ), mark_band_size=10)

    assert tracks(result) == {"host": 0, "child-one": 0, "child-two": 1}
    assert source.lanes[0].member_item_ids == ("host", "child-one", "child-two")


def test_shared_comparison_instances_can_share_only_declared_facet_pairs():
    source = membership(("work", "lane", "g", "single", "work"))
    first = unit("work", rect("primary-mark", 0, 0, 10, 10, ("scenario-mark",)))
    second = unit("work", rect("scenario-mark", 0, 0, 10, 10, ("primary-mark",)),
                  source_kind="scenario")
    result = assign_lane_subtracks(source, (first, second), mark_band_size=10)

    assert [item.track_index for item in result.items] == [0, 0]
    assert result.instance(second.projection_instance_id).track_index == 0


def test_unlisted_overlap_inside_one_instance_fails_closed():
    source = membership(("a", "lane", "g", "single", "a"))
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_SUBTRACK_OVERLAY_MISSING"):
        assign_lane_subtracks(source, (
            unit("a", rect("path-one", 0, 0, 10, 10), rect("path-two", 5, 5, 15, 15)),
        ), mark_band_size=10)


def test_rejects_asymmetric_or_unknown_overlay_references():
    source = membership(("a", "lane", "g", "explicit", "key"),
                        ("b", "lane", "g", "explicit", "key"))
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_SUBTRACK_OVERLAY_INVALID"):
        assign_lane_subtracks(source, (
            unit("a", rect("a-mark", 0, 0, 10, 10, ("b-mark",))),
            unit("b", rect("b-mark", 0, 0, 10, 10)),
        ), mark_band_size=10)
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_SUBTRACK_OVERLAY_INVALID"):
        assign_lane_subtracks(source, (
            unit("a", rect("a-mark", 0, 0, 10, 10, ("missing",))),
            unit("b", rect("b-mark", 20, 0, 30, 10)),
        ), mark_band_size=10)


def test_protruding_stroked_icon_footprint_controls_pitch_and_offset():
    source = membership(("a", "lane", "g", "explicit", "key"),
                        ("b", "lane", "g", "explicit", "key"))
    result = assign_lane_subtracks(source, (
        unit("a", rect("a-mark", 0, 0, 10, 10, ("icon-stroke",)),
             ("icon-stroke", ObstacleSegment((5, -2), (5, 12), 2), ("a-mark",))),
        unit("b", rect("b-mark", 5, 0, 15, 10)),
    ), mark_band_size=10)

    lane = result.lanes[0]
    assert lane.offset == 3
    assert lane.pitch == 16
    assert lane.block_extent == 32
    assert result.instance(result.items[0].projection_instance_id).block_offset == 3
    assert result.items[1].block_offset == 19


def test_theme_geometry_changes_instance_tracks_without_mutating_membership():
    source = membership(("a", "lane", "g", "explicit", "key"),
                        ("b", "lane", "g", "explicit", "key"))
    narrow = assign_lane_subtracks(source, (
        unit("a", rect("a-mark", 0, 0, 4, 10)),
        unit("b", rect("b-mark", 5, 0, 10, 10)),
    ), mark_band_size=10)
    wide = assign_lane_subtracks(source, (
        unit("a", rect("a-mark", 0, 0, 7, 10)),
        unit("b", rect("b-mark", 5, 0, 12, 10)),
    ), mark_band_size=10)

    assert [item.track_index for item in narrow.items] == [0, 0]
    assert [item.track_index for item in wide.items] == [0, 1]
    assert source.lanes[0].member_item_ids == ("a", "b")


@pytest.mark.parametrize(("mark_band_size", "clearance"),
                         [(0, 0), (float("nan"), 0), (10, -1), (True, 0)])
def test_rejects_invalid_metrics(mark_band_size: float, clearance: float):
    source = membership(("a", "lane", "g", "single", "a"))
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_SUBTRACK_INPUT"):
        assign_lane_subtracks(source, (unit("a", rect("a", 0, 0, 1, 1)),),
                              mark_band_size=mark_band_size, clearance=clearance)


def test_rejects_incomplete_or_empty_footprint_inventory():
    source = membership(("a", "lane", "g", "single", "a"))
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_SUBTRACK_INPUT"):
        assign_lane_subtracks(source, (), mark_band_size=10)
    instance = LaneProjectionInstance("row", "a", "a", "primary")
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_SUBTRACK_INPUT"):
        assign_lane_subtracks(source, (LaneItemFootprints("a", instance, ()),), mark_band_size=10)


def test_clearance_is_applied_by_canonical_collision_predicate():
    source = membership(("a", "lane", "g", "explicit", "key"),
                        ("b", "lane", "g", "explicit", "key"))
    values = (
        unit("a", rect("a", 0, 0, 10, 10)),
        unit("b", rect("b", 10.5, 0, 20, 10)),
    )
    no_clearance = assign_lane_subtracks(source, values, mark_band_size=10)
    with_clearance = assign_lane_subtracks(source, values, mark_band_size=10, clearance=1)

    assert [item.track_index for item in no_clearance.items] == [0, 0]
    assert [item.track_index for item in with_clearance.items] == [0, 1]


def test_composer_translates_each_projection_instance_without_collapsing_member_identity():
    source = membership(("a", "lane", "g", "explicit", "key"),
                        ("b", "lane", "g", "explicit", "key"))
    first = LaneProjectionInstance("source-a", "a", "a", "combined")
    comparison = LaneProjectionInstance("source-a", "scenario:a", "a", "scenario")
    second = LaneProjectionInstance("source-b", "b", "b", "combined")
    plan = assign_lane_subtracks(source, (
        LaneItemFootprints("a", first, (LaneFacetFootprint("first", ObstacleRect(0, 0, 10, 10), ("comparison",)),)),
        LaneItemFootprints("a", comparison,
                           (LaneFacetFootprint("comparison", ObstacleRect(0, 0, 10, 10), ("first",)),)),
        LaneItemFootprints("b", second, (LaneFacetFootprint("second", ObstacleRect(5, 0, 15, 10)),)),
    ), mark_band_size=10)
    items = tuple(SimpleNamespace(item_id=item_id, object_id=object_id, source_kind=source_kind)
                  for item_id, object_id, source_kind in (("a", "a", "combined"),
                                                          ("scenario:a", "a", "scenario"),
                                                          ("b", "b", "combined")))
    row = _LaneLayoutRow("lane", "g", items, ("a", "a", "b"))

    tracks = _place_lane_mark_tracks(
        review_rows=(row,), row_placements=(RowPlacement("lane", "g", (0, 20, 100, 30)),),
        plan=plan, mark_block_size=10,
    )

    assert [(track.instance_id, track.block) for track in tracks] == [
        ("lane:a", 25), ("lane:scenario:a", 25), ("lane:b", 35),
    ]
