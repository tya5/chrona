"""Does the painted area of a completed Symbol outline meet a rectangle (#848)?

The contrast gate reads the serialized Scene alone. A vector artwork behind an annotation is a few `Symbol` parts
whose bounds are the whole note, so a bounds test cannot say whether a line of text lies on the artwork's ink or in
the paper a frame leaves open. This module answers from the part's own outline: a fill part is its closed path under
the non-zero winding rule (a hole wound the other way is empty), a stroke part is the flattened path widened by half
its stroke width. Pure arithmetic, no clock, hash or ordering dependence.
"""
from __future__ import annotations

from math import hypot, isfinite
from typing import Any, Iterable, Mapping, Sequence

Point = tuple[float, float]
Rect = tuple[float, float, float, float]  # x, y, width, height

# A quadratic is flattened to this many chords. The chord deviates from the curve by at most 1/(4 n^2) of the
# distance between the control point and the chord's midpoint, so the test is exact for lines and within a small,
# fixed fraction of the curve's own height for a curve. The stroke test adds nothing for the deviation: the
# half-width pad of a stroke dwarfs it for any stroke that is visible.
QUADRATIC_CHORDS = 8


class InkTouchError(ValueError):
    """A malformed outline: not a list of finite `move`, `line` and `quadratic` commands."""


def subpaths(outline: Iterable[Mapping[str, Any]], *, include_degenerate: bool = False) -> tuple[tuple[Point, ...], ...]:
    """Flatten a completed outline into polylines, one per `move`; a closing line stays an explicit point."""
    result: list[list[Point]] = []
    for command in outline:
        kind = command.get("kind") if isinstance(command, Mapping) else None
        points = command.get("points") if isinstance(command, Mapping) else None
        try:
            coords = [(float(point[0]), float(point[1])) for point in points]  # type: ignore[union-attr]
        except (TypeError, ValueError, IndexError) as error:
            raise InkTouchError("invalid outline point") from error
        if not all(isfinite(value) for point in coords for value in point):
            raise InkTouchError("non-finite outline point")
        if kind == "move" and len(coords) == 1:
            result.append([coords[0]])
        elif kind == "line" and len(coords) == 1 and result:
            result[-1].append(coords[0])
        elif kind == "quadratic" and len(coords) == 2 and result:
            start, (control, end) = result[-1][-1], coords
            for step in range(1, QUADRATIC_CHORDS + 1):
                t = step / QUADRATIC_CHORDS
                u = 1.0 - t
                result[-1].append((u * u * start[0] + 2 * u * t * control[0] + t * t * end[0],
                                   u * u * start[1] + 2 * u * t * control[1] + t * t * end[1]))
        else:
            raise InkTouchError("invalid outline command")
    return tuple(tuple(path) for path in result if include_degenerate or len(path) >= 2)


def fill_touches(outline: Sequence[Mapping[str, Any]], bounds: Rect) -> bool:
    """True when the filled area of `outline` (non-zero winding, every subpath closed) meets `bounds`."""
    paths = subpaths(outline)
    x0, y0, width, height = bounds
    x1, y1 = x0 + width, y0 + height
    for path in paths:
        for start, end in _edges(path, closed=True):
            if _segment_meets_rect(start, end, x0, y0, x1, y1):
                return True
    # No edge meets the rectangle, so it lies wholly inside or wholly outside the filled area: one point decides.
    centre = ((x0 + x1) / 2, (y0 + y1) / 2)
    return sum(_winding(path, centre) for path in paths) != 0


