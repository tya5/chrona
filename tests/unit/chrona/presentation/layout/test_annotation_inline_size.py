"""#1051: the pure fill arithmetic, over a fake measurement (no font, no render)."""
from __future__ import annotations

from math import cos, radians, sin

import pytest

from chrona.presentation.layout.annotation_inline_size import fill_note, fill_target

CHAR, LINE = 10.0, 20.0


def _measure(text, header=0.0):
    """A monospace measurer: ten per character, twenty per line, the content frame is chrome 6 + the widest line."""
    def measure(bound):
        words, lines, current = text.split(), [], ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and len(candidate) * CHAR > bound:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
        widest = max(len(line) for line in lines) * CHAR
        return tuple(lines), widest, (max(widest, header) + 6.0, LINE * len(lines))
    return measure


def test_the_target_is_the_slot_or_the_smaller_maximum():
    assert fill_target(300, max_inline_em=None, text_size=14) == 300
    assert fill_target(300, max_inline_em=10, text_size=14) == 140
    assert fill_target(300, max_inline_em=100, text_size=14) == 300


def test_a_short_body_keeps_the_target_and_a_long_one_wraps_inside_what_the_chrome_leaves():
    short = fill_note(_measure("hi"), target=200, chrome=6.0)
    assert short.frame_inline == 200 and short.lines == ("hi",)
    long = fill_note(_measure("aaaa " * 20), target=200, chrome=6.0)
    assert long.frame_inline == 200 and len(long.lines) > 1
    assert long.text_width <= 200 - 6.0


@pytest.mark.parametrize("degrees", [0, -3, 4, 15])
def test_fill_retains_the_exact_selected_measurement_bound(degrees):
    calls = []
    measure = _measure("aaaa bbbb " * 12)
    def tracked(bound):
        calls.append(bound)
        return measure(bound)
    note = fill_note(tracked, target=240, chrome=6, tilt_degrees=degrees)
    assert note.wrap_inline == calls[-1]
    assert note.lines == measure(note.wrap_inline)[0]


def test_an_unbreakable_word_or_a_header_wider_than_the_target_widens_the_frame_and_is_not_clipped():
    word = fill_note(_measure("x" * 40), target=200, chrome=6.0)
    assert word.frame_inline == 40 * CHAR + 6.0 and word.lines == ("x" * 40,)
    header = fill_note(_measure("hi", header=500.0), target=200, chrome=6.0)
    assert header.frame_inline == 506.0


@pytest.mark.parametrize("degrees", [-12.0, -3.0, 4.0, 15.0])
def test_a_tilted_frame_has_rotated_bounds_equal_to_the_target(degrees):
    note = fill_note(_measure("aaaa bbbb " * 12), target=240, chrome=6.0, tilt_degrees=degrees)
    angle = radians(degrees)
    rotated = note.frame_inline * abs(cos(angle)) + note.frame_block * abs(sin(angle))
    assert rotated == pytest.approx(240, abs=1e-3)
    assert note.text_width + 6.0 <= note.frame_inline + 1e-9
