"""Actual periodic-pattern ink contact for completed Rect and cut-Symbol hosts."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import ceil, cos, floor, hypot, isfinite, radians, sin
from typing import Any

from chrona.presentation.scene.ink_touch import InkTouchError, filled_trapezoids, subpaths
from chrona.presentation.scene.paint_analysis import is_hex_color

MAX_PATTERN_COPIES = 4096


def pattern_ink_touches(primitive: Mapping[str, Any],
                        subject_bounds: tuple[float, float, float, float]) -> bool:
    """Whether completed catalog-pattern ink touches a subject rectangle.

    The work cap counts every tile copy whose transformed cell can meet the
    subject, before checking whether that cell's ink actually touches it.
    """
    try:
        pattern = primitive["pattern"]
        paint = primitive["paint"]
        if not isinstance(pattern, Mapping) or not isinstance(paint, Mapping):
            raise InkTouchError("unreadable completed pattern or paint")
        tile_w = _positive(pattern.get("tileInlineSize"))
        tile_h = _positive(pattern.get("tileBlockSize"))
        angle = _finite(pattern.get("angleDegrees"))
        if not 0 <= angle < 360:
            raise InkTouchError("invalid pattern angle")
        origin = _pair(pattern.get("origin"))
        clip = _bounds(pattern.get("clipBounds"))
        region = _bounds(pattern.get("regionBounds"))
        primitive_bounds = _bounds(primitive.get("bounds"))
        if (clip != region or primitive_bounds != region
                or region[2] <= 0 or region[3] <= 0):
            raise InkTouchError("pattern region and clip do not match the completed host")
        ink = paint.get("stroke")
        opacity = paint.get("opacity", 1.0)
        if not is_hex_color(ink) or not _unit_interval(opacity):
            raise InkTouchError("unreadable pattern ink paint")
        raw_primitives = pattern.get("primitives")
        if not isinstance(raw_primitives, (list, tuple)) or not raw_primitives:
            raise InkTouchError("unreadable pattern primitives")
        # Validate all declared tile geometry before any possible false result.
        primitives = tuple(_tile_primitive(item) for item in raw_primitives)
        host_cells = None
        if primitive.get("kind") == "Symbol":
            symbol = primitive.get("symbol")
            if not isinstance(symbol, Mapping) or not isinstance(symbol.get("outline"), (list, tuple)):
                raise InkTouchError("unreadable completed pattern host contour")
            outline = symbol["outline"]
            host_cells = filled_trapezoids(outline)
            x, y, width, height = region
            if any(not (x <= px <= x + width and y <= py <= y + height)
                   for command in outline for point in command["points"]
                   for px, py in (_pair(point),)):
                raise InkTouchError("pattern host contour is outside its completed region")
        subject = _bounds(subject_bounds)
        clipped_subject = _intersect_rect(subject, clip)
        if clipped_subject is None:
            return False
        x, y, width, height = clipped_subject
        world_corners = ((x, y), (x + width, y), (x + width, y + height), (x, y + height))
        tile_corners = tuple(_inverse(point, origin, tile_w, tile_h, angle) for point in world_corners)
        if not all(isfinite(value) for point in tile_corners for value in point):
            raise InkTouchError("non-finite inverse pattern transform")
        min_x, max_x = min(point[0] for point in tile_corners), max(point[0] for point in tile_corners)
        min_y, max_y = min(point[1] for point in tile_corners), max(point[1] for point in tile_corners)
        first_i, last_i = ceil(min_x / tile_w) - 1, floor(max_x / tile_w)
        first_j, last_j = ceil(min_y / tile_h) - 1, floor(max_y / tile_h)
        count = max(0, last_i - first_i + 1) * max(0, last_j - first_j + 1)
        if count > MAX_PATTERN_COPIES:
            raise InkTouchError("pattern contact candidate tile-copy limit exceeded")
        if float(opacity) == 0:
            return False
        query_polygons = (world_corners,) if host_cells is None else tuple(
            polygon for cell in host_cells if (polygon := _clip_polygon_rect(cell, clipped_subject)))
        tile_polygons = tuple(tuple(_inverse(point, origin, tile_w, tile_h, angle) for point in polygon)
                              for polygon in query_polygons)
        for tile_i in range(first_i, last_i + 1):
            for tile_j in range(first_j, last_j + 1):
                for polygon in tile_polygons:
                    local = tuple((px - tile_i * tile_w, py - tile_j * tile_h) for px, py in polygon)
                    cell = _clip_polygon_rect(local, (0.0, 0.0, tile_w, tile_h))
                    if cell and any(_primitive_touches(item, cell) for item in primitives):
                        return True
        return False
    except InkTouchError:
        raise
    except (KeyError, TypeError, ValueError, OverflowError, ZeroDivisionError) as error:
        raise InkTouchError("unreadable completed pattern contact geometry") from error


def _tile_primitive(value: Any) -> tuple[str, Any]:
    if not isinstance(value, Mapping):
        raise InkTouchError("unreadable tile primitive")
    kind = value.get("kind")
    if kind == "circle":
        if not {"kind", "cx", "cy", "radius"} <= set(value) <= {
                "kind", "cx", "cy", "radius", "fillChannel", "strokeWidth"}:
            raise InkTouchError("invalid pattern circle fields")
        cx, cy, radius = (_finite(value.get(key)) for key in ("cx", "cy", "radius"))
        if radius <= 0:
            raise InkTouchError("invalid pattern circle")
        channel = value.get("fillChannel", "ink")
        if not isinstance(channel, str) or channel not in {"ink", "substrate", "none"}:
            raise InkTouchError("invalid pattern circle fill channel")
        if channel == "substrate":
            raise InkTouchError("substrate circle reached sparse-ink observer")
        stroke_width = value.get("strokeWidth")
        if "strokeWidth" in value and stroke_width is None:
            raise InkTouchError("invalid pattern circle stroke width")
        if stroke_width is not None:
            stroke_width = _positive(stroke_width)
            if stroke_width > 16:
                raise InkTouchError("invalid pattern circle stroke width")
        if channel == "none" and stroke_width is None:
            raise InkTouchError("unpainted pattern circle reached sparse-ink observer")
        return kind, (cx, cy, radius, channel, stroke_width)
    if kind == "rect":
        x, y = _finite(value.get("x")), _finite(value.get("y"))
        width, height = _positive(value.get("inlineSize")), _positive(value.get("blockSize"))
        return kind, ((x, y), (x + width, y), (x + width, y + height), (x, y + height))
    if kind != "path" or value.get("paint") not in {"fill", "stroke"}:
        raise InkTouchError("unknown tile primitive")
    commands = value.get("commands")
    if not isinstance(commands, (list, tuple)) or not commands:
        raise InkTouchError("invalid pattern path")
    outline = _path_commands(commands)
    width = None
    cap = join = None
    if value["paint"] == "stroke":
        width = _positive(value.get("strokeWidth"))
        cap, join = value.get("lineCap"), value.get("lineJoin")
        if cap not in {"butt", "round", "square"} or join not in {"miter", "round", "bevel"}:
            raise InkTouchError("invalid pattern stroke style")
    if not subpaths(outline):
        raise InkTouchError("empty pattern path")
    return value["paint"], (outline, width, cap, join)


def _path_commands(commands: Sequence[Any]) -> tuple[Mapping[str, Any], ...]:
    converted: list[Mapping[str, Any]] = []
    current_start: tuple[float, float] | None = None
    for command in commands:
        if not isinstance(command, Mapping):
            raise InkTouchError("invalid pattern path command")
        kind = command.get("kind")
        raw = command.get("points")
        if not isinstance(raw, (list, tuple)) or len(raw) % 2:
            raise InkTouchError("invalid pattern path points")
        coords = tuple(_finite(item) for item in raw)
        if kind == "close":
            if raw:
                raise InkTouchError("invalid close command")
            if current_start is None:
                raise InkTouchError("close without an open subpath")
            converted.append({"kind": "line", "points": [current_start]})
            current_start = None
            continue
        if kind != "move" and current_start is None:
            raise InkTouchError("path command outside an open subpath")
        sizes = {"move": 2, "line": 2, "quadratic": 4}
        if kind not in sizes or len(coords) != sizes[kind]:
            raise InkTouchError("invalid pattern path command")
        points = [coords[index:index + 2] for index in range(0, len(coords), 2)]
        converted.append({"kind": kind, "points": points})
        if kind == "move":
            current_start = points[0]
    # ink_touch accepts the serialized command vocabulary; close is implicit
    # for fills and explicitly added for strokes below by the polygon checker.
    return tuple(converted)


def _primitive_touches(item: tuple[str, Any], polygon: Sequence[tuple[float, float]]) -> bool:
    if len(polygon) < 1:
        return False
    kind, geometry = item
    if kind == "circle":
        cx, cy, radius, channel, stroke_width = geometry
        if channel == "ink":
            reach = radius + (stroke_width or 0.0) / 2
            if not isfinite(reach):
                raise InkTouchError("non-finite pattern circle ink radius")
            return _circle_touches((cx, cy), reach, polygon)
        if channel == "none":
            half = stroke_width / 2
            inner, outer = max(0.0, radius - half), radius + half
            if not all(isfinite(value) for value in (inner, outer)):
                raise InkTouchError("non-finite pattern circle annulus")
            minimum, maximum = _radial_range((cx, cy), polygon)
            return minimum <= outer and maximum >= inner
        raise InkTouchError("unsupported pattern circle fill channel")
    if kind == "rect":
        return _filled_polygon_touches(geometry, polygon)
    paint, (commands, width, cap, join) = kind, geometry
    paths = _command_subpaths(commands)
    if paint == "fill":
        return _filled_paths_touches(paths, polygon)
    return any(_stroke_path_touches(path, polygon, width, cap, join) for path in paths)


def _stroke_path_touches(path, polygon, width, cap, join):
    # A move-only subpath has no stroked segment. In particular, do not let
    # square-cap handling index a nonexistent adjacent point.
    if len(path) < 2:
        return False
    half = width / 2
    closed = len(path) > 2 and path[0] == path[-1]
    segments = tuple(zip(path, path[1:]))
    for a, b in segments:
        quad = _segment_quad(a, b, half)
        if quad and _filled_polygon_touches(quad, polygon):
            return True
    if closed:
        vertices = path[:-1]
        for index, vertex in enumerate(vertices):
            previous, following = vertices[index - 1], vertices[(index + 1) % len(vertices)]
            if _join_touches(previous, vertex, following, polygon, half, join):
                return True
    else:
        if cap == "round" and any(_circle_touches(endpoint, half, polygon) for endpoint in (path[0], path[-1])):
            return True
        if cap == "square":
            if _cap_quad_touches(path[0], path[1], polygon, half, start=True):
                return True
            if _cap_quad_touches(path[-1], path[-2], polygon, half, start=True):
                return True
        for index in range(1, len(path) - 1):
            if _join_touches(path[index - 1], path[index], path[index + 1], polygon, half, join):
                return True
    return False


def _segment_quad(a, b, half):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = hypot(dx, dy)
    if not all(isfinite(value) for value in (dx, dy, length)):
        raise InkTouchError("non-finite pattern stroke segment")
    if length == 0:
        return ()
    nx, ny = -dy * half / length, dx * half / length
    quad = ((a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny),
            (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny))
    if not all(isfinite(value) for point in quad for value in point):
        raise InkTouchError("non-finite pattern stroke segment bounds")
    return quad


def _cap_quad_touches(endpoint, adjacent, polygon, half, *, start):
    dx, dy = adjacent[0] - endpoint[0], adjacent[1] - endpoint[1]
    length = hypot(dx, dy)
    if not all(isfinite(value) for value in (dx, dy, length)):
        raise InkTouchError("non-finite pattern stroke cap")
    if length == 0:
        return False
    direction = (-dx / length, -dy / length) if start else (dx / length, dy / length)
    nx, ny = -dy * half / length, dx * half / length
    tip = (endpoint[0] + direction[0] * half, endpoint[1] + direction[1] * half)
    quad = ((endpoint[0] + nx, endpoint[1] + ny), (tip[0] + nx, tip[1] + ny),
            (tip[0] - nx, tip[1] - ny), (endpoint[0] - nx, endpoint[1] - ny))
    if not all(isfinite(value) for item in (direction, (nx, ny), tip) for value in item):
        raise InkTouchError("non-finite pattern stroke cap geometry")
    if not all(isfinite(value) for point in quad for value in point):
        raise InkTouchError("non-finite pattern stroke cap bounds")
    return _filled_polygon_touches(quad, polygon)


def _circle_touches(center, radius, polygon):
    minimum, _ = _radial_range(center, polygon)
    return minimum <= radius


def _radial_range(center, polygon):
    """Exact min/max center distance over a clipped convex query polygon."""
    if not polygon:
        raise InkTouchError("empty clipped circle contact polygon")
    if _point_in_polygon(center, polygon):
        minimum = 0.0
    else:
        distances = (hypot(center[0] - x, center[1] - y) for x, y in polygon)
        if len(polygon) == 1:
            minimum = next(distances)
        else:
            minimum = min(_point_segment_distance(center, a, b)
                          for a, b in _polygon_edges(polygon))
    maximum = max(hypot(center[0] - x, center[1] - y) for x, y in polygon)
    if not isfinite(minimum) or not isfinite(maximum):
        raise InkTouchError("non-finite pattern circle radial range")
    return minimum, maximum


def _join_touches(previous, vertex, following, polygon, half, join):
    incoming = (vertex[0] - previous[0], vertex[1] - previous[1])
    outgoing = (following[0] - vertex[0], following[1] - vertex[1])
    in_len, out_len = hypot(*incoming), hypot(*outgoing)
    if not isfinite(in_len) or not isfinite(out_len):
        raise InkTouchError("non-finite pattern join length")
    if in_len == 0 or out_len == 0:
        return join == "round" and _circle_touches(vertex, half, polygon)
    cross = incoming[0] * outgoing[1] - incoming[1] * outgoing[0]
    if not isfinite(cross):
        raise InkTouchError("non-finite pattern join")
    if cross == 0:
        return False
    side = -1.0 if cross > 0 else 1.0  # outer side of the turn
    n1 = (side * -incoming[1] / in_len, side * incoming[0] / in_len)
    n2 = (side * -outgoing[1] / out_len, side * outgoing[0] / out_len)
    p1 = (vertex[0] + half * n1[0], vertex[1] + half * n1[1])
    p2 = (vertex[0] + half * n2[0], vertex[1] + half * n2[1])
    if not all(isfinite(value) for point in (p1, p2) for value in point):
        raise InkTouchError("non-finite pattern join offset")
    if join == "round":
        return _circle_touches(vertex, half, polygon)
    if join == "bevel":
        return _filled_polygon_touches((vertex, p1, p2), polygon)
    miter = _line_intersection(p1, incoming, p2, outgoing)
    if miter is None:
        return _filled_polygon_touches((vertex, p1, p2), polygon)
    # Spec46 §7's conservative path envelope admits miter limits up to ten;
    # cap only at that published envelope, never at an ad hoc angle threshold.
    reach = 10 * (2 * half)
    dx, dy = miter[0] - vertex[0], miter[1] - vertex[1]
    length = hypot(dx, dy)
    if not all(isfinite(value) for value in (reach, dx, dy, length)):
        raise InkTouchError("non-finite pattern miter extent")
    if length > reach:
        # Do not clamp the unbounded miter tip into an unsupported triangle.
        # The published Scene observer contract uses a local conservative disk
        # for intersections beyond the admitted ten-width envelope.
        return _circle_touches(vertex, reach, polygon)
    return _filled_polygon_touches((vertex, p1, miter, p2), polygon)


def _line_intersection(p, r, q, s):
    denominator = r[0] * s[1] - r[1] * s[0]
    if not isfinite(denominator):
        raise InkTouchError("non-finite pattern miter denominator")
    if denominator == 0:
        return None
    delta = (q[0] - p[0], q[1] - p[1])
    numerator = delta[0] * s[1] - delta[1] * s[0]
    if not isfinite(numerator):
        raise InkTouchError("non-finite pattern miter numerator")
    t = numerator / denominator
    if not isfinite(t):
        raise InkTouchError("non-finite pattern miter parameter")
    result = (p[0] + t * r[0], p[1] + t * r[1])
    if not all(isfinite(value) for value in result):
        raise InkTouchError("non-finite pattern miter")
    return result


def _command_subpaths(commands: Sequence[Mapping[str, Any]]) -> tuple[tuple[tuple[float, float], ...], ...]:
    # Reuse the established quadratic flattening and validation. Add close as
    # explicit line segments in an auxiliary pass; fill itself is implicitly closed.
    paths = subpaths(commands)
    return paths


def _filled_paths_touches(paths: Sequence[Sequence[tuple[float, float]]], polygon: Sequence[tuple[float, float]]) -> bool:
    if any(_segment_meets_polygon(a, b, polygon)
           for path in paths for a, b in zip(path, (*path[1:], path[0]))):
        return True
    return (any(_winding(paths, point) != 0 for point in polygon)
            or any(_point_in_polygon(point, polygon) for path in paths for point in path))


def _filled_polygon_touches(shape: Sequence[tuple[float, float]], polygon: Sequence[tuple[float, float]]) -> bool:
    if len(shape) < 3:
        return False
    if len(polygon) == 1:
        return _point_in_polygon(polygon[0], shape)
    if len(polygon) == 2:
        return (_point_in_polygon(polygon[0], shape) or _point_in_polygon(polygon[1], shape)
                or any(_segments_intersect(a, b, polygon[0], polygon[1])
                       for a, b in zip(shape, (*shape[1:], shape[0]))))
    for a, b in zip(shape, (*shape[1:], shape[0])):
        if _segment_meets_polygon(a, b, polygon):
            return True
    return any(_point_in_polygon(point, shape) for point in polygon) or any(
        _point_in_polygon(point, polygon) for point in shape)


def _winding(paths: Sequence[Sequence[tuple[float, float]]], point: tuple[float, float]) -> int:
    px, py = point
    winding = 0
    for path in paths:
        if len(path) < 3:
            continue
        for (ax, ay), (bx, by) in zip(path, (*path[1:], path[0])):
            if ay <= py < by or by <= py < ay:
                crossing = ax + (py - ay) * (bx - ax) / (by - ay)
                if crossing > px:
                    winding += 1 if by > ay else -1
    return winding


def _point_in_polygon(point: tuple[float, float], polygon: Sequence[tuple[float, float]]) -> bool:
    if len(polygon) == 1:
        return hypot(point[0] - polygon[0][0], point[1] - polygon[0][1]) <= 1e-9
    if len(polygon) == 2:
        return any(_point_segment_distance(point, a, b) <= 1e-9 for a, b in _polygon_edges(polygon))
    if len(polygon) < 1:
        return False
    return _winding((polygon,), point) != 0


def _segment_meets_polygon(a: tuple[float, float], b: tuple[float, float],
                           polygon: Sequence[tuple[float, float]]) -> bool:
    return _point_in_polygon(a, polygon) or _point_in_polygon(b, polygon) or any(
        _segments_intersect(a, b, p, q) for p, q in _polygon_edges(polygon))


def _segment_polygon_distance(a: tuple[float, float], b: tuple[float, float],
                              polygon: Sequence[tuple[float, float]]) -> float:
    if _segment_meets_polygon(a, b, polygon):
        return 0.0
    return min((_segment_distance(a, b, p, q) for p, q in _polygon_edges(polygon)), default=float("inf"))


def _point_segment_distance(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = dx * dx + dy * dy
    t = 0.0 if length == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length))
    return hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def _segment_distance(a: tuple[float, float], b: tuple[float, float],
                      c: tuple[float, float], d: tuple[float, float]) -> float:
    if _segments_intersect(a, b, c, d):
        return 0.0
    return min(_point_segment_distance(a, c, d), _point_segment_distance(b, c, d),
               _point_segment_distance(c, a, b), _point_segment_distance(d, a, b))


def _segments_intersect(a: tuple[float, float], b: tuple[float, float],
                        c: tuple[float, float], d: tuple[float, float]) -> bool:
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    def on_segment(p, q, r):
        return (min(p[0], r[0]) - 1e-12 <= q[0] <= max(p[0], r[0]) + 1e-12
                and min(p[1], r[1]) - 1e-12 <= q[1] <= max(p[1], r[1]) + 1e-12)
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    return ((o1 * o2 < 0 and o3 * o4 < 0)
            or (abs(o1) <= 1e-12 and on_segment(a, c, b))
            or (abs(o2) <= 1e-12 and on_segment(a, d, b))
            or (abs(o3) <= 1e-12 and on_segment(c, a, d))
            or (abs(o4) <= 1e-12 and on_segment(c, b, d)))


def _polygon_edges(polygon: Sequence[tuple[float, float]]):
    if len(polygon) == 2:
        yield polygon[0], polygon[1]
    elif len(polygon) > 2:
        yield from zip(polygon, (*polygon[1:], polygon[0]))


def _clip_polygon_rect(polygon: Sequence[tuple[float, float]],
                       rect: tuple[float, float, float, float]) -> tuple[tuple[float, float], ...]:
    x, y, width, height = rect
    x2, y2 = x + width, y + height
    points = list(polygon)
    for inside, cross in (
        (lambda p: p[0] >= x, lambda a, b: _cross_x(a, b, x)),
        (lambda p: p[0] <= x2, lambda a, b: _cross_x(a, b, x2)),
        (lambda p: p[1] >= y, lambda a, b: _cross_y(a, b, y)),
        (lambda p: p[1] <= y2, lambda a, b: _cross_y(a, b, y2)),
    ):
        if not points:
            break
        result = []
        previous = points[-1]
        for current in points:
            if inside(current):
                if not inside(previous): result.append(cross(previous, current))
                result.append(current)
            elif inside(previous):
                result.append(cross(previous, current))
            previous = current
        points = result
    return tuple(points)


def _cross_x(a, b, x):
    ratio = 0.0 if b[0] == a[0] else (x - a[0]) / (b[0] - a[0])
    return x, a[1] + ratio * (b[1] - a[1])


def _cross_y(a, b, y):
    ratio = 0.0 if b[1] == a[1] else (y - a[1]) / (b[1] - a[1])
    return a[0] + ratio * (b[0] - a[0]), y


def _inverse(point, origin, tile_w, tile_h, angle):
    center = (tile_w / 2, tile_h / 2)
    dx, dy = point[0] - origin[0] - center[0], point[1] - origin[1] - center[1]
    theta = radians(-angle)
    return (center[0] + cos(theta) * dx - sin(theta) * dy,
            center[1] + sin(theta) * dx + cos(theta) * dy)


def _bounds(value):
    if isinstance(value, Mapping):
        keys = ("inline", "block", "inlineSize", "blockSize")
        if any(key not in value for key in keys):
            raise InkTouchError("invalid serialized pattern bounds")
        values = tuple(value[key] for key in keys)
    elif isinstance(value, (list, tuple)) and len(value) == 4:
        values = value
    else:
        raise InkTouchError("invalid pattern bounds")
    x, y, width, height = (_finite(item) for item in values)
    if width < 0 or height < 0:
        raise InkTouchError("negative pattern bounds")
    return x, y, width, height


def _intersect_rect(a, b):
    x, y, width, height = a
    bx, by, bw, bh = b
    x0, y0, x1, y1 = max(x, bx), max(y, by), min(x + width, bx + bw), min(y + height, by + bh)
    return None if x1 < x0 or y1 < y0 else (x0, y0, x1 - x0, y1 - y0)


def _pair(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise InkTouchError("invalid pattern origin")
    return _finite(value[0]), _finite(value[1])


def _positive(value):
    result = _finite(value)
    if result <= 0:
        raise InkTouchError("non-positive pattern dimension")
    return result


def _finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        raise InkTouchError("non-finite pattern value")
    return float(value)


def _unit_interval(value):
    try:
        return (not isinstance(value, bool) and isinstance(value, (int, float))
                and isfinite(float(value)) and 0 <= float(value) <= 1)
    except (OverflowError, ValueError):
        return False
