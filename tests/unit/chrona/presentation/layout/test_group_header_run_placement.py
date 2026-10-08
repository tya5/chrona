"""Group-header runs (#1192): exact measurement, gaps, one baseline, which run gives way, and role admission."""
from __future__ import annotations

from decimal import Decimal

import pytest

from chrona.presentation.layout.group_header_runs import place_group_header_runs, validate_group_header_roles
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.model.theme_tokens import TextTreatment

SIZES = {"groupHeader": 10, "ordinal": 20, "gloss": 5}
SPACING = {"gloss": Decimal("0.5")}
TRANSFORM = {"gloss": "uppercase"}


class _Font:
    """Every character is half the font size wide, so each width is exact arithmetic."""

    content_identity = "sha256:test"
    ascent = 900

    def width(self, content, size, letter_spacing=0, numeric_spacing="proportional"):
        return len(content) * size / 2 + max(0, len(content) - 1) * letter_spacing

    def ensure_numeric_spacing(self, _spacing):
        return None


class _Tokens:
    def text_treatment(self, role):
        size = Decimal(SIZES[role])
        return TextTreatment("Test Sans", 400, size, Decimal("1.2"), SPACING.get(role, Decimal(0)),
                             TRANSFORM.get(role, "none"), "proportional", Decimal(1))


def _place(runs, *, start=100, size=1000, bounded=False):
    return place_group_header_runs(
        group_id="g", runs=runs, start=Decimal(start), size=Decimal(size), bounded=bounded, baseline_block=50.0,
        header_block_size=20.0, theme_tokens=_Tokens(), font_metrics=_Font())


def _starts(placements):
    return [item.baseline[0] for item in placements]


def test_runs_are_laid_in_order_on_one_baseline_each_in_its_own_role_and_size():
    placements, warnings = _place((("01", "ordinal"), (" Bus  ", None), ("gloss", "gloss")))

    assert warnings == ()
    assert [item.placement_id for item in placements] == ["group-header:g#run0", "group-header:g#run1",
                                                          "group-header:g#run2"]
    assert [item.typography_role for item in placements] == ["ordinal", "groupHeader", "gloss"]
    assert [item.font_size for item in placements] == [20, 10, 5]
    assert {item.baseline[1] for item in placements} == {50.0}
    assert [item.content for item in placements] == ["01", "Bus", "GLOSS"]


def test_the_block_is_the_sum_of_the_runs_and_the_gaps():
    # ordinal 2 x 10 = 20; " " before Bus = 1 space of the groupHeader face = 5; Bus = 15; two spaces = 10;
    # GLOSS is five characters of 2.5 plus four letter-spacings of 0.5 x 5 = 12.5 + 10 = 22.5.
    placements, _ = _place((("01", "ordinal"), (" Bus  ", None), ("gloss", "gloss")))

    assert _starts(placements) == [100, 125, 150]
    assert placements[0].bounds.inline_size == 20
    assert placements[1].bounds.inline_size == 15
    right = _starts(placements)[-1] + float(placements[-1].bounds.inline_size)
    assert right - 100 == 20 + 5 + 15 + 10 + float(placements[-1].bounds.inline_size)


def test_whitespace_is_measured_in_the_face_of_the_run_it_belongs_to():
    # The space after the ordinal belongs to the ordinal's own text here, so it is 2 x 10 / 2 wide.
    in_ordinal, _ = _place((("01 ", "ordinal"), ("Bus", None)))
    in_title, _ = _place((("01", "ordinal"), (" Bus", None)))

    assert _starts(in_ordinal) == [100, 130]
    assert _starts(in_title) == [100, 125]


def test_a_whitespace_only_run_is_a_gap_and_trailing_whitespace_is_nothing():
    placements, _ = _place((("a", "ordinal"), ("   ", None), ("b", "gloss"), ("   ", None)))

    assert len(placements) == 2 and _starts(placements) == [100, 100 + 10 + 15]


def test_an_unbounded_block_keeps_every_run_even_past_the_available_size():
    placements, warnings = _place((("0123456789", "ordinal"), ("Title text", None)), size=50)

    assert warnings == () and [item.content for item in placements] == ["0123456789", "Title text"]


