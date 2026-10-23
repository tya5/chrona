"""Complete point hosting in one coordinate frame, before downstream consumers."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.point_hosting import PointHostPlan
from chrona.presentation.layout.surface_quality import MarkPlacement, PhysicalMarkHost
from chrona.presentation.layout.lane_mark_facets import _mark_facets
from chrona.presentation.layout.obstacles import obstacles_intersect
from chrona.presentation.model.paint_capabilities import PaintWitnessCapabilities


def translate_point_block(mark: MarkPlacement, offset: float) -> MarkPlacement:
    """Translate every local glyph/port operand while retaining date and identity.

    A paint clip is a global viewport constraint, not local glyph geometry.
    Admitted point facets keep their existing window admission and clip.
    """
    if mark.mark_shape != "point":
        raise LayoutError("E_PRESENTATION_PLACEMENT_REQUIRED", mark.placement_id,
                          detail="physical point hosting requires a point mark")

    def commands(values):
        return tuple(replace(command, points=tuple((x, y + offset) for x, y in command.points))
                     for command in values)

    def port(value):
        return None if value is None else (value[0], value[1] + offset)

    return replace(mark,
        bounds=replace(mark.bounds, block=mark.bounds.block + Decimal(str(offset))),
        start_port=port(mark.start_port), end_port=port(mark.end_port),
        path_commands=commands(mark.path_commands),
        symbol_parts=tuple(replace(part, commands=commands(part.commands)) for part in mark.symbol_parts),
        pattern_origin=(None if mark.pattern_origin is None else
                        (mark.pattern_origin[0], mark.pattern_origin[1] + offset)))


def complete_hosted_point_geometry(plan: PointHostPlan, marks: tuple[MarkPlacement, ...], *,
                                   source_frame: bool = False) -> tuple[MarkPlacement, ...]:
    """Use the same host-relative translation in preflight and final coordinates."""
    if not plan.relations:
        return marks
    original = {mark.placement_id: mark for mark in marks}
    completed = {}
    for relation in plan.relations:
        identity = (lambda occurrence: occurrence.source_mark_id(relation.facet)) if source_frame else (
            lambda occurrence: occurrence.final_mark_id(relation.facet))
        point_id, span_id = identity(relation.point), identity(relation.span)
        point, span = original.get(point_id), original.get(span_id)
        if point is None or span is None or span.mark_shape not in {"span", "open-span"}:
            raise LayoutError("E_PRESENTATION_PLACEMENT_REQUIRED", "/projection/items",
                node_id=point_id, detail=f"physical host closure missing: point={point_id!r}; host={span_id!r}")
        offset = float(span.bounds.block + span.bounds.block_size / 2
                       - point.bounds.block - point.bounds.block_size / 2)
        placed = translate_point_block(point, offset)
        # Compound host parts have consecutive completed paint orders.
        completed[point_id] = replace(placed,
            paint_order=max(point.paint_order, span.paint_order + max(1, len(span.symbol_parts))),
            physical_host=(None if source_frame else
                           PhysicalMarkHost(span_id, relation.span.row_id)))
    return tuple(completed.get(mark.placement_id, mark) for mark in marks)


def validate_hosted_point_collisions(plan: PointHostPlan, marks: tuple[MarkPlacement, ...], theme, *,
                                     paint_capabilities: PaintWitnessCapabilities = PaintWitnessCapabilities()) -> None:
    """Reject conflicting fixed glyphs in lane and non-lane compositions alike."""
    by_id = {mark.placement_id: mark for mark in marks}
    glyphs = []
    for relation in plan.relations:
        mark = by_id[relation.point.final_mark_id(relation.facet)]
        facets = _mark_facets(relation.point.item, relation.point.instance, mark, theme,
                              paint_capabilities=paint_capabilities)
        glyphs.append((relation, mark, facets))
    for index, (left, left_mark, left_facets) in enumerate(glyphs):
        for right, right_mark, right_facets in glyphs[index + 1:]:
            # One combined occurrence's Plan/Actual overlay remains declared.
            if left.point.instance == right.point.instance:
                continue
            if any(obstacles_intersect(a.visible_footprint, b.visible_footprint, 0.0)
                   for a in left_facets for b in right_facets):
                raise LayoutError("E_LAYOUT_POINT_HOST_OVERLAP", "/projection/items",
                    detail=f"fixed hosted glyphs collide: {left_mark.placement_id!r}, {right_mark.placement_id!r}")
