"""Owns fixed-lane geometry preflight; reads View lane membership and measured Layout inputs."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from chrona.presentation.layout.lane_preflight import lane_inline_frame_for_manifest
from chrona.presentation.layout.lane_subtracks import FixedLanePreflight, LaneSubtrackPlan, assign_lane_subtracks
from chrona.presentation.layout.lane_item_footprints import compose_lane_item_footprints
from chrona.presentation.layout.mark_aware_scale import PointMarkFootprint, inset_scale_for_point_facets
from chrona.presentation.layout.obstacles import obstacle_envelope
from chrona.presentation.layout.model import geometry_sum
from chrona.presentation.layout.presentation import TrackPlacement, table_text_line_block
from chrona.presentation.layout.surface_marks import resolve_mark_geometries, resolve_mark_band
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.lane_projection import (
    LaneProjectionClosure, LaneProjectionInstance, close_lane_projection,
    lane_instance_owners as _lane_instance_owners,
)
from chrona.presentation.layout.lane_visual_binding import bind_lane_visual_requests
from chrona.presentation.layout.lane_label_intent import measure_lane_member_labels
from chrona.presentation.layout.lane_label_preflight import lane_label_row_requirements
from chrona.presentation.layout.surface_quality import ScalePlacement
from chrona.presentation.layout.lane_mark_facets import (
    _mark_facets, _overlay_compound_facets, _with_mark_visuals,
)
from chrona.presentation.layout.obstacles import ObstacleRect
from chrona.presentation.layout.surface_mark_visibility import (
    ItemMarkVisibilityIndex, ensure_item_mark_visibility_index,
)
from chrona.presentation.layout.surface_geometry import bounds_from_rect as _bounds
from chrona.presentation.layout.surface_quality import (
    IconPlacement, LaneEmissionFacet, LaneEmissionPlacement, MarkPlacement, ShapePlacement, TextPlacement,
)
from chrona.presentation.model.semantic_registry import semantic_binding


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


def review_rows(projection: Any) -> tuple[Any, ...]:
    """Read completed View rows, validating lane occurrence identity without reselecting membership."""
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


def place_lane_mark_tracks(*, review_rows: tuple[Any, ...], row_placements: tuple[Any, ...],
                           plan: LaneSubtrackPlan, mark_block_size: float) -> tuple[TrackPlacement, ...]:
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


def lane_owner(review_row: Any, item: Any) -> tuple[str, str] | None:
    """Join one fixed row item to its immutable member ID by projection facts."""
    member_ids = getattr(review_row, "member_item_ids", ())
    if not member_ids:
        return None
    matches = [member_id for candidate, member_id in zip(review_row.items, member_ids, strict=True)
               if ((candidate.item_id or candidate.object_id, candidate.object_id, candidate.source_kind)
                   == (item.item_id or item.object_id, item.object_id, item.source_kind))]
    if len(matches) != 1:
        raise LayoutError("E_LAYOUT_LANE_PROJECTION_INVALID", f"/projection/laneRows/{review_row.row_id}")
    return review_row.row_id, matches[0]


def resolved_lane_visual_requests(projection: Any, visual_requests: tuple[Any, ...],
                                  *, as_of: date | None) -> tuple[Any, ...]:
    """Bind View selectors once to the final lane occurrence identities."""
    if not visual_requests:
        return ()
    closure = close_lane_projection(projection, as_of=as_of)
    label_visuals, mark_visuals = bind_lane_visual_requests(projection, closure, visual_requests)
    owners = _lane_instance_owners(projection, closure)
    resolved = [visual for visual in visual_requests
                if visual.target_kind not in {"plot-label", "mark"}]
    for instance, visuals in label_visuals.items():
        lane_id, item_id = owners[instance]
        placement_id = f"member-label:{lane_id}:{item_id}"
        resolved.extend(replace(visual, selector=(("placementId", placement_id),)) for visual in visuals)
    for (instance, purpose), visual in mark_visuals.items():
        lane_id, item_id = owners[instance]
        placement_id = f"{purpose}:{lane_id}:{item_id}"
        resolved.append(replace(visual, selector=(("placementId", placement_id),)))
    return tuple(resolved)


def preflight_fixed_lane_layout(*, projection: Any, layout_manifest: Any,
                                surface_content: Any, theme_tokens: Any,
                                metric_values: dict[str, Decimal], icon_assets: Mapping[str, Any],
                                visual_requests: tuple[Any, ...], font_metrics: Any,
                                mark_visibility_index: ItemMarkVisibilityIndex | None = None
                                ) -> FixedLanePreflight:
    """Close fixed-lane tracks before final allocation from fixed View rows and Layout inputs."""
    membership = getattr(projection, "lane_membership", None)
    if membership is None:
        raise LayoutError("E_LAYOUT_LANE_PREFLIGHT_INVALID", "/projection/laneRows")
    mark_visibility_index = ensure_item_mark_visibility_index(
        projection, as_of=surface_content.as_of, index=mark_visibility_index)
    start, end = projection.window
    rows = review_rows(projection)
    frame = lane_inline_frame_for_manifest(layout_manifest, window=(start, end))
    timeline = next(item for item in layout_manifest.decisions if item.source == "timeline")
    provisional_scale = ScalePlacement("table-timeline", "primary", start, end,
                                       float(frame.timeline_inline),
                                       float(frame.timeline_inline + frame.timeline_inline_size),
                                       float(frame.timeline_inline), float(frame.temporal_scale))
    mark_band_size = float(metric_values["timeline.mark.blockSize"])
    role_geometries = resolve_mark_geometries(theme_tokens)
    mark_band_allocation = resolve_mark_band(theme_tokens, mark_band_size, role_geometries=role_geometries)
    footprint_inputs = dict(
        projection=projection, as_of=surface_content.as_of,
        theme_tokens=theme_tokens, mark_band_size=mark_band_size,
        role_geometries=role_geometries, slot_id=timeline.source,
        mark_band_allocation=mark_band_allocation,
        icon_assets=icon_assets, visual_requests=visual_requests,
        progress_fill_source=surface_content.progress_fill_source,
        mark_visibility_index=mark_visibility_index,
    )
    provisional_footprints = compose_lane_item_footprints(scale=provisional_scale, **footprint_inputs)
    point_facets = []
    for item_footprints in provisional_footprints:
        for facet in item_footprints.facets:
            if facet.point_anchor_date is not None:
                left, _, right, _ = obstacle_envelope(facet.footprint)
                point_facets.append(PointMarkFootprint(facet.point_anchor_date, left, right))
    scale = inset_scale_for_point_facets(provisional_scale, point_facets)
    footprints = (provisional_footprints if scale is provisional_scale else
                  compose_lane_item_footprints(scale=scale, **footprint_inputs))
    subtracks = assign_lane_subtracks(membership, footprints, mark_band_size=mark_band_size,
                                     reserved_band_bounds=mark_band_allocation.outer_bounds,
                                     mark_visibility_index=mark_visibility_index)
    resolved_visuals = resolved_lane_visual_requests(
        projection, visual_requests, as_of=surface_content.as_of)
    measured_labels = measure_lane_member_labels(
        projection, surface_content, timeline_inline_size=float(frame.timeline_inline_size),
        theme_tokens=theme_tokens, font_metrics=font_metrics,
        visual_requests=resolved_visuals, icon_assets=dict(icon_assets),
        mark_visibility_index=mark_visibility_index)
    row_padding = float(metric_values["timeline.row.paddingBlock"])
    lane_requirements = (lane_label_row_requirements(
        measured_labels, scale, subtracks, footprints,
        timeline_bounds=(float(frame.timeline_inline), float(frame.timeline_inline + frame.timeline_inline_size)),
        row_padding=row_padding)
        if layout_manifest.row_distribution == "fill" else
        {lane.lane_id: lane.block_extent + row_padding for lane in subtracks.lanes})
    line_block = table_text_line_block(theme_tokens, (cell.typography_role for cell in surface_content.table_cells))
    requirements = tuple(max(float(metric_values["timeline.row.minBlockSize"]),
                             line_block + row_padding if line_block else 0.0,
                             lane_requirements[row.row_id]) for row in rows)
    # A vertical group label replaces the header row, so no header row is reserved (#585).
    header_rows = (surface_content.group_presentation == "header"
                   and theme_tokens.writing_mode("groupHeader") != "vertical")
    headers = len(tuple(row for index, row in enumerate(rows)
                        if row.group_id and header_rows
                        and (index == 0 or rows[index - 1].group_id != row.group_id)))
    required = (Decimal(str(geometry_sum(requirements)))
                + Decimal(headers) * metric_values.get("timeline.groupHeader.blockSize", 0))
    return FixedLanePreflight(subtracks, frame, required, surface_content.as_of, scale,
                              measured_labels, resolved_visuals,
                              tuple(zip((row.row_id for row in rows), requirements, strict=True)),
                              mark_band_allocation, mark_visibility_index)


def build_lane_emissions(projection: Any, review_rows: tuple[Any, ...], marks: list[MarkPlacement],
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
        # A catalog chip remains one Layout placement (and therefore one
        # viewer-fit/box identity), but Scene emits a Symbol per completed
        # part. Close every one of those primitives against the same complete
        # chip obstacle so lane ownership has the same cardinality as Scene.
        chip_parts = shape.symbol_parts if shape.placement_id.startswith("chip:") else ()
        footprint = (shape.collision_bounds or shape.bounds) if chip_parts else shape.bounds
        left, top, width, height = _bounds(footprint)
        if width <= 0 or height <= 0:
            continue
        purpose = semantic_binding(shape.semantic_id).purpose
        obstacle = ObstacleRect(left, top, left + width, top + height)
        if chip_parts:
            for index, _part in enumerate(chip_parts):
                primitive_id = (shape.placement_id if index == 0
                                else f"{shape.placement_id}:part{index}")
                add("shape", shape.placement_id, shape.lane_row_id, shape.lane_member_id,
                    purpose, LaneEmissionFacet(f"shape:{shape.placement_id}:part{index}", "shape",
                                               shape.placement_id, primitive_id, obstacle,
                                               "required-label", index))
        else:
            add("shape", shape.placement_id, shape.lane_row_id, shape.lane_member_id,
                purpose, LaneEmissionFacet(f"shape:{shape.placement_id}", "shape", shape.placement_id,
                                           shape.placement_id, obstacle, "required-label"))
    return tuple(LaneEmissionPlacement(kind, placement_id, row_id, member_id, purpose,
                                       tuple(facets))
                 for (kind, placement_id, row_id, member_id, purpose), facets in grouped.items())


def complete_hosted_text_identity(
        text: tuple[TextPlacement, ...], marks: tuple[MarkPlacement, ...],
        lane_emissions: tuple[LaneEmissionPlacement, ...]) -> tuple[TextPlacement, ...]:
    """Resolve abstract lane-mark hosts to their first emitted glyph part."""
    emitted_mark_hosts: dict[str, str] = {}
    for emission in lane_emissions:
        if emission.placement_type != "mark":
            continue
        ordered = sorted(emission.facets, key=lambda facet: (
            -1 if facet.part_index is None else facet.part_index, facet.primitive_id))
        host_id = ordered[0].primitive_id
        previous = emitted_mark_hosts.setdefault(emission.placement_id, host_id)
        if previous != host_id:
            raise LayoutError("E_LAYOUT_HOST_EMISSION_INVALID", emission.placement_id)
    lane_marks_by_id = {mark.placement_id: mark for mark in marks if mark.lane_row_id is not None}
    completed = []
    for placed in text:
        host_id = placed.host_placement_id
        if host_id not in lane_marks_by_id:
            completed.append(placed)
            continue
        mark = lane_marks_by_id[host_id]
        emitted_id = emitted_mark_hosts.get(host_id)
        if (emitted_id is None or placed.slot_id != mark.slot_id
                or placed.paint_order <= mark.paint_order):
            raise LayoutError("E_LAYOUT_HOST_EMISSION_INVALID", placed.placement_id)
        completed.append(replace(placed, host_placement_id=emitted_id)
                         if emitted_id != host_id else placed)
    return tuple(completed)


FOREGROUND_TEXT_PAINT_ORDER = 300
# Layout emits coordinates at micro-point precision.  Intermediate measurement
# APIs are float-based, so containment must not turn a sub-micro-point binary
# conversion residue into a user-visible overflow diagnostic.
