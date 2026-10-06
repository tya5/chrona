"""Layout-owned same-port arrival classification and shared terminal paint."""
from __future__ import annotations

from dataclasses import dataclass, replace

from chrona.presentation.layout.obstacles import segment_overlap_length
from chrona.presentation.layout.surface_quality import MarkerGeometry, RelationFanIn, RelationPlacement

Point = tuple[float, float]


def target_port_identity(instance_id: str, endpoint: str, side: str, *, point: bool) -> str:
    """Name the semantic anchor, not the route's comparison-cluster exit."""
    anchor = side if point or endpoint == "body" else "end" if endpoint == "finish" else endpoint
    return f"{instance_id}:{anchor}"


def terminal_style(marker: MarkerGeometry | None) -> tuple | None:
    if marker is None:
        return None
    # Centred markers retain the same semantic centre even when a tight route
    # completes a different stroke setback/reference offset.
    style = (marker.outline, marker.head_length, marker.head_width, marker.paint_mode,
             marker.centred, marker.angle_degrees, 0.0 if marker.centred else marker.attachment_offset)
    return (*style, "userSpaceOnUse", marker.stroke_width) if marker.physical_units else style


def approach_direction(segment: tuple[Point, Point]) -> tuple[int, int] | None:
    a, b = segment
    if a == b or (a[0] != b[0] and a[1] != b[1]):
        return None
    return ((1 if b[0] > a[0] else -1) if a[0] != b[0] else 0,
            (1 if b[1] > a[1] else -1) if a[1] != b[1] else 0)


@dataclass(frozen=True)
class NodeApproach:
    relation_id: str
    segment: tuple[Point, Point]
    # None denotes a departure, which is never eligible for fan-in.
    arrival_port_id: str | None = None
    paint_id: str = ""
    terminal: tuple | None = None


def same_port_arrivals(first: NodeApproach, second: NodeApproach) -> bool:
    direction = approach_direction(first.segment)
    return (first.arrival_port_id is not None
            and first.arrival_port_id == second.arrival_port_id
            and first.paint_id == second.paint_id and first.terminal == second.terminal
            and direction is not None and direction == approach_direction(second.segment)
            and segment_overlap_length(first.segment, second.segment) > 1e-9)


def complete_fan_in(relations: tuple[RelationPlacement, ...]) -> tuple[RelationPlacement, ...]:
    """Preserve declared order and all routes; emit each shared head once."""
    groups: list[list[RelationPlacement]] = []
    for relation in relations:
        if relation.suppressed or relation.to_instance_id is None or len(relation.points) < 2:
            continue
        candidate = _arrival(relation)
        group = next((items for items in groups
                      if items[0].to_instance_id == relation.to_instance_id
                      and all(same_port_arrivals(candidate, _arrival(item)) for item in items)), None)
        if group is None:
            groups.append([relation])
        else:
            group.append(relation)
    replacements = {}
    for group in groups:
        if len(group) < 2:
            continue
        owner = group[0]
        shared = RelationFanIn(owner.target_port_id, owner.relation_id)
        for relation in group:
            replacements[relation.relation_id] = replace(relation, fan_in=shared,
                marker_end=relation.marker_end if relation is owner else None)
    return tuple(replacements.get(relation.relation_id, relation) for relation in relations)


def _arrival(relation: RelationPlacement) -> NodeApproach:
    return NodeApproach(relation.relation_id, (relation.points[-2], relation.points[-1]),
                        relation.target_port_id, relation.semantic_id, terminal_style(relation.marker_end))
