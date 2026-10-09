"""Pure flat-paint composition facts shared by Scene quality policies."""
from __future__ import annotations

import re
from math import isfinite
from typing import Any, Mapping


_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _brief(value: object) -> str:
    if isinstance(value, str):
        clipped = value[:64]
        return repr(clipped + ("…" if len(value) > len(clipped) else ""))
    if value is None or isinstance(value, (bool, int, float)):
        return repr(value)
    if isinstance(value, (tuple, list)) and len(value) <= 4 and all(
            item is None or isinstance(item, (bool, int, float, str)) for item in value):
        return repr(type(value)(value))
    return f"<{type(value).__name__}>"


def _analysis_error(detail: str) -> ValueError:
    return ValueError(f"E_SCENE_PAINT_ANALYSIS_INPUT: {detail}")


def is_hex_color(value: object) -> bool:
    """Return whether a value is one closed six-digit Scene colour."""
    return isinstance(value, str) and _HEX.fullmatch(value) is not None


def composited_contrast(*, fill: str, opacity: float, ground: str) -> float:
    """Return the contrast of flat fill composited over an opaque flat ground."""
    if not is_hex_color(fill) or not is_hex_color(ground) or not 0 <= opacity <= 1:
        raise _analysis_error(f"fill={_brief(fill)} and ground={_brief(ground)} must be #RRGGBB; opacity={_brief(opacity)} must be in [0, 1]")
    ground_rgb = _rgb(ground)
    return _contrast(_composite(_rgb(fill), opacity, ground_rgb), ground_rgb)


def sample_linear_gradient(gradient: Mapping[str, Any], point: tuple[float, float]) -> str:
    """Sample one completed opaque SVG-like user-space linear gradient in sRGB."""
    try:
        start, end = gradient["start"], gradient["end"]
        x0, y0, x1, y1 = float(start[0]), float(start[1]), float(end[0]), float(end[1])
        stops = [(float(item["offset"]), item["color"]) for item in gradient["stops"]]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise _analysis_error(f"gradient must provide finite start/end coordinate pairs and ordered stop mappings; malformed field or value type={type(error).__name__}") from error
    if (not all(isfinite(value) for value in (x0, y0, x1, y1, *point))
            or len(stops) < 2 or stops[0][0] != 0 or stops[-1][0] != 1
            or any(not isfinite(offset) or not is_hex_color(color) for offset, color in stops)
            or any(left[0] >= right[0] for left, right in zip(stops, stops[1:]))):
        raise _analysis_error(f"linear gradient requires finite endpoints and sample point, at least two #RRGGBB stops spanning offsets 0..1 in strict order; sample point={_brief(point)}, stop_count={len(stops)}, first_offset={_brief(stops[0][0]) if stops else 'missing'}, last_offset={_brief(stops[-1][0]) if stops else 'missing'}")
    dx, dy = x1 - x0, y1 - y0
    length_sq = dx * dx + dy * dy
    t = 1.0 if length_sq == 0 else max(0.0, min(1.0, ((point[0] - x0) * dx + (point[1] - y0) * dy) / length_sq))
    for (low_t, low_color), (high_t, high_color) in zip(stops, stops[1:]):
        if t <= high_t:
            weight = (t - low_t) / (high_t - low_t)
            low, high = _rgb(low_color), _rgb(high_color)
            channels = tuple(min(255, max(0, int((a + (b - a) * weight) * 255 + 0.5)))
                             for a, b in zip(low, high))
            return "#" + "".join(f"{channel:02X}" for channel in channels)
    return str(stops[-1][1]).upper()


def _rgb(value: str) -> tuple[float, float, float]:
    return tuple(int(value[index:index + 2], 16) / 255 for index in (1, 3, 5))


def _composite(foreground: tuple[float, float, float], opacity: float,
               background: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(opacity * front + (1 - opacity) * back for front, back in zip(foreground, background))


def _contrast(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    def luminance(color: tuple[float, float, float]) -> float:
        channels = tuple(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
                         for channel in color)
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
    return (max(luminance(first), luminance(second)) + 0.05) / (min(luminance(first), luminance(second)) + 0.05)


def blend_over(*, ink: str, opacity: float, ground: str) -> str:
    """Return the opaque colour of ``ink`` at ``opacity`` composited over an opaque ground, as ``#RRGGBB``."""
    if not is_hex_color(ink) or not is_hex_color(ground) or not 0 <= opacity <= 1:
        raise _analysis_error(f"ink={_brief(ink)} and ground={_brief(ground)} must be #RRGGBB; opacity={_brief(opacity)} must be in [0, 1]")
    channels = _composite(_rgb(ink), opacity, _rgb(ground))
    return "#" + "".join(f"{min(255, max(0, int(channel * 255 + 0.5))):02X}" for channel in channels)
