"""Annotation box inline sizing: `annotationContainer.inlineSize: fill` in a notes slot (#1051).

A `fill` note is as wide as its annotations slot (or `maxInlineEm` text sizes when that is smaller), so the
notes of a slot form one aligned column.  This module is pure arithmetic over a caller-supplied measurement:
the caller wraps and measures with the one text measurement (#493) and the kind frame and content insets (#584,
#991), and this module only chooses the width the wrap bound and the box take.  Scene and adapters see the
completed Rect, as for a content-sized note.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians, sin
from typing import Callable

# Measures a note for a wrap bound: (lines, widest line, unrotated frame (inline, block) the content needs).
NoteMeasurer = Callable[[float], tuple[tuple[str, ...], float, tuple[float, float]]]

MAX_TILT_ROUNDS = 16
_TILT_EPSILON = 1e-6


@dataclass(frozen=True)
class FilledNote:
    """The wrapped lines and unrotated frame of a note sized to its slot."""

    lines: tuple[str, ...]
    text_width: float
    frame_inline: float
    frame_block: float
    wrap_inline: float


def fill_target(slot_inline: float, *, max_inline_em: float | None, text_size: float) -> float:
    """The outer inline size a `fill` box aims at: the slot, or the declared maximum when smaller."""
    if max_inline_em is None:
        return slot_inline
    return min(slot_inline, max_inline_em * text_size)


def fill_note(measure: NoteMeasurer, *, target: float, chrome: float, tilt_degrees: float = 0.0) -> FilledNote:
    """Size a note to `target` along the inline axis.

    `chrome` is everything between the box edge and the wrapped text on the inline axis (visuals, kind insets,
    content insets, borders); the wrap bound is `target - chrome`.  A body, header or word the box cannot hold
    makes the frame wider than `target` (the content need wins; it takes the existing visible-overflow path), so
    nothing is clipped.  With a tilt the rotated bounds, not the frame, equal `target`: the frame width solves
    `w * |cos a| + h * |sin a| = target`, where the height `h` follows the wrap, by a bounded monotone iteration.
    """
    if not tilt_degrees:
        wrap_inline = max(1.0, target - chrome)
        lines, text_width, (need_inline, block) = measure(wrap_inline)
        return FilledNote(lines, text_width, max(target, need_inline), block, wrap_inline)
    angle = radians(tilt_degrees)
    along, across = abs(cos(angle)), abs(sin(angle))
    frame = target
    for _ in range(MAX_TILT_ROUNDS):
        wrap_inline = max(1.0, frame - chrome)
        lines, text_width, (need_inline, block) = measure(wrap_inline)
        allowed = (target - block * across) / along - _TILT_EPSILON
        if allowed >= frame - _TILT_EPSILON:
            return FilledNote(lines, text_width, max(allowed, need_inline), block, wrap_inline)
        frame = max(allowed, 1.0)
    return FilledNote(lines, text_width, max(frame, need_inline), block, wrap_inline)
