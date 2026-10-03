"""Rounded rectangle outline and the strips of a per-side border that follow it (#1087).

Pure Layout geometry over completed numbers.  A rounded rectangle is four circular corner arcs joined by straight edges,
drawn as quadratic segments of at most 45 degrees (the radial error of a quadratic over 45 degrees is 0.3 percent, over
90 degrees 6 percent).  A border follows it as in CSS: the padding outline has radii ``max(R - width, 0)`` per axis (an
ellipse where the adjacent widths differ, a sharp corner where either is 0), and each side is the part of the ring
between the two outlines, cut at every corner by the mitre line from the box corner to the padding-box corner.

Corners are numbered clockwise from the start-top corner: 0 top-start, 1 top-end, 2 bottom-end, 3 bottom-start.  Angles
are in degrees in the surface frame (block axis down): the arc of corner ``k`` spans ``ARC_START[k]`` to ``+90``.
"""
from __future__ import annotations

from math import atan2, ceil, cos, degrees, radians, sin, sqrt
from typing import Mapping, Sequence

from chrona.presentation.layout.surface_quality import PathCommand

Point = tuple[float, float]
Box = tuple[float, float, float, float]
ARC_START = (180.0, 270.0, 360.0, 450.0)
MAX_PIECE_DEGREES = 45.0
# side -> (first corner, second corner) walking the outline clockwise
# The inset from both edges of a corner at which a point is on the arc: R (1 - 1/sqrt 2).
CORNER_CLEARANCE = 1.0 - 1.0 / sqrt(2.0)
SIDE_CORNERS = {"top": (0, 1), "end": (1, 2), "bottom": (2, 3), "start": (3, 0)}


def clamp_radius(radius: float, width: float, height: float) -> float:
    """The radius a ``width`` x ``height`` box can carry: at most half its shorter side."""
    return max(0.0, min(radius, width / 2, height / 2))


class _Corner:
    """One corner arc of an outline: centre, radii (both 0 when the corner is sharp) and the corner point."""

    def __init__(self, index: int, box: Box, rx: float, ry: float) -> None:
        x, y, width, height = box
        self.index = index
        if rx <= 0 or ry <= 0:
            rx = ry = 0.0
        self.rx, self.ry = rx, ry
        self.start = ARC_START[index]
        self.end = self.start + 90.0
        corner = ((x, y), (x + width, y), (x + width, y + height), (x, y + height))[index]
        sign_x = 1.0 if index in (0, 3) else -1.0
        sign_y = 1.0 if index in (0, 1) else -1.0
        self.corner = corner
        self.cx, self.cy = corner[0] + sign_x * rx, corner[1] + sign_y * ry

    def point(self, angle: float) -> Point:
        return (self.cx + self.rx * cos(radians(angle)), self.cy + self.ry * sin(radians(angle)))

    def angle_of(self, point: Point) -> float:
        """The parametric angle of ``point`` on this corner's ellipse, in the corner's own range."""
        if self.rx == 0:
            return self.start
        angle = degrees(atan2((point[1] - self.cy) / self.ry, (point[0] - self.cx) / self.rx))
        while angle < self.start - 1e-6:
            angle += 360.0
        while angle > self.end + 1e-6:
            angle -= 360.0
        return min(max(angle, self.start), self.end)

    def arc(self, first: float, last: float) -> list[PathCommand]:
        """Quadratic segments along the arc from angle ``first`` to ``last`` (either direction); none when sharp."""
        if self.rx == 0 or abs(last - first) < 1e-9:
            return []
        pieces = max(1, ceil(abs(last - first) / MAX_PIECE_DEGREES - 1e-9))
        step = (last - first) / pieces
        commands = []
        for index in range(pieces):
            a, b = first + step * index, first + step * (index + 1)
            middle, half = radians((a + b) / 2), radians(abs(b - a) / 2)
            control = (self.cx + self.rx * cos(middle) / cos(half), self.cy + self.ry * sin(middle) / cos(half))
            commands.append(PathCommand("quadratic", (control, self.point(b))))
        return commands


def _outline(box: Box, radii: Sequence[tuple[float, float]]) -> list[_Corner]:
    return [_Corner(index, box, *radii[index]) for index in range(4)]


def _trace(corners: Sequence[_Corner], first: int, first_angle: float, second: int, second_angle: float
           ) -> list[PathCommand]:
    """Walk the outline clockwise from ``first`` (at its angle) to ``second`` (at its angle)."""
    a, b = corners[first], corners[second]
    commands = a.arc(first_angle, a.end)
    commands.append(PathCommand("line", (b.point(b.start),)))
    commands.extend(b.arc(b.start, second_angle))
    return commands


