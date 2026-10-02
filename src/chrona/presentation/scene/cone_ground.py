"""The as-of light cone as a translucent ground for the contrast gate (#890).

A cone is a gradient polygon whose ink fades to transparent. It is never an ordinary opaque host: the
gate keeps the host a mark truly lies on and composites the cone's ink over it at the strength the
gradient has where the mark lies. The gradient is linear and the polygon convex, so the worst ground over
the stops a mark spans is found at the two ends of its block extent inside the gradient range.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping

from chrona.presentation.scene.paint_analysis import blend_over, is_hex_color

AS_OF_CONE_ROLE = "as-of-cone"
_EPSILON = 1e-9
Point = tuple[float, float]


@dataclass(frozen=True)
class ConeGround:
    """One completed cone read from the serialized Scene."""

    cone_id: str
    key: tuple[int, int]
    ink: str
    strength: float
    start_block: float
    end_block: float
    start_opacity: float
    end_opacity: float
    polygon: tuple[Point, ...]

    def strength_at(self, block: float) -> float:
        span = self.end_block - self.start_block
        t = 1.0 if span <= 0 else max(0.0, min(1.0, (block - self.start_block) / span))
        return self.strength * (self.start_opacity + (self.end_opacity - self.start_opacity) * t)

    def chord(self, block: float) -> tuple[float, float] | None:
        """The inline extent of the polygon at one block coordinate."""
        xs: list[float] = []
        for (x0, y0), (x1, y1) in zip(self.polygon, (*self.polygon[1:], self.polygon[0])):
            if y0 == y1:
                if abs(block - y0) <= _EPSILON:
                    xs.extend((x0, x1))
            elif min(y0, y1) - _EPSILON <= block <= max(y0, y1) + _EPSILON:
                xs.append(x0 + (block - y0) / (y1 - y0) * (x1 - x0))
        return (min(xs), max(xs)) if xs else None

    def contains(self, point: Point) -> bool:
        signs = [(x1 - x0) * (point[1] - y0) - (y1 - y0) * (point[0] - x0)
                 for (x0, y0), (x1, y1) in zip(self.polygon, (*self.polygon[1:], self.polygon[0]))]
        return all(sign >= -_EPSILON for sign in signs) or all(sign <= _EPSILON for sign in signs)

    def blends(self, bounds: tuple[float, float, float, float], ground: str) -> tuple[tuple[str, ...], bool]:
        """The grounds a box meets inside the cone, and whether part of it lies outside.

        Returns ``((), False)`` when the box misses the cone, so the unblended ground stands.
        """
        x, y, width, height = bounds
        top, bottom = max(y, self.start_block), min(y + height, self.end_block)
        if top > bottom:
            return (), False
        colours: list[str] = []
        for block in dict.fromkeys((top, bottom)):
            chord = self.chord(block)
            if chord is not None and x < chord[1] + _EPSILON and x + width > chord[0] - _EPSILON:
                colours.append(blend_over(ink=self.ink, opacity=self.strength_at(block), ground=ground))
        if not colours:
            return (), False
        corners = ((x, y), (x + width, y), (x, y + height), (x + width, y + height))
        return tuple(dict.fromkeys(colours)), not all(self.contains(corner) for corner in corners)


def cones_in(primitives: list[Any]) -> tuple[ConeGround, ...]:
    """Every completed as-of cone of a surface; a cone whose paint cannot be read is a malformed document."""
    result: list[ConeGround] = []
    for index, primitive in enumerate(primitives):
        if not isinstance(primitive, Mapping) or primitive.get("visualRole") != AS_OF_CONE_ROLE:
            continue
        cone = _read(primitive, index)
        if cone is None:
            raise ValueError(f"E_SCENE_PAINT_ANALYSIS_INPUT: as-of cone {primitive.get('id')!r} has no readable gradient or outline")
        result.append(cone)
    return tuple(result)


def _read(primitive: Mapping[str, Any], index: int) -> ConeGround | None:
    paint, symbol = primitive.get("paint"), primitive.get("symbol")
    gradient = paint.get("gradient") if isinstance(paint, Mapping) else None
    outline = symbol.get("outline") if isinstance(symbol, Mapping) else None
    if not isinstance(gradient, Mapping) or not isinstance(outline, list) or not isinstance(primitive.get("id"), str):
        return None
    try:
        stops = gradient["stops"]
        start, end = gradient["start"], gradient["end"]
        opacities = [float(stop["opacity"]) for stop in stops]
        ink = stops[0]["color"]
        polygon = tuple((float(point[0]), float(point[1])) for command in outline for point in command["points"])
        strength = float(paint.get("opacity", 1.0))
        order = primitive.get("paintOrder", 0)
        start_block, end_block = float(start[1]), float(end[1])
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    if (len(opacities) != 2 or not is_hex_color(ink) or len(polygon) < 3 or not isinstance(order, int)
            or not all(isfinite(value) for value in (strength, start_block, end_block, *opacities))
            or not 0 <= strength <= 1 or any(not 0 <= value <= 1 for value in opacities)):
        return None
    return ConeGround(primitive["id"], (order, index), str(ink), strength, start_block, end_block,
                      opacities[0], opacities[1], polygon[:-1] if polygon[0] == polygon[-1] else polygon)
