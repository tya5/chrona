"""Compose zero-origin visible footprints for immutable Review lane members."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from chrona.presentation.layout.lane_bundle_mapper import (
    _compose_mark_icons,
    _compose_progress,
    _item_by_instance,
    _mark_facets,
    _with_mark_visuals,
)
from chrona.presentation.layout.lane_projection import close_lane_projection
from chrona.presentation.layout.lane_subtracks import LaneFootprint, LaneItemFootprints
from chrona.presentation.layout.lane_visual_binding import bind_lane_visual_requests
from chrona.presentation.layout.mark_geometry import compose_item_marks
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment
from chrona.presentation.layout.presentation import MarkBandFrame
from chrona.presentation.layout.surface_quality import ScalePlacement, VisualRequest
from chrona.presentation.model.projection import ReviewProjection


def compose_lane_item_footprints(
    projection: ReviewProjection,
    *,
    scale: ScalePlacement,
    as_of: date | None,
    theme_tokens: Any,
    mark_band_size: float,
    role_geometries: Mapping[str, Any],
    slot_id: str,
    icon_assets: Mapping[str, Any],
    visual_requests: Sequence[VisualRequest] = (),
    progress_fill_source: str | None = None,
) -> tuple[LaneItemFootprints, ...]:
    """Return all visible mark facets grouped by fixed data-only membership.

    Geometry is composed in a zero-origin frame and can affect only internal
    subtrack placement.  Membership identities and ordering come exclusively
    from ``projection.lane_membership``; labels are intentionally not read.
    """
    membership = projection.lane_membership
    if (membership is None or not projection.lane_rows or not isinstance(slot_id, str)
            or not slot_id or progress_fill_source not in {None, "actual", "planned"}
            or not isinstance(mark_band_size, (int, float)) or isinstance(mark_band_size, bool)
            or mark_band_size <= 0):
        raise LayoutError("E_LAYOUT_LANE_FOOTPRINT_INPUT", "/projection/laneRows")
    closure = close_lane_projection(projection, as_of=as_of)
    items = _item_by_instance(projection, closure)
    bound_marks: dict = {}
    if visual_requests:
        _, bound_marks = bind_lane_visual_requests(projection, closure, visual_requests)

    member_order = tuple(item_id for lane in membership.lanes for item_id in lane.member_item_ids)
    if (len(set(member_order)) != len(member_order)
            or tuple(row.lane_id for row in projection.lane_rows) != tuple(lane.lane_id for lane in membership.lanes)):
        raise LayoutError("E_LAYOUT_LANE_FOOTPRINT_MEMBERSHIP_MISMATCH", "/projection/laneRows")
    owner_for_instance = {}
    seen_instances: set = set()
    for lane_row, lane in zip(projection.lane_rows, membership.lanes):
        if (lane_row.group_id != lane.group_id or len(lane_row.items) != len(lane_row.member_item_ids)
                or not lane_row.member_item_ids):
            raise LayoutError("E_LAYOUT_LANE_FOOTPRINT_MEMBERSHIP_MISMATCH", "/projection/laneRows")
        for item, member_id in zip(lane_row.items, lane_row.member_item_ids):
            if member_id not in lane.member_item_ids:
                raise LayoutError("E_LAYOUT_LANE_FOOTPRINT_MEMBERSHIP_MISMATCH", "/projection/laneRows")
            match = next((instance for instance in closure.instances
                          if instance.item_id == (item.item_id or item.object_id)
                          and instance.object_id == item.object_id
                          and instance.source_kind == item.source_kind), None)
            if match is None or match in seen_instances:
                raise LayoutError("E_LAYOUT_LANE_FOOTPRINT_MEMBERSHIP_MISMATCH", "/projection/laneRows")
            seen_instances.add(match)
            owner_for_instance[match] = member_id
    if seen_instances != set(closure.instances) or set(owner_for_instance.values()) != set(member_order):
        raise LayoutError("E_LAYOUT_LANE_FOOTPRINT_MEMBERSHIP_MISMATCH", "/projection/laneRows")

    frame = MarkBandFrame.zero_origin(scale, float(mark_band_size), role_geometries)
    marks_by_instance = {}
    for instance in closure.instances:
        composition = compose_item_marks(
            item=items[instance], instance_id=instance.placement_key,
            source_kind=instance.source_kind, frame=frame, as_of=as_of,
            theme_tokens=theme_tokens, slot_id=slot_id,
            emit_missing_actual=True, emit_diagnostics=False,
        )
        marks_by_instance[instance] = composition.marks
    all_marks = tuple(mark for instance in closure.instances for mark in marks_by_instance[instance])
    icons = _compose_mark_icons(all_marks, bound_marks, icon_assets, theme_tokens)
    progress, _ = _compose_progress(closure, items, marks_by_instance, progress_fill_source, theme_tokens)
    collected: dict[str, list[LaneFootprint]] = defaultdict(list)
    for instance in closure.instances:
        item = items[instance]
        for mark in marks_by_instance[instance]:
            facets = _mark_facets(item, instance, mark, theme_tokens)
            visible = _with_mark_visuals(item, instance, mark, facets,
                                         icons.get(mark.placement_id, ()),
                                         progress.get(mark.placement_id, ()), theme_tokens)
            for facet in visible:
                footprint = facet.visible_footprint
                if not isinstance(footprint, (ObstacleRect, ObstacleSegment)):
                    raise LayoutError("E_LAYOUT_LANE_FOOTPRINT_INVALID", mark.placement_id)
                collected[owner_for_instance[instance]].append(footprint)
    if any(not collected.get(member_id) for member_id in member_order):
        raise LayoutError("E_LAYOUT_LANE_FOOTPRINT_EMPTY", "/projection/laneRows")
    return tuple(LaneItemFootprints(member_id, tuple(collected[member_id]))
                 for member_id in member_order)
