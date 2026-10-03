"""Layout-owned nine-slice warp of a catalogue glyph behind an annotation container (#848).

Pure geometry, the vector counterpart of ``image_slice_geometry`` (#465). A glyph is a viewport and parts whose
data is a path of ``M``, ``L``, ``Q`` and ``Z``. The artwork is stretched to a paint box by a piecewise-linear map
that is separable in the two axes: the glyph's viewport is cut into three source columns and three source rows by
four declared insets (in viewport units); each fixed border keeps its authored size (inset times ``unit_px``) and the
middle absorbs the rest. A map that is linear only within a cell would bend a line or a curve that crosses a cell
boundary, so every ``L`` and ``Q`` is first split at each boundary it crosses; each piece then lies in one cell,
where the map is affine and takes a line to a line and a quadratic to a quadratic. The warp is therefore exact for
the glyph grammar, keeps the winding of every sub-path (a hole stays a hole) and has no tolerance, random source or
iteration-order dependence. Stroke widths scale with ``unit_px`` and are not warped.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite, sqrt

from chrona.presentation.icons.normalizer import IconNormalizationError, parse_path_commands
from chrona.presentation.layout.mark_geometry import SymbolPartPlacement
from chrona.presentation.layout.surface_quality import PathCommand

Point = tuple[float, float]
Insets = tuple[float, float, float, float]  # top, right, bottom, left, in glyph viewport units

_EPS = 1e-9


class GlyphSliceError(ValueError):
    """A glyph or declaration the nine-slice warp cannot complete: a stable code and what is wrong."""

    def __init__(self, code: str, detail: str):
        super().__init__(code)
        self.code = code
        self.detail = detail


class _Axis:
    """One axis of the map: four source breakpoints onto four destination breakpoints."""

    def __init__(self, source: Sequence[float], destination: Sequence[float]):
        self.source = tuple(source)
        self.destination = tuple(destination)
        self.interior = tuple(value for value in self.source[1:3] if self.source[0] < value < self.source[3])

    def cell(self, value: float) -> int:
        """The cell a coordinate lies in: the first non-degenerate cell whose far edge is not before it."""
        last = 0
        for index in range(3):
            if self.source[index + 1] > self.source[index]:
                last = index
                if value <= self.source[index + 1] + _EPS:
                    return index
        return last

    def apply(self, cell: int, value: float) -> float:
        s0, s1 = self.source[cell], self.source[cell + 1]
        d0, d1 = self.destination[cell], self.destination[cell + 1]
        if s1 <= s0:
            return d0
        return d0 + (value - s0) * (d1 - d0) / (s1 - s0)


def slice_glyph_parts(glyph: Mapping[str, object], box: tuple[float, float, float, float], *,
                      slice_insets: Insets, unit_px: float) -> tuple[SymbolPartPlacement, ...]:
    """Stretch every part of ``glyph`` over ``box`` (x, y, width, height) with fixed borders of ``slice_insets``.

    ``unit_px`` is the destination size of one viewport unit. Raises ``ValueError`` with a stable code on a
    malformed glyph, on insets that exceed the viewport, and on a box or unit that is not positive.
    """
    view = glyph.get("viewport")
    if not isinstance(view, Mapping):
        raise GlyphSliceError("E_THEME_TOKEN_TYPE", "the glyph has no viewport")
    try:
        view_width, view_height = float(view["inlineSize"]), float(view["blockSize"])  # type: ignore[arg-type]
    except (KeyError, TypeError, ValueError) as error:
        raise GlyphSliceError("E_THEME_TOKEN_TYPE", "the glyph viewport has no inline and block size") from error
    top, right, bottom, left = slice_insets
    x, y, width, height = box
    if (not all(isfinite(value) for value in (view_width, view_height, top, right, bottom, left, x, y, width, height,
                                              unit_px))
            or view_width <= 0 or view_height <= 0 or unit_px <= 0 or width <= 0 or height <= 0
            or min(top, right, bottom, left) < 0 or left + right > view_width + _EPS or top + bottom > view_height + _EPS):
        raise GlyphSliceError("E_LAYOUT_ARTWORK_SLICE_GEOMETRY", "the box, unit or insets are not positive, or the insets exceed the glyph viewport")
    # A paint box smaller than the fixed borders scales both borders of that axis down by one factor, so no
    # cell inverts (the rule of `image_slice_tiles`).
    fixed_x, fixed_y = (left + right) * unit_px, (top + bottom) * unit_px
    scale_x = min(1.0, width / fixed_x) if fixed_x > 0 else 1.0
    scale_y = min(1.0, height / fixed_y) if fixed_y > 0 else 1.0
    dest_left, dest_right = left * unit_px * scale_x, right * unit_px * scale_x
    dest_top, dest_bottom = top * unit_px * scale_y, bottom * unit_px * scale_y
    columns = _Axis((0.0, left, view_width - right, view_width), (x, x + dest_left, x + width - dest_right, x + width))
    rows = _Axis((0.0, top, view_height - bottom, view_height), (y, y + dest_top, y + height - dest_bottom, y + height))
    parts = glyph.get("parts")
    if not isinstance(parts, (list, tuple)) or not parts:
        raise GlyphSliceError("E_THEME_TOKEN_TYPE", "the glyph has no parts")
    return tuple(_warp_part(part, columns, rows, unit_px) for part in parts)


def _warp_part(part: object, columns: _Axis, rows: _Axis, unit_px: float) -> SymbolPartPlacement:
    if not isinstance(part, Mapping):
        raise GlyphSliceError("E_THEME_TOKEN_TYPE", "a glyph part has no fill or stroke paint, or no path data")
    paint, raw = part.get("paint"), part.get("data")
    if paint not in {"fill", "stroke"} or not isinstance(raw, str) or not raw:
        raise GlyphSliceError("E_THEME_TOKEN_TYPE", "a glyph part path is not a path of M, L, Q and Z")
    try:
        parsed = parse_path_commands(raw)
    except IconNormalizationError as error:
        raise GlyphSliceError("E_THEME_TOKEN_TYPE", "a glyph part path cannot be parsed") from error
    commands: list[PathCommand] = []
    start: Point | None = None
    current: Point | None = None
    for command in parsed:
        if command.kind == "move":
            start = current = (float(command.points[0][0]), float(command.points[0][1]))
            commands.append(PathCommand("move", (_map_point(start, columns, rows, columns.cell(start[0]),
                                                            rows.cell(start[1])),)))
        elif command.kind == "line" and current is not None:
            end = (float(command.points[0][0]), float(command.points[0][1]))
            commands.extend(_warp_line(current, end, columns, rows))
            current = end
        elif command.kind == "quadratic" and current is not None:
            control = (float(command.points[0][0]), float(command.points[0][1]))
            end = (float(command.points[1][0]), float(command.points[1][1]))
            commands.extend(_warp_quadratic(current, control, end, columns, rows))
            current = end
        elif command.kind == "close" and start is not None and current is not None:
            commands.extend(_warp_line(current, start, columns, rows))
            current = start
        else:
            raise GlyphSliceError("E_THEME_TOKEN_TYPE", "a glyph path continues without a start or uses an unsupported command")
    if not commands:
        raise GlyphSliceError("E_THEME_TOKEN_TYPE", "a glyph part path is empty")
    stroke_width = line_cap = line_join = None
    if paint == "stroke":
        width, line_cap, line_join = part.get("strokeWidth"), part.get("lineCap"), part.get("lineJoin")
        if (not isinstance(width, (int, float)) or isinstance(width, bool) or not isfinite(float(width))
                or float(width) <= 0 or line_cap not in {"butt", "round", "square"}
                or line_join not in {"miter", "round", "bevel"}):
            raise GlyphSliceError("E_THEME_TOKEN_TYPE", "a stroke part lacks a positive width, a cap or a join")
        stroke_width = float(width) * unit_px
    return SymbolPartPlacement(tuple(commands), str(paint), None, stroke_width,
                               line_cap if isinstance(line_cap, str) else None,
                               line_join if isinstance(line_join, str) else None)


def _map_point(point: Point, columns: _Axis, rows: _Axis, column: int, row: int) -> Point:
    return columns.apply(column, point[0]), rows.apply(row, point[1])


def _warp_line(a: Point, b: Point, columns: _Axis, rows: _Axis) -> list[PathCommand]:
    cuts = sorted({t for axis, index in ((columns, 0), (rows, 1)) for boundary in axis.interior
                   for t in _line_crossings(a[index], b[index], boundary)})
    knots = [0.0, *cuts, 1.0]
    result = []
    for t0, t1 in zip(knots, knots[1:]):
        end = b if t1 == 1.0 else _lerp(a, b, t1)
        middle = _lerp(a, b, (t0 + t1) / 2)
        column, row = columns.cell(middle[0]), rows.cell(middle[1])
        result.append(PathCommand("line", (_map_point(end, columns, rows, column, row),)))
    return result


def _warp_quadratic(a: Point, control: Point, b: Point, columns: _Axis, rows: _Axis) -> list[PathCommand]:
    cuts = sorted({t for axis, index in ((columns, 0), (rows, 1)) for boundary in axis.interior
                   for t in _quadratic_crossings(a[index], control[index], b[index], boundary)})
    pieces: list[tuple[Point, Point, Point]] = []
    rest = (a, control, b)
    consumed = 0.0
    for t in cuts:
        local = (t - consumed) / (1.0 - consumed)
        left, rest = _split_quadratic(rest, local)
        pieces.append(left)
        consumed = t
    pieces.append(rest)
    result = []
    for p0, c, p1 in pieces:
        middle = _quadratic_point(p0, c, p1, 0.5)
        column, row = columns.cell(middle[0]), rows.cell(middle[1])
        result.append(PathCommand("quadratic", (_map_point(c, columns, rows, column, row),
                                                _map_point(p1, columns, rows, column, row))))
    return result


def _lerp(a: Point, b: Point, t: float) -> Point:
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t


def _line_crossings(a: float, b: float, boundary: float) -> list[float]:
    if a == b:
        return []
    t = (boundary - a) / (b - a)
    return [t] if _EPS < t < 1.0 - _EPS else []


def _quadratic_crossings(a: float, c: float, b: float, boundary: float) -> list[float]:
    """The parameters in (0, 1) at which the coordinate of a quadratic equals ``boundary``."""
    qa, qb, qc = a - 2 * c + b, 2 * (c - a), a - boundary
    if abs(qa) < 1e-12:
        roots = [] if abs(qb) < 1e-12 else [-qc / qb]
    else:
        discriminant = qb * qb - 4 * qa * qc
        if discriminant < 0:
            return []
        root = sqrt(discriminant)
        roots = [(-qb - root) / (2 * qa), (-qb + root) / (2 * qa)]
    return [t for t in roots if _EPS < t < 1.0 - _EPS]


def _quadratic_point(p0: Point, c: Point, p1: Point, t: float) -> Point:
    u = 1.0 - t
    return (u * u * p0[0] + 2 * u * t * c[0] + t * t * p1[0], u * u * p0[1] + 2 * u * t * c[1] + t * t * p1[1])


def _split_quadratic(curve: tuple[Point, Point, Point], t: float
                     ) -> tuple[tuple[Point, Point, Point], tuple[Point, Point, Point]]:
    """De Casteljau subdivision of a quadratic at ``t``."""
    p0, c, p1 = curve
    left_control, right_control = _lerp(p0, c, t), _lerp(c, p1, t)
    mid = _lerp(left_control, right_control, t)
    return (p0, left_control, mid), (mid, right_control, p1)
