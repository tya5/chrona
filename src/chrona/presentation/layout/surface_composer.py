"""Complete shared surface geometry before Scene primitive projection."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from collections.abc import Mapping
import re
from typing import Any

from chrona.presentation.layout.model import LayoutError, LayoutManifest, Rect, geometry_sum
from chrona.presentation.layout.label_visual_measurement import (
    resolve_label_visual_advances, visual_target_placement_id,
)
from chrona.presentation.layout.lane_preflight import (
    lane_inline_frame_for_manifest,
)
from chrona.presentation.layout.lane_subtracks import FixedLanePreflight, LaneSubtrackPlan, assign_lane_subtracks
from chrona.presentation.layout.lane_item_footprints import compose_lane_item_footprints
from chrona.presentation.model.semantic_registry import (
    axis_band_semantic_ids, axis_label_semantic_ids, REQUIRED_SLOTS, label_chip_semantic, semantic_binding)
from chrona.presentation.model.projection import shared_track_member_key
from chrona.presentation.layout.presentation import MarkBandFrame, MarkGeometry, TrackPlacement, place_mark_tracks, place_rows, place_table_columns, required_row_block_extents, table_cell_indent, table_text_line_block, table_text_measurer
from chrona.presentation.layout.axis import axis_intervals, axis_label_fits, format_axis_tier_label, thinning_schedule
from chrona.presentation.model.axis_names import axis_name_table
from chrona.presentation.layout.text import ellipsize_text, measure_text_width, metric_for_family, metric_for_role, paint_text, place_text, wrap_text
from chrona.presentation.layout.annotations import (
    AnnotationBox, annotation_rail_candidates, nearest_box_port, place_annotation_rail, project_annotation_box,
    resolve_annotation_anchor, route_annotation_leader,
)
from chrona.presentation.layout.annotation_search import lattice_positions, nearest_free_box, nearest_free_tail_box
from chrona.presentation.layout.balloon_geometry import balloon_outline
from chrona.presentation.layout.labels import LabelPlacement
from chrona.presentation.layout.annotation_topology import (
    AnnotationRouteTrial, local_route_bounds, route_annotation_candidate, visible_segments,
)
from chrona.presentation.layout.comparison_marks import ComparisonMark
from chrona.presentation.layout.labels import LabelRect, LabelRequest, place_label
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex, obstacles_intersect,
)
from chrona.presentation.layout.ports import ConnectorEgress, coincident_endpoint_port_ids, connector_egress_candidates
from chrona.presentation.model.placement_candidates import candidate_order
from chrona.presentation.model.info_diagnostics import SuppressedPlotLabels
from chrona.presentation.layout.relation_terminals import marker_geometry
from chrona.presentation.layout.routing import (
    RouteSearchFailure, RouteSuppressionEvidence, place_relation_route,
    relation_route_quality, select_lane_relation_route,
)
from chrona.presentation.layout.path_geometry import rounded_orthogonal_path
from chrona.presentation.layout.mark_geometry import MarkFacetAbsence, compose_item_marks, symbol_parts
from chrona.presentation.layout.icon_geometry import complete_icon_paths
from chrona.presentation.layout.lane_mark_facets import (
    _mark_facets, _overlay_compound_facets, _with_mark_visuals,
)
from chrona.presentation.layout.lane_projection import LaneProjectionClosure, LaneProjectionInstance, close_lane_projection, lane_missing_actual_visible
from chrona.presentation.layout.lane_visual_binding import bind_lane_visual_requests
from chrona.presentation.layout.surface_quality import (
    AxisIntervalOutcome, AxisTierOutcome, CollisionDomain, ColumnPlacement, FitWarning, GroupPlacement, MarkPlacement, PathCommand, PlacementDecision, RelationPlacement, RowPlacement, ScalePlacement,
    IconPlacement, LayoutImageFill, ShapePlacement, SlotPlacement, SurfacePlacement, SurfaceLayoutRequest,
    TextPlacement, LaneEmissionFacet, LaneEmissionPlacement, annotation_presentation, intersects,
)
from chrona.presentation.layout.image_slice_geometry import image_slice_tiles


@dataclass(frozen=True)
class SurfaceLayoutComposition:
    """Completed common surface geometry and the semantic rows it was derived from."""

    placement: SurfacePlacement
    review_rows: tuple[Any, ...]
    track_placements: tuple[TrackPlacement, ...]
    mark_absences: tuple[MarkFacetAbsence, ...] = ()


@dataclass(frozen=True)
class _LaneLayoutRow:
    """Layout adapter for one already-fixed View lane, never a member selector."""

    row_id: str
    group_id: str
    items: tuple[Any, ...]
    member_item_ids: tuple[str, ...]
    label: str = ""
    table_subject_id: str = ""
    depth: int = 0
    rollup_presentation: str = "none"


def _lane_fallback_clears_required_labels(
    points: tuple[tuple[float, float], ...], placed_text: tuple[TextPlacement, ...],
) -> bool:
    """A lane-only direct route may overflow marks, never required member text."""
    labels = tuple(ObstacleRect(*(
        float(item.bounds.inline), float(item.bounds.block),
        float(item.bounds.inline + item.bounds.inline_size),
        float(item.bounds.block + item.bounds.block_size),
    )) for item in placed_text if item.semantic_id in {"memberLabel", "finishDelta"}
                    and item.required and item.overflow != "suppressed")
    return all(not obstacles_intersect(ObstacleSegment(start, end), label)
               for start, end in zip(points, points[1:]) for label in labels)


def _review_rows(projection: Any) -> tuple[Any, ...]:
    lane_membership = getattr(projection, "lane_membership", None)
    if lane_membership is not None:
        lane_rows = getattr(projection, "lane_rows", ())
        if len(lane_rows) != len(lane_membership.lanes):
            raise LayoutError("E_LAYOUT_LANE_PROJECTION_INVALID", "/projection/laneRows")
        if any(len(row.items) != len(row.member_item_ids) for row in lane_rows):
            raise LayoutError("E_LAYOUT_LANE_PROJECTION_INVALID", "/projection/laneRows")
        return tuple(_LaneLayoutRow(row.lane_id, row.group_id, row.items, row.member_item_ids,
                                    table_subject_id=row.lane_id) for row in lane_rows)
    return projection.rows or ()


def _lane_owner(review_row: Any, item: Any) -> tuple[str, str] | None:
    """Join one row item to its immutable member ID by typed projection facts."""
    member_ids = getattr(review_row, "member_item_ids", ())
    if not member_ids:
        return None
    matches = [member_id for candidate, member_id in zip(review_row.items, member_ids, strict=True)
               if ((candidate.item_id or candidate.object_id, candidate.object_id, candidate.source_kind)
                   == (item.item_id or item.object_id, item.object_id, item.source_kind))]
    if len(matches) != 1:
        raise LayoutError("E_LAYOUT_LANE_PROJECTION_INVALID", f"/projection/laneRows/{review_row.row_id}")
    return review_row.row_id, matches[0]


def _lane_instance_owners(projection: Any, closure: LaneProjectionClosure) -> dict[LaneProjectionInstance, tuple[str, str]]:
    """Join original Review occurrences to final lanes without decoding IDs."""
    lane_rows = {row.lane_id: row for row in projection.lane_rows}
    source_rows = {row.row_id: row for row in projection.rows}
    owners: dict[LaneProjectionInstance, tuple[str, str]] = {}
    for instance in closure.instances:
        row = source_rows.get(instance.row_id)
        if row is None or not row.items:
            raise LayoutError("E_LAYOUT_LANE_PROJECTION_INVALID", "/projection/rows")
        member_id = row.items[0].item_id or row.items[0].object_id
        assignment = projection.lane_membership.assignment_for(member_id)
        lane_row = lane_rows.get(assignment.lane_id)
        if lane_row is None or not any(
            candidate_member_id == member_id
            and (item.item_id or item.object_id, item.object_id, item.source_kind)
            == (instance.item_id, instance.object_id, instance.source_kind)
            for item, candidate_member_id in zip(lane_row.items, lane_row.member_item_ids, strict=True)
        ):
            raise LayoutError("E_LAYOUT_LANE_PROJECTION_INVALID", "/projection/laneRows")
        owners[instance] = (lane_row.lane_id, instance.item_id)
    return owners


def _lane_emissions(projection: Any, review_rows: tuple[Any, ...], marks: list[MarkPlacement],
                    text: list[Any], shapes: list[ShapePlacement], icons: tuple[IconPlacement, ...],
                    theme_tokens: Any) -> tuple[LaneEmissionPlacement, ...]:
    """Close the typed Layout-to-Scene member inventory after all geometry is final."""
    if projection.lane_membership is None:
        return ()
    items: dict[tuple[str, str, str, str], Any] = {}
    for row in review_rows:
        for item, member_id in zip(row.items, row.member_item_ids, strict=True):
            key = (row.row_id, member_id, item.source_kind, item.object_id)
            if key in items:
                raise LayoutError("E_LAYOUT_LANE_EMISSION_INVALID", f"/projection/laneRows/{row.row_id}")
            items[key] = item
    icons_by_host: dict[str, list[IconPlacement]] = {}
    for icon in icons:
        if icon.host_placement_id is not None:
            icons_by_host.setdefault(icon.host_placement_id, []).append(icon)
    progress_by_host: dict[str, list[ShapePlacement]] = {}
    for shape in shapes:
        if shape.clip_host_id is not None and shape.semantic_id == "progressFill":
            progress_by_host.setdefault(shape.clip_host_id, []).append(shape)

    grouped: dict[tuple[str, str, str, str, str], list[LaneEmissionFacet]] = {}

    def add(placement_type: str, placement_id: str, row_id: str, member_id: str,
            purpose: str, facet: LaneEmissionFacet) -> None:
        grouped.setdefault((placement_type, placement_id, row_id, member_id, purpose), []).append(facet)

    for mark in marks:
        if mark.lane_row_id is None:
            continue
        if mark.lane_member_id is None or mark.lane_source_kind is None:
            raise LayoutError("E_LAYOUT_LANE_EMISSION_INVALID", mark.placement_id)
        item = items.get((mark.lane_row_id, mark.lane_member_id,
                          mark.lane_source_kind, mark.source_ref))
        if item is None:
            raise LayoutError("E_LAYOUT_LANE_EMISSION_INVALID", mark.placement_id)
        instance = LaneProjectionInstance(mark.lane_row_id, item.item_id or item.object_id,
                                          item.object_id, item.source_kind)
        facets = _overlay_compound_facets(_mark_facets(item, instance, mark, theme_tokens))
        facets = _with_mark_visuals(item, instance, mark, facets,
                                    icons_by_host.get(mark.placement_id, ()),
                                    progress_by_host.get(mark.placement_id, ()), theme_tokens)
        for facet in facets:
            if facet.icon_projection is not None:
                placement_type = "icon"
                placement_id = facet.icon_projection.placement_id
            elif facet.progress_projection is not None:
                placement_type = "shape"
                placement_id = facet.primitive_id
            else:
                placement_type = "mark"
                placement_id = mark.placement_id
            add(placement_type, placement_id, mark.lane_row_id, mark.lane_member_id,
                facet.purpose,
                LaneEmissionFacet(facet.facet_id, placement_type, placement_id,
                                  facet.primitive_id, facet.visible_footprint, "mark",
                                  (facet.glyph_part_projection.part_index
                                   if facet.glyph_part_projection is not None else
                                   facet.icon_projection.path_index
                                   if facet.icon_projection is not None else None)))

    for placed in text:
        if (placed.lane_row_id is None or placed.overflow == "suppressed"
                or placed.semantic_id not in {"memberLabel", "finishDelta"}):
            continue
        if placed.lane_member_id is None:
            raise LayoutError("E_LAYOUT_LANE_EMISSION_INVALID", placed.placement_id)
        left, top, width, height = _bounds(placed.bounds)
        if width <= 0 or height <= 0:
            raise LayoutError("E_LAYOUT_LANE_EMISSION_INVALID", placed.placement_id)
        obstacle = ObstacleRect(left, top, left + width, top + height)
        purpose = semantic_binding(placed.semantic_id).purpose
        add("text", placed.placement_id, placed.lane_row_id, placed.lane_member_id,
            purpose, LaneEmissionFacet(f"label:{placed.placement_id}", "text", placed.placement_id,
                                       placed.placement_id, obstacle, "required-label"))

    # Text-associated icons and chips are independent Scene primitives but
    # retain the same typed owner and Layout-completed viewport/box footprint.
    for icon in icons:
        if icon.lane_row_id is None or icon.semantic_id == "iconMark":
            continue
        if icon.lane_member_id is None:
            raise LayoutError("E_LAYOUT_LANE_EMISSION_INVALID", icon.placement_id)
        left, top, width, height = _bounds(icon.bounds)
        obstacle = ObstacleRect(left, top, left + width, top + height)
        purpose = semantic_binding(icon.semantic_id).purpose
        add("icon", icon.placement_id, icon.lane_row_id, icon.lane_member_id,
            purpose, LaneEmissionFacet(f"icon:{icon.placement_id}", "icon", icon.placement_id,
                                       icon.placement_id, obstacle, "required-label"))
    for shape in shapes:
        if shape.lane_row_id is None or shape.clip_host_id is not None:
            continue
        if shape.lane_member_id is None:
            raise LayoutError("E_LAYOUT_LANE_EMISSION_INVALID", shape.placement_id)
        left, top, width, height = _bounds(shape.bounds)
        if width <= 0 or height <= 0:
            continue
        purpose = semantic_binding(shape.semantic_id).purpose
        add("shape", shape.placement_id, shape.lane_row_id, shape.lane_member_id,
            purpose, LaneEmissionFacet(f"shape:{shape.placement_id}", "shape", shape.placement_id,
                                       shape.placement_id,
                                       ObstacleRect(left, top, left + width, top + height),
                                       "required-label"))
    return tuple(LaneEmissionPlacement(kind, placement_id, row_id, member_id, purpose,
                                       tuple(facets))
                 for (kind, placement_id, row_id, member_id, purpose), facets in grouped.items())


def _lane_label_candidates(side: str, fallback: tuple[str, ...], preferred: str | None) -> tuple[str, ...]:
    """Preserve authored side/fallback; auto alone supplies end/start defaults."""
    ordered = []
    if preferred and preferred != "auto":
        ordered.append(preferred)
    if side != "auto":
        ordered.append(side)
    ordered.extend(fallback if fallback else (("end", "start") if side == "auto" else ()))
    candidates = []
    for candidate in ordered:
        if candidate == "suppress":
            break
        if candidate not in candidates:
            candidates.append(candidate)
    return tuple(candidates)


def _place_lane_mark_tracks(*, review_rows: tuple[_LaneLayoutRow, ...],
                            row_placements: tuple[Any, ...], plan: LaneSubtrackPlan,
                            mark_block_size: float) -> tuple[TrackPlacement, ...]:
    """Project typed source-instance subtracks without revisiting membership."""
    lane_plan = {lane.lane_id: lane for lane in plan.lanes}
    item_plan = {(item.item_id, item.projection_instance_id.item_id,
                  item.projection_instance_id.object_id, item.projection_instance_id.source_kind): item
                 for item in plan.items}
    if len(review_rows) != len(row_placements) or len(review_rows) != len(lane_plan):
        raise LayoutError("E_LAYOUT_LANE_SUBTRACK_INVALID", "/projection/laneRows")
    tracks: list[TrackPlacement] = []
    for review_row, row in zip(review_rows, row_placements, strict=True):
        lane = lane_plan.get(review_row.row_id)
        if lane is None or row.row_id != review_row.row_id or row.bounds[3] < lane.block_extent:
            raise LayoutError("E_LAYOUT_LANE_SUBTRACK_INVALID", "/projection/laneRows")
        origin = row.bounds[1] + (row.bounds[3] - lane.block_extent) / 2
        for member_id, item in zip(review_row.member_item_ids, review_row.items, strict=True):
            subtrack = item_plan.get((member_id, item.item_id or item.object_id,
                                      item.object_id, item.source_kind))
            if subtrack is None or subtrack.lane_id != lane.lane_id:
                raise LayoutError("E_LAYOUT_LANE_SUBTRACK_INVALID", "/projection/laneRows")
            block = origin + subtrack.block_offset
            if block < row.bounds[1] or block + mark_block_size > row.bounds[1] + row.bounds[3]:
                raise LayoutError("E_LAYOUT_MARK_OVERFLOW", "/projection/laneRows")
            tracks.append(TrackPlacement(f"{review_row.row_id}:{item.item_id or item.object_id}",
                                         block, block, mark_block_size))
    if len(tracks) != len(plan.items) or len(item_plan) != len(plan.items):
        raise LayoutError("E_LAYOUT_LANE_SUBTRACK_INVALID", "/projection/laneRows")
    return tuple(tracks)


MARK_GEOMETRY_ROLES = ("planned", "actual", "snapshot", "scenario", "missing-actual")
BACKGROUND_SEMANTIC_IDS = frozenset({"rowBand", "groupBand", "groupHeaderBand", "calendarClosed", *axis_band_semantic_ids()})
BACKGROUND_PAINT_ORDER = 10
MARK_PAINT_ORDER_BASE = 100
HOSTED_TEXT_PAINT_ORDER = 200
FOREGROUND_TEXT_PAINT_ORDER = 300
ANNOTATION_PAINT_ORDER = 400
# Layout emits coordinates at micro-point precision.  Intermediate measurement
# APIs are float-based, so containment must not turn a sub-micro-point binary
# conversion residue into a user-visible overflow diagnostic.
GEOMETRY_TOLERANCE = Decimal("0.000001")


def _background_bounds(*, semantic_id: str, extent: str, source_bounds: Rect, table_bounds: tuple[float, float, float, float],
                       timeline_bounds: tuple[float, float, float, float]) -> tuple[Rect, str]:
    """Resolve one finite background extent without exposing coordinates to View."""
    if semantic_id == "calendarClosed":
        if extent != "timeline":
            raise LayoutError("E_LAYOUT_BACKGROUND_EXTENT", "/layoutManifest/reviewSurface/backgroundExtents")
        _, timeline_block, _, timeline_block_size = timeline_bounds
        return (Rect(source_bounds.inline, Decimal(str(timeline_block)), source_bounds.inline_size,
                     Decimal(str(timeline_block_size)),), "timeline")
    table_inline, _, table_inline_size, _ = table_bounds
    timeline_inline, _, timeline_inline_size, _ = timeline_bounds
    if extent == "table":
        return Rect(Decimal(str(table_inline)), source_bounds.block, Decimal(str(table_inline_size)), source_bounds.block_size), "table"
    if extent == "timeline":
        return Rect(Decimal(str(timeline_inline)), source_bounds.block, Decimal(str(timeline_inline_size)), source_bounds.block_size), "timeline"
    if extent == "both":
        return (Rect(Decimal(str(table_inline)), source_bounds.block,
                     Decimal(str(timeline_inline + timeline_inline_size - table_inline)), source_bounds.block_size),
                "review-surface")
    raise LayoutError("E_LAYOUT_BACKGROUND_EXTENT", "/layoutManifest/reviewSurface/backgroundExtents")


def _validate_background_shapes(shapes: list[ShapePlacement], theme_tokens: Any) -> None:
    """Reject completed translucent background fills that would compound."""
    translucent: list[ShapePlacement] = []
    for shape in shapes:
        if shape.semantic_id not in BACKGROUND_SEMANTIC_IDS:
            continue
        role = semantic_binding(shape.semantic_id).scene_role
        treatment, _ = theme_tokens.background(role)
        if treatment == "fill" and theme_tokens.opacity(role) < 1:
            translucent.append(shape)
    for index, shape in enumerate(translucent):
        for other in translucent[index + 1:]:
            # A group's own band intentionally includes its own header row
            # (Specification 45, Specification 50 §3.4), so its groupBand and
            # groupHeaderBand shapes are one group's two decoration layers,
            # not two conflicting decorations, and may legitimately overlap.
            if (shape.source_ref == other.source_ref
                    and {shape.semantic_id, other.semantic_id} == {"groupBand", "groupHeaderBand"}):
                continue
            if intersects(shape.bounds, other.bounds):
                raise LayoutError("E_LAYOUT_BACKGROUND_OVERLAP", "/layoutManifest/reviewSurface/backgroundExtents",
                                  detail=f"{shape.placement_id}:{other.placement_id}")


def _contains_block_interval(*, container_start: Decimal, container_end: Decimal,
                             item_start: Decimal, item_end: Decimal) -> bool:
    """Apply the Layout coordinate tolerance to a physical containment test."""
    return item_start >= container_start - GEOMETRY_TOLERANCE and item_end <= container_end + GEOMETRY_TOLERANCE


def _completed_canvas(*, requested: Rect, rectangles: tuple[Rect, ...],
                      paths: tuple[tuple[tuple[float, float], ...], ...]) -> Rect:
    """Expand the requested canvas to contain Layout's completed geometry.

    A requested viewport is a minimum allocation.  This deliberately lives in
    the composition layer rather than in Scene or a renderer: every target
    receives the identical, already-completed extent.
    """
    inline_start, block_start = requested.inline, requested.block
    inline_end = requested.inline + requested.inline_size
    block_end = requested.block + requested.block_size
    for bounds in rectangles:
        inline_start = min(inline_start, bounds.inline)
        block_start = min(block_start, bounds.block)
        inline_end = max(inline_end, bounds.inline + bounds.inline_size)
        block_end = max(block_end, bounds.block + bounds.block_size)
    for points in paths:
        for inline, block in points:
            inline_start = min(inline_start, Decimal(str(inline)))
            block_start = min(block_start, Decimal(str(block)))
            inline_end = max(inline_end, Decimal(str(inline)))
            block_end = max(block_end, Decimal(str(block)))
    return Rect(inline_start, block_start,
                inline_end - inline_start, block_end - block_start)


def _visual_reservation(*, typography_role: str, font_size: float,
                        visuals: Mapping[str, Any], request: SurfaceLayoutRequest) -> tuple[dict[str, tuple[Any, float, float]], float, float]:
    """Resolve one text run's icon inline budget before its text is measured."""
    resolved: dict[str, tuple[Any, float, float]] = {}
    for side, visual in visuals.items():
        icon = request.icon_assets.get(visual.ref)
        if icon is None:
            raise LayoutError("E_ICON_NAME_UNKNOWN", visual.source_ref)
        try:
            scale, gap_ratio = request.theme_tokens.icon_ratios(typography_role)
        except Exception as error:
            raise LayoutError("E_THEME_ICON_RATIO", visual.source_ref) from error
        height = font_size * float(scale)
        if height <= 0:
            raise LayoutError("E_THEME_ICON_RATIO", visual.source_ref)
        if icon.viewport[1] <= 0:
            raise LayoutError("E_ICON_IMPORT_VIEWPORT", visual.source_ref)
        resolved[side] = (icon, height * icon.viewport[0] / icon.viewport[1], font_size * float(gap_ratio))
    leading = geometry_sum(width + gap for side, (_, width, gap) in resolved.items() if side == "leading")
    trailing = geometry_sum(width + gap for side, (_, width, gap) in resolved.items() if side == "trailing")
    return resolved, leading, trailing


