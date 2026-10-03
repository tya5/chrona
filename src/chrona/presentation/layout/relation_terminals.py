"""Finite Theme terminal treatments resolved into Layout-owned geometry."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from math import atan2, cos, hypot, isfinite, pi, sin, tan

from chrona.presentation.layout.surface_quality import MarkerGeometry, PathCommand

SHAPES = {"triangle", "open-triangle", "chevron", "circle", "open-circle",
          "stealth", "rounded-triangle", "dot", "half", "double-chevron"}
ROUND_SHAPES = {"circle", "open-circle", "dot"}
FILLED_SHAPES = {"triangle", "stealth", "rounded-triangle", "half"}
STEALTH_NOTCH = 0.3          # the notch lies this fraction of the length in from the barbs (0.7 L from the tip)
ROUNDED_CORNER = 0.12        # corner radius of `rounded-triangle`, as a fraction of the head width
CHEVRON_STEP = 0.4           # `double-chevron`: the back chevron is offset by this fraction of the length


def marker_geometry(value: Mapping[str, object]) -> MarkerGeometry:
    """Resolve a closed terminal token before Scene receives the relation."""
    shape = _choice(value, "shape", SHAPES)
    length, width, offset = (_number(value, name) for name in ("headLength", "headWidth", "attachmentOffset"))
    if length <= 0 or width <= 0 or not 0 <= offset <= length:
        raise ValueError("E_THEME_TOKEN_TYPE")
    if shape in ROUND_SHAPES:
        diameter = min(length, width)
        outline = (PathCommand("move", ((diameter / 2, 0.0),)),
                   PathCommand("quadratic", ((diameter, 0.0), (diameter, diameter / 2))),
                   PathCommand("quadratic", ((diameter, diameter), (diameter / 2, diameter))),
                   PathCommand("quadratic", ((0.0, diameter), (0.0, diameter / 2))),
                   PathCommand("quadratic", ((0.0, 0.0), (diameter / 2, 0.0))))
        return MarkerGeometry(outline, diameter, diameter, min(offset, diameter),
                              "stroke" if shape == "open-circle" else "fill", centred=True)
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
    return MarkerGeometry(outline, length, width, offset, mode)


def centred_on_route(marker: MarkerGeometry, role: str) -> MarkerGeometry:
    """A round terminal is centred on the endpoint and the line touches its edge (#1044).

    The SVG marker's reference point is the path start (source) or end (target): the source circle lies behind
    its start (the leg leaves from the circle's edge); the target circle lies ahead of its end (the leg stops at
    the circle's near edge). A declared ``attachmentOffset`` is superseded for these shapes.
    """
    if not marker.centred:
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
        raise ValueError("E_THEME_TOKEN_TYPE")
    return result


def _number(value: Mapping[str, object], name: str) -> float:
    raw = value.get(name)
    if not isinstance(raw, (int, float)) or isinstance(raw, bool) or not isfinite(float(raw)):
        raise ValueError("E_THEME_TOKEN_TYPE")
    return float(raw)
