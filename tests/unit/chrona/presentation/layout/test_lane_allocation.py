"""Neutral, schema-free tests for the #467 collision-aware lane allocator.

These tests exercise `allocate_lanes` directly with synthetic measured
footprints; they never touch View/Project resources. Schema and View-facing
behavior belongs to L1/L3.
"""
from __future__ import annotations

import pytest
from decimal import Decimal

from chrona.presentation.layout.lane_allocation import (
    LaneCandidate, LaneFacetPort, LaneIconProjection, LaneMark, LaneMarkFacet, LaneMember, allocate_lanes,
)
from chrona.presentation.layout.mark_geometry import symbol_parts
from chrona.presentation.layout.surface_quality import MarkPlacement
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment


def facet(facet_id: str, footprint, *, projection_instance_id: str = "row:item",
          source_item_id: str = "item", source_ref: str = "project:item",
          source_kind: str = "primary", purpose: str = "planned",
          primitive_id: str | None = None, primitive_type: str | None = None,
          ports: tuple[LaneFacetPort, ...] = (), overlay_with: tuple[str, ...] = (),
          port_host_bounds: tuple[float, float, float, float] | None = None,
          icon_projection: LaneIconProjection | None = None) -> LaneMarkFacet:
    if isinstance(footprint, ObstacleRect):
        geometry = (("rect", ((footprint.left, footprint.top), (footprint.right, footprint.bottom))),)
        default_type = "Rect"
        bounds = (footprint.left, footprint.top, footprint.right, footprint.bottom)
    else:
        assert isinstance(footprint, ObstacleSegment)
        geometry = (("segment", (footprint.start, footprint.end)),)
        default_type = "Path"
        bounds = (min(footprint.start[0], footprint.end[0]),
                  min(footprint.start[1], footprint.end[1]),
                  max(footprint.start[0], footprint.end[0]),
                  max(footprint.start[1], footprint.end[1]))
    return LaneMarkFacet(facet_id, projection_instance_id, source_item_id, source_ref,
                         source_kind, purpose, primitive_id or facet_id,
                         primitive_type or default_type, geometry, bounds, footprint, ports, overlay_with,
                         port_host_bounds if port_host_bounds is not None else (bounds if ports else None),
                         icon_projection)


