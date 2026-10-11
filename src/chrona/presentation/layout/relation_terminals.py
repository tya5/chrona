"""Finite Theme terminal treatments resolved into Layout-owned geometry."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from math import atan2, cos, degrees, hypot, isfinite, pi, sin, tan

from chrona.presentation.layout.surface_quality import MarkerGeometry, PathCommand

SHAPES = {"triangle", "open-triangle", "chevron", "circle", "open-circle",
          "stealth", "rounded-triangle", "dot", "half", "double-chevron", "none"}
ROUND_SHAPES = {"circle", "open-circle", "dot"}
FILLED_SHAPES = {"triangle", "stealth", "rounded-triangle", "half"}
STEALTH_NOTCH = 0.3          # the notch lies this fraction of the length in from the barbs (0.7 L from the tip)
ROUNDED_CORNER = 0.12        # corner radius of `rounded-triangle`, as a fraction of the head width
CHEVRON_STEP = 0.4           # `double-chevron`: the back chevron is offset by this fraction of the length


def _brief(value: object) -> str:
    if isinstance(value, str):
        clipped = value[:64]
        return repr(clipped + ("…" if len(value) > len(clipped) else ""))
    if value is None or isinstance(value, (bool, int, float)):
        return repr(value)
    return f"<{type(value).__name__}>"


def marker_geometry(value: Mapping[str, object], *, stroke_width: float = 1.0) -> MarkerGeometry | None:
    """Resolve a closed terminal token before Scene receives the relation.

    ``none`` (#1105) resolves to ``None``, the existing "no marker" value: no primitive, no setback. Its numbers
    are validated like any other shape and ignored.
    """
    shape = _choice(value, "shape", SHAPES)
    length, width = (_number(value, name) for name in ("headLength", "headWidth"))
    derived = "attachmentOffset" not in value
    offset = 0.0 if derived else _number(value, "attachmentOffset")
    if length <= 0 or width <= 0 or not 0 <= offset <= length:
        raise ValueError(f"E_THEME_TOKEN_TYPE: terminal shape={shape!r} requires positive headLength/headWidth and attachmentOffset in [0, headLength]; headLength={length!r}, headWidth={width!r}, attachmentOffset={offset!r}")
    if derived and (isinstance(stroke_width, bool) or not isinstance(stroke_width, (int, float))
                    or not isfinite(stroke_width) or stroke_width < 0):
        raise ValueError(f"E_THEME_TOKEN_TYPE: derived terminal stroke width={_brief(stroke_width)} must be finite and nonnegative")
    if shape == "none":
        return None
    if shape in ROUND_SHAPES:
        diameter = min(length, width)
        outline = (PathCommand("move", ((diameter / 2, 0.0),)),
                   PathCommand("quadratic", ((diameter, 0.0), (diameter, diameter / 2))),
                   PathCommand("quadratic", ((diameter, diameter), (diameter / 2, diameter))),
                   PathCommand("quadratic", ((0.0, diameter), (0.0, diameter / 2))),
                   PathCommand("quadratic", ((0.0, 0.0), (diameter / 2, 0.0))))
        return MarkerGeometry(outline, diameter, diameter, min(offset, diameter),
                              "stroke" if shape == "open-circle" else "fill", centred=True,
                              physical_units=derived,
                              stroke_width=float(stroke_width) if derived and shape == "open-circle" else None)
    mode = "fill" if shape in FILLED_SHAPES else "stroke"
    if shape == "rounded-triangle":
        outline = _rounded_polygon(((0.0, 0.0), (length, width / 2), (0.0, width)), ROUNDED_CORNER * width)
    elif shape == "stealth":
        outline = _polygon(((0.0, 0.0), (length, width / 2), (0.0, width), (STEALTH_NOTCH * length, width / 2)))
    elif shape == "half":  # one barb on the left of the line's direction (SVG y grows downward: the top)
        outline = _polygon(((length, width / 2), (0.0, 0.0), (0.0, width / 2)))
    elif shape == "double-chevron":
        step = CHEVRON_STEP * length
        outline = ()
        for origin in (0.0, step):
            outline += (PathCommand("move", ((origin, 0.0),)), PathCommand("line", ((origin + length - step, width / 2),)),
                        PathCommand("line", ((origin, width),)))
    else:  # triangle, open-triangle (closed, three edges) and chevron (an open V, no closing edge) (#1042)
        outline = (PathCommand("move", ((0.0, 0.0),)), PathCommand("line", ((length, width / 2),)),
                   PathCommand("line", ((0.0, width),)))
        if shape in {"triangle", "open-triangle"}:
            outline += (PathCommand("line", ((0.0, 0.0),)),)
    painted_run = None
    if derived:
        tip = _outline_tip(outline)
        back = -_outline_tip(tuple(PathCommand(command.kind, tuple((-x, y) for x, y in command.points))
                                  for command in outline))
        if mode == "stroke":
            # SVG's established butt-cap/miter-join treatment, completed here
            # in physical units. A sharp join beyond the miter limit is beveled.
            run = length * (1 - CHEVRON_STEP) if shape == "double-chevron" else length
            miter_ratio = hypot(run, width / 2) / (width / 2)
            tip += stroke_width / 2 * (miter_ratio if miter_ratio <= 4 else 1 / miter_ratio)
            # The closed triangle's rear vertical edge reaches half a stroke
            # behind x=0; open Vs have butt caps with only their normal's x reach.
            back -= stroke_width / 2 * (1 if shape == "open-triangle" else 1 / miter_ratio)
        offset = length - tip
        painted_run = tip - back
    return MarkerGeometry(outline, length, width, offset, mode,
                          physical_units=derived,
                          stroke_width=float(stroke_width) if derived and mode == "stroke" else None,
                          painted_run=painted_run)


def _outline_tip(outline: tuple[PathCommand, ...]) -> float:
    """Exact forward extent, including interior extrema of quadratic curves."""
    extent = float("-inf")
    previous = None
    for command in outline:
        end = command.points[-1]
        extent = max(extent, end[0])
        if command.kind == "quadratic":
            if previous is None:
                raise ValueError("E_LAYOUT_PATH_COMMAND_INVALID: terminal quadratic contour requires a preceding move or line endpoint")
            start_x, control_x, end_x = previous[0], command.points[0][0], end[0]
            denominator = start_x - 2 * control_x + end_x
            if denominator:
                t = (start_x - control_x) / denominator
                if 0 < t < 1:
                    extent = max(extent, (1 - t)**2 * start_x + 2 * (1 - t) * t * control_x + t*t * end_x)
        previous = end
    return extent


def terminal_run(marker: MarkerGeometry | None) -> float:
    """The straight run a terminal needs on its leg: none for no terminal or a centred round one."""
    return 0.0 if marker is None or marker.centred else terminal_length(marker)


def terminal_length(marker: MarkerGeometry | None) -> float:
    """How far a terminal reaches back from its port along the route (0 for none)."""
    if marker is None:
        return 0.0
    return marker.painted_run if marker.painted_run is not None and not marker.centred else marker.head_length


def project_marker_outline(marker: MarkerGeometry, *, side: str, points: tuple[tuple[float, float], ...],
                           path_commands: tuple[PathCommand, ...], stroke_width: float | None
                           ) -> tuple[PathCommand, ...]:
    """Project a completed marker outline exactly as the SVG marker reference transform does.

    This is a geometry projection only: it chooses neither a route nor a port. ``side`` names the already
    completed path endpoint, whose point and tangent are supplied by Layout/Scene. SVG's reference point is
    ``(head_length - attachment_offset, head_width / 2)``. ``userSpaceOnUse`` has unit scale; legacy
    ``markerUnits=strokeWidth`` scales the viewBox by the completed host stroke width.
    """
    if side not in {"start", "end"}:
        raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID: marker side must be a completed start or end endpoint")
    anchors = _marker_anchor_tangents(side, points, path_commands)
    if (not isfinite(marker.head_length) or not isfinite(marker.head_width)
            or marker.head_length <= 0 or marker.head_width <= 0
            or not isfinite(marker.attachment_offset)
            or (not marker.physical_units
                and not 0 <= marker.attachment_offset <= marker.head_length)):
        raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID: marker projection requires finite completed dimensions, offset, and angle")
    if (not marker.outline or any(not isfinite(value) for command in marker.outline
                                  for point in command.points for value in point)):
        raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID: marker projection requires a finite non-empty completed outline")
    if marker.physical_units:
        scale = 1.0
    else:
        if (isinstance(stroke_width, bool) or not isinstance(stroke_width, (int, float))
                or not isfinite(stroke_width) or stroke_width <= 0):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID: strokeWidth-unit marker requires a finite positive host stroke width")
        scale = float(stroke_width)
    ref_x, ref_y = marker.head_length - marker.attachment_offset, marker.head_width / 2
    projected: list[PathCommand] = []
    for anchor, tangent in anchors:
        angle = marker.angle_degrees if marker.angle_degrees is not None else tangent
        if not isfinite(angle):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID: marker projection requires a finite completed angle")
        for command in marker.outline:
            transformed = tuple(_marker_point(point, anchor, angle, scale, ref_x, ref_y)
                                for point in command.points)
            if any(not isfinite(value) for point in transformed for value in point):
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID: marker projection produced a non-finite absolute coordinate")
            projected.append(PathCommand(command.kind, transformed))
    return tuple(projected)


def _marker_anchor_tangents(side: str, points: tuple[tuple[float, float], ...],
                            commands: tuple[PathCommand, ...]) -> tuple[tuple[tuple[float, float], float], ...]:
    """Read SVG marker anchors and true endpoint tangents without changing the supplied path."""
    if commands:
        if any(command.kind not in {"move", "line", "quadratic"} for command in commands):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID: marker projection requires completed move/line/quadratic path commands")
        if any(not isfinite(value) for command in commands for point in command.points for value in point):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID: marker projection path has non-finite coordinates")
        if commands[0].kind != "move":
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID: marker projection path must begin with a move command")
        subpaths: list[list[PathCommand]] = []
        for command in commands:
            if command.kind == "move":
                subpaths.append([command])
            elif not subpaths:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID: marker projection path has drawing commands before its move")
            else:
                subpaths[-1].append(command)
        results = []
        # SVG marker-start/end belong to the entire path, not every subpath.
        # https://www.w3.org/TR/SVG2/painting.html#VertexMarkerProperties
        for subpath in (subpaths[0] if side == "start" else subpaths[-1],):
            anchor = subpath[0].points[0] if side == "start" else subpath[-1].points[-1]
            current = subpath[0].points[0]
            directed: list[tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]]] = []
            for command in subpath[1:]:
                end = command.points[-1]
                start_tangent = command.points[0] if command.kind == "quadratic" else end
                end_tangent = current if command.kind == "line" else command.points[0]
                directed.append((current, start_tangent, end_tangent, end))
                current = end
            samples = directed if side == "start" else list(reversed(directed))
            tangent = None
            for start, start_tangent, end_tangent, end in samples:
                if side == "start":
                    dx, dy = start_tangent[0] - start[0], start_tangent[1] - start[1]
                    if dx == 0 and dy == 0:
                        dx, dy = end[0] - start[0], end[1] - start[1]
                else:
                    dx, dy = end[0] - end_tangent[0], end[1] - end_tangent[1]
                    if dx == 0 and dy == 0:
                        dx, dy = end[0] - start[0], end[1] - start[1]
                if dx or dy:
                    tangent = degrees(atan2(dy, dx))
                    break
            if tangent is None:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID: marker projection path has no nonzero endpoint tangent")
            results.append((anchor, tangent))
        return tuple(results)
    else:
        if len(points) < 2:
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID: marker projection requires a completed path endpoint and tangent")
        if any(not isfinite(value) for point in points for value in point):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID: marker projection path has non-finite coordinates")
        anchor = points[0] if side == "start" else points[-1]
        candidates = list(zip(points, points[1:]))
        if side == "end":
            candidates.reverse()
    for start, end in candidates:
        dx, dy = end[0] - start[0], end[1] - start[1]
        if dx or dy:
            return ((anchor, degrees(atan2(dy, dx))),)
    raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID: marker projection requires a nonzero endpoint tangent")


def _marker_point(point: tuple[float, float], anchor: tuple[float, float], angle: float,
                  scale: float, ref_x: float, ref_y: float) -> tuple[float, float]:
    radians = angle % 360
    if radians in {0, 90, 180, 270}:
        cosine, sine = ((1, 0), (0, 1), (-1, 0), (0, -1))[int(radians / 90)]
    else:
        radians *= pi / 180
        cosine, sine = cos(radians), sin(radians)
    x, y = (point[0] - ref_x) * scale, (point[1] - ref_y) * scale
    return (anchor[0] + x * cosine - y * sine,
            anchor[1] + x * sine + y * cosine)


def orient_terminal(marker: MarkerGeometry | None, points: tuple[tuple[float, float], ...],
                    side: str, *, source: bool) -> MarkerGeometry | None:
    """Complete a short-tangent marker's axis in Layout, leaving honest tangents unchanged."""
    if marker is None or len(points) < 2:
        return marker
    segments = list(zip(points, points[1:]))
    if not source:
        segments.reverse()
    a, b = segments[0]
    required = terminal_length(marker)
    if hypot(b[0] - a[0], b[1] - a[1]) + 1e-6 >= required:
        return marker
    direction = {"start": (-1, 0), "end": (1, 0), "above": (0, -1), "below": (0, 1)}.get(side)
    if direction is not None and not source:
        direction = (-direction[0], -direction[1])
    if direction is None:
        direction = next(((b[0] - a[0], b[1] - a[1]) for a, b in segments
                          if hypot(b[0] - a[0], b[1] - a[1]) + 1e-6 >= required),
                         (b[0] - a[0], b[1] - a[1]))
    angle = degrees(atan2(direction[1], direction[0]))
    # An equivalent auto tangent retains the established public bytes.
    tangent = degrees(atan2(segments[0][1][1] - segments[0][0][1],
                           segments[0][1][0] - segments[0][0][0]))
    return marker if abs(angle - tangent) < 1e-6 else replace(marker, angle_degrees=angle)


def complete_centred_terminals(points: tuple[tuple[float, float], ...], start: MarkerGeometry | None,
                              end: MarkerGeometry | None, minimum: float
                              ) -> tuple[tuple[tuple[float, float], ...], MarkerGeometry | None, MarkerGeometry | None]:
    """Keep a stroke-width run between nearby round terminals, centred on the original ports.

    When the clear gap is narrower than the stroke, the stroke extends slightly
    under the round heads. Their reference offsets change, never their centres.
    """
    if len(points) == 2:
        leg = hypot(points[1][0] - points[0][0], points[1][1] - points[0][1])
        first = start.head_length / 2 if start is not None and start.centred else 0.0
        last = end.head_length / 2 if end is not None and end.centred else 0.0
        total = first + last
        if total and leg < total + minimum:
            factor = max(0.0, leg - minimum) / total
            first *= factor; last *= factor
            if start is not None and start.centred:
                start = replace(start, attachment_offset=start.head_length / 2 - first)
            if end is not None and end.centred:
                end = replace(end, attachment_offset=end.head_length / 2 + last)
            return ((_along(points[0], points[1], first, last),
                     _along(points[1], points[0], last, first)), start, end)
    return trim_for_centred_terminals(points, start, end), start, end


def centred_on_route(marker: MarkerGeometry | None, role: str) -> MarkerGeometry | None:
    """A round terminal is centred on the endpoint and the line touches its edge (#1044).

    The SVG marker's reference point is the path start (source) or end (target): the source circle lies behind
    its start (the leg leaves from the circle's edge); the target circle lies ahead of its end (the leg stops at
    the circle's near edge). A declared ``attachmentOffset`` is superseded for these shapes.
    """
    if marker is None or not marker.centred:
        return marker
    return replace(marker, attachment_offset=marker.head_length if role == "target" else 0.0)


def trim_for_centred_terminals(points: tuple[tuple[float, float], ...], start: MarkerGeometry | None,
                               end: MarkerGeometry | None) -> tuple[tuple[float, float], ...]:
    """Move the first and last route point inward by the circle radius so the circle's centre is the port.

    A leg shorter than the radius limits the shift to half the leg: the circle is then not exactly centred.
    """
    if len(points) < 2:
        return points
    first = start.head_length / 2 if start is not None and start.centred else 0.0
    last = end.head_length / 2 if end is not None and end.centred else 0.0
    result = list(points)
    single = len(points) == 2
    if first:
        result[0] = _along(points[0], points[1], first, last if single else 0.0)
    if last:
        result[-1] = _along(points[-1], points[-2], last, first if single else 0.0)
    return tuple(result)


def _along(origin: tuple[float, float], toward: tuple[float, float], amount: float, reserved: float
           ) -> tuple[float, float]:
    leg = hypot(toward[0] - origin[0], toward[1] - origin[1])
    if leg == 0:
        return origin
    shift = amount if leg >= amount + reserved + 1e-6 else 0.5 * leg * amount / (amount + reserved)
    return (origin[0] + (toward[0] - origin[0]) * shift / leg, origin[1] + (toward[1] - origin[1]) * shift / leg)


def _polygon(points: tuple[tuple[float, float], ...]) -> tuple[PathCommand, ...]:
    return (PathCommand("move", (points[0],)), *(PathCommand("line", (point,)) for point in points[1:]),
            PathCommand("line", (points[0],)))


def _rounded_polygon(points: tuple[tuple[float, float], ...], radius: float) -> tuple[PathCommand, ...]:
    """A closed polygon whose corners are cut to an arc of about ``radius``; the corner is the control point."""
    commands: list[PathCommand] = []
    for index, vertex in enumerate(points):
        previous, following = points[index - 1], points[(index + 1) % len(points)]
        back = atan2(previous[1] - vertex[1], previous[0] - vertex[0])
        forward = atan2(following[1] - vertex[1], following[0] - vertex[0])
        angle = abs((forward - back + pi) % (2 * pi) - pi)
        cut = min(radius / tan(angle / 2), hypot(previous[0] - vertex[0], previous[1] - vertex[1]) / 2,
                  hypot(following[0] - vertex[0], following[1] - vertex[1]) / 2)
        commands.append(PathCommand("move" if index == 0 else "line",
                                    ((vertex[0] + cos(back) * cut, vertex[1] + sin(back) * cut),)))
        commands.append(PathCommand("quadratic", (vertex, (vertex[0] + cos(forward) * cut,
                                                           vertex[1] + sin(forward) * cut))))
    commands.append(PathCommand("line", (commands[0].points[0],)))
    return tuple(commands)


def _choice(value: Mapping[str, object], name: str, choices: set[str]) -> str:
    result = value.get(name)
    if not isinstance(result, str) or result not in choices:
        raise ValueError(f"E_THEME_TOKEN_TYPE: terminal {name}={_brief(result)}; expected one of {sorted(choices)!r}")
    return result


def _number(value: Mapping[str, object], name: str) -> float:
    raw = value.get(name)
    if not isinstance(raw, (int, float)) or isinstance(raw, bool) or not isfinite(float(raw)):
        raise ValueError(f"E_THEME_TOKEN_TYPE: terminal {name}={_brief(raw)}; expected a finite number")
    return float(raw)
