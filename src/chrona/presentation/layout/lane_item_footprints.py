"""Compose zero-origin visible footprints for immutable Review lane members."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import date
from typing import Any

from chrona.presentation.layout.lane_mark_facets import (
    _compose_mark_icons,
    _compose_progress,
    _item_by_instance,
    _mark_facets,
    _overlay_compound_facets,
    _with_mark_visuals,
)
from chrona.presentation.layout.lane_projection import (
    LaneProjectionInstance,
    close_lane_projection,
    lane_missing_actual_visible,
)
from chrona.presentation.layout.lane_subtracks import (
    LaneFacetFootprint,
    LaneItemFootprints,
)
from chrona.presentation.layout.lane_visual_binding import bind_lane_visual_requests
from chrona.presentation.layout.mark_geometry import compose_item_marks
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment
from chrona.presentation.layout.presentation import MarkBandFrame
from chrona.presentation.layout.mark_band_allocation import MarkBandAllocation
from chrona.presentation.layout.surface_quality import ScalePlacement, VisualRequest
from chrona.presentation.layout.surface_mark_visibility import (
    ItemMarkVisibilityIndex, MarkOccurrence, MarkOccurrenceKind,
    ensure_item_mark_visibility_index,
)
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
    mark_band_allocation: MarkBandAllocation | None = None,
    visual_requests: Sequence[VisualRequest] = (),
    progress_fill_source: str | None = None,
    mark_visibility_index: ItemMarkVisibilityIndex | None = None,
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
    mark_visibility_index = ensure_item_mark_visibility_index(
        projection, as_of=as_of, index=mark_visibility_index)
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

    frame = MarkBandFrame.zero_origin(scale, float(mark_band_size), role_geometries, mark_band_allocation)
    marks_by_instance = {}
    for instance in closure.instances:
        occurrence = MarkOccurrence(
            MarkOccurrenceKind.LANE_SOURCE, instance.row_id, instance.item_id,
            instance.object_id, instance.source_kind,
        )
        visibility = mark_visibility_index.lookup(
            occurrence, projection=projection, as_of=as_of)
        composition = compose_item_marks(
            item=items[instance], instance_id=instance.placement_key,
            source_kind=instance.source_kind, frame=frame, as_of=as_of,
            theme_tokens=theme_tokens, slot_id=slot_id,
            emit_missing_actual=lane_missing_actual_visible(projection), emit_diagnostics=False,
            selection=visibility.selection,
        )
        marks_by_instance[instance] = composition.marks
    all_marks = tuple(mark for instance in closure.instances for mark in marks_by_instance[instance])
    icons = _compose_mark_icons(all_marks, bound_marks, icon_assets, theme_tokens)
    progress = _compose_progress(closure, items, marks_by_instance, progress_fill_source, theme_tokens)
    collected: dict[LaneProjectionInstance, list[LaneFacetFootprint]] = defaultdict(list)
    facet_purposes: dict[LaneProjectionInstance, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    hosted_icons: dict[LaneProjectionInstance, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for instance in closure.instances:
        item = items[instance]
        for mark in marks_by_instance[instance]:
            facets = _overlay_compound_facets(_mark_facets(item, instance, mark, theme_tokens))
            visible = _with_mark_visuals(item, instance, mark, facets,
                                         icons.get(mark.placement_id, ()),
                                         progress.get(mark.placement_id, ()), theme_tokens)
            for facet in visible:
                footprint = facet.visible_footprint
                if not isinstance(footprint, (ObstacleRect, ObstacleSegment)):
                    raise LayoutError("E_LAYOUT_LANE_FOOTPRINT_INVALID", mark.placement_id)
                point_anchor = None
                if mark.mark_shape == "point":
                    candidate = ((item.actual or {}).get("at") if mark.semantic_id == "actual"
                                 else item.planned.get("at"))
                    point_anchor = candidate if isinstance(candidate, date) else None
                collected[instance].append(LaneFacetFootprint(
                    facet.facet_id, footprint, facet.overlay_with, point_anchor,
                ))
                facet_purposes[instance][facet.purpose].append(facet.facet_id)
                if facet.purpose == "icon":
                    hosted_icons[instance][mark.semantic_id].append(facet.facet_id)

    # A combined source explicitly paints its Plan and Actual state in one
    # band. Name only those exact pairs; common object identity is not a
    # general collision exemption for icons, children or other instances.
    for instance in closure.instances:
        if items[instance].source_kind != "combined":
            continue
        planned_ids = tuple(facet_purposes[instance].get("planned", ()))
        observed_ids = tuple(facet_purposes[instance].get("actual", ())) + tuple(
            facet_purposes[instance].get("missing-actual", ()))
        # Each mark's hosted icon follows that exact mark into the already
        # declared Plan↔Actual overlay, including when both marks have icons.
        _add_intra_instance_overlay_pairs(
            collected, instance,
            planned_ids + tuple(hosted_icons[instance].get("planned", ())),
            observed_ids + tuple(hosted_icons[instance].get("actual", ()))
            + tuple(hosted_icons[instance].get("missing-actual", ())),
        )
        if progress_fill_source == "actual":
            _add_intra_instance_overlay_pairs(
                collected, instance, planned_ids,
                tuple(facet_purposes[instance].get("progress", ())),
            )
    instances_by_member: dict[str, list[LaneProjectionInstance]] = defaultdict(list)
    for instance in closure.instances:
        instances_by_member[owner_for_instance[instance]].append(instance)

    # Shared comparison composition is an exact cross-instance facet relation.
    for member_id, instances in instances_by_member.items():
        for index, left in enumerate(instances):
            for right in instances[index + 1:]:
                if items[left].track == items[right].track == "shared":
                    _add_overlay_pairs(collected, left, right)
    # Attachments permit only host↔each-child overlays, never child↔child.
    assignments = {assignment.item_id: assignment for assignment in membership.assignments}
    for member_id in member_order:
        assignment = assignments[member_id]
        if assignment.rule == "attached":
            host_instances = instances_by_member.get(assignment.source_id, ())
            child_instances = instances_by_member.get(member_id, ())
            if not host_instances or not child_instances:
                raise LayoutError("E_LAYOUT_LANE_FOOTPRINT_MEMBERSHIP_MISMATCH", "/projection/laneRows")
            for host in host_instances:
                for child in child_instances:
                    _add_overlay_pairs(collected, host, child)

    if any(not any(collected.get(instance) for instance in instances_by_member.get(member_id, ()))
           for member_id in member_order):
        raise LayoutError("E_LAYOUT_LANE_FOOTPRINT_EMPTY", "/projection/laneRows")
    return tuple(
        LaneItemFootprints(member_id, instance, tuple(collected[instance]))
        for member_id in member_order
        for instance in instances_by_member[member_id]
    )


def _add_overlay_pairs(
    collected: dict[LaneProjectionInstance, list[LaneFacetFootprint]],
    left: LaneProjectionInstance,
    right: LaneProjectionInstance,
) -> None:
    left_ids = tuple(facet.facet_id for facet in collected[left])
    right_ids = tuple(facet.facet_id for facet in collected[right])
    collected[left] = [replace(facet, overlay_with=tuple(dict.fromkeys((*facet.overlay_with, *right_ids))))
                       for facet in collected[left]]
    collected[right] = [replace(facet, overlay_with=tuple(dict.fromkeys((*facet.overlay_with, *left_ids))))
                        for facet in collected[right]]


def _add_intra_instance_overlay_pairs(
    collected: dict[LaneProjectionInstance, list[LaneFacetFootprint]],
    instance: LaneProjectionInstance,
    left_ids: tuple[str, ...],
    right_ids: tuple[str, ...],
) -> None:
    targets = ({**{facet_id: right_ids for facet_id in left_ids},
                **{facet_id: left_ids for facet_id in right_ids}})
    collected[instance] = [replace(facet, overlay_with=tuple(dict.fromkeys(
        (*facet.overlay_with, *targets.get(facet.facet_id, ())))))
                           for facet in collected[instance]]