def _detail_visual_requests(request: SurfaceLayoutRequest) -> dict[str, dict[str, Any]]:
    """Select detail-panel visual intents without assigning any Scene geometry."""
    result: dict[str, dict[str, Any]] = {}
    prefixes = {"group-detail": "group-detail", "milestone": "milestone"}
    for visual in request.visual_requests:
        prefix = prefixes.get(visual.target_kind)
        if prefix is None:
            continue
        selector = dict(visual.selector)
        identifier = selector.get("id")
        if not identifier:
            continue
        placement_id = f"{prefix}:{identifier}"
        if visual.side in result.setdefault(placement_id, {}):
            raise LayoutError("E_LAYOUT_VISUAL_DUPLICATE", visual.source_ref)
        result[placement_id][visual.side] = visual
    return result


def _detail_panel_entries(source: str, values: tuple[Any, ...]) -> tuple[tuple[str, str], ...]:
    """Keep Review Detail formatting semantic while delegating geometry to Layout."""
    if source == "group-details":
        return tuple((value[0], f"{value[1]}: {value[2]}") for value in values)
    return tuple((value[0], f"{value[1]} — {value[2].isoformat()}") for value in values)


def _compose_detail_panel_blocks(*, slots: tuple[SlotPlacement, ...], request: SurfaceLayoutRequest,
                                 requested_canvas: Rect) -> tuple[tuple[SlotPlacement, ...], list[Any], list[FitWarning], frozenset[str]]:
    """Complete Review Detail panel lines, rectangles, and visible-fit records."""
    slot_by_source = {slot.source_ref: slot for slot in slots}
    sources = (("group-details", request.surface_content.group_details, "group-detail"),
               ("milestones", request.surface_content.milestones, "milestone"))
    visual_requests = _detail_visual_requests(request)
    completed: list[Any] = []
    warnings: list[FitWarning] = []
    replacements: dict[str, SlotPlacement] = {}
    allocated: list[SlotPlacement] = []
    pre_reserved: set[str] = set()
    treatment = request.theme_tokens.text_treatment("text")
    font_size = float(treatment.font_size)
    metrics = metric_for_role(request.theme_tokens, "text", request.font_metrics)
    requested_end = requested_canvas.block + requested_canvas.block_size

    for source, values, prefix in sources:
        slot = slot_by_source.get(source)
        if slot is None or not values:
            continue
        available = float(slot.bounds.inline_size)
        block = slot.bounds.block
        for previous in allocated:
            left, right = slot.bounds.inline, slot.bounds.inline + slot.bounds.inline_size
            previous_left = previous.bounds.inline
            previous_right = previous.bounds.inline + previous.bounds.inline_size
            if left < previous_right and previous_left < right:
                block = max(block, previous.bounds.block + previous.bounds.block_size)
        cursor = block
        item_overflows: list[tuple[Any, float, float]] = []
        for source_ref, content in _detail_panel_entries(source, values):
            placement_id = f"{prefix}:{source_ref}"
            _, leading, trailing = _visual_reservation(
                typography_role="text", font_size=font_size,
                visuals=visual_requests.get(placement_id, {}), request=request,
            )
            text_available = max(0.0, available - leading - trailing)
            lines = ((content,) if text_available == 0 else
                     wrap_text(content, available_inline=text_available, font_size=font_size, font_metrics=metrics,
                               letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
                               numeric_spacing=treatment.numeric_spacing))
            natural_width = max(measure_text_width(line, font_size=font_size, font_metrics=metrics,
                                                   letter_spacing=float(treatment.letter_spacing),
                                                   text_transform=treatment.transform,
                                                   numeric_spacing=treatment.numeric_spacing) for line in lines)
            disposition = "fit"
            if natural_width > text_available:
                ellipsis_width = measure_text_width("…", font_size=font_size, font_metrics=metrics,
                                                     letter_spacing=float(treatment.letter_spacing),
                                                     text_transform=treatment.transform,
                                                     numeric_spacing=treatment.numeric_spacing)
                if slot.overflow == "ellipsize-with-source" and text_available >= ellipsis_width:
                    lines = tuple(ellipsize_text(line, available_inline=text_available, font_size=font_size,
                                                  font_metrics=metrics, letter_spacing=float(treatment.letter_spacing),
                                                  text_transform=treatment.transform,
                                                  numeric_spacing=treatment.numeric_spacing) for line in lines)
                    disposition = "ellipsized"
                elif slot.overflow == "clip-optional":
                    suppressed = place_text(placement_id=placement_id, source_ref=source_ref, content=content,
                                            inline=float(slot.bounds.inline), baseline_block=float(cursor + Decimal(str(font_size))),
                                            typography_role="text", theme_tokens=request.theme_tokens,
                                            font_metrics=request.font_metrics, overflow="suppressed", required=False,
                                            collision_region=f"{source}:{source_ref}",
                                            collision_domain=CollisionDomain(source, "content"), source_content=content,
                                            lines=lines, available_inline_start=float(slot.bounds.inline),
                                            available_inline_size=text_available, slot_id=slot.slot_id)
                    completed.append(suppressed)
                    warnings.append(FitWarning("W_LAYOUT_DETAIL_PANEL_CLIPPED", placement_id, source_ref,
                                               "detail-panel", "clip-optional", natural_width,
                                               float(suppressed.bounds.block_size), text_available,
                                               float(slot.bounds.block_size)))
                    continue
                else:
                    disposition = "visible-overflow"
            placed = place_text(placement_id=placement_id, source_ref=source_ref, content="\n".join(lines),
                                inline=float(slot.bounds.inline), baseline_block=float(cursor + Decimal(str(font_size))),
                                typography_role="text", theme_tokens=request.theme_tokens,
                                font_metrics=request.font_metrics, overflow=disposition,
                                collision_region=f"{source}:{source_ref}",
                                collision_domain=CollisionDomain(source, "content"), source_content=content,
                                lines=lines, available_inline_start=float(slot.bounds.inline),
                                available_inline_size=available, slot_id=slot.slot_id)
            completed.append(placed)
            pre_reserved.add(placement_id)
            cursor += placed.bounds.block_size
            if disposition == "visible-overflow":
                item_overflows.append((placed, leading + natural_width + trailing, max(0.0, available)))
        final_size = max(slot.bounds.block_size, cursor - block)
        final_slot = replace(slot, bounds=Rect(slot.bounds.inline, block, slot.bounds.inline_size,
                                                final_size))
        replacements[source] = final_slot
        allocated.append(final_slot)
        for placed, required_inline, available_inline in item_overflows:
            warnings.append(FitWarning("W_LAYOUT_VISIBLE_OVERFLOW", placed.placement_id, placed.source_ref,
                                       "detail-panel", "visible-overflow", required_inline,
                                       float(placed.bounds.block_size), available_inline, float(final_size)))
        if final_slot.bounds.block + final_slot.bounds.block_size > requested_end + GEOMETRY_TOLERANCE:
            warnings.append(FitWarning("W_LAYOUT_VISIBLE_OVERFLOW", f"detail-panel:{source}", source,
                                       "detail-panel", "visible-overflow", float(final_slot.bounds.inline_size),
                                       float(final_slot.bounds.block_size), float(final_slot.bounds.inline_size),
                                       max(0.0, float(requested_end - final_slot.bounds.block))))
    final_slots = tuple(replacements.get(slot.source_ref, slot) for slot in slots)
    return final_slots, completed, warnings, frozenset(pre_reserved)


_FOOTER_SOURCES = frozenset({"group-details", "milestones", "observations", "legend", "notes"})


def _complete_footer_band(*, provisional_slots: tuple[SlotPlacement, ...],
                          completed_slots: tuple[SlotPlacement, ...]) -> tuple[SlotPlacement, ...]:
    """Translate the physical annotations successor from the final footer union."""
    provisional_by_source = {slot.source_ref: slot for slot in provisional_slots}
    completed_by_source = {slot.source_ref: slot for slot in completed_slots}
    panel_start = min((slot.bounds.block for source, slot in provisional_by_source.items()
                       if source in {"group-details", "milestones"}), default=None)
    if panel_start is None:
        return completed_slots
    panel_line = max((slot.bounds.block_size for source, slot in provisional_by_source.items()
                      if source in {"group-details", "milestones"}), default=Decimal(0))
    provisional_footer = tuple(slot for source, slot in provisional_by_source.items()
                               if source in _FOOTER_SOURCES
                               and panel_start <= slot.bounds.block <= panel_start + panel_line + GEOMETRY_TOLERANCE)
    if not provisional_footer:
        return completed_slots
    provisional_end = max(slot.bounds.block + slot.bounds.block_size for slot in provisional_footer)
    completed_footer = tuple(completed_by_source[slot.source_ref] for slot in provisional_footer)
    completed_end = max(slot.bounds.block + slot.bounds.block_size for slot in completed_footer)
    annotation = completed_by_source.get("annotations")
    panels = tuple(completed_by_source[source] for source in ("group-details", "milestones")
                   if source in completed_by_source)
    overlaps_panel_inline = annotation is not None and any(
        annotation.bounds.inline < panel.bounds.inline + panel.bounds.inline_size
        and panel.bounds.inline < annotation.bounds.inline + annotation.bounds.inline_size
        for panel in panels
    )
    growth = completed_end - provisional_end
    if (growth <= GEOMETRY_TOLERANCE or annotation is None
            or annotation.bounds.block < provisional_end or not overlaps_panel_inline):
        return completed_slots
    translated = replace(annotation, bounds=Rect(annotation.bounds.inline, annotation.bounds.block + growth,
                                                 annotation.bounds.inline_size, annotation.bounds.block_size))
    return tuple(translated if slot.source_ref == "annotations" else slot for slot in completed_slots)


def _validate_detail_panel_placement(text: list[Any], slots: tuple[SlotPlacement, ...]) -> None:
    """Keep final detail text and final panel rectangles consistent after visual projection."""
    slot_by_id = {slot.slot_id: slot for slot in slots}
    panels = [item for item in text if item.placement_id.startswith(("group-detail:", "milestone:"))]
    for item in panels:
        if item.overflow in {"suppressed", "visible-overflow"}:
            continue
        slot = slot_by_id.get(item.slot_id)
        if slot is None:
            raise LayoutError("E_LAYOUT_SLOT_OWNERSHIP_INVALID", item.placement_id)
        if (item.bounds.inline < slot.bounds.inline - GEOMETRY_TOLERANCE
                or item.bounds.inline + item.bounds.inline_size > slot.bounds.inline + slot.bounds.inline_size + GEOMETRY_TOLERANCE
                or item.bounds.block < slot.bounds.block - GEOMETRY_TOLERANCE
                or item.bounds.block + item.bounds.block_size > slot.bounds.block + slot.bounds.block_size + GEOMETRY_TOLERANCE):
            raise LayoutError("E_LAYOUT_DETAIL_PANEL_CONTAINMENT", item.placement_id)
    groups = [item for item in panels if item.placement_id.startswith("group-detail:") and item.overflow != "suppressed"]
    milestones = [item for item in panels if item.placement_id.startswith("milestone:") and item.overflow != "suppressed"]
    for group in groups:
        for milestone in milestones:
            if (group.overflow != "visible-overflow" and milestone.overflow != "visible-overflow"
                    and intersects(group.bounds, milestone.bounds)):
                raise LayoutError("E_LAYOUT_DETAIL_PANEL_OVERLAP", f"{group.placement_id}:{milestone.placement_id}")


def resolve_mark_geometries(theme_tokens: Any) -> dict[str, MarkGeometry]:
    """Close every comparison-mark role to lane-relative Layout geometry."""
    result = {}
    for role in MARK_GEOMETRY_ROLES:
        height, offset, paint_order, corner_radius = theme_tokens.mark_geometry(role)
        result[role] = MarkGeometry(float(height), float(offset), paint_order, float(corner_radius))
    return result


def _centred_cell_baseline(row: Rect, treatment: Any) -> float:
    """Centre a table cell's line box in its row, in the cell's own role."""
    line_block = float(treatment.font_size * treatment.line_height)
    return float(row.block) + (float(row.block_size) - line_block) / 2 + float(treatment.font_size)


def _axis_label_inset(theme_tokens: Any, tier: Any, font_size: float) -> float:
    """Return a start-aligned axis label's declared inset from its cell edge (#426 row 8)."""
    if tier.label is None or tier.label.align != "start":
        return 0.0
    ratio = theme_tokens.optional_number(tier.typography_role or "axis", "labelInset")
    return float(ratio) * font_size if ratio is not None else 0.0


def timeline_content_block_requirement(*, projection: Any, group_presentation: str,
                                       metric_values: dict[str, Decimal], role_geometries: dict[str, MarkGeometry] | None = None,
                                       text_line_block: float = 0.0) -> Decimal:
    """Return the minimum timeline block extent for explicit review rows."""
    rows = _review_rows(projection) or tuple(
        type("_Row", (), {"group_id": item.group_id, "items": (item,)})()
        for item in projection.items
    )
    if getattr(projection, "lane_membership", None) is not None:
        # The View fixes lane count before measurement. Its full mark-facet
        # subtrack extent is closed after the inline scale exists; one mark
        # band per lane is the profile's minimum, not a second membership solve.
        rows = tuple(replace(row, items=row.items[:1]) for row in rows)
    requirements = required_row_block_extents(
        review_rows=tuple(rows), row_minimum=float(metric_values["timeline.row.minBlockSize"]),
        row_padding=float(metric_values["timeline.row.paddingBlock"]),
        mark_block_size=float(metric_values["timeline.mark.blockSize"]), role_geometries=role_geometries,
        text_line_block=text_line_block,
    )
    headers = 0
    previous = object()
    for row in rows:
        if row.group_id != previous:
            headers += 1 if row.group_id and group_presentation == "header" else 0
            previous = row.group_id
    return Decimal(str(geometry_sum(requirements))) + Decimal(headers) * metric_values.get("timeline.groupHeader.blockSize", 0)


def preflight_fixed_lane_layout(*, projection: Any, layout_manifest: LayoutManifest,
                                surface_content: Any, theme_tokens: Any,
                                metric_values: dict[str, Decimal], icon_assets: Mapping[str, Any],
                                visual_requests: tuple[Any, ...]) -> FixedLanePreflight:
    """Close fixed-lane mark tracks once, before final profile block allocation."""
    membership = getattr(projection, "lane_membership", None)
    if membership is None:
        raise LayoutError("E_LAYOUT_LANE_PREFLIGHT_INVALID", "/projection/laneRows")
    start, end = projection.window
    frame = lane_inline_frame_for_manifest(layout_manifest, window=(start, end))
    timeline = next(item for item in layout_manifest.decisions if item.source == "timeline")
    scale = ScalePlacement("table-timeline", "primary", start, end,
                           float(frame.timeline_inline),
                           float(frame.timeline_inline + frame.timeline_inline_size),
                           float(frame.timeline_inline), float(frame.temporal_scale))
    mark_band_size = float(metric_values["timeline.mark.blockSize"])
    footprints = compose_lane_item_footprints(
        projection, scale=scale, as_of=surface_content.as_of,
        theme_tokens=theme_tokens, mark_band_size=mark_band_size,
        role_geometries=resolve_mark_geometries(theme_tokens), slot_id=timeline.source,
        icon_assets=icon_assets, visual_requests=visual_requests,
        progress_fill_source=surface_content.progress_fill_source,
    )
    subtracks = assign_lane_subtracks(membership, footprints, mark_band_size=mark_band_size)
    lane_extent = {lane.lane_id: lane.block_extent for lane in subtracks.lanes}
    row_padding = float(metric_values["timeline.row.paddingBlock"])
    line_block = table_text_line_block(
        theme_tokens, (cell.typography_role for cell in surface_content.table_cells))
    rows = _review_rows(projection)
    requirements = tuple(max(float(metric_values["timeline.row.minBlockSize"]),
                             line_block + row_padding if line_block else 0.0,
                             lane_extent[row.row_id] + row_padding)
                         for row in rows)
    headers = len(tuple(row for index, row in enumerate(rows)
                        if row.group_id and surface_content.group_presentation == "header"
                        and (index == 0 or rows[index - 1].group_id != row.group_id)))
    required = (Decimal(str(geometry_sum(requirements)))
                + Decimal(headers) * metric_values.get("timeline.groupHeader.blockSize", 0))
    return FixedLanePreflight(subtracks, frame, required, surface_content.as_of)


def progress_fill_bounds(host: Rect, fraction: float, inset_ratio: Decimal = Decimal(0)) -> Rect | None:
    """Return the optional completed progress submark bounds for one host mark.

    The host is the track.  A declared inset deflates it by ``inset_ratio`` of
    its block size (inline inset capped at a quarter of the host's inline size)
    and the fraction is measured against that inner track, so 0 is empty and 1
    fills the inner track edge to edge at every bar length (#430).
    """
    if not 0 <= fraction <= 1:
        raise LayoutError("E_PRESENTATION_PROGRESS_INVALID", "/progressFill")
    if fraction == 0:
        return None
    if inset_ratio == 0:
        return Rect(host.inline, host.block, host.inline_size * Decimal(str(fraction)), host.block_size)
    block_inset = host.block_size * inset_ratio
    inline_inset = min(block_inset, host.inline_size / 4)
    return Rect(host.inline + inline_inset, host.block + block_inset,
                (host.inline_size - 2 * inline_inset) * Decimal(str(fraction)), host.block_size - 2 * block_inset)


def relation_label_content(relation: Any) -> str:
    """Format only selected, non-zero relation facts before measured placement."""
    parts: list[str] = []
    if "endpointPair" in relation.label_content:
        parts.append(f"{relation.source_endpoint}->{relation.target_endpoint}")
    if "lag" in relation.label_content:
        raw = relation.lag.get("value") if isinstance(relation.lag, Mapping) else relation.lag
        value = str(raw)
        if all(int(component) == 0 for component in re.findall(r"-?\d+", value)):
            value = ""
        elif value and value[0] not in "+-":
            value = "+" + value
        if value:
            parts.append(value + (f" [{relation.lag_calendar}]" if relation.lag_calendar else ""))
    return " ".join(parts)


def relation_label_anchor(points: tuple[tuple[float, float], ...]) -> LabelRect:
    """Choose the first longest route segment; ties retain canonical route order."""
    left, right = max(zip(points, points[1:]), key=lambda pair: abs(pair[1][0] - pair[0][0]) + abs(pair[1][1] - pair[0][1]))
    x1, y1 = left
    x2, y2 = right
    return LabelRect(min(x1, x2), min(y1, y2), max(1.0, abs(x2 - x1)), max(1.0, abs(y2 - y1)))


