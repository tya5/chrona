"""Deterministic annotation tilt: the angle rule and rigid rotation of completed note geometry (#584).

A Theme declares `annotationContainer.tiltDegrees`, a non-empty list of angles in degrees, clockwise in
the surface's (inline right, block down) frame.  The annotation at position `i` of the View's declared
annotations takes `tiltDegrees[i mod len]`: no random source, hash or iteration order is involved, so two
renders are equal and the declared list and the position are the whole rule.

This module is pure geometry.  The search and the obstacle index see a tilted note only through the
axis-aligned bounds of its rotated frame (`rotated_extent`); once a position is chosen, every element of
the note frame (box, bar, accent, stamp, header and body text) is rotated rigidly about the centre of
those bounds by Layout, so Scene carries completed rotated geometry and no adapter decides anything.
"""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from math import cos, radians, sin
from typing import Sequence

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_quality import PathCommand, ShapePlacement, TextPlacement

Point = tuple[float, float]
MAX_TILT_DEGREES = 15.0


def tilt_for(degrees: Sequence[object] | None, position: int) -> float:
    """The angle of the annotation at `position` (0-based, View order): the declared list cycled, two decimals."""
    if not degrees:
        return 0.0
    return round(float(degrees[position % len(degrees)]), 2)


def rotate_point(point: Point, center: Point, degrees: float) -> Point:
    """Rotate `point` about `center` clockwise (block axis down) by `degrees`."""
    angle = radians(degrees)
    dx, dy = point[0] - center[0], point[1] - center[1]
    return (center[0] + dx * cos(angle) - dy * sin(angle), center[1] + dx * sin(angle) + dy * cos(angle))


def rotated_extent(width: float, height: float, degrees: float) -> tuple[float, float]:
    """The axis-aligned size of a `width` x `height` frame rotated by `degrees`."""
    angle = radians(degrees)
    return (width * abs(cos(angle)) + height * abs(sin(angle)), width * abs(sin(angle)) + height * abs(cos(angle)))


def rect_corners(x: float, y: float, width: float, height: float) -> tuple[Point, Point, Point, Point]:
    return ((x, y), (x + width, y), (x + width, y + height), (x, y + height))


def rotated_corners(x: float, y: float, width: float, height: float, center: Point,
                    degrees: float) -> tuple[Point, ...]:
    return tuple(rotate_point(corner, center, degrees) for corner in rect_corners(x, y, width, height))


def polygon_commands(points: Sequence[Point]) -> tuple[PathCommand, ...]:
    """A closed polygon as Layout path commands (the form a balloon outline already uses)."""
    return (PathCommand("move", (points[0],)), *(PathCommand("line", (point,)) for point in points[1:]),
            PathCommand("line", (points[0],)))


def bounding_rect(points: Sequence[Point]) -> Rect:
    xs, ys = [point[0] for point in points], [point[1] for point in points]
    return Rect(Decimal(str(min(xs))), Decimal(str(min(ys))),
                Decimal(str(max(xs) - min(xs))), Decimal(str(max(ys) - min(ys))))


def _rotate_commands(commands: Sequence[PathCommand], center: Point, degrees: float) -> tuple[PathCommand, ...]:
    return tuple(PathCommand(command.kind, tuple(rotate_point(point, center, degrees) for point in command.points))
                 for command in commands)


def rotate_shape(shape: ShapePlacement, center: Point, degrees: float) -> ShapePlacement:
    """Rotate one completed note shape: a Rect becomes a closed polygon, a glyph keeps its parts, rotated."""
    bounds = shape.bounds
    corners = rotated_corners(float(bounds.inline), float(bounds.block), float(bounds.inline_size),
                              float(bounds.block_size), center, degrees)
    if shape.kind == "Rect":
        return replace(shape, kind="Tilt", bounds=bounding_rect(corners), path_commands=polygon_commands(corners))
    if shape.kind == "Polygon":
        # A mitred border strip (#1049): its own corners rotate, not those of its bounds.
        commands = _rotate_commands(shape.path_commands, center, degrees)
        return replace(shape, kind="Tilt", path_commands=commands,
                       bounds=bounding_rect([point for command in commands for point in command.points]))
    if shape.kind == "Glyph":
        parts = tuple(replace(part, commands=_rotate_commands(part.commands, center, degrees))
                      for part in shape.symbol_parts)
        return replace(shape, bounds=bounding_rect(corners), symbol_parts=parts)
    raise ValueError(f"E_LAYOUT_ANNOTATION_TILT_SHAPE:{shape.placement_id}:{shape.kind}")


def rotate_text(text: TextPlacement, center: Point, degrees: float) -> TextPlacement:
    """Rotate one horizontal text run rigidly: its baseline origin moves, its bounds become the rotated box."""
    if text.baseline is None or text.orientation != "horizontal":
        raise ValueError(f"E_LAYOUT_ANNOTATION_TILT_TEXT:{text.placement_id}:{text.orientation}")
    bounds = text.bounds
    corners = rotated_corners(float(bounds.inline), float(bounds.block), float(bounds.inline_size),
                              float(bounds.block_size), center, degrees)
    return replace(text, baseline=rotate_point(text.baseline, center, degrees), bounds=bounding_rect(corners),
                   orientation="tilt", rotation_degrees=degrees)


def nearest_boundary_point(polygon: Sequence[Point], point: Point) -> Point:
    """The point of the polygon's boundary nearest `point` (first edge wins a tie)."""
    best: tuple[float, Point] | None = None
    for start, end in zip(polygon, (*polygon[1:], polygon[0])):
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = dx * dx + dy * dy
        t = 0.0 if length == 0 else max(0.0, min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length))
        candidate = (start[0] + t * dx, start[1] + t * dy)
        distance = (candidate[0] - point[0]) ** 2 + (candidate[1] - point[1]) ** 2
        if best is None or distance < best[0] - 1e-12:
            best = (distance, candidate)
    assert best is not None
    return best[1]
