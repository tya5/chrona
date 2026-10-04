"""#1096: which declaration a text takes in the surface-wide stamping pass, on fake Theme tokens and a fake metric."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_quality import TextFit, TextPlacement
from chrona.presentation.layout.viewer_fit import stamp_text_fits
from chrona.presentation.model.theme_tokens import ViewerFitToken


class Metric:
    content_identity = "sha256:fake"

    def width(self, content, size, letter_spacing=0, numeric_spacing="proportional"):
        return len(content) * size * 0.5


class Tokens:
    """Roles that declare a mode, and which chip roles exist; records every question."""

    def __init__(self, declared, chips=()):
        self.declared, self.chips, self.asked = declared, set(chips), []

    def label_chip(self, role):
        return (Decimal(1), Decimal(0)) if role in self.chips else None

    def viewer_fit(self, role, *, box_follows=True):
        self.asked.append((role, box_follows))
        return ViewerFitToken(self.declared.get(role, "raw"))


def _text(semantic="tableCell", role="text", lines=("abcd",), **extra):
    return TextPlacement("t:" + semantic, "n", " ".join(lines), Rect(Decimal(0), Decimal(0), Decimal(20), Decimal(12)), role,
                         lines=tuple(lines), font_family="F", font_weight=400, font_size=10.0, line_height=1.2,
                         baseline=(0.0, 10.0), semantic_id=semantic, **extra)


def test_raw_everywhere_returns_the_very_same_placements():
    texts = (_text(), _text("legendLabel", "legend"))
    assert stamp_text_fits(texts, Tokens({}), Metric()) == texts
    assert all(a is b for a, b in zip(stamp_text_fits(texts, Tokens({}), Metric()), texts))


def test_a_text_takes_the_mode_of_its_typography_role_without_a_box_to_follow():
    tokens = Tokens({"legend": "text-follows-box"})
    legend, cell = stamp_text_fits((_text("legendLabel", "legend"), _text()), tokens, Metric())
    assert legend.fit == TextFit("text-follows-box", "spacing", (20.0,)) and cell.fit is None
    assert ("legend", False) in tokens.asked and ("text", False) in tokens.asked  # box-follows-text is refused there


def test_a_label_with_a_chip_takes_its_chip_role_and_one_without_takes_its_text_role():
    declared = {"as-of-label-chip": "text-follows-box", "text": "raw"}
    chipped = stamp_text_fits((_text("asOfLabel"),), Tokens(declared, chips={"as-of-label-chip"}), Metric())[0]
    assert chipped.fit is not None
    bare = stamp_text_fits((_text("asOfLabel"),), Tokens(declared), Metric())[0]
    assert bare.fit is None  # no chip is drawn: the chip role's declaration does not apply
    other = stamp_text_fits((_text("memberLabel"),), Tokens(declared, chips={"as-of-label-chip"}), Metric())[0]
    assert other.fit is None  # another label's chip is another role


def test_an_annotation_a_suppressed_run_and_an_empty_line_are_left_alone():
    tokens = Tokens({"text": "text-follows-box"})
    pinned = _text(fit=TextFit("text-follows-box", "spacingAndGlyphs", (7.0,)))
    suppressed = _text("legendLabel", overflow="suppressed")
    empty = _text("tableCell", lines=("ab", ""))
    out = stamp_text_fits((pinned, suppressed, empty), tokens, Metric())
    assert out[0] is pinned and out[1] is suppressed and out[2] is empty
    assert stamp_text_fits((replace(empty, lines=("ab", "abc")),), tokens, Metric())[0].fit.line_inline_sizes == (10.0, 15.0)
