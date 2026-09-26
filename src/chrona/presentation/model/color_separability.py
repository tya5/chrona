"""Perceptual separability of categorical colours (Specification 60).

Pure colour arithmetic: CIEDE2000 on sRGB and colour-vision-deficiency
simulation with the Machado, Oliveira and Fernandes (2009) matrices at
severity 1.0.  No Theme, Layout or renderer knowledge lives here.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import combinations

MINIMUM_CATEGORY_DELTA_E = 5.0
SIMULATED_VISIONS = ("protanopia", "deuteranopia", "tritanopia")

_MACHADO = {
    "protanopia": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    "deuteranopia": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    "tritanopia": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
}


@dataclass(frozen=True)
class ScaleCollision:
    """Two domain values of one scale that a reader cannot tell apart."""

    scale_id: str
    first: str
    second: str
    vision: str
    delta_e: float

    @property
    def code(self) -> str:
        return "W_PRESENTATION_SCALE_NOT_SEPARABLE"

    def scene_diagnostic(self) -> str:
        return f"{self.code}:{self.scale_id}:{self.first}:{self.second}:{self.vision}"


def _linear(hex_colour: str) -> tuple[float, float, float]:
    value = hex_colour.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"E_COLOR_VALUE:{hex_colour}")
    channels = tuple(int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))
    red, green, blue = (part / 12.92 if part <= 0.04045 else ((part + 0.055) / 1.055) ** 2.4 for part in channels)
    return red, green, blue


def _lab(linear: tuple[float, float, float]) -> tuple[float, float, float]:
    red, green, blue = (min(1.0, max(0.0, part)) for part in linear)
    x = (0.4124564 * red + 0.3575761 * green + 0.1804375 * blue) / 0.95047
    y = 0.2126729 * red + 0.7151522 * green + 0.0721750 * blue
    z = (0.0193339 * red + 0.1191920 * green + 0.9503041 * blue) / 1.08883

    def f(value: float) -> float:
        return value ** (1 / 3) if value > 216 / 24389 else (24389 / 27 * value + 16) / 116

    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def _simulate(linear: tuple[float, float, float], vision: str) -> tuple[float, float, float]:
    if vision == "normal":
        return linear
    matrix = _MACHADO[vision]
    red, green, blue = (sum(row[index] * linear[index] for index in range(3)) for row in matrix)
    return red, green, blue


def _ciede2000(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    l1, a1, b1 = first
    l2, a2, b2 = second
    c_bar = (math.hypot(a1, b1) + math.hypot(a2, b2)) / 2
    g = 0.5 * (1 - math.sqrt(c_bar ** 7 / (c_bar ** 7 + 25 ** 7)))
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    delta_l, delta_c = l2 - l1, c2p - c1p
    delta_h = h2p - h1p
    if c1p * c2p == 0:
        delta_h = 0.0
    elif delta_h > 180:
        delta_h -= 360
    elif delta_h < -180:
        delta_h += 360
    delta_hp = 2 * math.sqrt(c1p * c2p) * math.sin(math.radians(delta_h / 2))
    l_bar, cp_bar = (l1 + l2) / 2, (c1p + c2p) / 2
    if c1p * c2p == 0:
        h_bar = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        h_bar = (h1p + h2p) / 2
    else:
        h_bar = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    t = (1 - 0.17 * math.cos(math.radians(h_bar - 30)) + 0.24 * math.cos(math.radians(2 * h_bar))
         + 0.32 * math.cos(math.radians(3 * h_bar + 6)) - 0.20 * math.cos(math.radians(4 * h_bar - 63)))
    delta_theta = 30 * math.exp(-((h_bar - 275) / 25) ** 2)
    r_c = 2 * math.sqrt(cp_bar ** 7 / (cp_bar ** 7 + 25 ** 7))
    s_l = 1 + 0.015 * (l_bar - 50) ** 2 / math.sqrt(20 + (l_bar - 50) ** 2)
    s_c = 1 + 0.045 * cp_bar
    s_h = 1 + 0.015 * cp_bar * t
    r_t = -math.sin(math.radians(2 * delta_theta)) * r_c
    return math.sqrt((delta_l / s_l) ** 2 + (delta_c / s_c) ** 2 + (delta_hp / s_h) ** 2
                     + r_t * (delta_c / s_c) * (delta_hp / s_h))


def delta_e_2000(first: str, second: str, *, vision: str = "normal") -> float:
    """Return the CIEDE2000 difference of two sRGB colours as seen under ``vision``."""
    if vision != "normal" and vision not in _MACHADO:
        raise ValueError(f"E_COLOR_VISION_UNKNOWN:{vision}")
    return _ciede2000(_lab(_simulate(_linear(first), vision)), _lab(_simulate(_linear(second), vision)))


def scale_collisions(scale_id: str, colours: tuple[tuple[str, str], ...],
                     color_vision: tuple[str, ...] = ()) -> tuple[ScaleCollision, ...]:
    """Return every domain pair below the minimum, in domain order, then vision order."""
    visions = ("normal", *(vision for vision in SIMULATED_VISIONS if vision in color_vision))
    collisions = []
    for (first, first_colour), (second, second_colour) in combinations(colours, 2):
        for vision in visions:
            distance = delta_e_2000(first_colour, second_colour, vision=vision)
            if distance < MINIMUM_CATEGORY_DELTA_E:
                collisions.append(ScaleCollision(scale_id, first, second, vision, round(distance, 3)))
    return tuple(collisions)
