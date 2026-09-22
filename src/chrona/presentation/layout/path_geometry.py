"""Completed rounded path geometry, derived only by Layout."""
from __future__ import annotations

from math import isfinite

from chrona.presentation.layout.surface_quality import PathCommand


def rounded_orthogonal_path(points: tuple[tuple[float, float], ...], radius: float) -> tuple[PathCommand, ...]:
    """Close an orthogonal polyline into move/line/quadratic commands.

    Each turn consumes no more than half of either adjoining leg.  The original
    turn is the quadratic control point, preserving endpoint provenance.
    """
    if len(points) < 2 or radius < 0 or not isfinite(radius):
        raise ValueError("E_LAYOUT_PATH_INPUT")
    if any(left[0] != right[0] and left[1] != right[1] for left, right in zip(points, points[1:])):
        raise ValueError("E_LAYOUT_PATH_INPUT")
    if radius == 0:
        return (PathCommand("move", (points[0],)),) + tuple(PathCommand("line", (point,)) for point in points[1:])
    commands: list[PathCommand] = [PathCommand("move", (points[0],))]
    current = points[0]
    for index, vertex in enumerate(points[1:-1], 1):
        previous, following = points[index - 1], points[index + 1]
        if not ((previous[0] == vertex[0] or previous[1] == vertex[1]) and (following[0] == vertex[0] or following[1] == vertex[1])):
            raise ValueError("E_LAYOUT_PATH_INPUT")
        left = abs(vertex[0] - previous[0]) + abs(vertex[1] - previous[1])
        right = abs(following[0] - vertex[0]) + abs(following[1] - vertex[1])
        amount = min(radius, left / 2, right / 2)
        before = (vertex[0] + (previous[0] - vertex[0]) * amount / left,
                  vertex[1] + (previous[1] - vertex[1]) * amount / left)
        after = (vertex[0] + (following[0] - vertex[0]) * amount / right,
                 vertex[1] + (following[1] - vertex[1]) * amount / right)
        if current != before:
            commands.append(PathCommand("line", (before,)))
        commands.append(PathCommand("quadratic", (vertex, after)))
        current = after
    commands.append(PathCommand("line", (points[-1],)))
    return tuple(commands)


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