def test_a_bounded_block_shortens_the_last_run_first_and_keeps_its_source():
    # Runs: ordinal 20, gap 5, title 15; room 30 leaves 5 for the title: one character and no room for an ellipsis.
    placements, warnings = _place((("01", "ordinal"), (" Bus", None)), size=38, bounded=True)

    assert placements[0].content == "01" and placements[0].overflow == "fit"
    assert placements[1].overflow == "ellipsized" and placements[1].content.endswith("…")
    assert placements[1].source_content == "Bus"
    assert [(item.code, item.placement_id, item.behaviour) for item in warnings] == [
        ("W_LAYOUT_TEXT_ELLIPSIZED", "group-header:g#run1", "ellipsize-with-source")]
    end = _starts(placements)[1] + float(placements[1].bounds.inline_size)
    assert end <= 100 + 38


def test_a_run_that_cannot_hold_an_ellipsis_is_suppressed_and_the_one_before_gives_way():
    placements, warnings = _place((("0123456", "ordinal"), (" Bus", None), (" tail", "gloss")), size=60, bounded=True)

    assert placements[-1].overflow == "suppressed"
    suppressed = [item for item in placements if item.overflow == "suppressed"]
    assert suppressed and all(not item.required for item in suppressed)
    assert {item.behaviour for item in warnings} <= {"ellipsize-with-source", "suppress-with-source"}
    kept = [item for item in placements if item.overflow != "suppressed"]
    assert _starts(kept)[-1] + float(kept[-1].bounds.inline_size) <= 100 + 60


def test_a_bounded_block_that_fits_is_untouched():
    placements, warnings = _place((("01", "ordinal"), (" Bus", None)), size=500, bounded=True)

    assert warnings == () and [item.overflow for item in placements] == ["fit", "fit"]


class _Theme:
    def __init__(self, roles):
        self.roles = roles

    def has_role(self, role):
        return role in self.roles

    def optional_color(self, role, name):
        return self.roles[role].get(name)

    def text_treatment(self, role):
        return _Tokens().text_treatment("groupHeader")


def test_role_admission_names_the_view_pointer_and_the_theme_pointer_in_the_detail():
    theme = _Theme({"ink": {"fill": "#fff"}, "noink": {}})
    validate_group_header_roles((("ink", "/body/grouping/header/text"),), theme)

    with pytest.raises(LayoutError) as missing:
        validate_group_header_roles((("nope", "/body/grouping/header/first"),), theme)
    with pytest.raises(LayoutError) as inkless:
        validate_group_header_roles((("noink", "/body/grouping/header/text"),), theme)

    assert (missing.value.diagnostic_id, missing.value.path) == ("E_THEME_ROLE_REQUIRED", "/body/grouping/header/first")
    assert "/body/roles/nope" in str(missing.value.detail)
    assert (inkless.value.diagnostic_id, inkless.value.path) == ("E_THEME_ROLE_REQUIRED", "/body/grouping/header/text")
    assert "/body/roles/noink/fill" in str(inkless.value.detail)


def test_edge_spaces_of_a_template_are_the_measured_gaps_between_its_runs():
    # "A {x|r} B" (#1238): the runs A, x, B with one space (5) before and after the marked span.
    placements, _ = _place((("A ", None), ("x", "ordinal"), (" B", None)))

    assert [item.content for item in placements] == ["A", "x", "B"]
    assert _starts(placements) == [100, 100 + 5 + 5, 110 + 10 + 5]


def test_the_gap_holds_the_letter_spacing_a_painted_line_would_put_around_the_space():
    # gloss: letter-spacing 0.5 x 5 = 2.5, glyph 2.5 wide; "g g" paints g, 2.5, space 2.5, 2.5, g.
    placements, _ = _place((("g ", "gloss"), ("g", "gloss")))
    flush, _ = _place((("g", "gloss"), ("g", "gloss")))

    assert _starts(placements)[1] - _starts(placements)[0] == 2.5 + 2.5 + 2.5 + 2.5
    assert _starts(flush)[1] - _starts(flush)[0] == 2.5  # no whitespace, no gap: unchanged


def test_a_leading_space_of_the_first_run_is_a_gap_before_it():
    placements, _ = _place(((" A", None), ("x", "ordinal")))

    assert _starts(placements)[0] == 100 + 5