def resolve_text_visual_requests(text: list[Any], request: SurfaceLayoutRequest, *,
                                 handled_sources: set[str] | None = None,
                                 axis_label_targets: Mapping[tuple[str, str, str], str] | None = None,
                                 pre_reserved_placements: frozenset[str] = frozenset()) -> tuple[list[Any], list[IconPlacement], list[FitWarning]]:
    """Turn already-resolved View visual intents into completed Layout geometry.

    The caller supplies only placement identities; target vocabulary translation
    remains at the typed View boundary.  This helper deliberately has no Scene,
    Theme lookup, or catalog lookup dependency.
    """
    handled_sources = handled_sources or set()
    requested: dict[str, dict[str, Any]] = {}
    occupied: set[tuple[str, str]] = set()
    for visual in request.visual_requests:
        if visual.target_kind == "mark" or visual.source_ref in handled_sources:
            continue
        selector = dict(visual.selector)
        if visual.target_kind == "axis-band":
            continue
        axis_key = (visual.target_kind, selector.get("level", ""), selector.get("index", ""))
        placement_id = (selector.get("placementId") or (axis_label_targets or {}).get(axis_key)
                        or visual_target_placement_id(visual.target_kind, selector))
        key = (placement_id, visual.side)
        if key in occupied:
            raise LayoutError("E_LAYOUT_VISUAL_DUPLICATE", visual.source_ref)
        occupied.add(key)
        if visual.ref is None:
            raise LayoutError("E_LAYOUT_VISUAL_TARGET", visual.source_ref)
        requested.setdefault(placement_id, {})[visual.side] = visual
    icons: list[IconPlacement] = []
    warnings: list[FitWarning] = []
    for placement_id, by_side in requested.items():
        matches = [item for item in text if item.placement_id == placement_id
                   and item.overflow != "suppressed"]
        if len(matches) != 1:
            raise LayoutError("E_LAYOUT_VISUAL_TARGET", next(iter(by_side.values())).source_ref)
    for index, item in enumerate(text):
        by_side = requested.pop(item.placement_id, None)
        if not by_side or item.overflow == "suppressed":
            continue
        item_metrics = metric_for_family(item.font_family, item.font_weight, request.font_metrics)
        resolved, leading, trailing = _visual_reservation(
            typography_role=item.typography_role, font_size=item.font_size,
            visuals=by_side, request=request,
        )
        allocated = (item.available_inline_size if item.available_inline_size is not None
                     else float(item.bounds.inline_size))
        available = allocated - leading - trailing
        source = item.source_content if item.source_content is not None else item.content
        natural_lines = (item.lines if item.source_content is None and len(item.lines) > 1
                         else (source,))
        if item.placement_id in pre_reserved_placements:
            lines, content, overflow = item.lines, item.content, item.overflow
        elif available <= 0:
            lines, content, overflow = natural_lines, "\n".join(natural_lines), "visible-overflow"
        elif len(item.lines) > 1:
            lines = wrap_text(source, available_inline=available, font_size=item.font_size, font_metrics=item_metrics,
                              letter_spacing=item.letter_spacing, text_transform=item.text_transform,
                              numeric_spacing=item.numeric_spacing)
            content, overflow = "\n".join(lines), item.overflow
        elif item.source_content is not None:
            ellipsis_width = measure_text_width("…", font_size=item.font_size, font_metrics=item_metrics,
                                                letter_spacing=item.letter_spacing,
                                                text_transform=item.text_transform,
                                                numeric_spacing=item.numeric_spacing)
            if available < ellipsis_width:
                lines, content, overflow = (source,), source, "visible-overflow"
            else:
                content = ellipsize_text(source, available_inline=available, font_size=item.font_size,
                                         font_metrics=item_metrics, letter_spacing=item.letter_spacing,
                                         text_transform=item.text_transform,
                                         numeric_spacing=item.numeric_spacing)
                lines, overflow = (content,), "ellipsized" if content != source else "fit"
        elif measure_text_width(source, font_size=item.font_size, font_metrics=item_metrics,
                                letter_spacing=item.letter_spacing, text_transform=item.text_transform,
                                numeric_spacing=item.numeric_spacing) <= available:
            content, lines, overflow = source, (source,), item.overflow
        else:
            lines, content, overflow = (source,), source, "visible-overflow"
        width = max(measure_text_width(line, font_size=item.font_size, font_metrics=item_metrics,
                                       letter_spacing=item.letter_spacing, text_transform=item.text_transform,
                                       numeric_spacing=item.numeric_spacing) for line in lines)
        if width > available:
            overflow = "visible-overflow"
            if item.placement_id not in pre_reserved_placements:
                warnings.append(FitWarning("W_LAYOUT_VISIBLE_OVERFLOW", item.placement_id, item.source_ref,
                                           "text-visual", "visible-overflow", leading + width + trailing,
                                           float(item.bounds.block_size), max(0.0, allocated),
                                           float(item.bounds.block_size)))
        baseline = item.baseline
        if baseline is None or not hasattr(item_metrics, "cap_height_at"):
            raise LayoutError("E_FONT_METRICS_CAP_HEIGHT", next(iter(by_side.values())).source_ref)
        available_start = (item.available_inline_start if item.available_inline_start is not None
                           else float(item.bounds.inline))
        shifted_baseline = (available_start + leading, baseline[1])
        painted_lines = tuple(paint_text(line, text_transform=item.text_transform) for line in lines)
        text[index] = replace(item, content=paint_text(content, text_transform=item.text_transform),
                              lines=painted_lines, overflow=overflow,
                              bounds=Rect(Decimal(str(shifted_baseline[0])), item.bounds.block,
                                          Decimal(str(width)), Decimal(str(item.font_size * item.line_height * len(lines)))),
                              baseline=shifted_baseline)
        cap_height = float(item_metrics.cap_height_at(item.font_size))
        for side, visual in by_side.items():
            icon, icon_width, gap = resolved[side]
            inline = (available_start if side == "leading"
                      else available_start + leading + max(available, width) + trailing - gap - icon_width)
            bounds = Rect(Decimal(str(inline)), Decimal(str(baseline[1] - cap_height + (cap_height - item.font_size * float(request.theme_tokens.icon_ratios(item.typography_role)[0])) / 2)),
                          Decimal(str(icon_width)), Decimal(str(item.font_size * float(request.theme_tokens.icon_ratios(item.typography_role)[0]))) )
            icons.append(IconPlacement(f"visual:{item.placement_id}:{side}", item.source_ref, visual.source_ref,
                                       icon.icon_id, icon.kind, icon.content_identity, icon.viewport, icon.payload, icon.alternative,
                                       visual.decorative, bounds, "labelVisual", icon_width / icon.viewport[0], item.slot_id,
                                       paint_order=item.paint_order, lane_row_id=item.lane_row_id,
                                       lane_member_id=item.lane_member_id,
                                       host_placement_id=item.placement_id))
    if requested:
        raise LayoutError("E_LAYOUT_VISUAL_TARGET", next(iter(next(iter(requested.values())).values())).source_ref)
    return text, icons, warnings


def resolve_mark_visual_requests(marks: list[MarkPlacement], request: SurfaceLayoutRequest) -> list[IconPlacement]:
    """Project the closed View mark target onto one completed planned/actual mark."""
    icons: list[IconPlacement] = []
    occupied: set[str] = set()
    for visual in request.visual_requests:
        if visual.target_kind != "mark":
            continue
        selector = dict(visual.selector)
        placement_id = selector.get("placementId") or visual_target_placement_id("mark", selector)
        if placement_id in occupied:
            raise LayoutError("E_LAYOUT_VISUAL_DUPLICATE", visual.source_ref)
        occupied.add(placement_id)
        # Row-instance identifiers extend the closed object/facet family after
        # the stable View selector; the selector itself never guesses an
        # instance suffix.
        mark = [item for item in marks if item.placement_id == placement_id
                or ("placementId" not in selector and item.placement_id.startswith(placement_id + ":"))]
        icon = request.icon_assets.get(visual.ref or "")
        if len(mark) != 1 or icon is None:
            raise LayoutError("E_LAYOUT_VISUAL_TARGET" if len(mark) != 1 else "E_ICON_NAME_UNKNOWN", visual.source_ref)
        host = mark[0]
        try:
            scale, _ = request.theme_tokens.icon_ratios("icon-mark")
        except Exception as error:
            raise LayoutError("E_THEME_ICON_RATIO", visual.source_ref) from error
        height = float(host.bounds.block_size) * float(scale)
        if height <= 0:
            raise LayoutError("E_THEME_ICON_RATIO", visual.source_ref)
        width = min(float(host.bounds.inline_size), height * icon.viewport[0] / icon.viewport[1])
        bounds = Rect(host.bounds.inline + (host.bounds.inline_size - Decimal(str(width))) / 2,
                      host.bounds.block + (host.bounds.block_size - Decimal(str(height))) / 2,
                      Decimal(str(width)), Decimal(str(height)))
        icons.append(IconPlacement(f"visual:{host.placement_id}", host.source_ref, visual.source_ref,
                                   icon.icon_id, icon.kind, icon.content_identity, icon.viewport, icon.payload, icon.alternative,
                                   visual.decorative, bounds, "iconMark", width / icon.viewport[0], host.slot_id,
                                   paint_order=host.paint_order + 1, lane_row_id=host.lane_row_id,
                                   lane_member_id=host.lane_member_id,
                                   host_placement_id=host.placement_id))
    return icons


def resolve_axis_band_visual_requests(shapes: list[ShapePlacement], request: SurfaceLayoutRequest,
                                      targets: Mapping[tuple[str, str, str], str]) -> list[IconPlacement]:
    """Place a band-targeted icon from typed axis metadata, never an ID parser."""
    icons: list[IconPlacement] = []
    for visual in request.visual_requests:
        if visual.target_kind != "axis-band":
            continue
        selector = dict(visual.selector)
        placement_id = targets.get(("axis-band", selector.get("level", ""), selector.get("index", "")))
        shape = next((item for item in shapes if item.placement_id == placement_id), None)
        icon = request.icon_assets.get(visual.ref or "")
        if shape is None or icon is None:
            raise LayoutError("E_LAYOUT_VISUAL_TARGET" if shape is None else "E_ICON_NAME_UNKNOWN", visual.source_ref)
        scale, _ = request.theme_tokens.icon_ratios("icon-mark")
        height = min(float(shape.bounds.inline_size), float(shape.bounds.block_size)) * float(scale)
        if height <= 0 or icon.viewport[1] <= 0:
            raise LayoutError("E_THEME_ICON_RATIO" if height <= 0 else "E_ICON_IMPORT_VIEWPORT", visual.source_ref)
        width = height * icon.viewport[0] / icon.viewport[1]
        bounds = Rect(shape.bounds.inline + (shape.bounds.inline_size - Decimal(str(width))) / 2,
                      shape.bounds.block + (shape.bounds.block_size - Decimal(str(height))) / 2,
                      Decimal(str(width)), Decimal(str(height)))
        icons.append(IconPlacement(f"visual:{shape.placement_id}", shape.source_ref, visual.source_ref,
                                   icon.icon_id, icon.kind, icon.content_identity, icon.viewport, icon.payload,
                                   icon.alternative, visual.decorative, bounds, "iconMark", width / icon.viewport[0], shape.slot_id,
                                   paint_order=HOSTED_TEXT_PAINT_ORDER))
    return icons


def candidate_label_visuals(placement_id: str, typography_role: str,
                            request: SurfaceLayoutRequest) -> tuple[tuple[Any, Any, float, float], ...]:
    """Resolve visual advances before a candidate-label solver chooses bounds."""
    return resolve_label_visual_advances(
        placement_id, typography_role, visual_requests=request.visual_requests,
        icon_assets=request.icon_assets, theme_tokens=request.theme_tokens,
    )


