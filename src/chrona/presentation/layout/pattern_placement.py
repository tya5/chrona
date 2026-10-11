"""Completed periodic catalogue pattern geometry owned by Layout."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping

from chrona.presentation.layout.model import LayoutError, Rect


def _detail_error(detail: str) -> ValueError:
    return ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: {detail}")


def _brief(value: object) -> str:
    if isinstance(value, str):
        clipped = value[:64]
        return repr(clipped + ("…" if len(value) > len(clipped) else ""))
    if value is None or isinstance(value, (bool, int, float)):
        return repr(value)
    return f"<{type(value).__name__}>"


@dataclass(frozen=True)
class PatternPathCommand:
    """One normalized tile-local path command, including explicit close."""

    kind: str
    points: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        expected = {"move": 1, "line": 1, "quadratic": 2, "close": 0}.get(self.kind)
        if (expected is None or len(self.points) != expected
                or not all(isfinite(value) for point in self.points for value in point)):
            raise _detail_error(f"PatternPathCommand.kind={self.kind!r} requires {expected if expected is not None else 'a supported command'} point(s); received {len(self.points)}")


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
            raise _detail_error(f"PatternTilePrimitive kind={self.kind!r} has incompatible or invalid geometry/paint fields; expected circle, positive rect, or fill/stroke path with finite dimensions")


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
    cut_contour: tuple[PatternPathCommand, ...] = ()

    def __post_init__(self) -> None:
        if (not isinstance(self.origin, tuple) or len(self.origin) != 2
                or not isinstance(self.cut_contour, tuple)
                or any(not isinstance(command, PatternPathCommand) for command in self.cut_contour)):
            raise _detail_error("PatternPlacement requires an origin pair and typed cut_contour commands")
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
                or (not self.cut_contour and self.origin != (float(self.region.inline), float(self.region.block)))
                or self.corner_radius < 0
                or self.corner_radius > min(float(self.region.inline_size),
                                            float(self.region.block_size)) / 2):
            raise _detail_error(f"PatternPlacement requires finite positive tile sizes, angle in [0, 360), density 1..10000, 1..64 primitives, matching clip/region/origin, and valid corner radius; tile=({self.tile_inline_size!r}, {self.tile_block_size!r}), angle={self.angle_degrees!r}, density={self.density_basis_points!r}, primitive_count={len(self.primitives)}, corner_radius={self.corner_radius!r}")
        if self.cut_contour:
            x, y, width, height = map(float, (self.region.inline, self.region.block,
                                            self.region.inline_size, self.region.block_size))
            start = end = None
            valid = self.corner_radius == 0 and self.cut_contour[0].kind == "move"
            for command in self.cut_contour:
                if command.kind == "move":
                    if start is not None and end != start:
                        valid = False
                    start = end = command.points[0]
                elif command.kind == "close":
                    end = start
                else:
                    end = command.points[-1]
                valid = valid and all(x <= px <= x + width and y <= py <= y + height
                                      for px, py in command.points)
            if not valid or end != start:
                raise _detail_error("PatternPlacement cut_contour requires closed completed subpaths within its visible region and zero corner radius")


@dataclass(frozen=True)
class PatternedPlacement:
    """Bind completed pattern geometry to its exact Layout placement ID."""

    placement_id: str
    pattern: PatternPlacement

    def __post_init__(self) -> None:
        if not self.placement_id or not isinstance(self.pattern, PatternPlacement):
            raise _detail_error(f"PatternedPlacement placement_id={_brief(self.placement_id)} must be non-empty and pattern must be PatternPlacement; pattern_type={type(self.pattern).__name__}")


def complete_pattern_placement(pattern: Mapping[str, object], bounds: Rect,
                               corner_radius: float = 0.0, *,
                               origin: tuple[float, float] | None = None,
                               cut_contour: tuple[PatternPathCommand, ...] = ()) -> PatternPlacement:
    """Complete a visible region; retain a different original phase only with a cut contour."""
    try:
        tile = pattern["tile"]
        if not isinstance(tile, Mapping):
            raise _detail_error(f"pattern.tile has type={type(tile).__name__}; expected mapping with inlineSize/blockSize")
        width = _positive(tile["inlineSize"], "pattern.tile.inlineSize")
        height = _positive(tile["blockSize"], "pattern.tile.blockSize")
        angle = _finite(pattern["angle"], "pattern.angle")
        density = pattern["densityBasisPoints"]
        source_primitives = pattern["primitives"]
        if not isinstance(source_primitives, (list, tuple)):
            raise _detail_error(f"pattern.primitives has type={type(source_primitives).__name__}; expected a sequence of 1..64 normalized tile primitives")
        primitives = tuple(_primitive(value, index) for index, value in enumerate(source_primitives))
        radius = _finite(corner_radius, "corner_radius")
        origin = origin if origin is not None else (float(bounds.inline), float(bounds.block))
        return PatternPlacement(width, height, angle, density, primitives, origin,
                                bounds, bounds, radius, cut_contour)
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        detail = str(error).replace("\n", " ")[:240] or f"invalid pattern fields={tuple(sorted(str(key) for key in pattern.keys()))!r}"
        raise LayoutError("E_PRESENTATION_PRIMITIVE_INVALID", "/layout/pattern", detail=detail) from error


def _primitive(value: object, index: int = 0) -> PatternTilePrimitive:
    if not isinstance(value, Mapping):
        raise _detail_error(f"pattern.primitives[{index}] has type={type(value).__name__}; expected a circle, rect, or path mapping")
    kind = value.get("kind")
    if kind == "circle" and {"kind", "cx", "cy", "radius"} <= set(value) <= {
            "kind", "cx", "cy", "radius", "fillChannel", "strokeWidth"}:
        fill_channel = value.get("fillChannel")
        if (("fillChannel" in value and fill_channel not in {"ink", "substrate", "none"})
                or ("strokeWidth" in value and value["strokeWidth"] is None)):
            raise _detail_error(f"pattern.primitives[{index}] circle fillChannel={_brief(fill_channel)}/strokeWidth={_brief(value.get('strokeWidth'))}; expected ink/substrate/none and a positive strokeWidth when present")
        stroke_width = _positive(value["strokeWidth"], f"pattern.primitives[{index}].strokeWidth") if "strokeWidth" in value else None
        if fill_channel == "none" and stroke_width is None:
            raise _detail_error(f"pattern.primitives[{index}] circle fillChannel='none' requires positive strokeWidth")
        return PatternTilePrimitive("circle", cx=_finite(value["cx"], f"pattern.primitives[{index}].cx"), cy=_finite(value["cy"], f"pattern.primitives[{index}].cy"),
                                    radius=_positive(value["radius"], f"pattern.primitives[{index}].radius"),
                                    fill_channel=None if fill_channel == "ink" else fill_channel,
                                    stroke_width=stroke_width)
    if kind == "rect" and set(value) == {"kind", "x", "y", "inlineSize", "blockSize"}:
        return PatternTilePrimitive("rect", x=_finite(value["x"], f"pattern.primitives[{index}].x"), y=_finite(value["y"], f"pattern.primitives[{index}].y"),
                                    inline_size=_positive(value["inlineSize"], f"pattern.primitives[{index}].inlineSize"),
                                    block_size=_positive(value["blockSize"], f"pattern.primitives[{index}].blockSize"))
    if kind == "path":
        expected = {"kind", "paint", "commands"}
        if value.get("paint") == "stroke":
            expected.update({"strokeWidth", "lineCap", "lineJoin"})
        if set(value) != expected:
            raise _detail_error(f"pattern.primitives[{index}] path keys={tuple(sorted(str(key) for key in value))!r}; expected {tuple(sorted(expected))!r}")
        commands_source = value["commands"]
        if not isinstance(commands_source, (list, tuple)) or not commands_source:
            raise _detail_error(f"pattern.primitives[{index}].commands has type={type(commands_source).__name__} and length={len(commands_source) if isinstance(commands_source, (list, tuple)) else 'n/a'}; expected a nonempty sequence")
        commands = tuple(_path_command(command, index, command_index)
                         for command_index, command in enumerate(commands_source))
        return PatternTilePrimitive(
            "path", paint=value["paint"], commands=commands,
            stroke_width=_positive(value["strokeWidth"], f"pattern.primitives[{index}].strokeWidth") if value["paint"] == "stroke" else None,
            line_cap=value.get("lineCap"), line_join=value.get("lineJoin"),
        )
    raise _detail_error(f"pattern.primitives[{index}] kind={_brief(kind)} has keys={tuple(sorted(str(key) for key in value))!r}; expected normalized circle, rect, or path fields")


def _path_command(value: object, primitive_index: int = 0, command_index: int = 0) -> PatternPathCommand:
    if not isinstance(value, Mapping) or set(value) != {"kind", "points"}:
        keys = tuple(sorted(str(key) for key in value)) if isinstance(value, Mapping) else ()
        raise _detail_error(f"pattern.primitives[{primitive_index}].commands[{command_index}] type={type(value).__name__}, keys={keys!r}; expected kind and points")
    kind, flat = value["kind"], value["points"]
    if not isinstance(flat, (list, tuple)) or len(flat) % 2:
        raise _detail_error(f"pattern.primitives[{primitive_index}].commands[{command_index}].points has type={type(flat).__name__} and length={len(flat) if isinstance(flat, (list, tuple)) else 'n/a'}; expected an even-length coordinate sequence")
    points = tuple((_finite(flat[index], f"pattern.primitives[{primitive_index}].commands[{command_index}].points[{index}]"), _finite(flat[index + 1], f"pattern.primitives[{primitive_index}].commands[{command_index}].points[{index + 1}]"))
                   for index in range(0, len(flat), 2))
    return PatternPathCommand(kind, points)


def _finite(value: object, field: str = "value") -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value):
        raise _detail_error(f"{field}={_brief(value)}; expected a finite number")
    return float(value)


def _positive(value: object, field: str = "value") -> float:
    result = _finite(value, field)
    if result <= 0:
        raise _detail_error(f"{field}={_brief(value)}; expected a positive number")
    return result
