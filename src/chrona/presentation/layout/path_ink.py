"""Layout-owned visible bounds for stroked path geometry."""
from __future__ import annotations

from math import hypot, isfinite

from chrona.presentation.layout.path_geometry import path_extrema
from chrona.presentation.layout.surface_quality import PathCommand


def stroked_path_bounds(commands: tuple[PathCommand, ...], stroke_width: float, *,
                        line_cap: str = "butt", line_join: str = "miter"
                        ) -> tuple[float, float, float, float]:
    """Return a conservative exact-path envelope including SVG stroke finish.

    Quadratic extrema are resolved before stroke radius is added. Open butt
    caps are bounded by their perpendicular cap edge; square caps extend by
    half a stroke along the endpoint tangent. Miter joins are included only
    within SVG's fixed miter limit of four.
    """
    if (not isfinite(stroke_width) or stroke_width <= 0
            or line_cap not in {"butt", "round", "square"}
            or line_join not in {"miter", "round", "bevel"}):
        raise ValueError("E_LAYOUT_PATH_INPUT: stroked path requires positive width and supported cap/join")
    subpaths: list[list[PathCommand]] = []
    for command in commands:
        if command.kind == "move":
            subpaths.append([command])
        elif not subpaths:
            raise ValueError("E_LAYOUT_PATH_INPUT: stroked path drawing command precedes move")
        else:
            subpaths[-1].append(command)
    if not subpaths:
        raise ValueError("E_LAYOUT_PATH_INPUT: stroked path requires a nonempty path")

    radius = stroke_width / 2
    extents: list[tuple[float, float]] = []
    for commands_in_subpath in subpaths:
        start = commands_in_subpath[0].points[0]
        end = commands_in_subpath[-1].points[-1]
        segments = _subpath_segments(commands_in_subpath)
        if not segments:
            # SVG move-only subpaths paint nothing and own no cap.
            continue
        extrema = list(path_extrema(tuple(commands_in_subpath)))
        closed = start == end and len(segments) > 1
        if not closed and line_cap == "butt":
            _remove_one(extrema, start)
            _remove_one(extrema, end)
            for point, tangent in ((start, segments[0][2]), (end, segments[-1][3])):
                length = hypot(*tangent)
                if length:
                    normal = (-tangent[1] / length, tangent[0] / length)
                    extents.extend(((point[0] + sign * normal[0] * radius,
                                     point[1] + sign * normal[1] * radius)
                                    for sign in (-1, 1)))
        elif not closed and line_cap == "square":
            for point, tangent, outward in ((start, segments[0][2], -1.0),
                                            (end, segments[-1][3], 1.0)):
                length = hypot(*tangent)
                if length:
                    unit = (tangent[0] / length * outward, tangent[1] / length * outward)
                    normal = (-unit[1], unit[0])
                    extents.extend((point[0] + unit[0] * radius + sign * normal[0] * radius,
                                    point[1] + unit[1] * radius + sign * normal[1] * radius)
                                   for sign in (-1, 1))

        # Stroke bodies and round/bevel joins fit inside this radius envelope.
        for point in extrema:
            extents.extend(((point[0] - radius, point[1] - radius),
                            (point[0] + radius, point[1] + radius)))
        if line_join != "miter":
            continue
        join_count = len(segments) if closed else max(0, len(segments) - 1)
        for index in range(join_count):
            incoming = segments[index]
            outgoing = segments[(index + 1) % len(segments)]
            vertex = incoming[1]
            left = _unit(incoming[3])
            right = _unit(outgoing[2])
            if left is None or right is None:
                continue
            cross = left[0] * right[1] - left[1] * right[0]
            dot = left[0] * right[0] + left[1] * right[1]
            denominator = 1 + dot
            if abs(cross) <= 1e-12 or denominator <= 1e-12:
                continue
            normal_in = (-left[1], left[0])
            normal_out = (-right[1], right[0])
            sign = -1.0 if cross > 0 else 1.0
            scale = sign * radius / denominator
            miter = (vertex[0] + scale * (normal_in[0] + normal_out[0]),
                     vertex[1] + scale * (normal_in[1] + normal_out[1]))
            if hypot(miter[0] - vertex[0], miter[1] - vertex[1]) <= 4 * radius + 1e-9:
                extents.append(miter)
    if not extents:
        raise ValueError("E_LAYOUT_PATH_INPUT: stroked path has no painted contour")
    return (min(point[0] for point in extents), min(point[1] for point in extents),
            max(point[0] for point in extents), max(point[1] for point in extents))


def _subpath_segments(commands: list[PathCommand]):
    current = commands[0].points[0]
    segments = []
    for command in commands[1:]:
        end = command.points[-1]
        if command.kind == "line":
            start_tangent = end_tangent = (end[0] - current[0], end[1] - current[1])
        else:
            control = command.points[0]
            start_tangent = (control[0] - current[0], control[1] - current[1])
            end_tangent = (end[0] - control[0], end[1] - control[1])
            if start_tangent == (0, 0):
                start_tangent = (end[0] - current[0], end[1] - current[1])
            if end_tangent == (0, 0):
                end_tangent = (end[0] - current[0], end[1] - current[1])
        segments.append((current, end, start_tangent, end_tangent))
        current = end
    return segments


def _unit(vector: tuple[float, float]) -> tuple[float, float] | None:
    length = hypot(*vector)
    return (vector[0] / length, vector[1] / length) if length else None


def _remove_one(points: list[tuple[float, float]], target: tuple[float, float]) -> None:
    try:
        points.remove(target)
    except ValueError:
        pass