def compose_surface_layout(request: SurfaceLayoutRequest) -> SurfaceLayoutComposition:
    """Resolve slots, rows, groups, temporal scale, and mark tracks in Layout."""
    projection = request.projection
    layout_manifest = request.layout_manifest
    measured_sources = request.measured_sources
    metric_values = getattr(measured_sources, "metric_values", None)
    if not isinstance(layout_manifest, LayoutManifest):
        raise LayoutError("E_PRESENTATION_LAYOUT_REQUIRED", "/layoutManifest")
    if not isinstance(metric_values, dict):
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    decisions = {item.source: item for item in layout_manifest.decisions if item.source}
    required = tuple(slot.value for slot in REQUIRED_SLOTS)
    missing = next((name for name in required if name not in decisions), None)
    if missing is not None:
        raise LayoutError("E_PRESENTATION_PRIMITIVE_MISSING", f"/layoutManifest/sources/{missing}")
    start, end = projection.window
    if not isinstance(start, date) or not isinstance(end, date) or start >= end:
        raise LayoutError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection/window")
    if projection.lane_membership is not None:
        preflight = request.fixed_lane_preflight
        if (preflight is None or preflight.as_of != request.surface_content.as_of
                or preflight.seed_inline_frame != lane_inline_frame_for_manifest(
                    layout_manifest, window=(start, end))):
            raise LayoutError("E_LAYOUT_LANE_PREFLIGHT_INVALID", "/layoutManifest")
        if request.visual_requests:
            # Spec 64: one object selector fans out to every selected lane
            # occurrence. Keep the View selector outside Layout placement IDs;
            # the typed projection instance supplies each final identity.
            closure = close_lane_projection(projection, as_of=request.surface_content.as_of)
            label_visuals, mark_visuals = bind_lane_visual_requests(
                projection, closure, request.visual_requests)
            owners = _lane_instance_owners(projection, closure)
            resolved_visuals = [visual for visual in request.visual_requests
                                if visual.target_kind not in {"plot-label", "mark"}]
            for instance, visuals in label_visuals.items():
                lane_id, item_id = owners[instance]
                placement_id = f"member-label:{lane_id}:{item_id}"
                resolved_visuals.extend(replace(visual, selector=(("placementId", placement_id),))
                                        for visual in visuals)
            for (instance, purpose), visual in mark_visuals.items():
                lane_id, item_id = owners[instance]
                placement_id = f"{purpose}:{lane_id}:{item_id}"
                resolved_visuals.append(replace(visual, selector=(("placementId", placement_id),)))
            request = replace(request, visual_requests=tuple(resolved_visuals))
    if ("timeline.row.minBlockSize" not in metric_values
            or "timeline.row.paddingBlock" not in metric_values
            or "timeline.mark.blockSize" not in metric_values):
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/metricValues")
    slots = tuple(
        SlotPlacement(source, source, item.bounds, item.priority or "required",
                      item.overflow or "visible-overflow", "primary" if source in {"timeline", "timeline-axis"} else None,
                      item.direction or "block", item.gap, item.item_min_inline_size)
        for source, item in sorted(decisions.items())
    )
    by_source = {slot.source_ref: slot for slot in slots}
    table = by_source["table"]
    timeline = by_source["timeline"]
    review_surface = SlotPlacement(
        "review-surface", "review-surface",
        Rect(table.bounds.inline, min(table.bounds.block, timeline.bounds.block),
             timeline.bounds.inline + timeline.bounds.inline_size - table.bounds.inline,
             max(table.bounds.block + table.bounds.block_size, timeline.bounds.block + timeline.bounds.block_size)
             - min(table.bounds.block, timeline.bounds.block)),
    )
    slots += (review_surface,)
    slot_ids = {slot.slot_id for slot in slots}

    def text_slot(item: Any) -> str:
        """Resolve a text host's Layout-owned slot before any visual uses it."""
        if item.slot_id in slot_ids:
            return item.slot_id
        if item.collision_domain.slot == "group-header":
            return table.slot_id
        raise LayoutError("E_LAYOUT_SLOT_OWNERSHIP_INVALID", item.placement_id)

    review_rows = _review_rows(projection) or tuple(
        type("_Row", (), {"row_id": item.object_id, "label": item.title, "group_id": item.group_id,
                            "table_subject_id": item.object_id, "items": (item,)})()
        for item in projection.items
    )
    timeline_bounds = _bounds(timeline.bounds)
    scale = ScalePlacement("table-timeline", "primary", start, end, timeline_bounds[0],
                           timeline_bounds[0] + timeline_bounds[2], timeline_bounds[0],
                           timeline_bounds[2] / max(1, (end - start).days))
    group_header_size = (float(metric_values["timeline.groupHeader.blockSize"])
                         if request.surface_content.group_presentation == "header" else 0.0)
    role_geometries = resolve_mark_geometries(request.theme_tokens)
    mark_block_size = float(metric_values["timeline.mark.blockSize"])
    row_padding = float(metric_values["timeline.row.paddingBlock"])
    text_line_block = table_text_line_block(
        request.theme_tokens, (cell.typography_role for cell in request.surface_content.table_cells))
    lane_subtracks = None
    if projection.lane_membership is not None:
        assert request.fixed_lane_preflight is not None
        lane_subtracks = request.fixed_lane_preflight.subtracks
        lane_extent = {item.lane_id: item.block_extent for item in lane_subtracks.lanes}
        requirements = tuple(max(float(metric_values["timeline.row.minBlockSize"]),
                                 text_line_block + row_padding if text_line_block else 0.0,
                                 lane_extent[row.row_id] + row_padding)
                             for row in review_rows)
    else:
        requirements = required_row_block_extents(
            review_rows=tuple(review_rows), row_minimum=float(metric_values["timeline.row.minBlockSize"]),
            row_padding=row_padding, mark_block_size=mark_block_size,
            role_geometries=role_geometries, text_line_block=text_line_block,
        )
    raw_rows = place_rows(review_rows=tuple(review_rows), timeline_bounds=timeline_bounds,
                          group_header_size=group_header_size, required_block_sizes=requirements,
                          distribution=layout_manifest.row_distribution)
    rows = tuple(
        RowPlacement(item.row_id, item.table_subject_id, placement.group_id or "", _rect(placement.bounds),
                     depth=int(getattr(item, "depth", 0)))
        for item, placement in zip(review_rows, raw_rows, strict=True)
    )
    groups: list[GroupPlacement] = []
    table_bounds = _bounds(table.bounds)
    for row in rows:
        if groups and groups[-1].group_id == row.group_id:
            previous = groups[-1]
            content = Rect(previous.content_bounds.inline, previous.content_bounds.block,
                           previous.content_bounds.inline_size,
                           previous.content_bounds.block_size + row.bounds.block_size)
            groups[-1] = GroupPlacement(previous.group_id, content, previous.header_bounds)
        else:
            header = None
            content = row.bounds
            if row.group_id and group_header_size:
                header = Rect(Decimal(str(table_bounds[0])), row.bounds.block - Decimal(str(group_header_size)),
                              Decimal(str(timeline_bounds[0] + timeline_bounds[2] - table_bounds[0])),
                              Decimal(str(group_header_size)))
                # A group's own band includes its own header row, so the
                # header is never painted as if it belonged to the group
                # before it (Specification 45, Specification 50 §3.4).
                content = Rect(row.bounds.inline, header.block, row.bounds.inline_size,
                               row.bounds.block_size + Decimal(str(group_header_size)))
            groups.append(GroupPlacement(row.group_id, content, header))
    if request.theme_tokens is None or request.font_metrics is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    def metric_for(typography_role: str) -> Any:
        return metric_for_role(request.theme_tokens, typography_role, request.font_metrics)
    body_treatment = request.theme_tokens.text_treatment("text")
    body_metrics = metric_for("text")
    body_size = float(body_treatment.font_size)
    title_input = measured_sources.inputs.get("title")
    title_measurement = measured_sources.measurements.get("title")
    if title_measurement is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/measurements/title")
    title = title_input.lines[0] if title_input and title_input.lines else ""
    text = [place_text(placement_id="title", source_ref="title", content=title,
                       inline=float(by_source["title"].bounds.inline),
                       baseline_block=float(by_source["title"].bounds.block) + float(title_measurement.first_baseline or 0),
                       typography_role="heading", theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                       collision_region="title", collision_domain=CollisionDomain("title", "content"),
                       source_content=title, available_inline_start=float(by_source["title"].bounds.inline),
                       available_inline_size=float(by_source["title"].bounds.inline_size))]
    footer_provisional_slots = slots
    slots, detail_panel_text, detail_panel_warnings, detail_visual_reservations = _compose_detail_panel_blocks(
        slots=slots, request=request, requested_canvas=request.layout_manifest.viewport,
    )
    by_source = {slot.source_ref: slot for slot in slots}
    text.extend(detail_panel_text)
    table_columns = request.surface_content.table_columns
    table_cells = request.surface_content.table_cells
    measure_table_text = table_text_measurer(request.theme_tokens, request.font_metrics)
    indent_token = metric_values.get("table.indent.inlineSize")
    cell_indents: dict[str, float] = {}
    for row in rows:
        row_indent = table_cell_indent(grouped=bool(row.group_id), depth=row.depth, inset=body_size,
                                       indent=float(indent_token) if indent_token is not None else None)
        cell_indents[row.row_id] = cell_indents[row.object_id] = row_indent
    columns = place_table_columns(columns=table_columns, cells=table_cells, bounds=table_bounds,
                                  measure_text=measure_table_text, minimum_inline=body_size,
                                  overflow=table.overflow,
                                  gutter=float(metric_values.get("table.column.gutter.inlineSize", 0)),
                                  hierarchy_column=request.surface_content.table_hierarchy_column,
                                  cell_indents=cell_indents)
    positions = {item.column_id: (item.inline, item.inline_size) for item in columns}
    column_widths = {item.column_id: item.inline_size for item in columns}
    column_intents = {item.column_id: item for item in table_columns}

    def table_text(content: str, available_inline: float, typography_role: str) -> tuple[str, str]:
        if table.overflow != "ellipsize-with-source":
            return content, "fit"
        treatment = request.theme_tokens.text_treatment(typography_role)
        resolved = ellipsize_text(content, available_inline=available_inline, font_size=float(treatment.font_size),
                                  font_metrics=metric_for(typography_role), letter_spacing=float(treatment.letter_spacing),
                                  text_transform=treatment.transform,
                                  numeric_spacing=treatment.numeric_spacing)
        return resolved, "ellipsized" if resolved != content else "fit"

    def aligned_inline(content: str, column_id: str, start: float, available_inline: float,
                       typography_role: str, orientation: str = "horizontal") -> float:
        width = measure_table_text(content, typography_role, orientation)
        align = column_intents[column_id].align
        if align == "end":
            return start + max(0.0, available_inline - width)
        if align == "center":
            return start + max(0.0, (available_inline - width) / 2)
        return start

    for column in table_columns:
        column_id, label = column.column_id, column.header
        available = max(0.0, column_widths[column_id] - body_size)
        resolved, overflow = table_text(label, available, "text")
        header_width = measure_text_width(resolved, font_size=body_size, font_metrics=body_metrics,
                                          letter_spacing=float(body_treatment.letter_spacing),
                                          text_transform=body_treatment.transform,
                                          numeric_spacing=body_treatment.numeric_spacing)
        header_block = timeline_bounds[1] - table_bounds[1]
        if column.header_orientation == "rotate-cw":
            baseline = table_bounds[1]
        elif column.header_orientation == "rotate-ccw":
            baseline = table_bounds[1] + header_width
        else:
            baseline = table_bounds[1] + body_size
        text.append(place_text(placement_id=f"column:{column_id}", source_ref="view:tableColumns", content=resolved,
                               inline=aligned_inline(resolved, column_id, positions[column_id][0], available, "text", column.header_orientation), baseline_block=baseline,
                               typography_role="text", theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                               overflow=overflow, collision_region="table", collision_domain=CollisionDomain("table", "header"),
                               source_content=label, available_inline_start=positions[column_id][0],
                               available_inline_size=available, orientation=column.header_orientation))
        # A rotated header may need more block extent than its allocated table
        # header.  Its completed text remains visible; the warning and canvas
        # expansion are assembled with all other Layout geometry below.
    row_by_subject = {item.row_id: item for item in rows} | {item.object_id: item for item in rows}
    for cell in table_cells:
        object_id, column_id, content, typography_role = cell.object_id, cell.column_id, cell.content, cell.typography_role
        row = row_by_subject.get(object_id)
        position = positions.get(column_id)
        if row is not None and position is not None and column_id in column_intents:
            indent = (cell_indents[object_id]
                      if column_id == request.surface_content.table_hierarchy_column else 0)
            available = max(0.0, column_widths[column_id] - indent - body_size)
            resolved, overflow = table_text(content, available, typography_role)
            text.append(place_text(placement_id=f"cell:{object_id}:{column_id}", source_ref=object_id, content=resolved,
                                   inline=aligned_inline(resolved, column_id, position[0] + indent, available, typography_role),
                                   baseline_block=_centred_cell_baseline(row.bounds, request.theme_tokens.text_treatment(typography_role)),
                                   typography_role=typography_role, theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                   overflow=overflow, collision_region="table",
                                   collision_domain=CollisionDomain("table", f"row:{row.row_id}"), source_content=content,
                                   available_inline_start=position[0] + indent,
                                   available_inline_size=available, semantic_id=cell.semantic_id))
    labels = {row.group_id: next((item.group_label for item in review_row.items if item.group_label), row.group_id)
              for review_row, row in zip(review_rows, rows, strict=True) if row.group_id}
    group_header_font_size = (float(request.theme_tokens.text_treatment("groupHeader").font_size)
                              if any(group.header_bounds is not None for group in groups) else body_size)
    for group in groups:
        if group.header_bounds is not None:
            text.append(place_text(placement_id=f"group-header:{group.group_id}", source_ref=group.group_id,
                                       content=labels[group.group_id], inline=float(group.header_bounds.inline),
                                       baseline_block=float(group.header_bounds.block) + group_header_font_size,
                                       typography_role="groupHeader",
                                   theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                   collision_region=f"group:{group.group_id}",
                                   collision_domain=CollisionDomain("group-header", group.group_id),
                                   source_content=labels[group.group_id], semantic_id="groupHeader",
                                   available_inline_start=float(group.header_bounds.inline),
                                   available_inline_size=float(group.header_bounds.inline_size)))
    axis = by_source["timeline-axis"]
    shapes: list[ShapePlacement] = []
    axis_tier_outcomes: list[AxisTierOutcome] = []
    axis_decisions: list[PlacementDecision] = []
    axis_label_targets: dict[tuple[str, str, str], str] = {}
    axis_band_targets: dict[tuple[str, str, str], str] = {}
    diagnostics: list[str] = []
    visible_label_overflows: list[tuple[Any, LabelRect]] = []
    background_extents = layout_manifest.background_extents

    def background_shape(placement_id: str, source_ref: str, semantic_id: str,
                         source_bounds: Rect) -> ShapePlacement | None:
        role = semantic_binding(semantic_id).scene_role
        treatment, paint_order = request.theme_tokens.background(role)
        if treatment == "none":
            return None
        bounds, slot_id = _background_bounds(semantic_id=semantic_id, extent=background_extents.get(semantic_id, ""), source_bounds=source_bounds,
                                             table_bounds=table_bounds, timeline_bounds=timeline_bounds)
        return ShapePlacement(placement_id, source_ref, "Rect", bounds, slot_id=slot_id,
                              paint_order=paint_order, semantic_id=semantic_id)

    row_decoration = request.surface_content.row_decoration
    group_decoration = request.surface_content.group_decoration
    # Group bands are emitted before row stripes so that, at the same
    # declared Theme backgroundPaintOrder (the default in every shipped
    # preset), a row stripe is the later/topmost primitive and remains
    # visible over an opaque group band (Specification 50 §3.4).
    for index, group in enumerate(groups):
        banded = group_decoration in {"all", "alternate"} and (group_decoration == "all" or index % 2 == 0)
        group_shape = None
        if banded:
            group_shape = background_shape(f"group:{group.group_id}", group.group_id, "groupBand", group.content_bounds)
            if group_shape is not None:
                shapes.append(group_shape)
        # A group's own band already includes its own header row (see the
        # group-building loop above), so a group the body decoration painted
        # needs no separate header accent: painting one would double-tint the
        # header row under its own band, at a contrast ratio the band's own
        # colour was never chosen against. The header-only band (`groups:
        # none`, or a selected group whose Theme suppresses the body fill)
        # remains the sole source of header decoration in those cases; an
        # unselected `alternate` group gets neither, so its header is never
        # painted as an extension of the group before it.
        if group.header_bounds is not None and (group_decoration == "none" or (banded and group_shape is None)):
            shape = background_shape(f"group-header-band:{group.group_id}", group.group_id,
                                     "groupHeaderBand", group.header_bounds)
            if shape is not None:
                shapes.append(shape)
    if row_decoration == "alternate":
        for index, row in enumerate(rows):
            if index % 2 == 0:
                shape = background_shape(f"row-band:{row.row_id}", row.row_id, "rowBand", row.bounds)
                if shape is not None:
                    shapes.append(shape)
    # Band and labels tiers each stack in their own independent, monotonic
    # lane cursor (#426): the Nth declared tier of a role occupies the Nth
    # lane of that role, sized from that tier's own bound typography. A View
    # with exactly one band tier keeps its historical whole-axis-slot rect
    # (Specification 39 §1.2), so band_lane_offset/band_ordinal are only
    # consulted once a second band tier is declared.
    label_lane_offset = 0.0
    band_lane_offset = 0.0
    band_ordinal = 0
    label_ordinal = 0
    band_tier_count = sum(item.role == "band" for item in request.surface_content.axis_tiers)
    # Declared lanes (#426 rows 5-6): a labels tier whose typography role
    # declares laneBlockSize has a fixed lane; lanes stack in labels-tier
    # order, and a band tier of the same unit fills exactly that lane.
    declared_lanes: dict[int, tuple[float, float]] = {}
    lane_by_unit: dict[str, tuple[float, float]] = {}
    lane_cursor = 0.0
    for tier_index, tier in enumerate(request.surface_content.axis_tiers):
        if tier.role != "labels" or tier.label is None:
            continue
        role = tier.typography_role or "axis"
        declared = request.theme_tokens.optional_number(role, "laneBlockSize")
        treatment = request.theme_tokens.text_treatment(role)
        if declared is not None and float(declared) > 0 and tier.label.orientation == "horizontal":
            declared_lanes[tier_index] = (lane_cursor, float(declared))
            lane_by_unit.setdefault(tier.unit, (lane_cursor, float(declared)))
            lane_cursor += float(declared)
        else:
            lane_cursor += float(treatment.font_size * treatment.line_height) + float(GEOMETRY_TOLERANCE)
    separator_marks: list[tuple[float, float, float]] = []
    for tier_index, tier in enumerate(request.surface_content.axis_tiers):
        form = tier.label.form if tier.label else None
        name_table = axis_name_table(tier.label.name_table_id) if tier.label else None
        axis_treatment = request.theme_tokens.text_treatment(tier.typography_role or "axis")
        axis_metrics = metric_for(tier.typography_role or "axis")
        axis_size = float(axis_treatment.font_size)
        requested_units = (tuple(candidate for candidate, _ in tier.label.candidate_forms)
                           if tier.unit == "auto" and tier.label else (tier.unit,))
        try:
            if tier.unit == "auto":
                selected = None
                forms = dict(tier.label.candidate_forms) if tier.label else {}
                for candidate in ("day", "week", "month", "quarter", "half", "year"):
                    if candidate not in forms:
                        continue
                    trial = axis_intervals(start, end, candidate, tick_step=tier.every,
                                           fiscal_start_month=request.surface_content.axis_fiscal_start_month)
                    fits_trial = all(axis_label_fits(content=format_axis_tier_label(item, forms[candidate], name_table),
                                                      available_inline=(item.end - item.start).days * scale.unit_ratio,
                                                      font_size=axis_size, font_metrics=axis_metrics,
                                                      letter_spacing=float(axis_treatment.letter_spacing),
                                                      text_transform=axis_treatment.transform,
                                                      numeric_spacing=axis_treatment.numeric_spacing,
                                                      orientation=tier.label.orientation,
                                                      line_height=float(axis_treatment.line_height)) for item in trial)
                    if fits_trial or tier.label.overflow == "visible-overflow":
                        selected, form = trial, forms[candidate]
                        break
                if selected is None:
                    # An explicit thinning request is not a refusal mode.  If
                    # no candidate can be thinned legally, retain the first
                    # declared deterministic form as a visible overlap.
                    candidate = next(item for item in ("day", "week", "month", "quarter", "half", "year")
                                     if item in forms)
                    selected, form = axis_intervals(start, end, candidate, tick_step=tier.every,
                                                    fiscal_start_month=request.surface_content.axis_fiscal_start_month), forms[candidate]
                intervals = selected
            else:
                intervals = axis_intervals(start, end, tier.unit, tick_step=tier.every,
                                           fiscal_start_month=request.surface_content.axis_fiscal_start_month)
        except ValueError as error:
            raise LayoutError(str(error), "/view/body/axis/tiers") from error
        interval_outcomes: tuple[AxisIntervalOutcome, ...]
        if tier.role == "labels" and form is not None:
            interval_outcomes = tuple(
                AxisIntervalOutcome(f"axis-label:{tier_index}:{interval.index}", interval.start, interval.end,
                                    interval.natural_start, interval.natural_end,
                                    format_axis_tier_label(interval, form, name_table),
                                    axis_label_fits(content=format_axis_tier_label(interval, form, name_table),
                                                   available_inline=max(0.0, _coordinate(interval.end, scale) - _coordinate(interval.start, scale)
                                                                        - _axis_label_inset(request.theme_tokens, tier, axis_size)),
                                                   font_size=axis_size, font_metrics=axis_metrics,
                                                   letter_spacing=float(axis_treatment.letter_spacing),
                                                   text_transform=axis_treatment.transform,
                                                   numeric_spacing=axis_treatment.numeric_spacing,
                                                   orientation=tier.label.orientation,
                                                   line_height=float(axis_treatment.line_height)))
                for interval in intervals
            )
            fits = tuple(bool(item.label_fits) for item in interval_outcomes)
            if not all(fits):
                if tier.label.overflow == "thin-with-record":
                    try:
                        schedule = thinning_schedule(fits)
                    except ValueError:
                        # A declared thinning policy cannot remove every
                        # interval. Keep the complete visible result and its
                        # measured reason instead of constructing an invalid
                        # placed outcome for a non-fitting label.
                        interval_outcomes = tuple(replace(
                            item, disposition="placed",
                            reason=None if item.label_fits else "visible-overflow",
                        ) for item in interval_outcomes)
                    else:
                        retained = set(schedule.retained_positions)
                        resolved_outcomes: list[AxisIntervalOutcome] = []
                        for position, outcome in enumerate(interval_outcomes):
                            if position in retained:
                                resolved_outcomes.append(replace(outcome, disposition="placed"))
                            else:
                                resolved_outcomes.append(replace(outcome, disposition="thinned", reason="label-does-not-fit"))
                                diagnostics.append(f"W_LAYOUT_AXIS_LABEL_THINNED:{outcome.candidate_id}:label-does-not-fit")
                                axis_decisions.append(PlacementDecision(outcome.candidate_id, f"/view/body/axis/tiers/{tier_index}",
                                                                        ("thin-with-record", "suppress"), "suppress", "suppressed"))
                        interval_outcomes = tuple(resolved_outcomes)
                        diagnostics.append(f"W_LAYOUT_AXIS_DENSITY:axis-tier:{tier_index}:thinned={len(schedule.thinned_positions)}")
                else:
                    interval_outcomes = tuple(replace(
                        item, disposition="placed",
                        reason=None if item.label_fits else "visible-overflow")
                        for item in interval_outcomes)
            else:
                interval_outcomes = tuple(replace(item, disposition="placed") for item in interval_outcomes)
        else:
            interval_outcomes = tuple(
                AxisIntervalOutcome(f"axis-tier:{tier_index}:{interval.index}", interval.start, interval.end,
                                    interval.natural_start, interval.natural_end)
                for interval in intervals
            )
        if tier.role == "labels" and form is not None:
            for interval, outcome in zip(intervals, interval_outcomes, strict=True):
                if outcome.disposition != "placed":
                    continue
                for canonical in name_table.coincident_canonicals(form, interval.natural_start.month):
                    diagnostics.append(
                        f"W_LAYOUT_AXIS_FORM_EQUIVALENT:{outcome.candidate_id}:table={name_table.table_id}:"
                        f"form={form}:canonical={canonical}:month={interval.natural_start.month}")
        axis_tier_outcomes.append(AxisTierOutcome(
            tier_index, f"/view/body/axis/tiers/{tier_index}", tier.role, requested_units,
            intervals[0].level if intervals else (tier.unit if tier.unit != "auto" else ""), tier.every, form,
            interval_outcomes, name_table.table_id if name_table else None,
        ))
        if tier.role == "band":
            if band_ordinal >= len(axis_band_semantic_ids()):
                raise LayoutError("E_PRESENTATION_AXIS_INVALID", f"/view/body/axis/tiers/{tier_index}",
                                  detail=f"too many band tiers:{band_ordinal + 1}")
            band_semantic_id = axis_band_semantic_ids()[band_ordinal]
            if tier.unit in lane_by_unit:
                lane_offset, lane_size = lane_by_unit[tier.unit]
                band_block = axis.bounds.block + Decimal(str(lane_offset))
                band_block_size = Decimal(str(lane_size))
            elif band_tier_count == 1:
                # The sole band tier keeps its historical whole-axis-slot
                # rect (Specification 39 §1.2); this is the only branch that
                # keeps every committed View's Scene output byte-identical.
                band_block, band_block_size = axis.bounds.block, axis.bounds.block_size
            else:
                band_lane_size = axis_size * float(axis_treatment.line_height) + float(GEOMETRY_TOLERANCE)
                if band_lane_offset + band_lane_size > float(axis.bounds.block_size) + float(GEOMETRY_TOLERANCE):
                    raise LayoutError("E_PRESENTATION_AXIS_OVERFLOW", f"/view/body/axis/tiers/{tier_index}",
                                      detail=f"band-lane:{band_ordinal}")
                band_block = axis.bounds.block + Decimal(str(band_lane_offset))
                band_block_size = Decimal(str(band_lane_size))
            cell_gap = float(request.theme_tokens.optional_number(
                semantic_binding(band_semantic_id).scene_role, "cellGap") or 0)
            for interval in intervals:
                x, x2 = _coordinate(interval.start, scale), _coordinate(interval.end, scale)
                if cell_gap:
                    x, x2 = x + cell_gap / 2, max(x + cell_gap / 2, x2 - cell_gap / 2)
                placement_id = f"axis-band-rect:{tier_index}:{interval.index}"
                treatment, paint_order = request.theme_tokens.background(
                    semantic_binding(band_semantic_id).scene_role)
                if treatment != "none":
                    axis_band_targets[("axis-band", interval.level, str(interval.index))] = placement_id
                    shapes.append(ShapePlacement(placement_id, "timeline-axis", "Rect",
                                                  Rect(Decimal(str(x)), band_block, Decimal(str(max(0.0, x2 - x))), band_block_size),
                                                  semantic_id=band_semantic_id,
                                                  paint_order=paint_order))
            if band_tier_count > 1 and tier.unit not in lane_by_unit:
                band_lane_offset += band_lane_size
            band_ordinal += 1
        elif tier.role in {"grid-major", "grid-minor"}:
            semantic_id = "axisGrid" if tier.role == "grid-major" else "axisGridMinor"
            for interval in intervals:
                x = _coordinate(interval.start, scale)
                shapes.append(ShapePlacement(f"axis-grid:{tier_index}:{interval.index}", "timeline-axis", "Path",
                                              Rect(Decimal(str(x)), timeline.bounds.block, Decimal(0), timeline.bounds.block_size),
                                              ((x, float(timeline.bounds.block)), (x, float(timeline.bounds.block + timeline.bounds.block_size))),
                                              semantic_id=semantic_id,
                                              paint_order=BACKGROUND_PAINT_ORDER + 1))
        elif tier.role == "labels" and form is not None:
            # A tier that leaves typographyRole at its default keeps the
            # single shared "axisLabel" id every committed View already
            # uses (byte-identical), no matter how many such default tiers
            # exist; only a tier that explicitly names a role claims one of
            # the ordinal ids, in declaration order among such tiers.
            if tier.typography_role is None:
                label_semantic_id = axis_label_semantic_ids()[0]
            else:
                label_ordinal += 1
                if label_ordinal >= len(axis_label_semantic_ids()):
                    raise LayoutError("E_PRESENTATION_AXIS_INVALID", f"/view/body/axis/tiers/{tier_index}",
                                      detail=f"too many typography-role labels tiers:{label_ordinal}")
                label_semantic_id = axis_label_semantic_ids()[label_ordinal]
            resolved_typography_role = tier.typography_role or "axis"
            orientation = tier.label.orientation
            label_widths = tuple(
                measure_text_width(outcome.label or "", font_size=axis_size, font_metrics=axis_metrics,
                                   letter_spacing=float(axis_treatment.letter_spacing),
                                   text_transform=axis_treatment.transform,
                                   numeric_spacing=axis_treatment.numeric_spacing)
                for outcome in interval_outcomes if outcome.disposition == "placed"
            )
            lane_size = (axis_size * float(axis_treatment.line_height) + float(GEOMETRY_TOLERANCE)
                         if orientation == "horizontal" else max(label_widths, default=0.0))
            if tier_index in declared_lanes:
                label_lane_offset, lane_size = declared_lanes[tier_index]
            inset = _axis_label_inset(request.theme_tokens, tier, axis_size)
            lane_overflow = label_lane_offset + lane_size > float(axis.bounds.block_size)
            for interval, outcome in zip(intervals, interval_outcomes, strict=True):
                if outcome.disposition == "thinned":
                    continue
                axis_label_targets[("axis-label", interval.level, str(interval.index))] = outcome.candidate_id
                x, x2 = _coordinate(interval.start, scale), _coordinate(interval.end, scale)
                if interval.index > 0 or x > _coordinate(start, scale) + float(GEOMETRY_TOLERANCE):
                    separator_marks.append((x, *((float(axis.bounds.block) + label_lane_offset,
                                                  float(axis.bounds.block) + label_lane_offset + lane_size)
                                                 if tier_index in declared_lanes else
                                                 (float(axis.bounds.block), float(axis.bounds.block + axis.bounds.block_size)))))
                if tier.label.align == "start" and inset:
                    x = x + inset
                available = max(0.0, x2 - x)
                label = outcome.label
                if label is None or outcome.disposition != "placed":
                    raise LayoutError("E_PRESENTATION_AXIS_OVERFLOW", f"/view/body/axis/tiers/{tier_index}",
                                      detail=outcome.candidate_id)
                width = measure_text_width(label, font_size=axis_size, font_metrics=axis_metrics,
                                           letter_spacing=float(axis_treatment.letter_spacing),
                                           text_transform=axis_treatment.transform,
                                           numeric_spacing=axis_treatment.numeric_spacing)
                occupied_inline = width if orientation == "horizontal" else axis_size * float(axis_treatment.line_height)
                inline = x if tier.label.align == "start" else x + (available - occupied_inline) / 2
                if tier_index in declared_lanes:
                    line_block = axis_size * float(axis_treatment.line_height)
                    baseline = float(axis.bounds.block) + label_lane_offset + (lane_size - line_block) / 2 + axis_size
                else:
                    baseline = float(axis.bounds.block) + label_lane_offset + (
                        axis_size if orientation == "horizontal" else (0 if orientation == "rotate-cw" else width))
                placed = place_text(placement_id=f"axis-label:{tier_index}:{interval.index}", source_ref="timeline-axis",
                                    content=label, inline=inline, baseline_block=baseline,
                                    typography_role=resolved_typography_role, theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                    collision_region="timeline-axis-label", collision_domain=CollisionDomain("timeline-axis", "labels"),
                                    source_content=label, available_inline_start=x, available_inline_size=available,
                                    orientation=orientation,
                                    overflow="visible-overflow" if not outcome.label_fits or lane_overflow else "fit")
                placed = replace(placed, semantic_id=label_semantic_id)
                text.append(placed)
                if not outcome.label_fits or lane_overflow:
                    visible_label_overflows.append((placed, LabelRect(*_bounds(axis.bounds))))
            label_lane_offset += lane_size
        else:
            raise LayoutError("E_PRESENTATION_AXIS_INVALID", "/view/body/axis/tiers")
    if request.theme_tokens.has_role("axis-cell-separator"):
        merged: dict[float, tuple[float, float]] = {}
        for x, top, bottom in separator_marks:
            key = round(x, 6)
            low, high = merged.get(key, (top, bottom))
            merged[key] = (min(low, top), max(high, bottom))
        for index, (x, (top, bottom)) in enumerate(sorted(merged.items())):
            shapes.append(ShapePlacement(f"axis-separator:{index}", "timeline-axis", "Path",
                                         Rect(Decimal(str(x)), Decimal(str(top)), Decimal(0), Decimal(str(bottom - top))),
                                         ((x, top), (x, bottom)), semantic_id="axisCellSeparator",
                                         paint_order=BACKGROUND_PAINT_ORDER + 2))
    if request.theme_tokens.has_role("axis-rule"):
        rule_y = float(axis.bounds.block + axis.bounds.block_size)
        left, right = float(timeline.bounds.inline), float(timeline.bounds.inline + timeline.bounds.inline_size)
        shapes.append(ShapePlacement("axis-rule", "timeline-axis", "Path",
                                     Rect(Decimal(str(left)), Decimal(str(rule_y)), Decimal(str(right - left)), Decimal(0)),
                                     ((left, rule_y), (right, rule_y)), semantic_id="axisRule",
                                     paint_order=BACKGROUND_PAINT_ORDER + 2))
    axis_bands = tuple(item for item in shapes if item.semantic_id in axis_band_semantic_ids())

    def axis_band_host(item: TextPlacement) -> str | None:
        # A label's host is the band occupying its own lane, not merely a
        # band whose columns happen to span the label's x-position (#426:
        # multiple band lanes can differ in width and no longer all span the
        # whole axis slot, so the inline test alone is no longer sufficient).
        centre = item.bounds.inline + item.bounds.inline_size / 2
        lane_centre = item.bounds.block + item.bounds.block_size / 2
        candidates = tuple(band for band in axis_bands
                           if band.bounds.inline <= centre <= band.bounds.inline + band.bounds.inline_size
                           and band.bounds.block <= lane_centre <= band.bounds.block + band.bounds.block_size)
        return min(candidates, key=lambda band: band.placement_id).placement_id if candidates else None

    text = [replace(item, host_placement_id=axis_band_host(item), paint_order=HOSTED_TEXT_PAINT_ORDER)
            if item.semantic_id in axis_label_semantic_ids() else item
            for item in text]
    contract = request.presentation_contract
    minimum_closed_day_width = metric_values.get("timeline.calendarClosed.minimumDayWidth")
    closed_days = contract.time.calendar_closed
    if minimum_closed_day_width is not None and scale.unit_ratio < float(minimum_closed_day_width):
        closed_days = contract.time.calendar_exceptions
    for closed_day in closed_days:
        if start <= closed_day < end:
            x1, x2 = _coordinate(closed_day, scale), _coordinate(closed_day.fromordinal(closed_day.toordinal() + 1), scale)
            shape = background_shape(
                f"calendar-closed:{closed_day.isoformat()}", "project-calendar", "calendarClosed",
                Rect(Decimal(str(x1)), timeline.bounds.block,
                     Decimal(str(max(0.0, x2 - x1))), timeline.bounds.block_size),
            )
            if shape is not None:
                shapes.append(shape)
    as_of_label: tuple[float, str] | None = None
    if contract.time.as_of is not None and start <= contract.time.as_of < end:
        x = _coordinate(contract.time.as_of, scale)
        shapes.append(ShapePlacement("as-of", "actual-set", "Path",
                                     Rect(Decimal(str(x)), timeline.bounds.block, Decimal(0), timeline.bounds.block_size),
                                     ((x, float(timeline.bounds.block)), (x, float(timeline.bounds.block + timeline.bounds.block_size))),
                                     paint_order=MARK_PAINT_ORDER_BASE))
        as_of_label = (x, contract.time.as_of_label) if contract.time.as_of_label else None
    tracks = (_place_lane_mark_tracks(review_rows=tuple(review_rows), row_placements=raw_rows,
                                      plan=lane_subtracks, mark_block_size=mark_block_size)
              if lane_subtracks is not None else
              place_mark_tracks(review_rows=tuple(review_rows), row_placements=raw_rows,
                                mark_block_size=mark_block_size, role_geometries=role_geometries))
    track_by_id = {item.instance_id: item for item in tracks}
    marks: list[MarkPlacement] = []

    mark_absences: list[MarkFacetAbsence] = []
    for review_row in review_rows:
        members = sorted(
            enumerate(review_row.items),
            key=lambda pair: shared_track_member_key(pair[1], pair[0]),
        )
        for _, item in members:
            layout_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
            lane_owner = _lane_owner(review_row, item) if projection.lane_membership is not None else None
            instance_id = layout_id if projection.rows else item.object_id
            track = track_by_id[layout_id]
            frame = MarkBandFrame.from_track(track, scale, role_geometries)
            source_kind = item.source_kind if projection.rows else "combined"
            composition = compose_item_marks(
                item=item, instance_id=instance_id, source_kind=source_kind, frame=frame,
                as_of=contract.time.as_of, theme_tokens=request.theme_tokens,
                slot_id=timeline.slot_id, paint_order_base=MARK_PAINT_ORDER_BASE,
                emit_missing_actual=(lane_missing_actual_visible(projection)
                                     if lane_owner is not None else True),
            )
            marks.extend(replace(mark, lane_row_id=lane_owner[0], lane_member_id=lane_owner[1],
                                 lane_source_kind=source_kind)
                         if lane_owner is not None else mark for mark in composition.marks)
            diagnostics.extend(composition.diagnostics)
            mark_absences.extend(composition.absences)
    # A group-header target is a real GroupPlacement extent, not a synthetic table row.
    group_by_id = {group.group_id: group for group in groups}
    visible_group_header_overflows: list[tuple[str, Rect, float]] = []
    folded_by_group: dict[str, list[Any]] = {}
    for folded in getattr(projection, "folded_points", ()):
        folded_by_group.setdefault(folded.group_id, []).append(folded)
    for group_id, folded_points in folded_by_group.items():
        group = group_by_id.get(group_id)
        if group is None or group.header_bounds is None:
            folded = folded_points[0]
            raise LayoutError("E_REVIEW_POINT_GROUP_HEADER_UNAVAILABLE", f"/projection/foldedPoints/{folded.item.object_id}")
        block_size = float(metric_values["timeline.mark.blockSize"])
        capacity = int(float(group.header_bounds.block_size) // block_size)
        occupied = len(folded_points) * block_size
        if occupied > float(group.header_bounds.block_size):
            # Folded marks retain their stable stack order.  Extend the real
            # group-header host rather than inventing a synthetic row or
            # suppressing excess milestones.
            expanded_header = Rect(group.header_bounds.inline, group.header_bounds.block,
                                   group.header_bounds.inline_size, Decimal(str(occupied)))
            replacement = GroupPlacement(group.group_id, group.content_bounds, expanded_header)
            groups[groups.index(group)] = replacement
            group_by_id[group_id] = replacement
            shapes = [replace(shape, bounds=expanded_header)
                      if shape.placement_id == f"group-header-band:{group_id}" else shape
                      for shape in shapes]
            visible_group_header_overflows.append((group_id, expanded_header,
                                                   float(group.header_bounds.block_size)))
            group = replacement
        first_block = float(group.header_bounds.block) + max(0.0, (float(group.header_bounds.block_size) - occupied) / 2)
        for track_index, folded in enumerate(sorted(folded_points, key=lambda point: (point.item.planned.get("at"), point.item.object_id))):
            block = first_block + track_index * block_size
            members = sorted(enumerate(folded.all_items),
                             key=lambda pair: shared_track_member_key(pair[1], pair[0]))
            for _, item in members:
                instance_id = _folded_instance_id(folded, item)
                # Folded marks occupy a real group-header band, so make that
                # band the frame origin while retaining its exact role offsets.
                frame = MarkBandFrame(scale, block, block_size, role_geometries)
                composition = compose_item_marks(
                    item=item, instance_id=instance_id,
                    source_kind=item.source_kind, frame=frame, as_of=contract.time.as_of,
                    theme_tokens=request.theme_tokens, slot_id=timeline.slot_id,
                    paint_order_base=MARK_PAINT_ORDER_BASE, emit_missing_actual=False,
                    emit_diagnostics=False,
                )
                marks.extend(composition.marks)
                diagnostics.extend(composition.diagnostics)
                mark_absences.extend(composition.absences)
    mark_by_id = {item.placement_id: item for item in marks}
    progress_source = request.surface_content.progress_fill_source
    if progress_source is not None:
        progress_inset, progress_radius = request.theme_tokens.progress_track("progress-fill")
        for review_row in review_rows:
            for item in review_row.items:
                if progress_source == "actual":
                    fraction = (item.actual or {}).get("progress")
                    host_prefix = "actual"
                else:
                    fraction = getattr(item, "planned_progress", None)
                    host_prefix = "planned"
                if not isinstance(fraction, (int, float)) or isinstance(fraction, bool) or not 0 <= fraction <= 1:
                    continue
                layout_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
                lane_owner = _lane_owner(review_row, item) if projection.lane_membership is not None else None
                instance_id = layout_id if projection.rows else item.object_id
                host = mark_by_id.get(f"{host_prefix}:{instance_id}")
                if host is None or fraction == 0:
                    continue
                bounds = progress_fill_bounds(host.bounds, float(fraction), progress_inset)
                if bounds is not None and bounds.inline_size > 0:
                    fill_radius = float(progress_radius) * float(min(bounds.inline_size, bounds.block_size))
                    shapes.append(ShapePlacement(f"progress-fill:{host.placement_id}", item.object_id,
                                                 "Rect", bounds, required=False, slot_id=host.slot_id,
                                                 clip_host_id=host.placement_id,
                                                 paint_order=host.paint_order + 1,
                                                 corner_radius=fill_radius,
                                                 semantic_id="progressFill",
                                                 lane_row_id=lane_owner[0] if lane_owner else None,
                                                 lane_member_id=lane_owner[1] if lane_owner else None))
    for review_row, row in zip(review_rows, rows, strict=True):
        if getattr(review_row, "rollup_presentation", "none") != "bar":
            continue
        subject = next((item for item in review_row.items
                        if item.item_id == review_row.table_subject_id and item.source_kind != "actual"), None)
        if subject is None or subject.source_type != "span":
            continue
        start_at, end_at = subject.planned.get("start"), subject.planned.get("end")
        if not isinstance(start_at, date) or not isinstance(end_at, date):
            continue
        x1, x2 = _coordinate(start_at, scale), _coordinate(end_at, scale)
        height = float(request.theme_tokens.summary_bar_height("summary-bar")) * float(metric_values["timeline.mark.blockSize"])
        shapes.append(ShapePlacement(f"summary-bar:{review_row.row_id}", subject.object_id, "Rect",
                                     Rect(Decimal(str(x1)), row.bounds.block,
                                          Decimal(str(max(1.0, x2 - x1))), Decimal(str(height)))))
    placement_decisions: list[PlacementDecision] = list(axis_decisions)
    label_requests: list[LabelRequest] = []
    candidate_icons: list[IconPlacement] = []
    handled_candidate_visuals: set[str] = set()
    if as_of_label is not None:
        x, content = as_of_label
        # A chip's block padding extends the anchor too, so a side candidate
        # keeps the chipped label's top where the bare label's top is (#428).
        as_of_chip = request.theme_tokens.label_chip(semantic_binding("asOfLabelChip").theme_role)
        as_of_anchor_block = (body_size if as_of_chip is None else
                              body_size * float(body_treatment.line_height) + float(as_of_chip[0]) * body_size)
        label_requests.append(LabelRequest(
            "as-of-label", "actual-set", content,
            LabelRect(x, timeline_bounds[1], 0.0, as_of_anchor_block), ("end", "start", "below"),
            "text", "timeline-as-of", CollisionDomain("timeline", "overlay"), "visible-overflow",
            visible_fallback_side="above",
            rule_host_obstacle_id="as-of",
            semantic_id="asOfLabel",
        ))
    row_band_by_id = {row.row_id: LabelRect(float(timeline.bounds.inline), float(row.bounds.block),
                                           float(timeline.bounds.inline_size), float(row.bounds.block_size))
                      for row in rows}
    attached_labels = dict(request.surface_content.attached_labels)
    if contract.labels.enabled or attached_labels:
        for review_row in review_rows:
            for item in review_row.items:
                layout_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
                lane_owner = _lane_owner(review_row, item) if projection.lane_membership is not None else None
                instance_id = layout_id if projection.rows else item.object_id
                planned = item.planned
                start_at, end_at = planned.get("start", planned.get("at")), planned.get("end", planned.get("at"))
                if not isinstance(start_at, date) and not isinstance(end_at, date):
                    continue
                attached = attached_labels.get(item.object_id) if getattr(item, "attached_to", None) else None
                parts = []
                if attached is not None:
                    parts.append(attached)  # required: an attached point's facts are never dropped (#486)
                elif not contract.labels.enabled:
                    continue
                if attached is None and "title" in contract.labels.content:
                    parts.append(item.title)
                if attached is None and "finishDelta" in contract.labels.content and item.finish_delta is not None:
                    parts.append(f"{item.finish_delta:+d}d")
                if not parts:
                    continue
                host_kind = "actual" if item.source_kind == "actual" else "planned"
                host_mark_id = f"{host_kind}:{instance_id}"
                mark = mark_by_id.get(host_mark_id)
                if item.source_kind == "actual" and mark is None:
                    raise LayoutError("E_LAYOUT_LABEL_HOST_UNAVAILABLE", f"/placement/member-label:{instance_id}")
                track = track_by_id[layout_id]
                anchor = LabelRect(*_bounds(mark.bounds)) if mark is not None else LabelRect(
                    _coordinate(end_at if isinstance(end_at, date) else start_at, scale), track.block,
                    max(1.0, track.block_size), track.block_size)
                lane_mode = projection.lane_membership is not None
                default_ladder = (request.surface_content.label_fallback or
                                  (("above", "below", "start", "end")
                                   if contract.labels.side == "auto" else (contract.labels.side,)))
                intent = getattr(item, "presentation", None) or {}
                preferred_side = (intent.get("label") or {}).get("side") if isinstance(intent, dict) else None
                wrap = ((intent.get("text") or {}).get("wrap", "forbid") if isinstance(intent, dict) else "forbid")
                ladder = (_lane_label_candidates(contract.labels.side,
                                                 request.surface_content.label_fallback, preferred_side)
                          if lane_mode else
                          ((preferred_side,) + tuple(side for side in default_ladder if side != preferred_side)
                           if preferred_side else default_ladder))
                sides = tuple(side for side in ladder if side != "suppress")
                # A member label's placement region is its own row band (#488):
                # every candidate, including the side-neighbourhood search,
                # stays inside it so a name never reads as the adjacent row's.
                row_band = row_band_by_id.get(review_row.row_id)
                label_requests.append(LabelRequest(f"member-label:{instance_id}", item.object_id, " ".join(parts),
                                                   anchor, sides, "text", "plot-label", CollisionDomain("timeline", "overlay"),
                                                   "visible-overflow" if attached is not None else
                                                   "suppress" if lane_mode else
                                                   "suppress" if "suppress" in ladder else contract.labels.overflow,
                                                   wrap, bounds=row_band,
                                                   inside_host_obstacle_id=host_mark_id if mark is not None else None,
                                                   semantic_id="memberLabel",
                                                   lane_row_id=lane_owner[0] if lane_owner else None,
                                                   lane_member_id=lane_owner[1] if lane_owner else None,
                                                   lane_source_kind=item.source_kind if lane_owner else None))
        for folded in getattr(projection, "folded_points", ()):
            instance_id = _folded_instance_id(folded, folded.item)
            host_kind = "actual" if folded.item.source_kind == "actual" else "planned"
            mark = mark_by_id.get(f"{host_kind}:{instance_id}")
            group = group_by_id.get(folded.group_id)
            if folded.item.source_kind == "actual" and mark is None:
                raise LayoutError("E_LAYOUT_LABEL_HOST_UNAVAILABLE", f"/placement/member-label:group-header:{folded.group_id}:{folded.item.object_id}")
            if mark is None or group is None or group.header_bounds is None:
                continue
            default_ladder = ("end", "start") if contract.labels.side == "auto" else (contract.labels.side,)
            label_requests.append(LabelRequest(
                f"member-label:group-header:{folded.group_id}:{folded.item.object_id}", folded.item.object_id,
                folded.item.title, LabelRect(*_bounds(mark.bounds)), default_ladder, "groupHeader", "group-header-point",
                CollisionDomain("group-header", folded.group_id), "visible-overflow", bounds=LabelRect(*_bounds(group.header_bounds)),
                inside_host_obstacle_id=mark.placement_id, semantic_id="memberLabel"))
    # The remaining text and routes are part of the same completed Layout closure.
    # Scene may select their semantic roles, but it must never remeasure or route them.
    for review_row in review_rows:
        for item in review_row.items:
            layout_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
            instance_id = layout_id if projection.rows else item.object_id
            if not projection.rows and item.source_kind != "combined":
                continue
            if (item.finish_delta is None or "finishDelta" in contract.labels.content
                    or projection.lane_membership is not None):
                continue
            mark = mark_by_id.get(f"actual:{instance_id}") or mark_by_id.get(f"planned:{instance_id}")
            track = track_by_id[layout_id]
            actual = item.actual or {}
            anchor = actual.get("finish", item.planned.get("end", item.planned.get("at")))
            if isinstance(anchor, date):
                anchor_bounds = LabelRect(*_bounds(mark.bounds)) if mark is not None else LabelRect(
                    _coordinate(anchor, scale), track.block, max(1.0, track.block_size), track.block_size)
                label_requests.append(LabelRequest(f"variance:{instance_id}", item.object_id, f"{item.finish_delta:+d}d",
                                                   anchor_bounds, ("above", "below", "end", "start"), "summary",
                                                   f"variance:{instance_id}", CollisionDomain("timeline", "overlay"),
                                                   request.surface_content.label_overflow, semantic_id="finishDelta"))

    # One monotonically growing Layout inventory is shared by labels, semantic
    # routes and annotations. Background bands deliberately do not enter it.
    surface_obstacles = SurfaceObstacleIndex()

    def register_rect(placement_id: str, obstacle_class: str, region_id: str, bounds: Rect) -> None:
        inline, block, inline_size, block_size = _bounds(bounds)
        if inline_size > 0 and block_size > 0:
            surface_obstacles.add(SurfaceObstacle(placement_id, obstacle_class, region_id,
                                                  ObstacleRect(inline, block, inline + inline_size, block + block_size)))

    def register_path(placement_id: str, obstacle_class: str, region_id: str,
                      points: tuple[tuple[float, float], ...], *, stroke_width: float = 0.0) -> None:
        for index, (source, target) in enumerate(zip(points, points[1:])):
            if source != target:
                surface_obstacles.add(SurfaceObstacle(f"{placement_id}:segment:{index}", obstacle_class,
                                                      region_id, ObstacleSegment(source, target, stroke_width)))

    def register_port(placement_id: str, point: tuple[float, float], region_id: str) -> None:
        surface_obstacles.add(SurfaceObstacle(placement_id, "port", region_id,
                                              ObstacleRect(point[0] - 0.01, point[1] - 0.01,
                                                           point[0] + 0.01, point[1] + 0.01)))

    for mark in marks:
        register_rect(mark.placement_id, "mark", "timeline", mark.bounds)
    for placed_text in text:
        if placed_text.required and placed_text.overflow != "suppressed":
            register_rect(placed_text.placement_id, "text", placed_text.collision_domain.slot, placed_text.bounds)
    for shape in shapes:
        if shape.placement_id == "as-of" and len(shape.points) >= 2:
            surface_obstacles.add(SurfaceObstacle(shape.placement_id, "rule", "timeline",
                                                  ObstacleSegment(shape.points[0], shape.points[1])))

    timeline_rect = LabelRect(*timeline_bounds)
    def place_requested_labels(requests: tuple[LabelRequest, ...]) -> None:
        for label_request in requests:
            label_treatment = request.theme_tokens.text_treatment(label_request.typography_role)
            label_metrics = metric_for(label_request.typography_role)
            font_size, line_height = label_treatment.font_size, label_treatment.line_height
            visuals = candidate_label_visuals(label_request.placement_id, label_request.typography_role, request)
            handled_candidate_visuals.update(visual.source_ref for visual, _, _, _ in visuals)
            leading = geometry_sum(width + gap for visual, icon, width, gap in visuals if visual.side == "leading")
            trailing = geometry_sum(width + gap for visual, icon, width, gap in visuals if visual.side == "trailing")
            available = max(1.0, timeline_rect.width * 0.4 - leading - trailing)
            lines = (wrap_text(label_request.content, available_inline=available,
                               font_size=float(font_size), font_metrics=label_metrics,
                               letter_spacing=float(label_treatment.letter_spacing),
                               text_transform=label_treatment.transform)
                     if label_request.wrap == "allow" else (label_request.content,))
            placement_bounds = label_request.bounds or timeline_rect
            text_width = max(measure_text_width(line, font_size=float(font_size), font_metrics=label_metrics,
                                                letter_spacing=float(label_treatment.letter_spacing),
                                                text_transform=label_treatment.transform) for line in lines)
            label_size = (leading + text_width + trailing,
                          float(font_size) * float(line_height) * len(lines))
            # A declared ``<purpose>-chip`` Theme role draws a background from
            # this label's own measured box; its padding is part of the footprint
            # every candidate negotiates (#428).  Nothing here names a purpose.
            chip_semantic = label_chip_semantic(label_request.semantic_id) or ""
            chip = (request.theme_tokens.label_chip(semantic_binding(chip_semantic).theme_role)
                    if chip_semantic else None)
            chip_pad = ((float(chip[0]) * float(font_size), float(chip[0]) * float(font_size) / 2)
                        if chip is not None else (0.0, 0.0))
            label_size = (label_size[0] + 2 * chip_pad[0], label_size[1] + 2 * chip_pad[1])
            if label_request.bounds is not None and chip is not None:
                # A declared region contains the text; its chip is decoration
                # drawn around it and may reach past the region by its padding.
                placement_bounds = LabelRect(placement_bounds.x - chip_pad[0], placement_bounds.y - chip_pad[1],
                                             placement_bounds.width + 2 * chip_pad[0],
                                             placement_bounds.height + 2 * chip_pad[1])
            # Mark labels remain subject to every completed mark.  ``place_label``
            # alone exempts this request's declared host for an ``inside``
            # candidate; a comparison sibling or another row is never an implicit
            # host.
            candidate = (place_label(label_request.anchor, label_size, label_request.candidates, bounds=placement_bounds,
                                     obstacles=surface_obstacles, gap=max(1.0, float(font_size) * 0.25),
                                     inside_host_obstacle_id=label_request.inside_host_obstacle_id,
                                     required=label_request.overflow == "diagnose", overflow=label_request.overflow,
                                     visible_fallback_side=label_request.visible_fallback_side,
                                     rule_host_obstacle_id=label_request.rule_host_obstacle_id,
                                     search_side_neighborhood=(label_request.rule_host_obstacle_id is None),
                                     classes=(("mark", "text", "label-visual", "rule")
                                              if label_request.rule_host_obstacle_id is not None
                                              else ("mark", "text", "label-visual", "dependency-route")))
                         if label_request.candidates else None)
            provisional = place_text(placement_id=label_request.placement_id, source_ref=label_request.source_ref,
                                     content=label_request.content, inline=0, baseline_block=float(font_size),
                                     typography_role=label_request.typography_role, theme_tokens=request.theme_tokens,
                                     font_metrics=request.font_metrics, collision_region=label_request.collision_region,
                                     collision_domain=label_request.collision_domain, semantic_id=label_request.semantic_id,
                                     lane_row_id=label_request.lane_row_id,
                                     lane_member_id=label_request.lane_member_id,
                                     lane_source_kind=label_request.lane_source_kind)
            fallback_ladder = label_request.candidates + (
                (label_request.visible_fallback_side,)
                if label_request.visible_fallback_side is not None
                and label_request.visible_fallback_side not in label_request.candidates else ())
            if candidate is None:
                ladder = fallback_ladder + (("suppress",) if label_request.overflow == "suppress" else ())
                if not ladder:
                    raise LayoutError("E_PRESENTATION_LABEL_UNPLACEABLE", f"/placement/{label_request.placement_id}")
                text.append(replace(provisional, overflow="suppressed", required=False,
                                    fallback_ladder=ladder,
                                    selected_rung="suppress"))
                placement_decisions.append(PlacementDecision(label_request.placement_id, label_request.source_ref,
                                                             ladder, "suppress", "suppressed"))
                diagnostics.append(f"W_LAYOUT_LABEL_SUPPRESSED:{label_request.placement_id}")
            else:
                chip_box = candidate.bounds
                if chip is not None:
                    candidate = replace(candidate, bounds=LabelRect(
                        chip_box.x + chip_pad[0], chip_box.y + chip_pad[1],
                        chip_box.width - 2 * chip_pad[0], chip_box.height - 2 * chip_pad[1]))
                host = mark_by_id.get(label_request.inside_host_obstacle_id or "")
                slot = by_source.get(label_request.collision_domain.slot)
                slot_bounds = LabelRect(*_bounds(slot.bounds)) if slot is not None else placement_bounds
                crosses_slot = (candidate.bounds.x < slot_bounds.x or candidate.bounds.y < slot_bounds.y
                                or candidate.bounds.right > slot_bounds.right
                                or candidate.bounds.bottom > slot_bounds.bottom)
                visible_overflow = candidate.visible_overflow or crosses_slot
                placed_text = replace(place_text(placement_id=provisional.placement_id, source_ref=provisional.source_ref,
                                       content=provisional.content, inline=candidate.bounds.x + leading,
                                       baseline_block=candidate.bounds.y + float(font_size),
                                       typography_role=provisional.typography_role, theme_tokens=request.theme_tokens,
                                       font_metrics=request.font_metrics, collision_region=provisional.collision_region,
                                       collision_domain=provisional.collision_domain, semantic_id=provisional.semantic_id,
                                       lane_row_id=provisional.lane_row_id,
                                       lane_member_id=provisional.lane_member_id,
                                       lane_source_kind=provisional.lane_source_kind,
                                       overflow="visible-overflow" if visible_overflow else "fit",
                                       lines=lines), fallback_ladder=fallback_ladder, selected_rung=candidate.side,
                                      host_placement_id=(host.placement_id if candidate.side == "inside" and host is not None else None),
                                      paint_order=max(HOSTED_TEXT_PAINT_ORDER, host.paint_order + 1)
                                      if candidate.side == "inside" and host is not None else FOREGROUND_TEXT_PAINT_ORDER)
                text.append(placed_text)
                register_rect(placed_text.placement_id, "text", placed_text.collision_domain.slot, placed_text.bounds)
                surface_obstacles.add(SurfaceObstacle(f"label-footprint:{placed_text.placement_id}", "label-visual",
                                                      placed_text.collision_domain.slot,
                                                      ObstacleRect(chip_box.x, chip_box.y,
                                                                   chip_box.right, chip_box.bottom)))
                if chip is not None:
                    shapes.append(ShapePlacement(
                        f"chip:{placed_text.placement_id}", placed_text.source_ref, "Rect",
                        Rect(Decimal(str(chip_box.x)), Decimal(str(chip_box.y)),
                             Decimal(str(chip_box.width)), Decimal(str(chip_box.height))),
                        required=False, slot_id=text_slot(placed_text),
                        paint_order=placed_text.paint_order - 1,
                        semantic_id=chip_semantic,
                        corner_radius=float(chip[1]) * chip_box.height,
                        lane_row_id=placed_text.lane_row_id,
                        lane_member_id=placed_text.lane_member_id))
                if visible_overflow:
                    visible_label_overflows.append((placed_text, slot_bounds))
                if visuals:
                    if not hasattr(label_metrics, "cap_height_at"):
                        raise LayoutError("E_FONT_METRICS_CAP_HEIGHT", next(visual.source_ref for visual, _, _, _ in visuals))
                    cap_height = float(label_metrics.cap_height_at(float(font_size)))
                    for visual, icon, width, gap in visuals:
                        inline = (candidate.bounds.x if visual.side == "leading"
                                  else candidate.bounds.x + leading + text_width + trailing - gap - width)
                        bounds = Rect(Decimal(str(inline)), Decimal(str(placed_text.baseline[1] - cap_height
                                                                           + (cap_height - float(font_size)) / 2)),
                                      Decimal(str(width)), Decimal(str(float(font_size))))
                        candidate_icons.append(IconPlacement(f"visual:{placed_text.placement_id}:{visual.side}",
                                                             placed_text.source_ref, visual.source_ref, icon.icon_id,
                                                             icon.kind, icon.content_identity, icon.viewport, icon.payload,
                                                             icon.alternative, visual.decorative, bounds, "labelVisual",
                                                             width / icon.viewport[0], text_slot(placed_text),
                                                             paint_order=placed_text.paint_order,
                                                             lane_row_id=placed_text.lane_row_id,
                                                             lane_member_id=placed_text.lane_member_id,
                                                             host_placement_id=placed_text.placement_id))
                placement_decisions.append(PlacementDecision(label_request.placement_id, label_request.source_ref,
                                                             fallback_ladder, candidate.side, "placed",
                                                             candidate.search_count))

    def before_relations(item: LabelRequest) -> bool:
        return (item.rule_host_obstacle_id is not None
                or (projection.lane_membership is not None and item.semantic_id == "memberLabel"))

    place_requested_labels(tuple(item for item in label_requests if before_relations(item)))

    relations: list[RelationPlacement] = []
    visible_route_fallbacks: list[RelationPlacement] = []
    instance_anchors: dict[str, list[tuple[str, tuple[float, float]]]] = {}
    instance_rows: dict[str, str] = {}
    for review_row, row in zip(review_rows, rows, strict=True):
        fallback = (float(row.bounds.inline + row.bounds.inline_size),
                    float(row.bounds.block + row.bounds.block_size / 2))
        for item in review_row.items:
            instance_id = f"{review_row.row_id}:{item.item_id or item.object_id}" if projection.rows else item.object_id
            instance_anchors.setdefault(item.object_id, []).append((instance_id, fallback))
            instance_rows[instance_id] = review_row.row_id
    for folded in getattr(projection, "folded_points", ()):
        instance_id = _folded_instance_id(folded, folded.item)
        mark = next((item for item in marks if item.placement_id == f"planned:{instance_id}"), None)
        if mark is not None:
            instance_anchors.setdefault(folded.item.object_id, []).append((instance_id, mark.end_port))
            instance_rows[instance_id] = f"group-header:{folded.group_id}"
    relation_marks = {mark.placement_id.removeprefix("planned:"): mark
                      for mark in marks if mark.placement_id.startswith("planned:")}
    comparison_clusters: dict[tuple[str, str], tuple[MarkPlacement, ...]] = {}
    for mark in marks:
        instance_id = mark.placement_id.split(":", 1)[1]
        row_id = instance_rows.get(instance_id)
        if row_id is not None:
            key = (mark.source_ref, row_id)
            comparison_clusters[key] = (*comparison_clusters.get(key, ()), mark)

    def combined_connector_points(source: ConnectorEgress, middle: tuple[tuple[float, float], ...],
                                  target: ConnectorEgress) -> tuple[tuple[float, float], ...]:
        pieces = (*source.corridor, *middle, *reversed(target.corridor))
        completed: list[tuple[float, float]] = []
        for point in pieces:
            if not completed or completed[-1] != point:
                completed.append(point)
        return tuple(completed)
    route_top = min((float(group.header_bounds.block) for group in groups if group.header_bounds is not None),
                    default=timeline_bounds[1])
    route_bottom = max((timeline_bounds[1] + timeline_bounds[3],
                        *(float(group.header_bounds.block + group.header_bounds.block_size)
                          for group in groups if group.header_bounds is not None)))
    for relation in request.surface_content.relations:
        source, target, relation_id = relation.source_object_id, relation.target_object_id, relation.relation_id
        for source_id, source_anchor in instance_anchors.get(str(source), ()):
            for target_id, target_anchor in instance_anchors.get(str(target), ()):
                source_mark, target_mark = relation_marks.get(source_id), relation_marks.get(target_id)
                source_nominal = (source_mark.start_port if relation.source_endpoint in {"start", "at"}
                                  else source_mark.end_port) if source_mark is not None else source_anchor
                target_nominal = (target_mark.start_port if relation.target_endpoint in {"start", "at"}
                                  else target_mark.end_port) if target_mark is not None else target_anchor
                scene_id = f"relation:{relation_id}:{source_id}:{target_id}" if projection.rows else f"relation:{relation_id}"
                source_candidates = (connector_egress_candidates(
                    source_mark, relation.source_endpoint, target_nominal,
                    comparison_clusters.get((source_mark.source_ref, instance_rows[source_id]), ()))
                    if source_mark is not None else (ConnectorEgress(relation.source_endpoint, source_nominal,
                                                                    source_nominal, ()),))
                target_candidates = (connector_egress_candidates(
                    target_mark, relation.target_endpoint, source_nominal,
                    comparison_clusters.get((target_mark.source_ref, instance_rows[target_id]), ()))
                    if target_mark is not None else (ConnectorEgress(relation.target_endpoint, target_nominal,
                                                                    target_nominal, ()),))
                port_pairs = tuple((source_candidate, target_candidate)
                                   for source_candidate in source_candidates
                                   for target_candidate in target_candidates)
                selected_pair: tuple[ConnectorEgress, ConnectorEgress] | None = None
                points: tuple[tuple[float, float], ...] = ()
                # Semantic relation variants may share/cross a path; their
                # routes remain obstacles for later annotations, not peers.
                route_classes = ("mark", "text", "label-visual")
                lane_selection = None
                if projection.lane_membership is not None:
                    lane_selection = select_lane_relation_route(
                        port_pairs, obstacles=surface_obstacles,
                        bounds=(timeline_bounds[0], route_top,
                                timeline_bounds[0] + timeline_bounds[2], route_bottom),
                        source_host_id=source_mark.placement_id if source_mark else None,
                        target_host_id=target_mark.placement_id if target_mark else None,
                        relation_scene_id=scene_id,
                        max_bends=layout_manifest.relation_max_bends,
                        max_detour_ratio=layout_manifest.relation_max_detour_ratio,
                        classes=route_classes,
                    )
                    selected_pair, points = lane_selection.selected_pair, lane_selection.points
                else:
                    for source_egress, target_egress in port_pairs:
                        if any(surface_obstacles.egress_collisions(
                                ObstacleSegment(*egress.corridor), host_ids=egress.host_ids,
                                classes=route_classes, regions=("timeline", "group-header"))
                               for egress in (source_egress, target_egress) if egress.corridor):
                            continue
                        source_port, target_port = source_egress.exposed_port, target_egress.exposed_port
                        source_obstacle_id = f"port:{source_mark.placement_id if source_mark else scene_id}:{source_egress.side}"
                        target_obstacle_id = f"port:{target_mark.placement_id if target_mark else scene_id}:{target_egress.side}"
                        existing_ports = tuple(port_id for port_id in (source_obstacle_id, target_obstacle_id)
                                               if surface_obstacles.has(port_id))
                        try:
                            middle = ((source_port,) if source_port == target_port else place_relation_route(
                                source_port=source_port, target_port=target_port, obstacles=surface_obstacles,
                                regions=("timeline", "group-header"), classes=route_classes,
                                port_ids=existing_ports,
                                bounds=(timeline_bounds[0], route_top,
                                        timeline_bounds[0] + timeline_bounds[2], route_bottom)))
                        except RouteSearchFailure:
                            continue
                        candidate_points = combined_connector_points(source_egress, middle, target_egress)
                        if len(candidate_points) < 2:
                            continue
                        if relation_route_quality(candidate_points, max_bends=layout_manifest.relation_max_bends,
                                                  max_detour_ratio=layout_manifest.relation_max_detour_ratio):
                            selected_pair, points = (source_egress, target_egress), candidate_points
                            break
                fallback = selected_pair is None
                if fallback:
                    if request.surface_content.relation_overflow == "suppress":
                        relations.append(RelationPlacement(scene_id, f"{source_id}:{relation.source_endpoint}",
                                                           f"{target_id}:{relation.target_endpoint}",
                                                           suppressed=True, diagnostic="W_LAYOUT_RELATION_SUPPRESSED"))
                        diagnostics.append(f"W_LAYOUT_RELATION_SUPPRESSED:{scene_id}")
                        if lane_selection is not None:
                            diagnostics.append(RouteSuppressionEvidence(scene_id, lane_selection.attempts).diagnostic)
                        continue
                    selected_pair = port_pairs[0]
                    first_source, first_target = selected_pair
                    points = ((first_source.semantic_port, first_target.semantic_port)
                              if first_source.semantic_port != first_target.semantic_port
                              else (first_source.semantic_port,
                                    (first_source.semantic_port[0] + 1.0, first_source.semantic_port[1])))
                    if (lane_selection is not None
                            and not _lane_fallback_clears_required_labels(points, tuple(text))):
                        relations.append(RelationPlacement(scene_id, f"{source_id}:{relation.source_endpoint}",
                                                           f"{target_id}:{relation.target_endpoint}",
                                                           suppressed=True, diagnostic="W_LAYOUT_RELATION_SUPPRESSED"))
                        diagnostics.append(f"W_LAYOUT_RELATION_SUPPRESSED:{scene_id}")
                        diagnostics.append(RouteSuppressionEvidence(scene_id, lane_selection.attempts).diagnostic)
                        continue
                source_egress, target_egress = selected_pair
                source_port_id = f"{source_id}:{relation.source_endpoint}:{source_egress.side}"
                target_port_id = f"{target_id}:{relation.target_endpoint}:{target_egress.side}"
                for mark, side, port in ((source_mark, source_egress.side, source_egress.exposed_port),
                                         (target_mark, target_egress.side, target_egress.exposed_port)):
                    obstacle_id = f"port:{mark.placement_id if mark else scene_id}:{side}"
                    if not surface_obstacles.has(obstacle_id):
                        register_port(obstacle_id, port, "timeline")
                relation_radius = float(metric_values.get("timeline.relation.cornerRadius", 0))
                placed = RelationPlacement(scene_id, source_port_id, target_port_id, tuple(points),
                                           semantic_id=relation.semantic_id,
                                           corner_radius=relation_radius,
                                           path_commands=(rounded_orthogonal_path(tuple(points), relation_radius)
                                                          if relation_radius > 0 and not fallback else ()),
                                           marker_start=marker_geometry(request.theme_tokens.marker("relationSourceTerminal")),
                                           marker_end=marker_geometry(request.theme_tokens.marker("relationTargetTerminal")),
                                           label_content=relation_label_content(relation), source_ref=relation_id)
                relations.append(placed)
                dependency_role = semantic_binding(placed.semantic_id).theme_role
                register_path(scene_id, "dependency-route", "timeline", placed.points,
                              stroke_width=float(request.theme_tokens.number(dependency_role, "strokeWidth")))
                if fallback:
                    visible_route_fallbacks.append(placed)

    # Relation labels are routed facts, not a Scene or adapter policy.  They run
    # after relation paths exist so their anchor is a stable completed segment.
    place_requested_labels(tuple(item for item in label_requests if not before_relations(item)))

    for placed_relation in relations:
        if placed_relation.suppressed:
            continue
        content = placed_relation.label_content
        if not content:
            continue
        relation_treatment = request.theme_tokens.text_treatment("annotation")
        relation_metrics = metric_for("annotation")
        font_size, line_height = relation_treatment.font_size, relation_treatment.line_height
        size = (measure_text_width(content, font_size=float(font_size), font_metrics=relation_metrics,
                                   letter_spacing=float(relation_treatment.letter_spacing),
                                   text_transform=relation_treatment.transform),
                float(font_size) * float(line_height))
        relation_text_id = f"relation-label:{placed_relation.relation_id.removeprefix('relation:')}"
        candidate = place_label(relation_label_anchor(placed_relation.points), size, ("above", "below", "start", "end"),
                                bounds=timeline_rect, obstacles=surface_obstacles, gap=max(1.0, float(font_size) * 0.25),
                                required=False, overflow=request.surface_content.relation_overflow,
                                classes=("mark", "text", "label-visual", "dependency-route"))
        if candidate is None:
            diagnostics.append(f"W_LAYOUT_RELATION_LABEL_SUPPRESSED:{placed_relation.relation_id}")
            continue
        placed_text = replace(place_text(placement_id=relation_text_id, source_ref=placed_relation.source_ref,
                                       content=content, inline=candidate.bounds.x,
                                       baseline_block=candidate.bounds.y + float(font_size), typography_role="annotation",
                                       theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                       collision_region="relation-label", collision_domain=CollisionDomain("timeline", "overlay")),
                            fallback_ladder=("above", "below", "start", "end"), selected_rung=candidate.side)
        text.append(placed_text)
        register_rect(placed_text.placement_id, "text", "timeline", placed_text.bounds)
        if candidate.visible_overflow:
            visible_label_overflows.append((placed_text, timeline_rect))

    side_content_warnings: list[FitWarning] = []
    legend = by_source.get("legend")
    if legend:
        legend_treatment = request.theme_tokens.text_treatment("legend")
        legend_size = float(legend_treatment.font_size)
        legend_step = legend_size * float(legend_treatment.line_height)
        text_line_block = legend_size * float(legend_treatment.line_height)
        mark_block_size = float(metric_values["timeline.mark.blockSize"])
        legacy_swatch_size = max(2.0, legend_size * 0.8)
        declared_inline = request.theme_tokens.optional_number("legend-swatch", "swatchInlineSize")
        fallback_inline = float(declared_inline) if declared_inline is not None else legacy_swatch_size
        # Today's fixed swatch->label offset was `swatch_size * 1.5`, i.e. one
        # swatch width plus a "gap" of exactly half a swatch; reproduce that
        # split so an unmigrated (no declared `gap`) legend slot lays out
        # byte-identically to before this change (#427).
        gap = float(legend.gap) if legend.gap is not None else legacy_swatch_size * 0.5
        direction = legend.direction
        item_min_inline = float(legend.item_min_inline_size) if legend.item_min_inline_size is not None else None

        def swatch_geometry(role: str) -> tuple[float, float, str]:
            """Return one legend entry's (inline size, block size, dispatch bucket) (#427).

            The size is the role's own mark geometry against the document's own
            `timeline.mark.blockSize` for a `mark`/`point` role -- literally the
            size the chart draws it -- or `legend-swatch.swatchInlineSize` (or its
            documented fallback) for a role with no single on-chart length. A
            role this table does not recognize keeps today's fixed square.
            """
            if role == "milestone":
                height_ratio, *_ = request.theme_tokens.mark_geometry("planned")
                side = float(height_ratio) * mark_block_size
                return side, side, "point"
            if role in MARK_GEOMETRY_ROLES:
                return fallback_inline, float(request.theme_tokens.mark_geometry(role)[0]) * mark_block_size, "mark"
            if role in ("asOf", "dependency", "dependency-critical"):
                return fallback_inline, text_line_block, "line"
            return legacy_swatch_size, legacy_swatch_size, "legacy"

        def emit_swatch(role: str, x: float, y: float, width: float, height: float, bucket: str) -> None:
            if bucket == "point":
                bounds = Rect(Decimal(str(x)), Decimal(str(y)), Decimal(str(width)), Decimal(str(height)))
                parts = symbol_parts(request.theme_tokens.variant_symbol("planned"), (x, y, width, height))
                marks.append(MarkPlacement(f"legend-swatch:{role}", role,
                                           bounds,
                                           (x + width / 2, y + height / 2), (x + width / 2, y + height / 2),
                                           mark_shape="point", slot_id=legend.slot_id, semantic_id="planned",
                                           symbol_parts=parts))
            elif bucket == "mark":
                height_ratio, offset_ratio, paint_order, corner_ratio = request.theme_tokens.mark_geometry(role)
                corner_radius = min(float(corner_ratio) * min(width, height), min(width, height) / 2)
                shapes.append(ShapePlacement(f"legend-swatch:{role}", role, "Rect",
                                             Rect(Decimal(str(x)), Decimal(str(y)), Decimal(str(width)), Decimal(str(height))),
                                             slot_id=legend.slot_id, corner_radius=corner_radius, paint_order=paint_order))
            elif bucket == "line":
                marker_token = request.theme_tokens.optional_token(role, "marker", "marker")
                relations.append(RelationPlacement(f"legend-swatch:{role}", f"legend-swatch:{role}:start",
                                                   f"legend-swatch:{role}:end",
                                                   points=((x, y + height / 2), (x + width, y + height / 2)),
                                                   semantic_id=role, slot_id=legend.slot_id, source_ref=role,
                                                   marker_end=marker_geometry(marker_token) if marker_token else None))
            else:
                shapes.append(ShapePlacement(f"legend-swatch:{role}", role, "Rect",
                                             Rect(Decimal(str(x)), Decimal(str(y)), Decimal(str(width)), Decimal(str(height))),
                                             slot_id=legend.slot_id))

        def emit_label(role: str, label: str, x: float, baseline: float, available: float) -> float:
            natural_width = measure_text_width(label, font_size=legend_size, font_metrics=metric_for("legend"),
                                               letter_spacing=float(legend_treatment.letter_spacing),
                                               text_transform=legend_treatment.transform,
                                               numeric_spacing=legend_treatment.numeric_spacing)
            content = label
            disposition = "fit"
            if natural_width > available and legend.overflow == "ellipsize-with-source":
                content = ellipsize_text(label, available_inline=available, font_size=legend_size,
                                         font_metrics=metric_for("legend"),
                                         letter_spacing=float(legend_treatment.letter_spacing),
                                         text_transform=legend_treatment.transform,
                                         numeric_spacing=legend_treatment.numeric_spacing)
                disposition = "ellipsized"
            elif natural_width > available and legend.overflow == "visible-overflow":
                disposition = "visible-overflow"
            placed = place_text(placement_id=f"legend:{role}", source_ref=role, content=content,
                                inline=x, baseline_block=baseline, typography_role="legend",
                                theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                overflow=disposition, collision_region="legend",
                                collision_domain=CollisionDomain("legend", "content"), source_content=label,
                                available_inline_start=x, available_inline_size=available)
            text.append(placed)
            if disposition == "visible-overflow":
                side_content_warnings.append(FitWarning(
                    "W_LAYOUT_VISIBLE_OVERFLOW", placed.placement_id, role, "legend-text", "visible-overflow",
                    natural_width, float(placed.bounds.block_size), available, float(legend.bounds.block_size),
                ))
            return placed.bounds.block + placed.bounds.block_size

        final_legend_end = legend.bounds.block
        if direction == "inline":
            x = float(legend.bounds.inline)
            y = float(legend.bounds.block)
            row_height = 0.0
            slot_end = float(legend.bounds.inline) + float(legend.bounds.inline_size)
            for role, label in request.surface_content.legend_entries:
                width, height, bucket = swatch_geometry(role)
                if item_min_inline is not None and x > float(legend.bounds.inline) and slot_end - x < item_min_inline:
                    y += row_height + gap
                    x = float(legend.bounds.inline)
                    row_height = 0.0
                emit_swatch(role, x, y, width, height, bucket)
                label_end = emit_label(role, label, x + width + gap, y + legend_size, max(0.0, slot_end - (x + width + gap)))
                row_height = max(row_height, height, text_line_block)
                final_legend_end = max(final_legend_end, Decimal(str(label_end)), Decimal(str(y + row_height)))
                x += width + gap + measure_text_width(label, font_size=legend_size, font_metrics=metric_for("legend"),
                                                       letter_spacing=float(legend_treatment.letter_spacing),
                                                       text_transform=legend_treatment.transform,
                                                       numeric_spacing=legend_treatment.numeric_spacing) + gap
        else:
            cursor = float(legend.bounds.block)
            for role, label in request.surface_content.legend_entries:
                width, height, bucket = swatch_geometry(role)
                row_height = max(height, text_line_block)
                swatch_top = cursor + (row_height - height) / 2.0
                baseline = cursor + (row_height - text_line_block) / 2.0 + legend_size
                text_inline = float(legend.bounds.inline) + width + gap
                text_available = max(0.0, float(legend.bounds.inline_size) - width - gap)
                emit_swatch(role, float(legend.bounds.inline), swatch_top, width, height, bucket)
                label_end = emit_label(role, label, text_inline, baseline, text_available)
                final_legend_end = max(final_legend_end, Decimal(str(label_end)))
                cursor += row_height + gap
        final_size = max(legend.bounds.block_size, final_legend_end - legend.bounds.block)
        replacement = replace(legend, bounds=Rect(legend.bounds.inline, legend.bounds.block,
                                                   legend.bounds.inline_size, final_size))
        slots = tuple(replacement if slot.source_ref == "legend" else slot for slot in slots)
    notes = by_source.get("notes")
    if notes:
        cursor = notes.bounds.block
        for index, (source, content) in enumerate(request.surface_content.notes):
            placed = place_text(placement_id=f"note:{source}", source_ref=source, content=content,
                                inline=float(notes.bounds.inline), baseline_block=float(cursor) + body_size,
                                typography_role="text", theme_tokens=request.theme_tokens,
                                font_metrics=request.font_metrics, collision_region=f"notes:{source}",
                                collision_domain=CollisionDomain("notes", f"line:{index}"), source_content=content,
                                available_inline_start=float(notes.bounds.inline),
                                available_inline_size=float(notes.bounds.inline_size))
            text.append(placed)
            cursor = placed.bounds.block + placed.bounds.block_size
        final_size = max(notes.bounds.block_size, cursor - notes.bounds.block)
        replacement = replace(notes, bounds=Rect(notes.bounds.inline, notes.bounds.block,
                                                  notes.bounds.inline_size, final_size))
        slots = tuple(replacement if slot.source_ref == "notes" else slot for slot in slots)
    slots = _complete_footer_band(provisional_slots=footer_provisional_slots, completed_slots=slots)
    by_source = {slot.source_ref: slot for slot in slots}
    summary_slot = by_source.get("summary")
    if summary_slot:
        cursor = float(summary_slot.bounds.block)
        for run in request.surface_content.summary.runs:
            summary_treatment = request.theme_tokens.text_treatment(run.typography_role)
            font_size, line_height = summary_treatment.font_size, summary_treatment.line_height
            text.append(place_text(placement_id=run.placement_id, source_ref=run.source_ref, content=run.content,
                                   inline=float(summary_slot.bounds.inline), baseline_block=cursor + float(font_size),
                                   typography_role=run.typography_role, theme_tokens=request.theme_tokens,
                                   font_metrics=request.font_metrics, collision_region="summary",
                                   collision_domain=CollisionDomain("summary", "content"), source_content=run.content,
                                   available_inline_start=float(summary_slot.bounds.inline),
                                   available_inline_size=float(summary_slot.bounds.inline_size)))
            cursor += float(font_size) * float(line_height)

    annotation_slot = by_source.get("annotations")
    annotation_slot_id = annotation_slot.slot_id if annotation_slot is not None else ""
    if annotation_slot or request.surface_content.annotations:
        annotation_marks = _comparison_marks(projection)
        for index, annotation in enumerate(request.surface_content.annotations):
            presentation = annotation_presentation(annotation.purpose)
            annotation_id, content = annotation.annotation_id, annotation.content
            content = f"{annotation.number}. {content}" if annotation.number is not None else content
            annotation_visuals = candidate_label_visuals(f"annotation-text:{annotation_id}", "annotation", request)
            handled_candidate_visuals.update(visual.source_ref for visual, _, _, _ in annotation_visuals)
            annotation_leading = geometry_sum(width + gap for visual, icon, width, gap in annotation_visuals if visual.side == "leading")
            annotation_trailing = geometry_sum(width + gap for visual, icon, width, gap in annotation_visuals if visual.side == "trailing")
            resolved = resolve_annotation_anchor(annotation, annotation_marks)
            matching = [(review_row, row) for review_row, row in zip(review_rows, rows, strict=True)
                        if any(item.object_id == resolved.object_id for item in review_row.items)]
            anchor = annotation.anchor
            row_id, item_id = anchor.get("rowId"), anchor.get("itemId")
            if row_id is not None or item_id is not None:
                matching = [(review_row, row) for review_row, row in matching
                            if (row_id is None or review_row.row_id == row_id)
                            and (item_id is None or any(item.item_id == item_id and item.object_id == resolved.object_id for item in review_row.items))]
            folded_matches = [(folded, mark_by_id.get(f"{resolved.facet}:{_folded_instance_id(folded, folded.item)}"))
                              for folded in getattr(projection, "folded_points", ())
                              if folded.item.object_id == resolved.object_id]
            if row_id is not None or item_id is not None:
                folded_matches = [(folded, mark) for folded, mark in folded_matches
                                  if (row_id is None or row_id == f"group-header:{folded.group_id}:{folded.item.object_id}")
                                  and (item_id is None or item_id == folded.item.item_id)]
            if len(matching) + len(folded_matches) > 1:
                raise LayoutError("E_PRESENTATION_ROW_ANCHOR_AMBIGUOUS", f"/annotations/{index}/anchor")
            if matching:
                anchor_bounds = _annotation_anchor_bounds(resolved.mark, resolved.endpoint, matching[0][1], scale)
                selected_items = tuple(item for item in matching[0][0].items
                                       if item.object_id == resolved.object_id and (item_id is None or item.item_id == item_id))
                anchor_item = selected_items[0] if selected_items else None
                anchor_instance_id = ((f"{matching[0][0].row_id}:{anchor_item.item_id or anchor_item.object_id}"
                                       if projection.rows else anchor_item.object_id)
                                      if anchor_item is not None else "")
                anchor_host = mark_by_id.get(f"{resolved.facet}:{anchor_instance_id}")
            elif folded_matches and folded_matches[0][1] is not None:
                folded, mark = folded_matches[0]
                anchor_bounds = LabelRect(*_bounds(mark.bounds))
                selected_items = (folded.item,)
                anchor_host = mark
            else:
                raise LayoutError("E_PRESENTATION_ANCHOR_MISSING", f"/annotations/{index}/anchor")
            as_of_side_constraint: tuple[float, str] | None = None
            if contract.time.as_of is not None and start <= contract.time.as_of < end:
                as_of_x = _coordinate(contract.time.as_of, scale)
                as_of_side_constraint = (as_of_x, "start" if anchor_bounds.x < as_of_x else "end")
            annotation_text_role = semantic_binding(presentation.text_semantic_id).theme_role
            annotation_treatment = request.theme_tokens.text_treatment(annotation_text_role)
            annotation_metrics = metric_for(annotation_text_role)
            size, line_height = float(annotation_treatment.font_size), float(annotation_treatment.line_height)
            if annotation_slot is not None:
                text_available = max(1.0, float(annotation_slot.bounds.inline_size) - annotation_leading - annotation_trailing)
            else:
                # A plot/content-only candidate list declares its own text
                # width bound (#466); an annotation with no annotations slot
                # must declare at least one bounded nearest-free/adjacent
                # candidate.
                declared_max_em = max((candidate.search.max_inline_em for candidate in annotation.candidates
                                       if candidate.search.max_inline_em is not None), default=None)
                if declared_max_em is None:
                    raise LayoutError("E_LAYOUT_ANNOTATION_WIDTH_UNBOUNDED", f"/annotations/{index}")
                text_available = max(1.0, declared_max_em * size - annotation_leading - annotation_trailing)
            text_width = min(text_available, max(size * 4, measure_text_width(
                content, font_size=size, font_metrics=annotation_metrics,
                letter_spacing=float(annotation_treatment.letter_spacing), text_transform=annotation_treatment.transform)))
            width = annotation_leading + text_width + annotation_trailing
            annotation_lines = (content,)
            annotation_search_count = 0
            selected_leader: tuple[ConnectorEgress, AnnotationRouteTrial,
                                   tuple[tuple[float, float], ...],
                                   tuple[tuple[float, float], ...]] | None = None

            def trial_leader(candidate_box: Any, rung: str
                             ) -> tuple[ConnectorEgress, AnnotationRouteTrial,
                                        tuple[tuple[float, float], ...],
                                        tuple[tuple[float, float], ...]] | None:
                nonlocal annotation_search_count
                if not candidate_box.leader_required or presentation.leader_semantic_id is None:
                    return None
                if anchor_host is None:
                    raise LayoutError("E_PRESENTATION_ANCHOR_MISSING", f"/annotations/{index}/anchor")
                candidate_bounds = candidate_box.placement.bounds
                target = nearest_box_port(candidate_bounds,
                                          (anchor_bounds.x + anchor_bounds.width / 2,
                                           anchor_bounds.y + anchor_bounds.height / 2))
                anchor_instance = anchor_host.placement_id.split(":", 1)[1]
                anchor_row = instance_rows.get(anchor_instance)
                source_candidates = connector_egress_candidates(
                    anchor_host, resolved.endpoint, target,
                    comparison_clusters.get((anchor_host.source_ref, anchor_row), (anchor_host,)))
                viewport = request.layout_manifest.viewport
                content_extent = (float(viewport.inline), float(viewport.block),
                                  max(float(viewport.inline + viewport.inline_size), candidate_bounds.right),
                                  max(float(viewport.block + viewport.block_size), candidate_bounds.bottom))
                route_bounds = local_route_bounds(
                    _bounds(anchor_host.bounds),
                    (candidate_bounds.x, candidate_bounds.y, candidate_bounds.width, candidate_bounds.height),
                    target, content_extent)
                connector_stroke_width = float(request.theme_tokens.number(
                    semantic_binding(presentation.leader_semantic_id).theme_role, "strokeWidth"))
                route_specs: list[tuple[ConnectorEgress, tuple[tuple[float, float], ...], tuple[str, ...]]] = []
                for source_egress in source_candidates:
                    source_port_id = f"port:{anchor_host.placement_id}:{source_egress.side}"
                    known_ports = coincident_endpoint_port_ids(
                        surface_obstacles, source_egress.exposed_port, source_egress.host_ids)
                    known_ports = tuple(dict.fromkeys((*known_ports, *coincident_endpoint_port_ids(
                        surface_obstacles, source_egress.semantic_port, source_egress.host_ids))))
                    if surface_obstacles.has(source_port_id) and source_port_id not in known_ports:
                        known_ports = (*known_ports, source_port_id)
                    if source_egress.corridor and surface_obstacles.egress_collisions(
                            ObstacleSegment(*source_egress.corridor), host_ids=source_egress.host_ids,
                            port_ids=known_ports):
                        continue
                    base_prefix = (source_egress.corridor if source_egress.corridor
                                   else (source_egress.semantic_port,))
                    # Clear the entire possible bridge gap before turning
                    # back across a dependency from the same endpoint.
                    fanout_deltas = ((6.0, 0.0), (-6.0, 0.0), (0.0, 6.0), (0.0, -6.0))
                    prefixes = (base_prefix, *(tuple((*base_prefix,
                                                      (source_egress.exposed_port[0] + dx,
                                                       source_egress.exposed_port[1] + dy)))
                                                for dx, dy in fanout_deltas))
                    for prefix in prefixes:
                        if len(prefix) > len(base_prefix):
                            stub = ObstacleSegment(source_egress.exposed_port, prefix[-1])
                            if (surface_obstacles.egress_collisions(
                                    stub, host_ids=source_egress.host_ids, port_ids=known_ports)
                                    or any(item.placement_id in source_egress.host_ids
                                           for item in surface_obstacles.collisions(stub, classes=("mark",)))):
                                continue
                        route_specs.append((source_egress, tuple(prefix), known_ports))
                # Probe every finite sparse endpoint before spending the
                # dense-grid budget on any one poor endpoint.
                for dense_search, candidates in ((False, route_specs), (True, route_specs[:2])):
                    for source_egress, prefix, known_ports in candidates:
                        annotation_search_count += 1
                        trial = route_annotation_candidate(
                            prefix[-1], target, surface_obstacles,
                            bounds=route_bounds, port_ids=known_ports,
                            max_bends=layout_manifest.annotation_max_bends,
                            max_detour_ratio=layout_manifest.annotation_max_detour_ratio,
                            allow_bridge=rung == "rail", dense=dense_search,
                            connector_stroke_width=connector_stroke_width)
                        if trial is None:
                            continue
                        full_points = (*prefix[:-1], *trial.points)
                        if relation_route_quality(full_points, max_bends=layout_manifest.annotation_max_bends,
                                                  max_detour_ratio=layout_manifest.annotation_max_detour_ratio):
                            return source_egress, trial, tuple(full_points), tuple(prefix)
                return None

            tail_tip: tuple[float, float] | None = None
            container = None
            content_top = content_right = content_bottom = content_left = 0.0
            try:
                if annotation.purpose in {"callout", "highlight", "note", "explanatory-arrow"}:
                    intent = selected_items[0].presentation if selected_items else None
                    preferred = ((intent or {}).get("callout") or {}).get("placement") if isinstance(intent, dict) else None
                    wrap = ((intent or {}).get("text") or {}).get("wrap", "forbid") if isinstance(intent, dict) else "forbid"
                    # A declared candidate's maxInlineEm is a text-width bound
                    # for a plot/content search (#466): it forces wrapping so
                    # a long note becomes a narrow, tall box rather than one
                    # too wide to fit any free lattice position.
                    plot_wrap_em = max((candidate.search.max_inline_em for candidate in annotation.candidates
                                        if candidate.search.max_inline_em is not None), default=None)
                    wrap_available = float(plot_wrap_em) * size if plot_wrap_em is not None else text_available
                    if plot_wrap_em is not None:
                        wrap = "allow"
                    annotation_lines = (wrap_text(content, available_inline=wrap_available, font_size=size, font_metrics=annotation_metrics,
                                                  letter_spacing=float(annotation_treatment.letter_spacing),
                                                  text_transform=annotation_treatment.transform)
                                        if wrap == "allow" else (content,))
                    text_width = max(measure_text_width(line, font_size=size, font_metrics=annotation_metrics,
                                                        letter_spacing=float(annotation_treatment.letter_spacing),
                                                        text_transform=annotation_treatment.transform)
                                     for line in annotation_lines)
                    annotation_box_role = semantic_binding(presentation.box_semantic_id).theme_role
                    container = request.theme_tokens.annotation_container(annotation_box_role)
                    # An image-backed container (#465) declares a content
                    # inset: Layout measures text into that smaller box, then
                    # expands it by the inset to the paint box the search and
                    # collision below actually use -- the box a rectangle or
                    # balloon container already uses today, unchanged.
                    content_top = content_right = content_bottom = content_left = 0.0
                    if container is not None and container.outline == "image":
                        content_top, content_right, content_bottom, content_left = (
                            float(value) * size for value in container.content_insets_em)
                    annotation_size = (annotation_leading + text_width + annotation_trailing + content_left + content_right,
                                       size * line_height * len(annotation_lines) + content_top + content_bottom)
                    candidates, ladder = candidate_order(annotation.candidates, annotation.purpose,
                                                          annotation.fallback_ladder, preferred)
                    box, selected_rung, tail_tip = None, None, None
                    for candidate in candidates:
                        rung = candidate.candidate_id
                        if candidate.search.kind == "row-aligned":
                            candidate_boxes = annotation_rail_candidates(
                                annotation, resolved, anchor_y=anchor_bounds.y + anchor_bounds.height / 2,
                                text_size=annotation_size, rail=LabelRect(*_bounds(annotation_slot.bounds)),
                                obstacles=surface_obstacles)
                            for candidate_box in candidate_boxes:
                                annotation_search_count += 1
                                leader_trial = trial_leader(candidate_box, rung)
                                if candidate_box.leader_required and presentation.leader_semantic_id is not None and leader_trial is None:
                                    continue
                                box, selected_rung, selected_leader = candidate_box, rung, leader_trial
                                break
                        elif candidate.search.kind == "nearest-free":
                            region_bounds = LabelRect(*_bounds(timeline.bounds))
                            host_id = anchor_host.placement_id if anchor_host is not None else None
                            if candidate.connector.kind == "tail":
                                if container is None or container.outline != "balloon":
                                    raise LayoutError("E_LAYOUT_ANNOTATION_TAIL_REQUIRES_BALLOON", f"/annotations/{index}")
                                corner_radius, tail_base = float(container.corner_radius) * size, float(container.tail_base) * size
                                free_box, trial_tip, trials = nearest_free_tail_box(
                                    region=region_bounds, anchor=anchor_bounds, box_size=annotation_size,
                                    max_positions=candidate.search.max_positions, obstacles=surface_obstacles,
                                    obstacle_classes=candidate.obstacles.classes, corner_radius=corner_radius,
                                    tail_base=tail_base, host_id=host_id, side_of_as_of=as_of_side_constraint)
                                annotation_search_count += trials
                                if free_box is not None:
                                    box = AnnotationBox(resolved, LabelPlacement(rung, free_box, False), False)
                                    selected_rung, tail_tip = rung, trial_tip
                            else:
                                anchor_center = (anchor_bounds.x + anchor_bounds.width / 2,
                                                 anchor_bounds.y + anchor_bounds.height / 2)
                                free_box, trials = nearest_free_box(
                                    region=region_bounds, anchor_center=anchor_center, box_size=annotation_size,
                                    max_positions=candidate.search.max_positions, obstacles=surface_obstacles,
                                    obstacle_classes=candidate.obstacles.classes, host_id=host_id,
                                    side_of_as_of=as_of_side_constraint)
                                annotation_search_count += trials
                                if free_box is not None:
                                    leader_required = candidate.connector.kind == "leader"
                                    candidate_box = AnnotationBox(resolved, LabelPlacement(rung, free_box, False), leader_required)
                                    leader_trial = trial_leader(candidate_box, rung) if leader_required else None
                                    if not (leader_required and presentation.leader_semantic_id is not None and leader_trial is None):
                                        box, selected_rung, selected_leader = candidate_box, rung, leader_trial
                        else:
                            candidate_box = project_annotation_box(
                                annotation, resolved, anchor_bounds=anchor_bounds, text_size=annotation_size,
                                candidate_sides=(rung,), viewport=LabelRect(*_bounds(annotation_slot.bounds)),
                                obstacles=surface_obstacles, overflow="clip-optional", required=False)
                            candidate_boxes = (candidate_box,) if candidate_box is not None else ()
                            for candidate_box in candidate_boxes:
                                annotation_search_count += 1
                                leader_trial = trial_leader(candidate_box, rung)
                                if candidate_box.leader_required and presentation.leader_semantic_id is not None and leader_trial is None:
                                    continue
                                box, selected_rung, selected_leader = candidate_box, rung, leader_trial
                                break
                        if box is not None:
                            break
                    if box is None:
                        if "suppress" in ladder:
                            placement_decisions.append(PlacementDecision(f"annotation:{annotation_id}", annotation_id,
                                                                         tuple(ladder), "suppress", "suppressed",
                                                                         search_count=annotation_search_count))
                            diagnostics.append(f"W_LAYOUT_ANNOTATION_SUPPRESSED:annotation:{annotation_id}")
                            continue
                        # A normal annotation is never silently suppressed or
                        # rejected.  Complete its first declared placement in
                        # visible-overflow mode after the explicit fit ladder
                        # has been exhausted.
                        selected_rung = next(rung for rung in ladder if rung != "suppress")
                        first_candidate = next((item for item in candidates if item.candidate_id == selected_rung), None)
                        if selected_rung == "rail":
                            box = place_annotation_rail(
                                annotation, resolved, anchor_y=anchor_bounds.y + anchor_bounds.height / 2,
                                text_size=annotation_size, rail=LabelRect(*_bounds(annotation_slot.bounds)),
                                obstacles=surface_obstacles, overflow="visible-overflow", required=True)
                        elif first_candidate is not None and first_candidate.search.kind == "nearest-free":
                            # #449 never refuses: complete the first declared
                            # candidate's own region at its nearest lattice
                            # position, visibly overflowing any obstacle.
                            region_bounds = LabelRect(*_bounds(timeline.bounds))
                            anchor_center = (anchor_bounds.x + anchor_bounds.width / 2,
                                             anchor_bounds.y + anchor_bounds.height / 2)
                            width, height = annotation_size
                            forced = LabelRect(min(max(anchor_center[0] - width / 2, region_bounds.x),
                                                   region_bounds.right - width),
                                               min(max(anchor_center[1] - height / 2, region_bounds.y),
                                                   region_bounds.bottom - height), width, height)
                            box = AnnotationBox(resolved, LabelPlacement(selected_rung, forced, True), False)
                        else:
                            box = project_annotation_box(
                                annotation, resolved, anchor_bounds=anchor_bounds, text_size=annotation_size,
                                candidate_sides=(selected_rung,), viewport=LabelRect(*_bounds(annotation_slot.bounds)),
                                obstacles=surface_obstacles, overflow="visible-overflow", required=True)
                        if box is None:  # Defensive: visible-overflow is a total Layout policy.
                            raise LayoutError("E_PRESENTATION_LABEL_UNPLACEABLE", f"/annotations/{index}")
                    placement_decisions.append(PlacementDecision(f"annotation:{annotation_id}", annotation_id,
                                                                 tuple(ladder), selected_rung, "placed",
                                                                 search_count=annotation_search_count,
                                                                 selected_topology=(selected_leader[1].topology
                                                                                    if selected_leader else None),
                                                                 crossing_ids=(selected_leader[1].crossing_ids
                                                                               if selected_leader else ())))
                else:
                    box = project_annotation_box(annotation, resolved, anchor_bounds=anchor_bounds, text_size=(width, size * line_height),
                                                 candidate_sides=(annotation.side,),
                                                 viewport=LabelRect(*_bounds(annotation_slot.bounds)), obstacles=surface_obstacles,
                                                 overflow=annotation_slot.overflow, required=annotation_slot.priority == "required")
            except ValueError as error:
                raise LayoutError(str(error), f"/annotations/{index}") from error
            if box is None:
                continue
            bounds = box.placement.bounds
            annotation_bounds = Rect(Decimal(str(bounds.x)), Decimal(str(bounds.y)),
                                     Decimal(str(bounds.width)), Decimal(str(bounds.height)))
            if tail_tip is not None:
                container = request.theme_tokens.annotation_container(
                    semantic_binding(presentation.box_semantic_id).theme_role)
                corner_radius, tail_base = float(container.corner_radius) * size, float(container.tail_base) * size
                outline = balloon_outline(bounds, tail_tip, corner_radius=corner_radius, tail_base=tail_base)
                shapes.append(ShapePlacement(f"annotation-box:{annotation_id}", annotation_id, "Balloon",
                                             annotation_bounds, path_commands=outline,
                                             semantic_id=presentation.box_semantic_id, annotation=presentation,
                                             paint_order=ANNOTATION_PAINT_ORDER))
            elif container is not None and container.outline == "image":
                icon = request.icon_assets.get(container.image_ref)
                if icon is None or icon.kind != "raster":
                    raise LayoutError("E_LAYOUT_ANNOTATION_IMAGE_UNRESOLVED", f"/annotations/{index}")
                slice_insets_px = tuple(float(value) * size for value in container.slice_insets_em)
                tiles = image_slice_tiles((bounds.x, bounds.y, bounds.width, bounds.height),
                                          viewport=icon.viewport, slice_insets=slice_insets_px)
                shapes.append(ShapePlacement(f"annotation-box:{annotation_id}", annotation_id, "Rect",
                                             annotation_bounds,
                                             semantic_id=presentation.box_semantic_id, annotation=presentation,
                                             paint_order=ANNOTATION_PAINT_ORDER,
                                             image_fill=LayoutImageFill(icon.content_identity, icon.viewport,
                                                                        icon.payload, tiles)))
            else:
                shapes.append(ShapePlacement(f"annotation-box:{annotation_id}", annotation_id, "Rect",
                                             annotation_bounds,
                                             semantic_id=presentation.box_semantic_id, annotation=presentation,
                                             paint_order=ANNOTATION_PAINT_ORDER))
            register_rect(f"annotation-box:{annotation_id}", "annotation-box", "annotations", annotation_bounds)
            annotation_text_slot = "annotations" if annotation_slot is not None else timeline.slot_id
            placed_annotation = place_text(placement_id=f"annotation-text:{annotation_id}", source_ref=annotation_id, content=content,
                                           inline=bounds.x + annotation_leading + content_left,
                                           baseline_block=bounds.y + content_top + size, typography_role=annotation_text_role,
                                           theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                           collision_region="annotations", collision_domain=CollisionDomain(annotation_text_slot, "content"),
                                           lines=annotation_lines, semantic_id=presentation.text_semantic_id,
                                           annotation=presentation)
            placed_annotation = replace(placed_annotation, paint_order=ANNOTATION_PAINT_ORDER + 1)
            text.append(placed_annotation)
            register_rect(placed_annotation.placement_id, "text", "annotations", placed_annotation.bounds)
            if box.placement.visible_overflow:
                overflow_viewport = (LabelRect(*_bounds(annotation_slot.bounds)) if annotation_slot is not None
                                     else LabelRect(*_bounds(timeline.bounds)))
                visible_label_overflows.append((placed_annotation, overflow_viewport))
            if annotation_visuals:
                if not hasattr(annotation_metrics, "cap_height_at"):
                    raise LayoutError("E_FONT_METRICS_CAP_HEIGHT", next(visual.source_ref for visual, _, _, _ in annotation_visuals))
                cap_height = float(annotation_metrics.cap_height_at(size))
                for visual, icon, icon_width, gap in annotation_visuals:
                    inline = (bounds.x if visual.side == "leading"
                              else bounds.x + annotation_leading + text_width + annotation_trailing - gap - icon_width)
                    icon_bounds = Rect(Decimal(str(inline)), Decimal(str(placed_annotation.baseline[1] - cap_height
                                                                          + (cap_height - size) / 2)),
                                       Decimal(str(icon_width)), Decimal(str(size)))
                    candidate_icons.append(IconPlacement(f"visual:{placed_annotation.placement_id}:{visual.side}",
                                                         annotation_id, visual.source_ref, icon.icon_id, icon.kind,
                                                         icon.content_identity, icon.viewport, icon.payload, icon.alternative,
                                                         visual.decorative, icon_bounds, "labelVisual",
                                                         icon_width / icon.viewport[0], annotation_slot_id,
                                                         paint_order=placed_annotation.paint_order))
            if annotation.number is not None:
                note_index_visuals = candidate_label_visuals(f"note-index:{annotation_id}", "annotation", request)
                handled_candidate_visuals.update(visual.source_ref for visual, _, _, _ in note_index_visuals)
                note_index_leading = geometry_sum(width + gap for visual, _, width, gap in note_index_visuals
                                                  if visual.side == "leading")
                note_index_trailing = geometry_sum(width + gap for visual, _, width, gap in note_index_visuals
                                                   if visual.side == "trailing")
                note_index_content = str(annotation.number)
                note_index_width = measure_text_width(note_index_content, font_size=size, font_metrics=annotation_metrics,
                                                      letter_spacing=float(annotation_treatment.letter_spacing),
                                                      text_transform=annotation_treatment.transform)
                note_index_size = (note_index_leading + note_index_width + note_index_trailing, size * line_height)
                note_index = place_label(
                    anchor_bounds, note_index_size, ("end", "start", "above", "below"),
                    bounds=LabelRect(*timeline_bounds), obstacles=surface_obstacles,
                    gap=max(1.0, size * 0.25), required=False, overflow="suppress",
                )
                if note_index is None:
                    diagnostics.append(f"W_LAYOUT_NOTE_INDEX_SUPPRESSED:{annotation_id}")
                else:
                    note_index_inline = note_index.bounds.x
                    note_index_text = place_text(placement_id=f"note-index:{annotation_id}", source_ref=annotation_id,
                                                 content=note_index_content, inline=note_index_inline + note_index_leading,
                                                 baseline_block=note_index.bounds.y + size, typography_role="annotation",
                                                 theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                                 collision_region="annotations",
                                                 collision_domain=CollisionDomain("timeline", "overlay"),
                                                 semantic_id="noteIndex")
                    if anchor_host is not None:
                        note_index_text = replace(note_index_text, host_placement_id=anchor_host.placement_id,
                                                  paint_order=max(HOSTED_TEXT_PAINT_ORDER, anchor_host.paint_order + 1))
                    text.append(note_index_text)
                    register_rect(note_index_text.placement_id, "text", "timeline", note_index_text.bounds)
                    if note_index_visuals:
                        if not hasattr(annotation_metrics, "cap_height_at"):
                            raise LayoutError("E_FONT_METRICS_CAP_HEIGHT", next(visual.source_ref for visual, _, _, _ in note_index_visuals))
                        cap_height = float(annotation_metrics.cap_height_at(size))
                        for visual, icon, icon_width, gap in note_index_visuals:
                            inline = (note_index.bounds.x if visual.side == "leading"
                                      else note_index.bounds.x + note_index_leading + note_index_width + note_index_trailing - gap - icon_width)
                            icon_bounds = Rect(Decimal(str(inline)), Decimal(str(note_index_text.baseline[1] - cap_height
                                                                                  + (cap_height - size) / 2)),
                                               Decimal(str(icon_width)), Decimal(str(size)))
                            candidate_icons.append(IconPlacement(f"visual:note-index:{annotation_id}:{visual.side}",
                                                                 annotation_id, visual.source_ref, icon.icon_id, icon.kind,
                                                                 icon.content_identity, icon.viewport, icon.payload, icon.alternative,
                                                                 visual.decorative, icon_bounds, "labelVisual",
                                                                 icon_width / icon.viewport[0], annotation_slot_id,
                                                                 paint_order=note_index_text.paint_order))
            if box.leader_required and presentation.leader_semantic_id is not None:
                target = nearest_box_port(bounds, (anchor_bounds.x + anchor_bounds.width / 2, anchor_bounds.y + anchor_bounds.height / 2))
                if anchor_host is None:
                    raise LayoutError("E_PRESENTATION_ANCHOR_MISSING", f"/annotations/{index}/anchor")
                target_port_obstacle_id = f"port:annotation:{annotation_id}:target"
                leader_fallback = selected_leader is None
                if leader_fallback:
                    anchor_instance_id = anchor_host.placement_id.split(":", 1)[1]
                    anchor_row_id = instance_rows.get(anchor_instance_id)
                    selected_source = connector_egress_candidates(
                        anchor_host, resolved.endpoint, target,
                        comparison_clusters.get((anchor_host.source_ref, anchor_row_id), (anchor_host,)))[0]
                    points = (selected_source.semantic_port, target)
                    path_commands = ()
                    visible_route_segments = tuple(zip(points, points[1:]))
                else:
                    selected_source, route_trial, points, prefix = selected_leader
                    path_commands = ((PathCommand("move", (prefix[0],)),
                                      *(PathCommand("line", (point,)) for point in prefix[1:]),
                                      *route_trial.commands[1:])
                                     if route_trial.commands else ())
                    visible_route_segments = tuple(zip(prefix, prefix[1:])) + visible_segments(route_trial)
                source_side = selected_source.side
                source_port_obstacle_id = f"port:{anchor_host.placement_id}:{source_side}"
                if not surface_obstacles.has(source_port_obstacle_id):
                    register_port(source_port_obstacle_id, selected_source.exposed_port, "timeline")
                if not surface_obstacles.has(target_port_obstacle_id):
                    register_port(target_port_obstacle_id, target, "annotations")
                leader_semantic_id = presentation.leader_semantic_id
                leader_stroke_width = float(request.theme_tokens.number(
                    semantic_binding(leader_semantic_id).theme_role, "strokeWidth"))
                marker_end = (marker_geometry(request.theme_tokens.marker(semantic_binding(leader_semantic_id).theme_role))
                              if presentation.purpose == "explanatory-arrow" else None)
                placed_leader = RelationPlacement(f"annotation-leader:{annotation_id}",
                                                  f"{resolved.object_id}:{resolved.facet}:{resolved.endpoint}:{source_side}",
                                                  f"annotation-box:{annotation_id}", tuple(points),
                                                  semantic_id=leader_semantic_id, marker_end=marker_end,
                                                  path_commands=path_commands,
                                                  annotation=presentation, source_ref=annotation_id)
                relations.append(placed_leader)
                for segment_index, (segment_start, segment_end) in enumerate(visible_route_segments):
                    if segment_start != segment_end:
                        surface_obstacles.add(SurfaceObstacle(
                            f"{placed_leader.relation_id}:segment:{segment_index}", "leader-route", "annotations",
                            ObstacleSegment(segment_start, segment_end, leader_stroke_width)))
                if leader_fallback:
                    visible_route_fallbacks.append(placed_leader)
    text = [replace(item, slot_id=text_slot(item)) for item in text]
    text, icons, text_visual_warnings = resolve_text_visual_requests(text, request, handled_sources=handled_candidate_visuals,
                                                axis_label_targets=axis_label_targets,
                                                pre_reserved_placements=detail_visual_reservations)
    _validate_detail_panel_placement(text, slots)
    icons.extend(candidate_icons)
    icons.extend(resolve_mark_visual_requests(marks, request))

    # Slot ownership is completed here with the rest of Layout geometry.  Scene
    # projection receives the relation verbatim and must never reconstruct it
    # from primitive purpose, identity, or containment.
    def shape_slot(item: Any) -> str:
        if item.semantic_id in axis_band_semantic_ids():
            return axis.slot_id
        if item.semantic_id in BACKGROUND_SEMANTIC_IDS:
            return item.slot_id
        if item.placement_id.startswith("legend-swatch:"):
            return by_source["legend"].slot_id
        if item.placement_id.startswith("summary-bar:"):
            return by_source.get("summary", timeline).slot_id
        if item.placement_id.startswith("annotation-box:"):
            return by_source.get("annotations", timeline).slot_id
        if item.source_ref == "timeline-axis":
            return axis.slot_id
        return timeline.slot_id
    shapes = [replace(item, slot_id=shape_slot(item)) for item in shapes]
    icons.extend(resolve_axis_band_visual_requests(shapes, request, axis_band_targets))
    relations = [replace(item, slot_id=(by_source.get("annotations", timeline).slot_id
                                        if item.relation_id.startswith("annotation-leader:")
                                        else by_source["legend"].slot_id
                                        if item.relation_id.startswith("legend-swatch:")
                                        else timeline.slot_id)) for item in relations]
    column_placements = tuple(
        ColumnPlacement(item.column_id, column.header,
                        Rect(Decimal(str(item.inline)), Decimal(str(table_bounds[1])),
                             Decimal(str(item.inline_size)), Decimal(str(table_bounds[3]))))
        for item, column in zip(columns, table_columns, strict=True)
    )
    _validate_background_shapes(shapes, request.theme_tokens)

    # Complete the observable fallback records at the same point as completed
    # geometry.  Neither Scene nor an adapter gets a policy question to answer.
    fit_warnings: list[FitWarning] = [*layout_manifest.fit_warnings, *detail_panel_warnings,
                                      *side_content_warnings, *text_visual_warnings]
    warned_placement_ids: set[str] = set()
    timeline_end = timeline.bounds.block + timeline.bounds.block_size
    header_start = Decimal(str(table_bounds[1]))
    header_end = Decimal(str(timeline_bounds[1]))
    row_by_id = {row.row_id: row for row in rows}
    table_end = table.bounds.inline + table.bounds.inline_size
    for column in column_placements:
        if column.bounds.inline + column.bounds.inline_size > table_end + GEOMETRY_TOLERANCE:
            placement_id = f"column:{column.column_id}"
            fit_warnings.append(FitWarning(
                "W_LAYOUT_VISIBLE_OVERFLOW", placement_id, "view:tableColumns",
                "table-text", "visible-overflow", float(column.bounds.inline_size),
                float(column.bounds.block_size), max(0.0, float(table_end - column.bounds.inline)),
                float(column.bounds.block_size),
            ))
            warned_placement_ids.add(placement_id)
    for item in text:
        if (not item.placement_id.startswith(("column:", "cell:")) or item.overflow != "fit"
                or item.placement_id in warned_placement_ids):
            continue
        inline_overflow = (item.available_inline_size is not None
                           and item.bounds.inline_size > Decimal(str(item.available_inline_size)) + GEOMETRY_TOLERANCE)
        if item.placement_id.startswith("column:"):
            block_available = max(0.0, float(header_end - header_start))
            block_overflow = not _contains_block_interval(
                container_start=header_start, container_end=header_end,
                item_start=item.bounds.block, item_end=item.bounds.block + item.bounds.block_size,
            )
        else:
            object_id = item.placement_id.split(":", 2)[1]
            row = row_by_id.get(object_id) or next((candidate for candidate in rows if candidate.object_id == object_id), None)
            block_available = float(row.bounds.block_size) if row is not None else 0.0
            block_overflow = row is not None and not _contains_block_interval(
                container_start=row.bounds.block, container_end=row.bounds.block + row.bounds.block_size,
                item_start=item.bounds.block, item_end=item.bounds.block + item.bounds.block_size,
            )
        if inline_overflow or block_overflow:
            fit_warnings.append(FitWarning(
                "W_LAYOUT_VISIBLE_OVERFLOW", item.placement_id, item.source_ref,
                "table-text", "visible-overflow", float(item.bounds.inline_size),
                float(item.bounds.block_size), float(item.available_inline_size or 0), block_available,
            ))
    for row in rows:
        if row.bounds.block + row.bounds.block_size > timeline_end + GEOMETRY_TOLERANCE:
            fit_warnings.append(FitWarning(
                "W_LAYOUT_ROW_DENSITY", f"row:{row.row_id}", row.object_id,
                "review-row-density", "visible-overflow", float(row.bounds.inline_size),
                float(row.bounds.block_size), float(timeline.bounds.inline_size),
                max(0.0, float(timeline_end - row.bounds.block)),
            ))
    for mark in marks:
        # A legend swatch drawn as the real point-shaped primitive (#427) lives in
        # the legend slot below the plot by construction, not in the timeline; it
        # is never meant to fit inside `timeline_end` and checking it here always
        # reports a spurious overflow with `available` clamped to 0. The legend's
        # own row-height accounting is the swatch's actual containment check.
        if mark.placement_id.startswith("legend-swatch:"):
            continue
        if mark.bounds.block + mark.bounds.block_size > timeline_end + GEOMETRY_TOLERANCE:
            fit_warnings.append(FitWarning(
                "W_LAYOUT_MARK_OVERFLOW", mark.placement_id, mark.source_ref,
                "mark-containment", "visible-overflow", float(mark.bounds.inline_size),
                float(mark.bounds.block_size), float(timeline.bounds.inline_size),
                max(0.0, float(timeline_end - mark.bounds.block)),
            ))
    for item, available in visible_label_overflows:
        fit_warnings.append(FitWarning(
            "W_LAYOUT_LABEL_OVERFLOW", item.placement_id, item.source_ref,
            "label-collision", "visible-overflow", float(item.bounds.inline_size),
            float(item.bounds.block_size), available.width, available.height,
        ))
    for relation in visible_route_fallbacks:
        fit_warnings.append(FitWarning(
            "W_LAYOUT_ROUTE_FALLBACK", relation.relation_id, relation.source_ref,
            "relation-route", "direct-path", 0.0, 0.0,
            float(timeline.bounds.inline_size), float(timeline.bounds.block_size),
        ))
    for group_id, header, available_block in visible_group_header_overflows:
        fit_warnings.append(FitWarning(
            "W_LAYOUT_GROUP_HEADER_OVERFLOW", f"group-header:{group_id}", group_id,
            "group-header-density", "visible-overflow", float(header.inline_size),
            float(header.block_size), float(header.inline_size), available_block,
        ))
    canvas = _completed_canvas(
        requested=request.layout_manifest.viewport,
        rectangles=(tuple(slot.bounds for slot in slots) + tuple(row.bounds for row in rows)
                    + tuple(column.bounds for column in column_placements)
                    + tuple(group.content_bounds for group in groups)
                    + tuple(group.header_bounds for group in groups if group.header_bounds is not None)
                    + tuple(item.bounds for item in text) + tuple(item.bounds for item in marks)
                    + tuple(item.bounds for item in shapes) + tuple(item.bounds for item in icons)),
        paths=tuple(item.points for item in relations),
    )
    suppressed_plot_labels = sum(item.semantic_id == "memberLabel" and item.overflow == "suppressed" for item in text)
    completed_icons = tuple(replace(icon, completed_paths=complete_icon_paths(
        icon.payload, (float(icon.bounds.inline), float(icon.bounds.block),
                       float(icon.bounds.inline_size), float(icon.bounds.block_size)), icon.stroke_scale))
        if icon.kind == "vector" else icon for icon in icons)
    if projection.lane_membership is not None:
        lane_mark_blocks: dict[str, Decimal] = {}
        for mark in marks:
            if mark.lane_row_id is not None:
                lane_mark_blocks[mark.lane_row_id] = min(
                    lane_mark_blocks.get(mark.lane_row_id, mark.bounds.block), mark.bounds.block)
        if any(row.row_id not in lane_mark_blocks for row in rows):
            raise LayoutError("E_LAYOUT_LANE_ROW_ANCHOR_INVALID", "/layout/rows")
        try:
            rows = tuple(replace(row, lane_mark_band_block=lane_mark_blocks[row.row_id]) for row in rows)
        except ValueError as error:
            raise LayoutError("E_LAYOUT_LANE_ROW_ANCHOR_INVALID", "/layout/rows",
                              "completed lane mark band falls outside its row bounds") from error
    lane_emissions = _lane_emissions(projection, tuple(review_rows), marks, text,
                                     shapes, completed_icons, request.theme_tokens)
    placement = SurfacePlacement(text=tuple(text), slots=slots, rows=rows, columns=column_placements,
                                 groups=tuple(groups), scale=scale,
                                 marks=tuple(marks), shapes=tuple(shapes), relations=tuple(relations),
                                 decisions=tuple(placement_decisions),
                                 axis_tier_outcomes=tuple(axis_tier_outcomes),
                                 diagnostics=tuple(diagnostics), icons=completed_icons,
                                 canvas_bounds=canvas, fit_warnings=tuple(fit_warnings),
                                 info_diagnostics=((SuppressedPlotLabels("table-timeline", suppressed_plot_labels),)
                                                   if suppressed_plot_labels else ()),
                                 lane_emissions=lane_emissions)
    placement.assert_valid()
    return SurfaceLayoutComposition(placement, tuple(review_rows), tracks, tuple(mark_absences))


def _rect(bounds: tuple[float, float, float, float]) -> Rect:
    return Rect(*(Decimal(str(value)) for value in bounds))


def _bounds(rect: Rect) -> tuple[float, float, float, float]:
    return (float(rect.inline), float(rect.block), float(rect.inline_size), float(rect.block_size))


def _coordinate(value: date, scale: ScalePlacement) -> float:
    return scale.origin + (value - scale.domain_start).days * scale.unit_ratio


def _folded_instance_id(folded: Any, item: Any) -> str:
    """Keep a header point's comparison members addressable without inventing rows."""
    return f"group-header:{folded.group_id}:{item.item_id or item.object_id}"


def _comparison_marks(projection: Any) -> tuple[ComparisonMark, ...]:
    marks: list[ComparisonMark] = []
    for item in projection.items:
        for facet, value in (("planned", item.planned), ("actual", item.actual)):
            if not value:
                continue
            if item.source_type == "point" and isinstance(value.get("at"), date):
                marks.append(ComparisonMark(item.object_id, facet, "point", at=value["at"]))
            elif item.source_type == "span" and isinstance(value.get("start"), date) and isinstance(value.get("end", value.get("finish")), date):
                marks.append(ComparisonMark(item.object_id, facet, "span", start=value["start"], end=value.get("end", value.get("finish"))))
    return tuple(marks)


def _annotation_anchor_bounds(mark: ComparisonMark, endpoint: str, row: RowPlacement,
                              scale: ScalePlacement) -> LabelRect:
    if endpoint == "start":
        at = mark.start
    elif endpoint == "finish":
        at = mark.end
    elif endpoint == "at":
        at = mark.at
    elif endpoint == "body":
        at = mark.at or (mark.start + (mark.end - mark.start) / 2 if mark.start and mark.end else None)
    else:
        at = None
    if not isinstance(at, date):
        raise LayoutError("E_PRESENTATION_ANCHOR_MISSING", "/annotations/anchor")
    return LabelRect(_coordinate(at, scale), float(row.bounds.block + row.bounds.block_size * Decimal("0.35")),
                     1.0, max(2.0, float(row.bounds.block_size) * 0.2))