def candidate(candidate_id: str, group_key: str, left: float, right: float, title_width: float = 30.0,
             delta_width: float | None = None, predecessors: tuple[tuple[str, str], ...] = (),
             order: tuple | None = None, facets: tuple[LaneMarkFacet, ...] = (), group_order: tuple = ()) -> LaneCandidate:
    if not facets:
        facets = (facet(f"{candidate_id}:planned", ObstacleRect(left, 0, right, 1),
                        projection_instance_id=f"row:{candidate_id}", source_item_id=candidate_id),)
    return LaneCandidate(candidate_id, group_key, order or (left, right, candidate_id, candidate_id),
                         LaneMark(left, right, facets), title_width, delta_width, predecessors,
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
    actual = ObstacleRect(25, 1, 30, 4)
    point = ObstacleSegment((32, 1), (32, 9), stroke_width=2)
    result = allocate_lanes([candidate("planned", "g", 0, 10, facets=(
                                 facet("planned:actual", actual, purpose="actual"),
                                 facet("planned:point", point, purpose="snapshot"))),
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
                        facets=(facet("outside:stroke", ObstacleRect(2, -1, 3, 1)),))
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_MARK_GEOMETRY"):
        allocate_lanes([outside], mark_row_height=10)


def test_mark_rect_requires_positive_width() -> None:
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_MARK_GEOMETRY"):
        LaneMark(10, 10)


def test_atomic_host_and_attached_point_count_once_each_with_source_keyed_comparison_facets() -> None:
    host_mark = LaneMark(0, 20, (
        facet("host:planned", ObstacleRect(0, 0, 20, 10),
              projection_instance_id="row:host", source_item_id="host"),
        facet("host:snapshot", ObstacleRect(0, 0, 20, 10),
              projection_instance_id="row:snapshot", source_item_id="snapshot-host",
              source_kind="snapshot", purpose="snapshot", overlay_with=("host:planned",)),
    ))
    gate_mark = LaneMark(8, 10, (
        facet("gate:planned", ObstacleRect(8, 0, 10, 10),
              projection_instance_id="row:gate", source_item_id="gate",
              overlay_with=("host:planned", "host:snapshot")),
    ))
    bundle = LaneCandidate(
        "host", "g", (0,), host_mark, 40.0,
        bundle=(
            LaneMember("host", host_mark, 40.0),
            LaneMember("gate", gate_mark, 30.0),
        ),
    )
    result = allocate_lanes([bundle], mark_row_height=10, label_row_height=10)
    lane = result.lanes[0]
    assert lane.members == ("host", "gate")
    assert set(lane.placements) == {"host", "gate"}
    assert all(not lane.placements[member].visible_overflow for member in lane.members)
    assert len({lane.placements[member].candidate_id for member in lane.members}) == 2
    assert {facet_value.facet_id for facet_value in host_mark.facets} == {"host:planned", "host:snapshot"}


def test_atomic_bundle_uses_one_lane_when_a_child_mark_would_collide_in_prior_lane() -> None:
    prior = candidate("prior", "g", 8, 10, title_width=2)
    host_mark = LaneMark(0, 20, (facet("host:planned", ObstacleRect(0, 0, 20, 10)),))
    gate_mark = LaneMark(8, 10, (facet("gate:point", ObstacleRect(8, 0, 10, 10),
                                       overlay_with=("host:planned",)),))
    bundle = LaneCandidate(
        "host", "g", (1,), host_mark, 5.0,
        bundle=(LaneMember("host", host_mark, 5.0), LaneMember("gate", gate_mark, 5.0)),
    )
    result = allocate_lanes([prior, bundle], mark_row_height=10, label_row_height=10)
    assert result.lane_of("prior").lane_id != result.lane_of("host").lane_id
    assert result.lane_of("host").lane_id == result.lane_of("gate").lane_id


def test_facet_overlay_exemption_must_be_explicit_and_member_ids_are_globally_unique() -> None:
    host_mark = LaneMark(0, 20, (facet("host:planned", ObstacleRect(0, 0, 20, 10)),))
    comparison_mark = LaneMark(0, 20, (facet("host:snapshot", ObstacleRect(0, 0, 20, 10),
                                             source_kind="snapshot", purpose="snapshot"),))
    unexempted = LaneCandidate("host", "g", (0,), host_mark, 5.0,
                               bundle=(LaneMember("host", host_mark, 5.0),
                                       LaneMember("attached", comparison_mark, 5.0)))
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_BUNDLE_MARK_COLLISION"):
        allocate_lanes([unexempted], mark_row_height=10, label_row_height=10)
    duplicate = candidate("host", "g", 30, 40)
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        allocate_lanes([unexempted, duplicate])


def test_facets_keep_repeated_source_instances_and_typed_ports_distinct_and_countable() -> None:
    first_port = LaneFacetPort("row-a:task:start", "start", (0, 5))
    second_port = LaneFacetPort("row-b:task:start", "start", (10, 5))
    first = facet("row-a:task:planned", ObstacleRect(0, 0, 5, 10),
                  projection_instance_id="row-a:task", source_item_id="task-a",
                  source_ref="project:task", ports=(first_port,))
    second = facet("row-b:task:planned", ObstacleRect(10, 0, 15, 10),
                   projection_instance_id="row-b:task", source_item_id="task-b",
                   source_ref="project:task", ports=(second_port,))
    first_mark, second_mark = LaneMark(0, 5, (first,)), LaneMark(10, 15, (second,))
    assert first_mark.footprints == (first.visible_footprint,)
    result = allocate_lanes([
        LaneCandidate("task-a", "g", (0,), first_mark, 1),
        LaneCandidate("task-b", "g", (1,), second_mark, 1),
    ], mark_row_height=10, label_row_height=2)
    lane = result.lanes[0]
    assert lane.members == ("task-a", "task-b")
    assert first.source_ref == second.source_ref == "project:task"
    assert first.projection_instance_id != second.projection_instance_id
    assert first.ports[0].port_id != second.ports[0].port_id


def test_facets_reject_unknown_overlay_duplicate_ports_and_mutable_geometry() -> None:
    dangling = facet("dangling", ObstacleRect(0, 0, 1, 1), overlay_with=("missing",))
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        LaneCandidate("item", "g", (0,), LaneMark(0, 1, (dangling,)), 1)
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        LaneMarkFacet("bad", "row:item", "item", "project:item", "primary", "planned", "p",
                      "Rect", (("rect", ((0, 0), (1, 1))),), (0, 0, 1, 1), ObstacleRect(0, 0, 1, 1),
                      (LaneFacetPort("same", "start", (0, 0)),
                       LaneFacetPort("same", "end", (1, 1))))
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        LaneMarkFacet("bad", "row:item", "item", "project:item", "primary", "planned", "p",
                      "Rect", (("rect", [[0, 0], [1, 1]]),), (0, 0, 1, 1), ObstacleRect(0, 0, 1, 1))
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        LaneMarkFacet("bad", "row:item", "item", "project:item", "primary", "planned", "p",
                      "Rect", (("rect", ((0, 0), (2, 2))),), (0, 0, 2, 2), ObstacleRect(0, 0, 1, 1))
    first_port = LaneFacetPort("same-port", "start", (0.5, 0.5))
    second_port = LaneFacetPort("same-port", "start", (2.5, 0.5))
    first = facet("first", ObstacleRect(0, 0, 1, 1), ports=(first_port,))
    second = facet("second", ObstacleRect(2, 0, 3, 1), ports=(second_port,))
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        allocate_lanes([candidate("first-item", "g", 0, 1, facets=(first,)),
                        candidate("second-item", "g", 2, 3, facets=(second,))])


def test_closed_candidate_requires_facets_and_preserves_unexpanded_primitive_bounds() -> None:
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        LaneCandidate("anonymous", "g", (0,), LaneMark(0, 10), 1)
    path = LaneMarkFacet(
        "item:path", "row:item", "item", "project:item", "primary", "planned",
        "primitive:path", "Path", (("move", ((2.0, 5.0),)), ("line", ((8.0, 5.0),))),
        (2.0, 5.0, 8.0, 5.0), ObstacleSegment((2, 5), (8, 5), stroke_width=2),
    )
    raster = LaneMarkFacet(
        "item:raster", "row:item", "item", "project:item", "primary", "raster",
        "primitive:raster", "Raster", (("image", ((3.0, 2.0), (7.0, 9.0))),),
        (3.0, 2.0, 7.0, 9.0), ObstacleRect(2.0, 1.0, 8.0, 10.0),
        overlay_with=("item:path",),
    )
    assert path.primitive_bounds == (2.0, 5.0, 8.0, 5.0)
    assert path.visible_footprint.stroke_width > 0
    assert raster.primitive_bounds == (3.0, 2.0, 7.0, 9.0)
    assert raster.visible_footprint == ObstacleRect(2.0, 1.0, 8.0, 10.0)
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        LaneMarkFacet(
            "item:bad-port", "row:item", "item", "project:item", "primary", "planned",
            "primitive:path", "Path", (("move", ((2.0, 5.0),)), ("line", ((8.0, 5.0),))),
            (2.0, 5.0, 8.0, 5.0), ObstacleSegment((2, 5), (8, 5), stroke_width=2),
            ports=(LaneFacetPort("bad-port", "outside", (2.0, 4.5)),),
            port_host_bounds=(2.0, 5.0, 8.0, 5.0),
        )


def icon_projection(*, placement_id: str = "placed-icon", kind: str = "vector",
                    path_index: int | None = 0, path_count: int | None = 2,
                    asset_identity: str = "sha256:asset", paint: str | None = "fill",
                    stroke_width: float | None = None, raster_payload: bytes | None = None
                    ) -> LaneIconProjection:
    if kind == "raster":
        path_index = path_count = None
        paint = None
    return LaneIconProjection(
        placement_id, "catalog-icon", kind, asset_identity, (24, 16),
        Rect(Decimal("0"), Decimal("0"), Decimal("10"), Decimal("10")),
        "/body/visuals/0", "", True, "timeline", 300, 2.0,
        path_index, path_count, paint, stroke_width,
        "round" if paint == "stroke" else None,
        "bevel" if paint == "stroke" else None,
        raster_payload,
    )


def test_vector_icon_projection_keeps_two_completed_paths_and_common_emission_identity() -> None:
    first_projection = icon_projection(path_index=0, paint="fill")
    second_projection = icon_projection(path_index=1, paint="stroke", stroke_width=3.5)
    first = facet("icon:path0", ObstacleRect(1, 1, 3, 3), primitive_id="placed-icon",
                  primitive_type="Icon", icon_projection=first_projection)
    second = facet("icon:path1", ObstacleSegment((5, 5), (9, 5), stroke_width=3.5),
                   primitive_id="placed-icon", primitive_type="Icon", icon_projection=second_projection)

    mark = LaneMark(0, 10, (first, second))

    assert tuple(item.path_index for item in
                 (first.icon_projection, second.icon_projection)) == (0, 1)
    assert (first.icon_projection.paint, second.icon_projection.paint) == ("fill", "stroke")
    assert second.icon_projection.stroke_width == 3.5
    assert (second.icon_projection.line_cap, second.icon_projection.line_join) == ("round", "bevel")
    assert mark.footprints == (first.visible_footprint, second.visible_footprint)
    assert all(item.bounds.inline_size == 10 for item in
               (first.icon_projection, second.icon_projection))


@pytest.mark.parametrize("indices", [(0,), (0, 0)])
def test_vector_icon_projection_rejects_missing_or_duplicate_path_indices(indices) -> None:
    projections = [icon_projection(path_index=index) for index in indices]
    facets = tuple(facet(f"p{index}", ObstacleRect(index, 0, index + 1, 1),
                         primitive_id="placed-icon", primitive_type="Icon",
                         icon_projection=projection)
                   for index, projection in enumerate(projections))
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        LaneMark(0, 10, facets)


def test_icon_projection_rejects_shared_asset_mismatch_and_preserves_raster_bytes() -> None:
    first = facet("p0", ObstacleRect(0, 0, 1, 1), primitive_id="placed-icon",
                  primitive_type="Icon", icon_projection=icon_projection(path_index=0))
    second = facet("p1", ObstacleRect(1, 0, 2, 1), primitive_id="placed-icon",
                   primitive_type="Icon", icon_projection=icon_projection(
                       path_index=1, asset_identity="sha256:other"))
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        LaneMark(0, 10, (first, second))

    payload = b"\x89PNG\r\n\x1a\nexact"
    raster = icon_projection(kind="raster", raster_payload=payload)
    facet_value = LaneMarkFacet(
        "raster-facet", "row:item", "item", "project:item", "primary", "iconMark",
        "placed-icon", "Icon", (("rect", ((0.0, 0.0), (10.0, 10.0))),),
        (0.0, 0.0, 10.0, 10.0), ObstacleRect(0.0, 0.0, 10.0, 10.0),
        icon_projection=raster,
    )
    assert facet_value.icon_projection.raster_payload is payload
    assert facet_value.icon_projection.viewport == (24, 16)
    LaneMark(0, 10, (facet_value,))

    repeated = LaneMarkFacet(
        "raster-facet-copy", "row:item-copy", "item-copy", "project:item", "primary", "iconMark",
        "placed-icon-copy", "Icon", (("rect", ((0.0, 0.0), (10.0, 10.0))),),
        (0.0, 0.0, 10.0, 10.0), ObstacleRect(0.0, 0.0, 10.0, 10.0),
        icon_projection=icon_projection(placement_id="placed-icon-copy", kind="raster",
                                        raster_payload=payload),
    )
    repeated_mark = LaneMark(0, 10, (facet_value, repeated))
    assert repeated_mark.facets[0].source_ref == repeated_mark.facets[1].source_ref
    assert repeated_mark.facets[0].projection_instance_id != repeated_mark.facets[1].projection_instance_id
    assert repeated_mark.facets[0].icon_projection.placement_id != repeated_mark.facets[1].icon_projection.placement_id


def test_attached_countable_member_also_requires_its_own_facet() -> None:
    root_mark = LaneMark(0, 10, (facet("root:planned", ObstacleRect(0, 0, 10, 10)),))
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        LaneCandidate("root", "g", (0,), root_mark, 1,
                      bundle=(LaneMember("root", root_mark, 1),
                              LaneMember("attached", LaneMark(2, 3), 1)))


def test_contain_center_glyph_ports_use_completed_host_bounds_without_widening_primitive() -> None:
    mark_bounds = Rect(10, 1, 5, 4)
    slot = (float(mark_bounds.inline), float(mark_bounds.block),
            float(mark_bounds.inline + mark_bounds.inline_size),
            float(mark_bounds.block + mark_bounds.block_size))
    parts = symbol_parts(
        {"shape": "glyph", "viewBox": [10, 10],
         "parts": [{"paint": "stroke", "d": "M4 4 L6 4"}]},
        (slot[0], slot[1], slot[2] - slot[0], slot[3] - slot[1]),
    )
    mark = MarkPlacement(
        "planned:row:item", "task", mark_bounds, (10.0, 3.0), (15.0, 3.0),
        mark_shape="point", semantic_id="planned", symbol_parts=parts,
    )
    path = parts[0].commands
    assert path[0].points[0] == (12.1, 2.6)
    assert path[1].points[0] == (12.9, 2.6)
    primitive_bounds = (12.1, 2.6, 12.9, 2.6)
    visible_footprint = ObstacleSegment((12.1, 2.6), (12.9, 2.6), stroke_width=1.0)
    owner = LaneMarkFacet(
        "row:item:planned:part0", "row:item", "item", "task", "primary", "planned",
        "planned:row:item:part0", "Symbol",
        tuple((command.kind, command.points) for command in path), primitive_bounds,
        visible_footprint,
        ports=(LaneFacetPort("row:item:start", "start", mark.start_port),
               LaneFacetPort("row:item:end", "end", mark.end_port)),
        port_host_bounds=slot,
    )
    assert owner.primitive_bounds == primitive_bounds
    assert owner.visible_footprint == visible_footprint
    assert owner.port_host_bounds == slot
    assert tuple(port.position for port in owner.ports) == (mark.start_port, mark.end_port)


def test_facet_port_host_bounds_are_required_and_reject_out_of_host_ports() -> None:
    footprint = ObstacleRect(12, 2, 13, 3)
    geometry = (("rect", ((12, 2), (13, 3))),)
    kwargs = dict(
        facet_id="row:attached:planned", projection_instance_id="row:attached",
        source_item_id="attached", source_ref="project:attached", source_kind="primary",
        purpose="planned", primitive_id="planned:row:attached", primitive_type="Rect",
        completed_geometry=geometry, primitive_bounds=(12, 2, 13, 3),
        visible_footprint=footprint,
        ports=(LaneFacetPort("row:attached:at", "at", (12.5, 2.5)),),
    )
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        LaneMarkFacet(**kwargs)
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_CANDIDATE_INPUT"):
        LaneMarkFacet(**kwargs, port_host_bounds=(10, 1, 12, 3))
    attached = LaneMarkFacet(**kwargs, port_host_bounds=(12, 2, 13, 3))
    root = facet("row:root:planned", ObstacleRect(0, 0, 2, 1))
    assert attached.projection_instance_id == "row:attached"
    assert attached.source_ref != root.source_ref
