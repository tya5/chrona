"""Completed periodic catalogue pattern geometry owned by Layout."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping

from chrona.presentation.layout.model import LayoutError, Rect


@dataclass(frozen=True)
class PatternPathCommand:
    """One normalized tile-local path command, including explicit close."""

    kind: str
    points: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        expected = {"move": 1, "line": 1, "quadratic": 2, "close": 0}.get(self.kind)
        if (expected is None or len(self.points) != expected
                or not all(isfinite(value) for point in self.points for value in point)):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")


@dataclass(frozen=True)
class PatternTilePrimitive:
    """One immutable normalized tile primitive with no paint colors."""

    kind: str
    cx: float | None = None
    cy: float | None = None
    radius: float | None = None
    x: float | None = None
    y: float | None = None
    inline_size: float | None = None
    block_size: float | None = None
    paint: str | None = None
    commands: tuple[PatternPathCommand, ...] = ()
    stroke_width: float | None = None
    line_cap: str | None = None
    line_join: str | None = None
    fill_channel: str | None = None

    def __post_init__(self) -> None:
        if self.kind == "circle":
            valid = (self.cx is not None and self.cy is not None and self.radius is not None
                     and self.x is self.y is self.inline_size is self.block_size is None
                     and self.paint is None and not self.commands
                     and self.line_cap is self.line_join is None
                     and (self.fill_channel is None
                          or isinstance(self.fill_channel, str)
                          and self.fill_channel in {"ink", "substrate", "none"})
                     and (self.fill_channel != "none" or self.stroke_width is not None))
        elif self.kind == "rect":
            valid = (self.x is not None and self.y is not None
                     and self.inline_size is not None and self.block_size is not None
                     and self.cx is self.cy is self.radius is None and self.paint is None
                     and not self.commands and self.stroke_width is self.line_cap is self.line_join is None
                     and self.fill_channel is None)
        elif self.kind == "path":
            valid = (self.paint in {"fill", "stroke"} and bool(self.commands)
                     and self.cx is self.cy is self.radius is self.x is self.y is None
                     and self.inline_size is self.block_size is None
                     and self.fill_channel is None
                     and ((self.paint == "fill" and self.stroke_width is self.line_cap is self.line_join is None)
                          or (self.paint == "stroke" and self.stroke_width is not None
                              and self.line_cap in {"butt", "round", "square"}
                              and self.line_join in {"miter", "round", "bevel"})))
        else:
            valid = False
        numbers = (self.cx, self.cy, self.radius, self.x, self.y, self.inline_size,
                   self.block_size, self.stroke_width)
        if (not valid or any(value is not None and (not isfinite(value)) for value in numbers)
                or (self.radius is not None and self.radius <= 0)
                or (self.inline_size is not None and self.inline_size <= 0)
                or (self.block_size is not None and self.block_size <= 0)
                or (self.stroke_width is not None and (self.stroke_width <= 0 or self.stroke_width > 16))):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")


@dataclass(frozen=True)
class PatternPlacement:
    """Pattern tile and its completed region, repeat phase, and clip."""

    tile_inline_size: float
    tile_block_size: float
    angle_degrees: float
    density_basis_points: int
    primitives: tuple[PatternTilePrimitive, ...]
    origin: tuple[float, float]
    region: Rect
    clip: Rect
    corner_radius: float

    def __post_init__(self) -> None:
        if (not all(isfinite(value) for value in
                    (self.tile_inline_size, self.tile_block_size, self.angle_degrees,
                     *self.origin, self.corner_radius))
                or self.tile_inline_size <= 0 or self.tile_block_size <= 0
                or not 0 <= self.angle_degrees < 360
                or not isinstance(self.density_basis_points, int)
                or isinstance(self.density_basis_points, bool)
                or not 1 <= self.density_basis_points <= 10_000
                or not 1 <= len(self.primitives) <= 64
                or not isinstance(self.region, Rect) or self.clip != self.region
                or self.origin != (float(self.region.inline), float(self.region.block))
                or self.corner_radius < 0
                or self.corner_radius > min(float(self.region.inline_size),
                                            float(self.region.block_size)) / 2):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")


@dataclass(frozen=True)
class PatternedPlacement:
    """Bind completed pattern geometry to its exact Layout placement ID."""

    placement_id: str
    pattern: PatternPlacement

    def __post_init__(self) -> None:
        if not self.placement_id or not isinstance(self.pattern, PatternPlacement):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")


def complete_pattern_placement(pattern: Mapping[str, object], bounds: Rect,
                               corner_radius: float = 0.0) -> PatternPlacement:
    """Complete one normalized catalogue pattern over a Rect's top-left phase."""
    try:
        tile = pattern["tile"]
        if not isinstance(tile, Mapping):
            raise ValueError
        width = _positive(tile["inlineSize"])
        height = _positive(tile["blockSize"])
        angle = _finite(pattern["angle"])
        density = pattern["densityBasisPoints"]
        source_primitives = pattern["primitives"]
        if not isinstance(source_primitives, (list, tuple)):
            raise ValueError
        primitives = tuple(_primitive(value) for value in source_primitives)
        radius = _finite(corner_radius)
        origin = (float(bounds.inline), float(bounds.block))
        return PatternPlacement(width, height, angle, density, primitives, origin,
                                bounds, bounds, radius)
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise LayoutError("E_PRESENTATION_PRIMITIVE_INVALID", "/layout/pattern") from error


