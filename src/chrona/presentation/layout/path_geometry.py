"""Completed rounded path geometry, derived only by Layout."""
from __future__ import annotations

from collections.abc import Callable
from math import hypot, inf, isfinite, nextafter

from chrona.presentation.layout.obstacles import ObstacleSegment
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


def curved_orthogonal_path(points: tuple[tuple[float, float], ...], *,
                           start_run: float = 0.0,
                           end_run: float = 0.0) -> tuple[PathCommand, ...]:
    """Smooth an orthogonal skeleton with tangent-continuous quadratic turns.

    Collinear forward vertices and repeated vertices are removed only from the
    drawn path. Each interior leg offers half its length to either adjacent
    turn; a terminal leg offers its length minus the required straight run.
    The original turn remains the quadratic control point.
    """
    _validate_orthogonal_points(points, start_run=start_run, end_run=end_run)
    route = _simplify_orthogonal_points(points)
    if len(route) < 2 or len(set(route)) < 2:
        raise _path_error("curved orthogonal path requires two distinct endpoints")

    lengths = tuple(_manhattan(left, right) for left, right in zip(route, route[1:]))
    allowances = [length / 2 for length in lengths]
    allowances[0] = max(0.0, lengths[0] - start_run)
    allowances[-1] = max(0.0, lengths[-1] - end_run)

    commands: list[PathCommand] = [PathCommand("move", (route[0],))]
    current = route[0]
    for index, vertex in enumerate(route[1:-1], 1):
        previous, following = route[index - 1], route[index + 1]
        if not _is_right_angle(previous, vertex, following):
            if current != vertex:
                commands.append(PathCommand("line", (vertex,)))
            current = vertex
            continue

        amount = min(allowances[index - 1], allowances[index])
        if amount <= 0:
            if current != vertex:
                commands.append(PathCommand("line", (vertex,)))
            current = vertex
            continue
        left, right = lengths[index - 1], lengths[index]
        before = (vertex[0] + (previous[0] - vertex[0]) * amount / left,
                  vertex[1] + (previous[1] - vertex[1]) * amount / left)
        after = (vertex[0] + (following[0] - vertex[0]) * amount / right,
                 vertex[1] + (following[1] - vertex[1]) * amount / right)
        if current != before:
            commands.append(PathCommand("line", (before,)))
        commands.append(PathCommand("quadratic", (vertex, after)))
        current = after

    if current != route[-1]:
        commands.append(PathCommand("line", (route[-1],)))
    return tuple(commands)


def conservative_path_segments(commands: tuple[PathCommand, ...], stroke_width: float, *,
                               max_deviation: float = 0.25) -> tuple[ObstacleSegment, ...]:
    """Cover a drawn path with stroked segments, conservatively enclosing quadratics.

    Each quadratic is subdivided by de Casteljau until its control hull is within
    ``max_deviation`` of its chord, or a fixed depth cap is reached. The measured
    hull-to-chord bound (not the requested tolerance) inflates each chord, so the
    cap can make the cover looser but never makes it under-approximate the curve.
    """
    if (isinstance(stroke_width, bool) or not isinstance(stroke_width, (int, float))
            or not isfinite(stroke_width) or stroke_width < 0):
        raise _path_error(f"stroke_width must be finite and nonnegative; found {stroke_width!r}")
    if (isinstance(max_deviation, bool) or not isinstance(max_deviation, (int, float))
            or not isfinite(max_deviation) or max_deviation <= 0):
        raise _path_error(f"max_deviation must be finite and positive; found {max_deviation!r}")
    if not commands or commands[0].kind != "move":
        raise _path_error("conservative path cover requires one initial move command")

    current = _finite_point(commands[0].points[0])
    segments: list[ObstacleSegment] = []
    for index, command in enumerate(commands[1:], 1):
        if command.kind == "move":
            raise _path_error(f"conservative path cover does not accept a second move at command[{index}]")
        if command.kind == "line":
            endpoint = _finite_point(command.points[0])
            if endpoint != current:
                segments.append(ObstacleSegment(current, endpoint, float(stroke_width)))
            current = endpoint
            continue
        if command.kind != "quadratic":
            raise _path_error(f"conservative path cover does not accept command[{index}] kind={command.kind!r}")
        control, endpoint = (_finite_point(point) for point in command.points)
        segments.extend(_quadratic_cover(current, control, endpoint, float(stroke_width),
                                         float(max_deviation)))
        current = endpoint
    return tuple(segments)


