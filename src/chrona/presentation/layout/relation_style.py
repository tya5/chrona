"""Complete an optional route appearance without changing selected routing policy."""
from collections.abc import Callable
from dataclasses import replace

from chrona.presentation.layout.obstacles import ObstacleSegment, obstacles_intersect
from chrona.presentation.layout.path_geometry import (
    conservative_path_segments, curved_orthogonal_path, metro_orthogonal_path,
)
from chrona.presentation.layout.relation_style_model import RelationStyleFallback
from chrona.presentation.layout.surface_quality import PathCommand, RelationPlacement


def changed_path_segments(commands: tuple[PathCommand, ...], stroke_width: float
                         ) -> tuple[ObstacleSegment, ...]:
    """Cover changed arcs and diagonals; retained axis-aligned runs were admitted."""
    result = []
    current = None
    for command in commands:
        if command.kind == "quadratic" or (command.kind == "line" and current is not None
                and current[0] != command.points[-1][0] and current[1] != command.points[-1][1]):
            result.extend(conservative_path_segments(
                (PathCommand("move", (current,)), command), stroke_width))
        current = command.points[-1]
    return tuple(result)


def _self_crosses(commands: tuple[PathCommand, ...]) -> bool:
    """Conservatively reject crossings of nonadjacent drawn path commands.

    A quadratic corner is monotone and its adjacent commands meet only at its
    tangent boundary. Nonadjacent covers use zero ink width: local stroke joins
    are not mistaken for a second centreline traversal.
    """
    groups = []
    current = None
    for command in commands:
        if command.kind != "move" and current != command.points[-1]:
            groups.append(conservative_path_segments(
                (PathCommand("move", (current,)), command), 0.0))
        current = command.points[-1]
    return any(obstacles_intersect(left, right)
               for index, first in enumerate(groups)
               for second in groups[index + 2:]
               for left in first for right in second)


def complete_relation_style(
    placement: RelationPlacement, *, style: str, stroke_width: float,
    start_run: float, end_run: float, recovery: bool,
    reject: Callable[[RelationPlacement, tuple[ObstacleSegment, ...]], str | None],
    join_radius: float | None = None,
) -> tuple[RelationPlacement, tuple[ObstacleSegment, ...]]:
    """Keep the existing mode verbatim unless the complete styled path is safe.

    Surface owners supply their actual stage-specific safety checks. The cover
    is returned for registration so subsequent placements see the same geometry
    that was admitted, rather than a less accurate resampling of it.
    """
    if style == "orthogonal":
        return placement, ()
    if style not in {"curved", "metro"}:
        raise ValueError("E_LAYOUT_PATH_INPUT: unsupported relation route style")

    def fallback(reason: str):
        return replace(placement, style_fallback=RelationStyleFallback(
            placement.relation_id, reason, requested=style)), ()

    if recovery or any(left[0] != right[0] and left[1] != right[1]
                       for left, right in zip(placement.points, placement.points[1:])):
        return fallback("recovery")
    commands = (curved_orthogonal_path(placement.points, start_run=start_run, end_run=end_run)
                if style == "curved" else metro_orthogonal_path(placement.points,
                    radius=stroke_width if join_radius is None else join_radius,
                    start_run=start_run, end_run=end_run))
    turns = any(not (a[0] == b[0] == c[0] or a[1] == b[1] == c[1])
                for a, b, c in zip(placement.points, placement.points[1:], placement.points[2:]))
    changed = (any(command.kind == "quadratic" for command in commands) if style == "curved"
               else any(command.kind == "line"
                        and previous.points[-1][0] != command.points[-1][0]
                        and previous.points[-1][1] != command.points[-1][1]
                        for previous, command in zip(commands, commands[1:])))
    if turns and not changed:
        return fallback("terminal")
    cover = conservative_path_segments(commands, stroke_width)
    candidate = replace(placement, path_commands=commands, corner_radius=0.0)
    if _self_crosses(commands):
        return fallback("self-overlap")
    reason = reject(candidate, cover)
    if reason is not None:
        return fallback(reason)
    return candidate, cover