def _trace_back(corners: Sequence[_Corner], first: int, first_angle: float, second: int, second_angle: float
                ) -> list[PathCommand]:
    """Walk the outline anticlockwise from ``second`` (at its angle) back to ``first`` (at its angle)."""
    a, b = corners[first], corners[second]
    commands = b.arc(second_angle, b.start)
    commands.append(PathCommand("line", (a.point(a.end),)))
    commands.extend(a.arc(a.end, first_angle))
    return commands


def rounded_rect_commands(box: Box, radius: float) -> tuple[PathCommand, ...]:
    """The closed outline of a rounded rectangle as ``move``, ``line`` and ``quadratic`` commands."""
    x, y, width, height = box
    radius = clamp_radius(radius, width, height)
    corners = _outline(box, [(radius, radius)] * 4)
    commands = [PathCommand("move", (corners[0].point(corners[0].start),))]
    for index in range(4):
        corner = corners[index]
        commands.extend(corner.arc(corner.start, corner.end))
        commands.append(PathCommand("line", (corners[(index + 1) % 4].point(corners[(index + 1) % 4].start),)))
    return tuple(commands)


def commands_points(commands: Sequence[PathCommand], samples: int = 4) -> list[Point]:
    """The outline as a polyline: the on-curve points, with ``samples`` points inside each quadratic."""
    points: list[Point] = []
    for command in commands:
        if command.kind != "quadratic":
            points.append(command.points[0])
            continue
        (cx, cy), (ex, ey) = command.points
        sx, sy = points[-1]
        for step in range(1, samples + 1):
            t = step / samples
            points.append(((1 - t) ** 2 * sx + 2 * (1 - t) * t * cx + t * t * ex,
                           (1 - t) ** 2 * sy + 2 * (1 - t) * t * cy + t * t * ey))
    return points


def _local(corner: int, box: Box, u: float, v: float) -> Point:
    """Map a point ``u`` inward along the inline axis and ``v`` inward along the block axis from ``corner``."""
    x, y, width, height = box
    return (x + u if corner in (0, 3) else x + width - u, y + v if corner in (0, 1) else y + height - v)


def border_strip(side: str, box: Box, radius: float, widths: Mapping[str, float]) -> tuple[PathCommand, ...]:
    """The closed strip of ``side`` of a border of ``widths`` (start, end, top, bottom) on a rounded ``box``."""
    x, y, width, height = box
    radius = clamp_radius(radius, width, height)
    bl, br, bt, bb = widths["start"], widths["end"], widths["top"], widths["bottom"]
    inner_box = (x + bl, y + bt, max(width - bl - br, 0.0), max(height - bt - bb, 0.0))
    # (inline width, block width) of the two sides that meet at each corner
    meeting = ((bl, bt), (br, bt), (br, bb), (bl, bb))
    outer = _outline(box, [(radius, radius)] * 4)
    inner = _outline(inner_box, [(max(radius - wv, 0.0), max(radius - wh, 0.0)) for wv, wh in meeting])
    first, second = SIDE_CORNERS[side]
    cuts = {}
    for index in (first, second):
        wv, wh = meeting[index]
        t = radius * ((wv + wh) - sqrt(2 * wv * wh)) / (wv * wv + wh * wh) if radius > 0 else 0.0
        outer_point = _local(index, box, t * wv, t * wh)
        rx, ry = inner[index].rx, inner[index].ry
        if rx > 0:
            a_coef, b_coef = (wv / rx) ** 2 + (wh / ry) ** 2, wv / rx + wh / ry
            s = (b_coef - sqrt(max(b_coef * b_coef - a_coef, 0.0))) / a_coef
            inner_point = _local(index, box, (1 + s) * wv, (1 + s) * wh)
        else:
            inner_point = inner[index].corner
        cuts[index] = (outer[index].angle_of(outer_point), outer_point,
                       inner[index].angle_of(inner_point), inner_point)
    commands = [PathCommand("move", (cuts[first][1],))]
    commands.extend(_trace(outer, first, cuts[first][0], second, cuts[second][0]))
    commands.append(PathCommand("line", (cuts[second][3],)))
    commands.extend(_trace_back(inner, first, cuts[first][2], second, cuts[second][2]))
    commands.append(PathCommand("line", (cuts[first][1],)))
    return tuple(commands)
