"""#1050: Layout's viewer-fit stamping, on a fake metric (no real face involved)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_quality import TextPlacement
from chrona.presentation.layout.viewer_fit import end_pad_spaces, fit_text, line_inline_sizes, require_followable_content
from chrona.presentation.model.theme_tokens import ViewerFitToken


class Metric:
    """Every glyph is half an em wide; a letter spacing is added per glyph."""

    content_identity = "sha256:fake"

    def width(self, content, size, letter_spacing=0, numeric_spacing="proportional"):
        return len(content) * (size * 0.5 + letter_spacing)


def _text(lines=("abcd", "ab"), *, size=10.0, spacing=0.0, scale=1.0):
    return TextPlacement("annotation-text:n", "n", " ".join(lines), Rect(Decimal(0), Decimal(0), Decimal(20), Decimal(24)),
                         "annotation", lines=tuple(lines), font_family="F", font_weight=400, font_size=size,
                         line_height=1.2, letter_spacing=spacing, horizontal_scale=scale, baseline=(0.0, 10.0))


def test_each_line_is_measured_on_its_own_with_the_letter_spacing_and_the_compression():
    assert line_inline_sizes(_text(), Metric()) == (20.0, 10.0)
    assert line_inline_sizes(_text(spacing=1.0), Metric()) == (24.0, 12.0)
    assert line_inline_sizes(_text(scale=0.5), Metric()) == (10.0, 5.0)  # the measured size already holds the squeeze


def test_raw_returns_the_placement_untouched_and_the_modes_stamp_their_facts():
    text = _text()
    assert fit_text(text, ViewerFitToken(), Metric(), box_id="b") is text
    follows = fit_text(text, ViewerFitToken("text-follows-box", "spacingAndGlyphs"), Metric(), box_id="b").fit
    assert (follows.mode, follows.adjust, follows.line_inline_sizes, follows.box_id) == (
        "text-follows-box", "spacingAndGlyphs", (20.0, 10.0), None)
    boxed = fit_text(text, ViewerFitToken("box-follows-text"), Metric(), box_id="b", end_inset=10.0).fit
    assert (boxed.mode, boxed.box_id, boxed.end_pad_spaces, boxed.line_inline_sizes) == ("box-follows-text", "b", 2, ())


@pytest.mark.parametrize("inset,spaces", [(0.0, 0), (-3.0, 0), (5.0, 1), (7.4, 1), (7.6, 2), (15.0, 3)])
def test_the_end_inset_is_the_nearest_whole_count_of_the_faces_own_spaces(inset, spaces):
    assert end_pad_spaces(_text(), Metric(), inset) == spaces  # a space is 5 px here


def test_static_chrome_is_refused_only_for_a_box_that_follows_its_text():
    for token in (ViewerFitToken(), ViewerFitToken("text-follows-box")):
        require_followable_content(token, has_kind_frame=True, has_visual=True, pointer="/annotations/0")
    follows = ViewerFitToken("box-follows-text")
    require_followable_content(follows, has_kind_frame=False, has_visual=False, pointer="/annotations/0")
    for kind, visual in ((True, False), (False, True)):
        with pytest.raises(LayoutError) as raised:
            require_followable_content(follows, has_kind_frame=kind, has_visual=visual, pointer="/annotations/3")
        assert (raised.value.diagnostic_id, raised.value.path) == ("E_LAYOUT_VIEWER_FIT_STATIC_CHROME", "/annotations/3")
