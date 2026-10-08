"""Ordered foreground/backdrop pairs after completed surface overprints."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import hypot, isfinite
from typing import Any

from chrona.presentation.scene.ink_touch import InkTouchError
from chrona.presentation.scene.paint_analysis import blend_over, is_hex_color
from chrona.presentation.scene.pattern_ink import pattern_ink_touches


@dataclass(frozen=True)
class OverprintPair:
    foreground: str
    backdrop: str
    ground_kind: str
    ground_id: str | None


def ordered_overprint_pairs(subject: Mapping[str, Any], primitives: Sequence[Any], index: int, *,
                              foreground: str, opacity: float,
                              grounds: Sequence[tuple[str, str, str | None]],
                              sample: tuple[float | None, float | None]) -> tuple[OverprintPair, ...]:
    """Apply each later overlay to BOTH colors of each effective pair.

    Sparse ink contributes covered and uncovered alternatives; those alternatives
    remain paired through subsequent layers, rather than mixing independent colors.
    """
    if not is_hex_color(foreground) or not _finite(opacity) or not 0 <= opacity <= 1:
        raise InkTouchError("invalid overprinted subject paint")
    pairs = tuple(OverprintPair(blend_over(ink=foreground, opacity=opacity, ground=ground),
                                ground, kind, identifier) for ground, kind, identifier in grounds)
    order = _order(subject, index)
    overlays = sorted(((_order(item, position), item) for position, item in enumerate(primitives)
                       if isinstance(item, Mapping) and item.get("visualRole") in {
                           "canvas-overlay", "canvas-overlay-gradient"} and _order(item, position) > order),
                      key=lambda item: item[0])
    for _, overlay in overlays:
        paint = overlay.get("paint")
        identifier = overlay.get("id")
        if not isinstance(paint, Mapping) or not isinstance(identifier, str):
            raise InkTouchError("invalid completed overlay paint")
        alpha = paint.get("opacity", 1)
        if not _finite(alpha) or not 0 <= alpha <= 1:
            raise InkTouchError("invalid overlay opacity")
        if overlay["visualRole"] == "canvas-overlay-gradient":
            if not _inside_sample(overlay.get("bounds"), sample):
                continue
            ink, fade = sample_radial_gradient(paint.get("radialGradient"), sample)
            pairs = tuple(_over(pair, ink, float(alpha) * fade, identifier) for pair in pairs)
        else:
            if not is_hex_color(paint.get("stroke")) or paint.get("fill") is not None:
                raise InkTouchError("invalid transparent overlay channels")
            if not pattern_ink_touches(overlay, _bounds(subject.get("bounds"))):
                continue
            pairs = (*pairs, *(_over(pair, paint["stroke"], float(alpha), identifier) for pair in pairs))
    return tuple(dict.fromkeys(pairs))


def sample_radial_gradient(gradient: Any, sample: tuple[float | None, float | None]) -> tuple[str, float]:
    """Read one completed constant-color elliptical alpha field at a channel point."""
    if not isinstance(gradient, Mapping) or not all(_finite(v) for v in sample):
        raise InkTouchError("missing radial gradient sample")
    center, radii, stops = gradient.get("center"), gradient.get("radii"), gradient.get("stops")
    if (not isinstance(center, (list, tuple)) or len(center) != 2 or not all(_finite(v) for v in center)
            or not isinstance(radii, (list, tuple)) or len(radii) != 2
            or not all(_finite(v) and v > 0 for v in radii)
            or not isinstance(stops, list) or len(stops) not in {2, 3}):
        raise InkTouchError("invalid radial gradient geometry")
    normalized = hypot((sample[0] - center[0]) / radii[0], (sample[1] - center[1]) / radii[1])
    color = None
    parsed = []
    for stop in stops:
        if (not isinstance(stop, Mapping) or not is_hex_color(stop.get("color"))
                or not _finite(stop.get("offset")) or not 0 <= stop["offset"] <= 1
                or not _finite(stop.get("opacity")) or not 0 <= stop["opacity"] <= 1):
            raise InkTouchError("invalid radial gradient stop")
        if color is not None and color != stop["color"]:
            raise InkTouchError("radial overlay must use constant ink")
        color = stop["color"]
        parsed.append((float(stop["offset"]), float(stop["opacity"])))
    if parsed[0] != (0, 0) or parsed[-1] != (1, 1) or any(
            first[0] >= second[0] for first, second in zip(parsed, parsed[1:])):
        raise InkTouchError("invalid radial gradient stop order")
    if len(parsed) == 3 and parsed[1][1] != 0:
        raise InkTouchError("invalid radial inner fade")
    position = min(1.0, max(0.0, normalized))
    for (low, low_alpha), (high, high_alpha) in zip(parsed, parsed[1:]):
        if position <= high:
            return color, low_alpha + (high_alpha - low_alpha) * (position - low) / (high - low)
    return color, parsed[-1][1]


def _over(pair: OverprintPair, ink: str, opacity: float, identifier: str) -> OverprintPair:
    return OverprintPair(blend_over(ink=ink, opacity=opacity, ground=pair.foreground),
                         blend_over(ink=ink, opacity=opacity, ground=pair.backdrop),
                         "overlay-blend", identifier)


def _order(primitive: Mapping[str, Any], index: int) -> tuple[int, int]:
    value = primitive.get("paintOrder", 0)
    if not isinstance(value, int) or isinstance(value, bool):
        raise InkTouchError("invalid overlay paint order")
    return value, index


def _bounds(value: Any) -> tuple[float, float, float, float]:
    if not isinstance(value, Mapping):
        raise InkTouchError("missing overprint bounds")
    result = tuple(value.get(name) for name in ("inline", "block", "inlineSize", "blockSize"))
    if not all(_finite(v) for v in result) or result[2] < 0 or result[3] < 0:
        raise InkTouchError("invalid overprint bounds")
    return result


def _inside_sample(bounds: Any, sample: tuple[float | None, float | None]) -> bool:
    x, y, width, height = _bounds(bounds)
    if sample[0] is None or sample[1] is None:
        raise InkTouchError("missing overlay channel point")
    return x <= sample[0] <= x + width and y <= sample[1] <= y + height


def _finite(value: Any) -> bool:
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)
    except (OverflowError, ValueError):
        return False