def _validate_orthogonal_points(points: tuple[tuple[float, float], ...], *,
                                start_run: float, end_run: float) -> None:
    if (len(points) < 2 or isinstance(start_run, bool) or isinstance(end_run, bool)
            or not isinstance(start_run, (int, float)) or not isinstance(end_run, (int, float))
            or not isfinite(start_run) or not isfinite(end_run) or start_run < 0 or end_run < 0):
        raise _path_error("curved orthogonal path requires at least two points and finite nonnegative terminal runs")
    for index, point in enumerate(points):
        if (not isinstance(point, (tuple, list)) or len(point) != 2
                or any(isinstance(value, bool) or not isinstance(value, (int, float))
                       or not isfinite(value) for value in point)):
            raise _path_error(f"point[{index}] must contain two finite coordinates")
    for index, (left, right) in enumerate(zip(points, points[1:])):
        if left[0] != right[0] and left[1] != right[1]:
            raise _path_error(f"segment {index} from {left!r} to {right!r} is diagonal; expected horizontal or vertical")


def _simplify_orthogonal_points(points: tuple[tuple[float, float], ...]) -> tuple[tuple[float, float], ...]:
    result: list[tuple[float, float]] = []
    for point in points:
        result.append((float(point[0]), float(point[1])))
        while len(result) >= 3:
            first, middle, last = result[-3:]
            first_delta = (middle[0] - first[0], middle[1] - first[1])
            second_delta = (last[0] - middle[0], last[1] - middle[1])
            dot = first_delta[0] * second_delta[0] + first_delta[1] * second_delta[1]
            collinear = (first[0] == middle[0] == last[0]
                         or first[1] == middle[1] == last[1])
            if middle == first or (collinear and dot >= 0):
                result.pop(-2)
            else:
                break
    return tuple(result)


def _manhattan(first: tuple[float, float], second: tuple[float, float]) -> float:
    return abs(second[0] - first[0]) + abs(second[1] - first[1])


def _is_right_angle(previous: tuple[float, float], vertex: tuple[float, float],
                    following: tuple[float, float]) -> bool:
    return ((previous[0] == vertex[0] and vertex[1] == following[1])
            or (previous[1] == vertex[1] and vertex[0] == following[0]))


def _finite_point(point: tuple[float, float]) -> tuple[float, float]:
    if (not isinstance(point, (tuple, list)) or len(point) != 2
            or any(isinstance(value, bool) or not isinstance(value, (int, float))
                   or not isfinite(value) for value in point)):
        raise _path_error(f"path point must contain two finite coordinates; found {point!r}")
    return float(point[0]), float(point[1])


def _quadratic_cover(start: tuple[float, float], control: tuple[float, float],
                     end: tuple[float, float], stroke_width: float,
                     max_deviation: float) -> tuple[ObstacleSegment, ...]:
    result: list[ObstacleSegment] = []
    pending = [(start, control, end, 0)]
    while pending:
        left, bend, right, depth = pending.pop()
        if left == right:
            if bend != left:
                cover_end = bend
                deviation = max(_point_segment_distance(point, left, cover_end)
                                for point in (left, bend, right))
                result.append(ObstacleSegment(
                    left, cover_end, nextafter(stroke_width + 2 * deviation, inf)))
            continue
        deviation = _point_segment_distance(bend, left, right)
        if deviation <= max_deviation or depth >= _QUADRATIC_COVER_MAX_DEPTH:
            inflated_width = nextafter(stroke_width + 2 * deviation, inf)
            result.append(ObstacleSegment(left, right, inflated_width))
            continue
        left_control = _midpoint(left, bend)
        right_control = _midpoint(bend, right)
        middle = _midpoint(left_control, right_control)
        next_depth = depth + 1
        # Reverse push order so the immutable output remains path ordered.
        pending.append((middle, right_control, right, next_depth))
        pending.append((left, left_control, middle, next_depth))
    return tuple(result)


_QUADRATIC_COVER_MAX_DEPTH = 12


def _midpoint(first: tuple[float, float], second: tuple[float, float]) -> tuple[float, float]:
    return (first[0] / 2 + second[0] / 2, first[1] / 2 + second[1] / 2)


def _point_segment_distance(point: tuple[float, float], start: tuple[float, float],
                            end: tuple[float, float]) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        return nextafter(hypot(point[0] - start[0], point[1] - start[1]), inf)
    amount = max(0.0, min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy)
                            / length_squared))
    closest = (start[0] + amount * dx, start[1] + amount * dy)
    return nextafter(hypot(point[0] - closest[0], point[1] - closest[1]), inf)


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
