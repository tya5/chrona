"""#1096: which declaration a text takes in the surface-wide stamping pass, on fake Theme tokens and a fake metric."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_quality import IconPlacement, ShapePlacement, TextFit, TextPlacement
from chrona.presentation.layout.viewer_fit import stamp_surface_fits
from chrona.presentation.model.theme_tokens import ViewerFitToken


class Metric:
    content_identity = "sha256:fake"

    def width(self, content, size, letter_spacing=0, numeric_spacing="proportional"):
        return len(content) * size * 0.5


class Tokens:
    """Roles that declare a mode, and which chip roles exist; records every question."""

    def __init__(self, declared):
        self.declared, self.asked = declared, []

    def viewer_fit(self, role, *, box_follows=True):
        self.asked.append((role, box_follows))
        return ViewerFitToken(self.declared.get(role, "raw"))


def _text(semantic="tableCell", role="text", lines=("abcd",), **extra):
    return TextPlacement("t:" + semantic, "n", " ".join(lines), Rect(Decimal(0), Decimal(0), Decimal(20), Decimal(12)), role,
                         lines=tuple(lines), font_family="F", font_weight=400, font_size=10.0, line_height=1.2,
                         baseline=(0.0, 10.0), semantic_id=semantic, **extra)


def _stamp(texts, tokens, shapes=()):
    return stamp_surface_fits(texts, shapes, (), tokens, Metric())[0]


def _chip(text):
    return ShapePlacement("chip:" + text.placement_id, "n", "rect",
                          Rect(Decimal(-5), Decimal(0), Decimal(30), Decimal(12)))


def test_raw_everywhere_returns_the_very_same_placements():
    texts = (_text(), _text("legendLabel", "legend"))
    assert _stamp(texts, Tokens({})) == texts
    assert all(a is b for a, b in zip(_stamp(texts, Tokens({})), texts))


def test_a_text_takes_the_mode_of_its_typography_role_without_a_box_to_follow():
    tokens = Tokens({"legend": "text-follows-box"})
    legend, cell = _stamp((_text("legendLabel", "legend"), _text()), tokens)
    assert legend.fit == TextFit("text-follows-box", "spacing", (20.0,)) and cell.fit is None
    assert ("legend", False) in tokens.asked and ("text", False) in tokens.asked  # box-follows-text is refused there


def test_a_label_with_a_chip_takes_its_chip_role_and_one_without_takes_its_text_role():
    declared = {"as-of-label-chip": "text-follows-box", "text": "raw"}
    label = _text("asOfLabel")
    chipped = _stamp((label,), Tokens(declared), (_chip(label),))[0]
    assert chipped.fit is not None
    bare = _stamp((label,), Tokens(declared))[0]
    assert bare.fit is None  # no chip is drawn: the chip role's declaration does not apply
    other = _stamp((_text("memberLabel"),), Tokens(declared), (_chip(label),))[0]
    assert other.fit is None  # another label's chip is another role


def test_an_annotation_a_suppressed_run_and_an_empty_line_are_left_alone():
    tokens = Tokens({"text": "text-follows-box"})
    pinned = _text(fit=TextFit("text-follows-box", "spacingAndGlyphs", (7.0,)))
    suppressed = _text("legendLabel", overflow="suppressed")
    empty = _text("tableCell", lines=("ab", ""))
    out = _stamp((pinned, suppressed, empty), tokens)
    assert out[0] is pinned and out[1] is suppressed and out[2] is empty
    assert _stamp((replace(empty, lines=("ab", "abc")),), tokens)[0].fit.line_inline_sizes == (10.0, 15.0)


def test_follower_pair_uses_completed_box_identity_and_end_inset():
    text = _text("memberLabel")
    chip = _chip(text)
    texts, shapes = stamp_surface_fits((text,), (chip,), (),
                                      Tokens({"member-label-chip": "box-follows-text"}), Metric())
    assert texts[0].fit == TextFit("box-follows-text", "spacing", (), chip.placement_id, 1)
    assert shapes[0].viewer_fit == "box-follows-text"
    assert shapes[0].bounds is chip.bounds


def test_empty_or_previously_fitted_text_does_not_stamp_a_follower_shape():
    empty = _text("memberLabel", lines=())
    chip = _chip(empty)
    texts, shapes = stamp_surface_fits((empty,), (chip,), (),
                                      Tokens({"member-label-chip": "box-follows-text"}), Metric())
    assert texts[0] is empty and shapes[0] is chip


def test_completed_label_visual_is_refused_before_stamping_a_follower():
    text = _text("memberLabel")
    icon = IconPlacement("visual:" + text.placement_id, "n", "n", "set:icon", "vector", "sha256:fake",
                         (1, 1), (), "", True, text.bounds, host_placement_id=text.placement_id)
    with pytest.raises(LayoutError) as raised:
        stamp_surface_fits((text,), (_chip(text),), (icon,),
                           Tokens({"member-label-chip": "box-follows-text"}), Metric())
    assert raised.value.diagnostic_id == "E_LAYOUT_VIEWER_FIT_STATIC_CHROME"
    assert raised.value.path == text.source_ref
