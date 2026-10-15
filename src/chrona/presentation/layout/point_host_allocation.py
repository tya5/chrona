"""Physical-only facet partition; semantic lane membership is never rewritten."""
from __future__ import annotations

from dataclasses import dataclass, replace

from chrona.presentation.layout.lane_projection import LaneProjectionInstance
from chrona.presentation.layout.lane_subtracks import LaneItemFootprints
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, obstacles_intersect
from chrona.presentation.layout.point_hosting import PointHostPlan


@dataclass(frozen=True)
class PhysicalFacetFrame:
    facet_id: str
    semantic_instance: LaneProjectionInstance
    allocation_instance: LaneProjectionInstance
    block_offset: float


@dataclass(frozen=True)
class PointHostAllocation:
    semantic_units: tuple[LaneItemFootprints, ...]
    physical_units: tuple[LaneItemFootprints, ...]
    frames: tuple[PhysicalFacetFrame, ...]
    hosted_only_instances: frozenset[LaneProjectionInstance]


def partition_hosted_facets(units: tuple[LaneItemFootprints, ...],
                            plan: PointHostPlan) -> PointHostAllocation:
    """Move each hosted mark and its bound visuals once into its host frame.

    The original inventory remains immutable and separately validated. Only
    mark/host geometry gains overlap authority, never icons or sibling points.
    """
    by_instance = {unit.projection_instance_id: unit for unit in units}
    if not plan.relations:
        return PointHostAllocation(units, units,
            tuple(PhysicalFacetFrame(facet.facet_id, unit.projection_instance_id,
                                    unit.projection_instance_id, 0.0)
                  for unit in units for facet in unit.facets), frozenset())
    facets = {facet.facet_id: (unit, facet) for unit in units for facet in unit.facets}
    if len(facets) != sum(len(unit.facets) for unit in units):
        raise LayoutError("E_PRESENTATION_PLACEMENT_REQUIRED", "/projection/items",
                          detail="duplicate source facet in physical host partition")
    moves = {}
    overlays: set[frozenset[str]] = set()
    for relation in plan.relations:
        point_id = relation.point.source_mark_id(relation.facet)
        span_id = relation.span.source_mark_id(relation.facet)
        point_facets = [facet for _, facet in facets.values() if facet.mark_id == point_id]
        host_facets = [facet for _, facet in facets.values() if facet.mark_id == span_id]
        if (not point_facets or not host_facets
                or relation.span.instance not in by_instance
                or point_facets[0].mark_block_center is None
                or host_facets[0].mark_block_center is None):
            raise LayoutError("E_PRESENTATION_PLACEMENT_REQUIRED", "/projection/items",
                              detail=f"missing physical facet account: {point_id!r} -> {span_id!r}")
        offset = host_facets[0].mark_block_center - point_facets[0].mark_block_center
        for facet in point_facets:
            moves[facet.facet_id] = (relation.span.instance, offset)
            if facet.is_mark_geometry:
                overlays.update(frozenset((facet.facet_id, host.facet_id))
                                for host in host_facets if host.is_mark_geometry)
    targets = {facet_id: moves.get(facet_id, (unit.projection_instance_id, 0.0))
               for facet_id, (unit, _) in facets.items()}
    collected = {instance: [] for instance in by_instance}
    frames = []
    for facet_id, (unit, facet) in facets.items():
        target, offset = targets[facet_id]
        # Existing overlay authority survives only inside its physical row.
        permitted = [other for other in facet.overlay_with
                     if other in targets and _same_lane(target, targets[other][0], plan)
                     and (not (facet_id in moves or other in moves)
                          or unit.projection_instance_id == facets[other][0].projection_instance_id
                          or frozenset((facet_id, other)) in overlays)]
        permitted.extend(next(iter(pair - {facet_id})) for pair in overlays if facet_id in pair)
        translated = replace(facet, footprint=_translate(facet.footprint, offset),
                             overlay_with=tuple(sorted(set(permitted))),
                             mark_block_center=(None if facet.mark_block_center is None else
                                                facet.mark_block_center + offset))
        collected[target].append(translated)
        frames.append(PhysicalFacetFrame(facet_id, unit.projection_instance_id, target, offset))
    physical = tuple(replace(unit, facets=tuple(collected[unit.projection_instance_id])) for unit in units)
    for unit in physical:
        for index, left in enumerate(unit.facets):
            for right in unit.facets[index + 1:]:
                if (left.facet_id in moves or right.facet_id in moves):
                    if (right.facet_id not in left.overlay_with
                            and obstacles_intersect(left.footprint, right.footprint, 0.0)):
                        raise LayoutError("E_LAYOUT_POINT_HOST_OVERLAP", "/projection/items",
                            detail=f"fixed hosted facets collide: {left.facet_id!r}, {right.facet_id!r}")
    emptied = frozenset(unit.projection_instance_id for unit in physical
                        if not unit.facets and by_instance[unit.projection_instance_id].facets)
    return PointHostAllocation(units, physical, tuple(frames), emptied)


def _same_lane(left: LaneProjectionInstance, right: LaneProjectionInstance,
               plan: PointHostPlan) -> bool:
    rows = {occurrence.instance: occurrence.row_id for occurrence in plan.occurrences}
    return left == right or (left in rows and right in rows and rows[left] == rows[right])


def _translate(value: ObstacleRect | ObstacleSegment, offset: float):
    if isinstance(value, ObstacleRect):
        return ObstacleRect(value.left, value.top + offset, value.right, value.bottom + offset)
    return ObstacleSegment((value.start[0], value.start[1] + offset),
                           (value.end[0], value.end[1] + offset), value.stroke_width)
