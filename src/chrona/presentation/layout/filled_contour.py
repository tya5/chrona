"""Exact Layout-owned union of closed, nonzero-filled path operands."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import isfinite
from numbers import Real

import pathops

from chrona.presentation.layout.model import LayoutError, Rect
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


class WindowContourError(LayoutError):
    """A bounded failure while completing an explicit-window span contour."""

    def __init__(self, source_ref: str, facet: str, stage: str, reason: str) -> None:
        allowed_stages = {"input", "intersection", "notch", "output"}
        allowed_reasons = {"empty", "open", "degenerate", "nonfinite", "unsupported-verb",
                           "operation-failed", "invalid-identity", "outside-host"}
        self.stage = stage if stage in allowed_stages else "output"
        self.reason = reason if reason in allowed_reasons else "operation-failed"
        # These are source identities, not payloads. Bound malformed values
        # before formatting so backend or caller data cannot produce a dump.
        def bounded(value):
            if not isinstance(value, str):
                return "<invalid>"
            return value[:120]
        self.source_ref = bounded(source_ref)
        self.facet = bounded(facet)
        detail = (f"source_ref={self.source_ref!r} facet={self.facet!r} "
                  f"stage={self.stage} reason={self.reason}")
        super().__init__("E_LAYOUT_WINDOW_CLIP", "/layout/windowContour",
                         node_id=self.source_ref, detail=detail)


def _window_op(left, right, operation, *, source_ref: str, facet: str, stage: str):
    try:
        return pathops.op(left, right, operation, fix_winding=True, keep_starting_points=True)
    except Exception as error:
        raise WindowContourError(source_ref, facet, stage, "operation-failed") from error


def _host_local(commands: tuple[PathCommand, ...], x: float, y: float,
                width: float, height: float) -> tuple[PathCommand, ...]:
    return tuple(PathCommand(command.kind, tuple(((point[0] - x) / width,
                                                   (point[1] - y) / height)
                                                  for point in command.points))
                 for command in commands)


def _host_world(commands: tuple[PathCommand, ...], x: float, y: float,
                width: float, height: float) -> tuple[PathCommand, ...]:
    return tuple(PathCommand(command.kind, tuple((x + point[0] * width,
                                                  y + point[1] * height)
                                                 for point in command.points))
                 for command in commands)


def _control_bounds_within(commands: tuple[PathCommand, ...], x: float, y: float,
                           right: float, bottom: float) -> bool:
    points = tuple(point for command in commands for point in command.points)
    return bool(points) and all(x <= px <= right and y <= py <= bottom for px, py in points)


def clip_span_contour(
    contour: tuple[PathCommand, ...],
    visible_host: Rect,
    *,
    cut_start: bool,
    cut_finish: bool,
    source_ref: str,
    facet: str,
) -> tuple[PathCommand, ...]:
    """Intersect a closed span fill with its host and complete inward cut notches.

    No-cut contours already contained by the host are returned by identity,
    preserving their original quadratic commands and rounding exactly.
    """
    if not isinstance(cut_start, bool) or not isinstance(cut_finish, bool):
        raise WindowContourError(source_ref, facet, "input", "invalid-identity")
    try:
        _validate(contour, stage="input")
        _rectangle_commands(visible_host)
        x, y, width, height = (float(visible_host.inline), float(visible_host.block),
                               float(visible_host.inline_size), float(visible_host.block_size))
        if not all(isfinite(value) for value in (x, y, width, height)):
            raise ContourUnionError("input", "nonfinite")
        right = x + width
        bottom = y + height
        if not isfinite(right) or not isfinite(bottom):
            raise ContourUnionError("input", "nonfinite")
        if not cut_start and not cut_finish and _control_bounds_within(contour, x, y, right, bottom):
            return contour
        local_contour = _host_local(contour, x, y, width, height)
        if any(not isfinite(value) for command in local_contour
               for point in command.points for value in point):
            raise ContourUnionError("input", "nonfinite")
        clip_commands = _rectangle_commands(Rect(Decimal(0), Decimal(0), Decimal(1), Decimal(1)))
        clipped = _window_op(_to_pathops(local_contour), _to_pathops(clip_commands), pathops.PathOp.INTERSECTION,
                             source_ref=source_ref, facet=facet, stage="intersection")
        if not tuple(clipped.segments):
            raise ContourUnionError("intersection", "empty")
        cuts = int(cut_start) + int(cut_finish)
        depth = min(height / (4 * width), 1 / (4 * cuts)) if cuts else 0.0
        notch_opening = 1 / 4  # half of H/2 is measured on either side of center.
        for at_start in (True, False):
            if (at_start and not cut_start) or (not at_start and not cut_finish):
                continue
            edge = 0.0 if at_start else 1.0
            apex = edge + depth if at_start else edge - depth
            triangle = (
                PathCommand("move", ((edge, 1 / 2 - notch_opening),)),
                PathCommand("line", ((apex, 1 / 2),)),
                PathCommand("line", ((edge, 1 / 2 + notch_opening),)),
                PathCommand("line", ((edge, 1 / 2 - notch_opening),)),
            )
            clipped = _window_op(clipped, _to_pathops(triangle), pathops.PathOp.DIFFERENCE,
                                 source_ref=source_ref, facet=facet, stage="notch")
        local_result = _from_pathops(clipped)
        result = _host_world(local_result, x, y, width, height)
        if not _control_bounds_within(result, x, y, right, bottom):
            raise WindowContourError(source_ref, facet, "output", "outside-host")
        return result
    except WindowContourError:
        raise
    except ContourUnionError as error:
        stage = error.stage if error.stage in {"input", "intersection", "notch", "output"} else "input"
        raise WindowContourError(source_ref, facet, stage, error.reason) from error
    except Exception as error:
        raise WindowContourError(source_ref, facet, "intersection", "operation-failed") from error


def intersect_visible_host_contour(
    source: tuple[PathCommand, ...], completed_host: tuple[PathCommand, ...],
    visible_host: Rect, *, source_ref: str, facet: str,
) -> tuple[PathCommand, ...]:
    """Intersect original submark ink with the already-notched visible host.

    Progress and multipart symbols share this geometry operation. Supply the
    original ink, never a fraction reapplied to the shortened host. Empty
    intersection is intentional absence; no second notch or substitute
    rectangle is introduced.
    """
    try:
        _validate(completed_host, stage="input")
        _rectangle_commands(visible_host)
        x, y, width, height = (float(visible_host.inline), float(visible_host.block),
                               float(visible_host.inline_size), float(visible_host.block_size))
        if not _control_bounds_within(completed_host, x, y, x + width, y + height):
            raise WindowContourError(source_ref, facet, "input", "outside-host")
        if not source:
            return ()
        _validate(source, stage="input")
        local_source = _host_local(source, x, y, width, height)
        local_host = _host_local(completed_host, x, y, width, height)
        if any(not isfinite(value) for commands in (local_source, local_host)
               for command in commands for point in command.points for value in point):
            raise ContourUnionError("input", "nonfinite")
        result = _window_op(_to_pathops(local_source), _to_pathops(local_host),
                            pathops.PathOp.INTERSECTION, source_ref=source_ref,
                            facet=facet, stage="intersection")
        if not tuple(result.segments):
            return ()
        completed = _host_world(_from_pathops(result), x, y, width, height)
        if not _control_bounds_within(completed, x, y, x + width, y + height):
            raise WindowContourError(source_ref, facet, "output", "outside-host")
        return completed
    except WindowContourError:
        raise
    except ContourUnionError as error:
        raise WindowContourError(source_ref, facet,
                                 "output" if error.stage == "output" else "input", error.reason) from error
    except Exception as error:
        raise WindowContourError(source_ref, facet, "intersection", "operation-failed") from error


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