def filled_trapezoids(outline: Sequence[Mapping[str, Any]]) -> tuple[tuple[Point, ...], ...]:
    """Convex cells of the completed nonzero fill, using the same curve chords.

    Vertex and crossing heights divide the paths into bands where edge order
    is fixed. Winding selects filled intervals, preserving holes and overlaps.
    This decomposes supplied ink; it does not create Layout placements.
    """
    paths = subpaths(outline, include_degenerate=True)
    if not paths or any(len(path) < 4 or path[-1] != path[0] for path in paths):
        raise InkTouchError("pattern host requires closed nondegenerate subpaths")
    edges = tuple((a, b) for path in paths for a, b in zip(path, path[1:]) if a[1] != b[1])
    heights = {point[1] for path in paths for point in path}
    for index, (a, b) in enumerate(edges):
        for c, d in edges[index + 1:]:
            if max(min(a[1], b[1]), min(c[1], d[1])) >= min(max(a[1], b[1]), max(c[1], d[1])):
                continue
            ax, ay = b[0] - a[0], b[1] - a[1]
            cx, cy = d[0] - c[0], d[1] - c[1]
            denominator = ax * cy - ay * cx
            if denominator == 0:
                continue
            dx, dy = c[0] - a[0], c[1] - a[1]
            t = (dx * cy - dy * cx) / denominator
            u = (dx * ay - dy * ax) / denominator
            if not all(isfinite(value) for value in (denominator, t, u)):
                raise InkTouchError("non-finite host contour crossing")
            if 0 < t < 1 and 0 < u < 1:
                heights.add(a[1] + t * ay)

    def at(edge, y):
        a, b = edge
        value = a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
        if not isfinite(value):
            raise InkTouchError("non-finite host contour band")
        return value

    result = []
    ordered = sorted(heights)
    for low, high in zip(ordered, ordered[1:]):
        mid = low + (high - low) / 2
        if not isfinite(mid):
            raise InkTouchError("non-finite host contour band")
        crossings = sorted((at(edge, mid), edge) for edge in edges
                           if min(edge[0][1], edge[1][1]) < mid < max(edge[0][1], edge[1][1]))
        winding = 0
        previous = None
        for position, edge in crossings:
            if winding and previous is not None and previous[0] < position:
                left = previous[1]
                result.append(((at(left, low), low), (at(edge, low), low),
                               (at(edge, high), high), (at(left, high), high)))
            winding += 1 if edge[1][1] > edge[0][1] else -1
            previous = (position, edge)
        if winding:
            raise InkTouchError("unclosed host contour winding")
    if not result:
        raise InkTouchError("empty host contour fill")
    return tuple(result)


def stroke_touches(outline: Sequence[Mapping[str, Any]], bounds: Rect, stroke_width: float) -> bool:
    """True when a stroke of `stroke_width` along `outline` comes within half its width of `bounds`."""
    reach = max(0.0, float(stroke_width)) / 2.0
    x0, y0, width, height = bounds
    x1, y1 = x0 + width, y0 + height
    for path in subpaths(outline):
        for start, end in _edges(path, closed=False):
            if _segment_rect_distance(start, end, x0, y0, x1, y1) <= reach + 1e-9:
                return True
    return False


def _edges(path: Sequence[Point], *, closed: bool) -> Iterable[tuple[Point, Point]]:
    for index in range(len(path) - 1):
        yield path[index], path[index + 1]
    if closed and path[0] != path[-1]:
        yield path[-1], path[0]


def _winding(path: Sequence[Point], point: Point) -> int:
    """The winding number of the closed `path` around `point` (the crossing rule of a ray to +x)."""
    px, py = point
    total = 0
    for (ax, ay), (bx, by) in _edges(path, closed=True):
        if ay <= py < by or by <= py < ay:
            crossing = ax + (py - ay) * (bx - ax) / (by - ay)
            if crossing > px:
                total += 1 if by > ay else -1
    return total


def _segment_meets_rect(a: Point, b: Point, x0: float, y0: float, x1: float, y1: float) -> bool:
    """Liang-Barsky clip of the segment against the closed rectangle: does any part of it lie inside?"""
    t0, t1 = 0.0, 1.0
    dx, dy = b[0] - a[0], b[1] - a[1]
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if p == 0.0:
            if q < 0.0:
                return False
            continue
        t = q / p
        if p < 0.0:
            if t > t1:
                return False
            t0 = max(t0, t)
        else:
            if t < t0:
                return False
            t1 = min(t1, t)
    return t0 <= t1


def _segment_rect_distance(a: Point, b: Point, x0: float, y0: float, x1: float, y1: float) -> float:
    if _segment_meets_rect(a, b, x0, y0, x1, y1):
        return 0.0
    corners = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    ends = min(_point_rect_distance(a, x0, y0, x1, y1), _point_rect_distance(b, x0, y0, x1, y1))
    sides = min(_point_segment_distance(corner, a, b) for corner in corners)
    return min(ends, sides)


def _point_rect_distance(point: Point, x0: float, y0: float, x1: float, y1: float) -> float:
    return hypot(max(x0 - point[0], 0.0, point[0] - x1), max(y0 - point[1], 0.0, point[1] - y1))


def _point_segment_distance(point: Point, a: Point, b: Point) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = dx * dx + dy * dy
    t = 0.0 if length == 0.0 else max(0.0, min(1.0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / length))
    return hypot(point[0] - (a[0] + t * dx), point[1] - (a[1] + t * dy))
