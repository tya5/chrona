"""Complete dependency-network routes, shared Theme terminals, and honest fallback evidence."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from math import isfinite
from typing import Any

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.network_ink import relation_paint_bounds
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, obstacles_intersect
from chrona.presentation.layout.path_geometry import flatten_path
from chrona.presentation.layout.relation_terminals import (
    centred_on_route, complete_centred_terminals, marker_geometry, project_marker_outline, terminal_run,
)
from chrona.presentation.layout.relation_style import complete_relation_style, curved_path_segments
from chrona.presentation.layout.routing import place_relation_route, relation_route_quality
from chrona.presentation.layout.route_search import RouteSearchFailure
from chrona.presentation.layout.surface_quality import FitWarning, MarkerGeometry, PathCommand, RelationPlacement
from chrona.presentation.model.diagnostic_sources import DiagnosticSubject
from chrona.presentation.model.render_progress import RenderProgress
from chrona.presentation.model.semantic_registry import semantic_binding
from chrona.presentation.model.theme_tokens import ThemeTokenView

Point = tuple[float, float]
PortPair = tuple[Point, Point]


def complete_network_routes(
    edges: Sequence[Any], *, ports: Mapping[str, PortPair], obstacles: Mapping[str, Rect],
    subjects: Mapping[str, DiagnosticSubject], bounds: Rect, max_bends: int,
    max_detour_ratio: float, theme_tokens: ThemeTokenView | None,
    progress: RenderProgress | None = None,
    relation_style: str = "orthogonal",
) -> tuple[tuple[RelationPlacement, ...], tuple[FitWarning, ...]]:
    """Complete each selected network edge through the existing deterministic route search.

    `ports[id]` is `(input, output)` and the obstacle inventory contains leaf nodes
    and actual group headers.  Theme absence is reserved for direct synthetic use;
    production callers supply the closed resolved Theme.
    """
    declarations = tuple(edges)
    if (isinstance(max_bends, bool) or not isinstance(max_bends, int) or max_bends < 0
            or isinstance(max_detour_ratio, bool) or not isinstance(max_detour_ratio, (int, float))
            or not isfinite(max_detour_ratio) or max_detour_ratio < 0):
        raise ValueError("E_LAYOUT_ROUTE_SEARCH_INPUT: invalid dependency-network quality limits")
    extent = (float(bounds.inline), float(bounds.block),
              float(bounds.inline + bounds.inline_size), float(bounds.block + bounds.block_size))
    if not all(isfinite(value) for value in extent) or extent[0] >= extent[2] or extent[1] >= extent[3]:
        raise ValueError("E_LAYOUT_ROUTE_SEARCH_INPUT: invalid dependency-network route bounds")
    obstacle_rects = {key: ObstacleRect(float(rect.inline), float(rect.block),
                                        float(rect.inline + rect.inline_size),
                                        float(rect.block + rect.block_size))
                      for key, rect in obstacles.items()}
    if any(not isinstance(value, DiagnosticSubject) for value in subjects.values()):
        raise ValueError("E_LAYOUT_NETWORK_GRAPH: route subjects must be DiagnosticSubject values")

    if not declarations:
        return (), ()

    resolved_ink: dict[str, tuple[float, MarkerGeometry | None, MarkerGeometry | None]] = {}
    if theme_tokens is not None:
        used_semantics = tuple(dict.fromkeys(
            "criticalEdge" if edge.critical else "networkEdge" for edge in declarations
        ))
        for semantic_id in used_semantics:
            role = semantic_binding(semantic_id).theme_role
            stroke = float(theme_tokens.number(role, "strokeWidth"))
            if not isfinite(stroke) or stroke <= 0:
                raise ValueError(f"E_THEME_TOKEN_TYPE: /body/roles/{role}/strokeWidth")
            # Scene resolves actual stroke/opacity from this semantic role; Layout
            # reads only width here because it changes the physical safety envelope.
            theme_tokens.optional_number(role, "opacity")
            start = marker_geometry(theme_tokens.marker("relationSourceTerminal"), stroke_width=stroke)
            end = marker_geometry(theme_tokens.marker("relationTargetTerminal"), stroke_width=stroke)
            resolved_ink[semantic_id] = (stroke, start, end)

    relations: list[RelationPlacement] = []
    warnings: list[FitWarning] = []
    iterator = (progress.routing(declarations, pass_name="network")
                if progress is not None else iter(declarations))
    for edge in iterator:
        source_id, target_id = edge.source_id, edge.target_id
        try:
            source_port = tuple(ports[source_id][1])
            target_port = tuple(ports[target_id][0])
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError(f"E_LAYOUT_NETWORK_GRAPH: missing completed port for relation {edge.relation_id}") from error
        if (len(source_port) != 2 or len(target_port) != 2
                or any(isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value)
                       for value in (*source_port, *target_port))):
            raise ValueError(f"E_LAYOUT_NETWORK_GRAPH: invalid completed port for relation {edge.relation_id}")
        source_port, target_port = (float(source_port[0]), float(source_port[1])), (float(target_port[0]), float(target_port[1]))
        semantic_id = "criticalEdge" if edge.critical else "networkEdge"
        if theme_tokens is None:
            stroke, marker_start, marker_end = 0.0, None, None
        else:
            stroke, marker_start, marker_end = resolved_ink[semantic_id]
        marker_start = centred_on_route(marker_start, "source")
        marker_end = centred_on_route(marker_end, "target")
        search_obstacles = tuple(
            (rect.left - stroke / 2, rect.top - stroke / 2,
             rect.right + stroke / 2, rect.bottom + stroke / 2)
            for key, rect in sorted(obstacle_rects.items()) if key not in {source_id, target_id}
        )
        fallback_reason: str | None = None
        try:
            points = place_relation_route(source_port=source_port, target_port=target_port,
                                          obstacles=search_obstacles, bounds=extent)
        except RouteSearchFailure as error:
            detail = str(getattr(error, "detail", "") or error)
            fallback_reason = "route-bounds" if "bounds exclude" in detail else "route-search"
            points = (source_port, target_port)
        if fallback_reason is None and not relation_route_quality(
                points, max_bends=max_bends, max_detour_ratio=max_detour_ratio):
            fallback_reason = "route-quality-limit"
        if fallback_reason is not None:
            points = (source_port, target_port)
        points, marker_start, marker_end = complete_centred_terminals(
            tuple(points), marker_start, marker_end, stroke)
        commands = _path_commands(tuple(points))
        if fallback_reason is None:
            blockers = _route_blockers(tuple(points), stroke, obstacle_rects,
                                       source_id=source_id, target_id=target_id)
            terminal_blockers: set[str] = set()
            if not blockers:
                terminal_blockers = _terminal_blockers(
                    tuple(points), commands, marker_start, marker_end, stroke, obstacle_rects,
                    source_id=source_id, target_id=target_id)
                blockers = terminal_blockers
            if blockers:
                fallback_reason = ("route-terminal-obstacle-crossing" if terminal_blockers
                                   else "route-stroke-obstacle-crossing")
                points = (source_port, target_port)
                points, marker_start, marker_end = complete_centred_terminals(
                    tuple(points), marker_start, marker_end, stroke)
                commands = _path_commands(tuple(points))

        if fallback_reason is not None:
            crossed = _route_blockers(tuple(points), stroke, obstacle_rects,
                                      source_id=source_id, target_id=target_id)
            crossed.update(_terminal_blockers(tuple(points), commands, marker_start, marker_end,
                                              stroke, obstacle_rects,
                                              source_id=source_id, target_id=target_id))
            warning_subjects = tuple(subjects[item] for item in sorted(crossed) if item in subjects)
            warnings.append(FitWarning(
                "W_LAYOUT_ROUTE_FALLBACK", edge.relation_id,
                f"/projection/network/edges/{edge.relation_id}", fallback_reason,
                "direct-path-crosses-node" if crossed else "direct-path-visible-overflow",
                0.0, 0.0, float(bounds.inline_size), float(bounds.block_size), warning_subjects,
            ))

        placement = RelationPlacement(
            edge.relation_id, f"{source_id}:output", f"{target_id}:input", tuple(points),
            semantic_id=semantic_id, path_commands=commands, marker_start=marker_start,
            marker_end=marker_end, slot_id="network", paint_order=100,
            from_instance_id=source_id, to_instance_id=target_id,
        )
        def reject_curve(candidate, cover):
            for segment in curved_path_segments(candidate.path_commands, stroke):
                radius = segment.stroke_width / 2
                if (min(segment.start[0], segment.end[0]) - radius < extent[0]
                        or min(segment.start[1], segment.end[1]) - radius < extent[1]
                        or max(segment.start[0], segment.end[0]) + radius > extent[2]
                        or max(segment.start[1], segment.end[1]) + radius > extent[3]):
                    return "bounds"
                # Node/group headers contain their required text. The changed
                # arcs must clear every host, including both endpoint hosts.
                if any(obstacles_intersect(segment, rect) for rect in obstacle_rects.values()):
                    return "clearance"
            if _terminal_blockers(candidate.points, candidate.path_commands,
                    candidate.marker_start, candidate.marker_end, stroke, obstacle_rects,
                    source_id=source_id, target_id=target_id):
                return "terminal"
            return None
        placement, _ = complete_relation_style(placement, style=relation_style,
            stroke_width=stroke, start_run=terminal_run(marker_start),
            end_run=terminal_run(marker_end), recovery=fallback_reason is not None,
            reject=reject_curve)
        relations.append(replace(placement, paint_bounds=relation_paint_bounds(placement, theme_tokens)))
    return tuple(relations), tuple(warnings)


def _path_commands(points: tuple[Point, ...]) -> tuple[PathCommand, ...]:
    return ((PathCommand("move", (points[0],)),)
            + tuple(PathCommand("line", (point,)) for point in points[1:]))


def _route_blockers(points: tuple[Point, ...], stroke: float,
                    obstacles: Mapping[str, ObstacleRect], *, source_id: str, target_id: str) -> set[str]:
    return {
        object_id
        for object_id, rect in obstacles.items() if object_id not in {source_id, target_id}
        if any(obstacles_intersect(ObstacleSegment(left, right, stroke), rect)
               for left, right in zip(points, points[1:]) if left != right)
    }


def _terminal_blockers(points: tuple[Point, ...], commands: tuple[PathCommand, ...],
                       start: MarkerGeometry | None, end: MarkerGeometry | None, stroke: float,
                       obstacles: Mapping[str, ObstacleRect], *, source_id: str, target_id: str) -> set[str]:
    result: set[str] = set()
    for marker, side in ((start, "start"), (end, "end")):
        if marker is None:
            continue
        outline = project_marker_outline(marker, side=side, points=points,
                                         path_commands=commands, stroke_width=stroke or None)
        for object_id, rect in obstacles.items():
            if object_id in {source_id, target_id}:
                continue
            if _marker_intersects_rect(outline, rect, stroke if marker.paint_mode == "stroke" else 0.0):
                result.add(object_id)
    return result


def _marker_intersects_rect(outline: tuple[PathCommand, ...], rect: ObstacleRect,
                            stroke: float) -> bool:
    subpaths: list[list[PathCommand]] = []
    for command in outline:
        if command.kind == "move":
            subpaths.append([command])
        elif not subpaths:
            continue
        else:
            subpaths[-1].append(command)
    for subpath in subpaths:
        points = flatten_path(tuple(subpath))
        if any(rect.left < x < rect.right and rect.top < y < rect.bottom for x, y in points):
            return True
        if any(obstacles_intersect(ObstacleSegment(left, right, stroke), rect)
               for left, right in zip(points, points[1:]) if left != right):
            return True
        if stroke == 0 and _rect_corner_inside_polygon(rect, points):
            return True
    return False


def _rect_corner_inside_polygon(rect: ObstacleRect, points: tuple[Point, ...]) -> bool:
    if len(points) < 3:
        return False
    corners = ((rect.left, rect.top), (rect.right, rect.top),
               (rect.right, rect.bottom), (rect.left, rect.bottom))
    for x, y in corners:
        inside = False
        for (x1, y1), (x2, y2) in zip(points, (*points[1:], points[0])):
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                inside = not inside
        if inside:
            return True
    return False
