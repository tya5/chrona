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
from chrona.presentation.layout.surface_marks import resolve_mark_geometries
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.lane_projection import (
    LaneProjectionClosure, LaneProjectionInstance, close_lane_projection,
)
from chrona.presentation.layout.lane_visual_binding import bind_lane_visual_requests
from chrona.presentation.layout.lane_label_intent import measure_lane_member_labels
from chrona.presentation.layout.lane_label_preflight import lane_label_row_requirements
from chrona.presentation.layout.surface_quality import ScalePlacement


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
                                visual_requests: tuple[Any, ...], font_metrics: Any) -> FixedLanePreflight:
    """Close fixed-lane tracks before final allocation from fixed View rows and Layout inputs."""
    membership = getattr(projection, "lane_membership", None)
    if membership is None:
        raise LayoutError("E_LAYOUT_LANE_PREFLIGHT_INVALID", "/projection/laneRows")
    start, end = projection.window
    rows = review_rows(projection)
    frame = lane_inline_frame_for_manifest(layout_manifest, window=(start, end))
    timeline = next(item for item in layout_manifest.decisions if item.source == "timeline")
    provisional_scale = ScalePlacement("table-timeline", "primary", start, end,
                                       float(frame.timeline_inline),
                                       float(frame.timeline_inline + frame.timeline_inline_size),
                                       float(frame.timeline_inline), float(frame.temporal_scale))
    mark_band_size = float(metric_values["timeline.mark.blockSize"])
    footprint_inputs = dict(
        projection=projection, as_of=surface_content.as_of,
        theme_tokens=theme_tokens, mark_band_size=mark_band_size,
        role_geometries=resolve_mark_geometries(theme_tokens), slot_id=timeline.source,
        icon_assets=icon_assets, visual_requests=visual_requests,
        progress_fill_source=surface_content.progress_fill_source,
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
    subtracks = assign_lane_subtracks(membership, footprints, mark_band_size=mark_band_size)
    resolved_visuals = resolved_lane_visual_requests(
        projection, visual_requests, as_of=surface_content.as_of)
    measured_labels = measure_lane_member_labels(
        projection, surface_content, timeline_inline_size=float(frame.timeline_inline_size),
        theme_tokens=theme_tokens, font_metrics=font_metrics,
        visual_requests=resolved_visuals, icon_assets=dict(icon_assets))
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
    headers = len(tuple(row for index, row in enumerate(rows)
                        if row.group_id and surface_content.group_presentation == "header"
                        and (index == 0 or rows[index - 1].group_id != row.group_id)))
    required = (Decimal(str(geometry_sum(requirements)))
                + Decimal(headers) * metric_values.get("timeline.groupHeader.blockSize", 0))
    return FixedLanePreflight(subtracks, frame, required, surface_content.as_of, scale,
                              measured_labels, resolved_visuals,
                              tuple(zip((row.row_id for row in rows), requirements, strict=True)))
