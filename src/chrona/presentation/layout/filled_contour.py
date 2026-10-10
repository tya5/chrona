"""Exact Layout-owned union of closed, nonzero-filled path operands."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import isfinite
from numbers import Real

import pathops

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_quality import PathCommand, is_closed_stroke_contour


@dataclass
class ContourUnionError(ValueError):
    """A bounded failure while checking or unioning filled contours."""

    stage: str
    reason: str

    def __post_init__(self) -> None:
        if self.stage not in {"input", "simplify", "union", "difference", "output"}:
            object.__setattr__(self, "stage", "output")
        if self.reason not in {"empty", "open", "degenerate", "nonfinite", "unsupported-verb", "operation-failed"}:
            object.__setattr__(self, "reason", "operation-failed")
        ValueError.__init__(self, f"contour union {self.stage}: {self.reason}")


def _validate(commands: tuple[PathCommand, ...], *, stage: str) -> None:
    if not commands:
        raise ContourUnionError(stage, "empty")
    for command in commands:
        if command.kind not in {"move", "line", "quadratic"}:
            raise ContourUnionError(stage, "unsupported-verb")
        if any(len(point) != 2 for point in command.points):
            raise ContourUnionError(stage, "unsupported-verb")
        if any(not isfinite(value) for point in command.points for value in point):
            raise ContourUnionError(stage, "nonfinite")
    if not is_closed_stroke_contour(commands):
        # Distinguish open paths from closed-but-degenerate contours without
        # expanding any user-provided value into an error message.
        contours: list[list[tuple[float, float]]] = []
        for command in commands:
            if command.kind == "move":
                contours.append([command.points[0]])
            elif not contours:
                raise ContourUnionError(stage, "open")
            else:
                contours[-1].extend(command.points)
        if any(len(points) < 2 or points[-1] != points[0] for points in contours):
            raise ContourUnionError(stage, "open")
        raise ContourUnionError(stage, "degenerate")


def _sort_key(commands: tuple[PathCommand, ...]) -> tuple[tuple[object, ...], ...]:
    return tuple((command.kind, *(coordinate for point in command.points for coordinate in point))
                 for command in commands)


def _to_pathops(commands: tuple[PathCommand, ...]):
    path = pathops.Path(fillType=pathops.FillType.WINDING)
    has_contour = False
    for command in commands:
        if command.kind == "move":
            if has_contour:
                path.close()
            path.moveTo(*command.points[0])
            has_contour = True
        elif command.kind == "line":
            path.lineTo(*command.points[0])
        elif command.kind == "quadratic":
            path.quadTo(*command.points[0], *command.points[1])
    if has_contour:
        path.close()
    return path


def _simplify_operand(commands: tuple[PathCommand, ...]):
    path = _to_pathops(commands)
    path.simplify(fix_winding=True, keep_starting_points=True)
    return path


def _union_pair(left, right):
    return pathops.op(left, right, pathops.PathOp.UNION,
                      fix_winding=True, keep_starting_points=True)


def _quadratic_commands(current: tuple[float, float], points: tuple[tuple[float, float], ...]
                        ) -> tuple[PathCommand, ...]:
    """Expand a qCurve-style control sequence using exact implied midpoints."""
    if len(points) < 2:
        raise ContourUnionError("output", "unsupported-verb")
    if len(points) == 2:
        return (PathCommand("quadratic", points),)
    controls, endpoint = points[:-1], points[-1]
    output: list[PathCommand] = []
    for index, control in enumerate(controls[:-1]):
        next_control = controls[index + 1]
        midpoint = ((control[0] + next_control[0]) / 2,
                    (control[1] + next_control[1]) / 2)
        output.append(PathCommand("quadratic", (control, midpoint)))
    output.append(PathCommand("quadratic", (controls[-1], endpoint)))
    return tuple(output)


def _from_pathops(path) -> tuple[PathCommand, ...]:
    output: list[PathCommand] = []
    current: tuple[float, float] | None = None
    contour_start: tuple[float, float] | None = None
    try:
        segments = tuple(path.segments)
    except Exception as error:
        raise ContourUnionError("output", "operation-failed") from error
    try:
        for segment in segments:
            if not isinstance(segment, (tuple, list)) or len(segment) != 2:
                raise ContourUnionError("output", "unsupported-verb")
            verb, raw_points = segment
            implicit_start = (verb == "qCurveTo" and bool(raw_points)
                              and raw_points[-1] is None)
            if implicit_start:
                raw_points = raw_points[:-1]
            points = tuple(tuple(float(value) for value in point) for point in raw_points)
            if any(len(point) != 2 for point in points):
                raise ContourUnionError("output", "unsupported-verb")
            if any(not isfinite(value) for point in points for value in point):
                raise ContourUnionError("output", "nonfinite")
            if implicit_start:
                if len(points) < 2:
                    raise ContourUnionError("output", "unsupported-verb")
                # The pen protocol's all-off-curve closed contour starts at
                # the implied midpoint of the last and first controls.
                current = contour_start = ((points[-1][0] + points[0][0]) / 2,
                                            (points[-1][1] + points[0][1]) / 2)
                output.append(PathCommand("move", (current,)))
                points = (*points, current)
            if verb == "moveTo" and len(points) == 1:
                current = contour_start = points[0]
                output.append(PathCommand("move", (current,)))
            elif verb == "lineTo" and len(points) == 1 and current is not None:
                current = points[0]
                output.append(PathCommand("line", (current,)))
            elif verb in {"quadTo", "qCurveTo"} and current is not None:
                expanded = _quadratic_commands(current, points)
                output.extend(expanded)
                current = expanded[-1].points[-1]
            elif verb == "closePath" and current is not None and contour_start is not None:
                if current != contour_start:
                    output.append(PathCommand("line", (contour_start,)))
                current = contour_start
            else:
                raise ContourUnionError("output", "unsupported-verb")
    except ContourUnionError:
        raise
    except Exception as error:
        raise ContourUnionError("output", "operation-failed") from error
    result = tuple(output)
    _validate(result, stage="output")
    return result


def union_filled_contours(
    operands: tuple[tuple[PathCommand, ...], ...],
) -> tuple[PathCommand, ...]:
    """Return the nonzero-winding union boundary for completed filled operands.

    Every operand is simplified, including a single operand with multiple
    subpaths. Source operands are sorted before the sequential UNION so the
    result does not depend on catalog-part declaration order.
    """
    if not operands:
        raise ContourUnionError("input", "empty")
    for operand in operands:
        _validate(operand, stage="input")
    ordered = tuple(sorted(operands, key=_sort_key))
    simplified = []
    for operand in ordered:
        try:
            simplified.append(_simplify_operand(operand))
        except ContourUnionError:
            raise
        except Exception as error:
            raise ContourUnionError("simplify", "operation-failed") from error
    result = simplified[0]
    for operand in simplified[1:]:
        try:
            result = _union_pair(result, operand)
        except ContourUnionError:
            raise
        except Exception as error:
            raise ContourUnionError("union", "operation-failed") from error
    return _from_pathops(result)


def _rectangle_commands(rectangle: Rect) -> tuple[PathCommand, ...]:
    """Validate a positive finite rectangle and express it in the shared path grammar."""
    try:
        raw = (rectangle.inline, rectangle.block, rectangle.inline_size, rectangle.block_size)
    except AttributeError as error:
        raise ContourUnionError("input", "unsupported-verb") from error
    if any(isinstance(value, bool) or not isinstance(value, (Real, Decimal)) for value in raw):
        raise ContourUnionError("input", "unsupported-verb")
    try:
        values = tuple(float(value) for value in raw)
    except (OverflowError, TypeError, ValueError) as error:
        raise ContourUnionError("input", "nonfinite") from error
    if not all(isfinite(value) for value in values):
        raise ContourUnionError("input", "nonfinite")
    x, y, width, height = values
    if width <= 0 or height <= 0:
        raise ContourUnionError("input", "degenerate")
    right, bottom = x + width, y + height
    if not isfinite(right) or not isfinite(bottom):
        raise ContourUnionError("input", "nonfinite")
    return (PathCommand("move", ((x, y),)), PathCommand("line", ((right, y),)),
            PathCommand("line", ((right, bottom),)),
            PathCommand("line", ((x, bottom),)), PathCommand("line", ((x, y),)))


def filled_contours_cover_rectangle(
    operands: tuple[tuple[PathCommand, ...], ...], rectangle: Rect,
) -> bool:
    """Return whether nonzero-filled closed operands cover every point of ``rectangle``.

    Coverage is decided by the exact M/L/Q path boolean difference, with no
    sampling, flattening or bounding-box approximation. An empty operand set
    covers nothing. Malformed inputs and pathops failures raise bounded
    ``ContourUnionError`` values so callers can fail closed.
    """
    rectangle_commands = _rectangle_commands(rectangle)
    if not operands:
        return False
    # Share the established operand validation, winding normalization, and
    # deterministic union order with point-outline completion.
    union = union_filled_contours(operands)
    try:
        remainder = pathops.op(_to_pathops(rectangle_commands), _to_pathops(union),
                               pathops.PathOp.DIFFERENCE,
                               fix_winding=True, keep_starting_points=True)
        if not tuple(remainder.segments):
            return True
        _from_pathops(remainder)  # Validate a nonempty backend result before refusing coverage.
        return False
    except ContourUnionError:
        raise
    except Exception as error:
        raise ContourUnionError("difference", "operation-failed") from error
