"""Layout-owned balloon outline: a box plus an integrated triangular tail.

The balloon is one closed path -- the box outline with the tail built into
the nearest eligible edge, tip at the named anchor port (#466).  This module
only computes geometry; Theme supplies the corner radius and tail base
width (in em), and the caller is responsible for collision-testing the tail
edges before the candidate is committed.
"""
from __future__ import annotations

from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.surface_quality import PathCommand

Point = tuple[float, float]


def nearest_eligible_edge(box: LabelRect, tip: Point) -> str:
    """Return the box edge the tip protrudes past the most."""
    outward = {
        "top": box.y - tip[1],
        "bottom": tip[1] - box.bottom,
        "left": box.x - tip[0],
        "right": tip[0] - box.right,
    }
    return max(outward, key=lambda side: outward[side])


def tail_base_points(box: LabelRect, tip: Point, *, edge: str, tail_base: float,
                     corner_radius: float) -> tuple[Point, Point]:
    """Return the two tail-base points on ``edge``, ordered with the edge's own
    clockwise direction and clamped clear of the (optionally rounded) corners.
    """
    if edge in ("top", "bottom"):
        y = box.y if edge == "top" else box.bottom
        low, high = box.x + corner_radius, box.right - corner_radius
        if high < low:
            low, high = box.x, box.right
        center = min(max(tip[0], low), high)
        half = min(tail_base / 2, max(0.0, (high - low) / 2))
        a, b = center - half, center + half
        return ((a, y), (b, y)) if edge == "top" else ((b, y), (a, y))
    x = box.x if edge == "left" else box.right
    low, high = box.y + corner_radius, box.bottom - corner_radius
    if high < low:
        low, high = box.y, box.bottom
    center = min(max(tip[1], low), high)
    half = min(tail_base / 2, max(0.0, (high - low) / 2))
    a, b = center - half, center + half
    return ((x, b), (x, a)) if edge == "left" else ((x, a), (x, b))


def balloon_outline(box: LabelRect, tip: Point, *, corner_radius: float, tail_base: float) -> tuple[PathCommand, ...]:
    """Return the closed box+tail outline as absolute Layout path commands.

    Corners are rendered as a straight chamfer of ``corner_radius`` rather
    than a true arc: a single closed polygon keeps the tail-edge collision
    test (two straight segments) exact and keeps this geometry renderer
    neutral without introducing curve-specific obstacle math.
    """
    if corner_radius < 0 or tail_base <= 0:
        raise ValueError(f"E_LAYOUT_BALLOON_GEOMETRY: corner_radius={corner_radius!r} must be nonnegative and tail_base={tail_base!r} positive for box={box!r}")
    radius = min(corner_radius, box.width / 2, box.height / 2)
    edge = nearest_eligible_edge(box, tip)
    base_a, base_b = tail_base_points(box, tip, edge=edge, tail_base=tail_base, corner_radius=radius)
    corners = {
        "TL": (box.x, box.y), "TR": (box.right, box.y),
        "BR": (box.right, box.bottom), "BL": (box.x, box.bottom),
    }
    order = ("TL", "TR", "BR", "BL")
    edge_of = {"top": ("TL", "TR"), "right": ("TR", "BR"), "bottom": ("BR", "BL"), "left": ("BL", "TL")}

    points: list[Point] = []
    for index, name in enumerate(order):
        next_name = order[(index + 1) % 4]
        start_corner, end_corner = corners[name], corners[next_name]
        edge_name = next(key for key, pair in edge_of.items() if pair == (name, next_name))
        points.append(_offset(start_corner, end_corner, radius) if radius > 0 else start_corner)
        if edge_name == edge:
            points.extend((base_a, tip, base_b))
        points.append(_offset(end_corner, start_corner, radius) if radius > 0 else end_corner)
    # Consecutive duplicate vertices collapse (radius 0 repeats the corner twice).
    deduped: list[Point] = []
    for point in points:
        if not deduped or deduped[-1] != point:
            deduped.append(point)
    if deduped[0] == deduped[-1]:
        deduped.pop()
    commands = [PathCommand("move", (deduped[0],))]
    commands.extend(PathCommand("line", (point,)) for point in deduped[1:])
    commands.append(PathCommand("line", (deduped[0],)))
    return tuple(commands)


def _offset(origin: Point, towards: Point, distance: float) -> Point:
    dx, dy = towards[0] - origin[0], towards[1] - origin[1]
    length = (dx * dx + dy * dy) ** 0.5
    if length == 0:
        return origin
    ratio = min(distance, length) / length
    return (origin[0] + dx * ratio, origin[1] + dy * ratio)
