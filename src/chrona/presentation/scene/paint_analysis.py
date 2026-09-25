"""Pure flat-paint composition facts shared by Scene quality policies."""
from __future__ import annotations

import re


_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def is_hex_color(value: object) -> bool:
    """Return whether a value is one closed six-digit Scene colour."""
    return isinstance(value, str) and _HEX.fullmatch(value) is not None


def composited_contrast(*, fill: str, opacity: float, ground: str) -> float:
    """Return the contrast of flat fill composited over an opaque flat ground."""
    if not is_hex_color(fill) or not is_hex_color(ground) or not 0 <= opacity <= 1:
        raise ValueError("E_SCENE_PAINT_ANALYSIS_INPUT")
    ground_rgb = _rgb(ground)
    return _contrast(_composite(_rgb(fill), opacity, ground_rgb), ground_rgb)


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