def _primitive(value: object) -> PatternTilePrimitive:
    if not isinstance(value, Mapping):
        raise ValueError
    kind = value.get("kind")
    if kind == "circle" and {"kind", "cx", "cy", "radius"} <= set(value) <= {
            "kind", "cx", "cy", "radius", "fillChannel", "strokeWidth"}:
        fill_channel = value.get("fillChannel")
        if (("fillChannel" in value and fill_channel not in {"ink", "substrate", "none"})
                or ("strokeWidth" in value and value["strokeWidth"] is None)):
            raise ValueError
        stroke_width = _positive(value["strokeWidth"]) if "strokeWidth" in value else None
        if fill_channel == "none" and stroke_width is None:
            raise ValueError
        return PatternTilePrimitive("circle", cx=_finite(value["cx"]), cy=_finite(value["cy"]),
                                    radius=_positive(value["radius"]),
                                    fill_channel=None if fill_channel == "ink" else fill_channel,
                                    stroke_width=stroke_width)
    if kind == "rect" and set(value) == {"kind", "x", "y", "inlineSize", "blockSize"}:
        return PatternTilePrimitive("rect", x=_finite(value["x"]), y=_finite(value["y"]),
                                    inline_size=_positive(value["inlineSize"]),
                                    block_size=_positive(value["blockSize"]))
    if kind == "path":
        expected = {"kind", "paint", "commands"}
        if value.get("paint") == "stroke":
            expected.update({"strokeWidth", "lineCap", "lineJoin"})
        if set(value) != expected:
            raise ValueError
        commands_source = value["commands"]
        if not isinstance(commands_source, (list, tuple)) or not commands_source:
            raise ValueError
        commands = tuple(_path_command(command) for command in commands_source)
        return PatternTilePrimitive(
            "path", paint=value["paint"], commands=commands,
            stroke_width=_positive(value["strokeWidth"]) if value["paint"] == "stroke" else None,
            line_cap=value.get("lineCap"), line_join=value.get("lineJoin"),
        )
    raise ValueError


def _path_command(value: object) -> PatternPathCommand:
    if not isinstance(value, Mapping) or set(value) != {"kind", "points"}:
        raise ValueError
    kind, flat = value["kind"], value["points"]
    if not isinstance(flat, (list, tuple)) or len(flat) % 2:
        raise ValueError
    points = tuple((_finite(flat[index]), _finite(flat[index + 1]))
                   for index in range(0, len(flat), 2))
    return PatternPathCommand(kind, points)


def _finite(value: object) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value):
        raise ValueError
    return float(value)


def _positive(value: object) -> float:
    result = _finite(value)
    if result <= 0:
        raise ValueError
    return result
