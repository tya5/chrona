"""Completed rounded path geometry, derived only by Layout."""
from __future__ import annotations

from collections.abc import Callable
from math import isfinite

from chrona.presentation.layout.surface_quality import PathCommand


def _path_error(detail: str) -> ValueError:
    return ValueError(f"E_LAYOUT_PATH_INPUT: {detail}")


def rounded_orthogonal_path(points: tuple[tuple[float, float], ...], radius: float, *,
                            start_run: float = 0.0, end_run: float = 0.0,
                            blocked: Callable[[tuple[tuple[float, float], ...]], bool] | None = None,
                            ) -> tuple[PathCommand, ...]:
    """Close an orthogonal polyline into move/line/quadratic commands (#1046).

    Each turn consumes no more than half of either adjoining leg.  The original
    turn is the quadratic control point, preserving endpoint provenance.
    ``start_run`` and ``end_run`` keep that much of the first and last leg
    straight (a terminal head needs its tangent).  ``blocked`` receives the
    flattened arc of one corner; a blocked corner halves its radius until the arc
    is clear, down to a square corner.
    """
    if len(points) < 2 or radius < 0 or not isfinite(radius) or start_run < 0 or end_run < 0:
        raise _path_error(f"rounded orthogonal path requires at least two points, finite nonnegative radius/start_run/end_run; point_count={len(points)}, radius={radius!r}, start_run={start_run!r}, end_run={end_run!r}")
    for index, (left, right) in enumerate(zip(points, points[1:])):
        if left[0] != right[0] and left[1] != right[1]:
            raise _path_error(f"segment {index} from {left!r} to {right!r} is diagonal; expected horizontal or vertical")
    if radius == 0:
        return (PathCommand("move", (points[0],)),) + tuple(PathCommand("line", (point,)) for point in points[1:])
    commands: list[PathCommand] = [PathCommand("move", (points[0],))]
    current = points[0]
    for index, vertex in enumerate(points[1:-1], 1):
        previous, following = points[index - 1], points[index + 1]
        left = abs(vertex[0] - previous[0]) + abs(vertex[1] - previous[1])
        right = abs(following[0] - vertex[0]) + abs(following[1] - vertex[1])
        cap = min(radius, left / 2, right / 2)
        if (previous[0] == vertex[0] == following[0]) or (previous[1] == vertex[1] == following[1]):
            cap = 0.0  # not a turn (straight or doubled back): nothing to round
        if index == 1:
            cap = min(cap, max(0.0, left - start_run))
        if index == len(points) - 2:
            cap = min(cap, max(0.0, right - end_run))
        amount = cap
        while amount > 0:
            before = (vertex[0] + (previous[0] - vertex[0]) * amount / left,
                      vertex[1] + (previous[1] - vertex[1]) * amount / left)
            after = (vertex[0] + (following[0] - vertex[0]) * amount / right,
                     vertex[1] + (following[1] - vertex[1]) * amount / right)
            if blocked is None or not blocked(flatten_corner(before, vertex, after)):
                break
            amount = amount / 2 if amount > 0.5 else 0.0
        if amount <= 0:
            if current != vertex:
                commands.append(PathCommand("line", (vertex,)))
            current = vertex
            continue
        if current != before:
            commands.append(PathCommand("line", (before,)))
        commands.append(PathCommand("quadratic", (vertex, after)))
        current = after
    commands.append(PathCommand("line", (points[-1],)))
    return tuple(commands)


CORNER_STEPS = 4


def flatten_corner(before: tuple[float, float], control: tuple[float, float],
                   after: tuple[float, float]) -> tuple[tuple[float, float], ...]:
    """Chords of one quadratic corner arc, ``before`` to ``after`` inclusive."""
    result = []
    for step in range(CORNER_STEPS + 1):
        t = step / CORNER_STEPS
        result.append(((1 - t) ** 2 * before[0] + 2 * (1 - t) * t * control[0] + t * t * after[0],
                       (1 - t) ** 2 * before[1] + 2 * (1 - t) * t * control[1] + t * t * after[1]))
    return tuple(result)


def flatten_path(commands: tuple[PathCommand, ...]) -> tuple[tuple[float, float], ...]:
    """The drawn route as a polyline: straight commands as given, quadratics as chords."""
    result: list[tuple[float, float]] = []
    for index, command in enumerate(commands):
        if command.kind in {"move", "line"}:
            result.append(command.points[0])
        elif command.kind == "quadratic":
            result.extend(flatten_corner(result[-1], *command.points)[1:])
        else:
            raise _path_error(f"path command[{index}].kind={command.kind!r}; expected move, line, or quadratic")
    return tuple(result)


def rounded_diamond_path(*, inline: float, block: float, inline_size: float, block_size: float,
                         radius: float) -> tuple[PathCommand, ...]:
    """Return a closed rounded-diamond boundary contained in completed bounds."""
    vertices = ((inline + inline_size / 2, block), (inline + inline_size, block + block_size / 2),
                (inline + inline_size / 2, block + block_size), (inline, block + block_size / 2))
    amount = min(radius, inline_size / 4, block_size / 4)
    if amount <= 0:
        return ()
    before_after = []
    for index, vertex in enumerate(vertices):
        previous, following = vertices[index - 1], vertices[(index + 1) % len(vertices)]
        left = abs(vertex[0] - previous[0]) + abs(vertex[1] - previous[1])
        right = abs(following[0] - vertex[0]) + abs(following[1] - vertex[1])
        before_after.append(((vertex[0] + (previous[0] - vertex[0]) * amount / left,
                              vertex[1] + (previous[1] - vertex[1]) * amount / left),
                             (vertex[0] + (following[0] - vertex[0]) * amount / right,
                              vertex[1] + (following[1] - vertex[1]) * amount / right)))
    commands = [PathCommand("move", (before_after[0][0],))]
    for index, vertex in enumerate(vertices):
        commands.append(PathCommand("quadratic", (vertex, before_after[index][1])))
        if index < len(vertices) - 1:
            commands.append(PathCommand("line", (before_after[index + 1][0],)))
    commands.append(PathCommand("line", (before_after[0][0],)))
    return tuple(commands)


def open_span_path(*, inline: float, block: float, inline_size: float, block_size: float,
                   radius: float) -> tuple[PathCommand, ...]:
    """Return a closed continuation-chevron outline for a completed open span."""
    if inline_size <= 0 or block_size <= 0 or radius < 0 or not isfinite(radius):
        raise _path_error(f"open span requires positive inline_size/block_size and finite nonnegative radius; inline_size={inline_size!r}, block_size={block_size!r}, radius={radius!r}")
    terminal = min(block_size / 2, inline_size / 2)
    leading = min(radius, block_size / 2, max(0.0, (inline_size - terminal) / 2))
    left, top = inline, block
    right, bottom = inline + inline_size, block + block_size
    shoulder = right - terminal
    return (
        PathCommand("move", ((left + leading, top),)),
        PathCommand("line", ((shoulder, top),)),
        PathCommand("line", ((right, top + block_size / 2),)),
        PathCommand("line", ((shoulder, bottom),)),
        PathCommand("line", ((left + leading, bottom),)),
        PathCommand("quadratic", ((left, bottom), (left, bottom - leading))),
        PathCommand("line", ((left, top + leading),)),
        PathCommand("quadratic", ((left, top), (left + leading, top))),
    )
