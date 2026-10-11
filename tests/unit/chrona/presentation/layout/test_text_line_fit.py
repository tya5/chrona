"""Bounded measured lines preserve fitting content and source-prefix ellipsis."""

from decimal import Decimal

import pytest

from chrona.presentation.layout.text import fit_text_lines, metric_for_role, place_text, scaled_metric
from chrona.presentation.model.theme_tokens import TextTreatment


class Font:
    content_identity = "sha256:line-fit-test-font"

    def width(self, content, size, letter_spacing=0, numeric_spacing="proportional"):
        advances = sum(0.8 if char.islower() else 1 for char in content)
        return advances * size / 2 + max(0, len(content) - 1) * letter_spacing


class Theme:
    def __init__(self, transform="none", scale=1):
        self.transform, self.scale = transform, scale

    def text_treatment(self, role):
        return TextTreatment("Synthetic", 400, Decimal(2), Decimal("1.2"), Decimal("0.1"),
                             self.transform, "proportional", Decimal(str(self.scale)))


@pytest.mark.parametrize("source", ["", "  AB   CD  ", "AB\t CD", "Aa…", "AB\nCD"])
@pytest.mark.parametrize("wrap", ["allow", "forbid"])
@pytest.mark.parametrize("transform", ["none", "uppercase", "small-caps:0.7"])
@pytest.mark.parametrize("scale", [1, 0.5])
def test_fitting_text_has_identical_completed_placement(source, wrap, transform, scale):
    theme, font = Theme(transform, scale), Font()
    treatment = theme.text_treatment("text")
    fit = fit_text_lines(source, available_inline=100, wrap=wrap, font_size=float(treatment.font_size),
                         font_metrics=metric_for_role(theme, "text", font),
                         letter_spacing=float(treatment.letter_spacing), text_transform=transform)
    assert fit.content == source and fit.lines == (source,) and not fit.ellipsized
    args = dict(placement_id="cell:one", source_ref="one", content=source, inline=2, baseline_block=8,
                typography_role="text", theme_tokens=theme, font_metrics=font,
                available_inline_start=2, available_inline_size=100)
    original = place_text(**args)
    completed = place_text(**args, lines=fit.lines)
    assert completed == original
    assert float(completed.bounds.inline_size) == fit.inline_size == fit.natural_inline_size


@pytest.mark.parametrize("source,expected", [
    ("AA BB CC", ("AA BB", "CC")),
    ("あい、うえお", ("あい、うえ", "お")),
    ("AA ABCDEFGH BB", ("AA", "ABCD…", "BB")),
])
def test_overwide_words_and_cjk_use_existing_boundaries_then_ellipsis(source, expected):
    fit = fit_text_lines(source, available_inline=5, font_size=2, font_metrics=Font(), wrap="allow")
    assert fit.lines == expected
    assert fit.inline_size <= 5
    assert fit.ellipsized == ("ABCDEFGH" in source)
    assert fit.natural_inline_size == Font().width(source, 2)


def test_forbidden_wrap_uses_source_prefix_not_a_dictionary():
    source = "AA BB CC"
    fit = fit_text_lines(source, available_inline=5, font_size=2, font_metrics=Font())
    assert fit.lines == ("AA B…",) and fit.ellipsized
    assert source.startswith(fit.content[:-1])


@pytest.mark.parametrize("available", [-1, 0, 0.5, float("nan"), float("inf")])
def test_infeasible_budget_is_returned_to_the_allocation_owner(available):
    assert fit_text_lines("AA", available_inline=available, font_size=2, font_metrics=Font(), wrap="allow") is None


def test_an_empty_fitting_cell_does_not_require_an_ellipsis():
    fit = fit_text_lines("", available_inline=0, font_size=2, font_metrics=Font())
    assert fit.content == "" and fit.inline_size == 0 and not fit.ellipsized


def test_compression_is_measured_exactly_once():
    fit = fit_text_lines("AA BB CC", available_inline=5, font_size=2,
                         font_metrics=scaled_metric(Font(), 0.5), wrap="allow")
    assert fit.lines == ("AA BB CC",) and fit.inline_size == 4 and not fit.ellipsized


def test_far_longer_than_canvas_wraps_without_any_line_exceeding_the_budget():
    source = "word " * 500
    fit = fit_text_lines(source, available_inline=40, font_size=2, font_metrics=Font(), wrap="allow")
    assert len(fit.lines) > 1 and not fit.ellipsized
    assert all(Font().width(line, 2) <= 40 for line in fit.lines)
    assert fit.natural_inline_size > 40 * 40


def test_numeric_spacing_features_participate_in_the_fit_before_wrapping():
    class NumericFont(Font):
        def ensure_numeric_spacing(self, spacing):
            assert spacing in {"proportional", "tabular"}

        def width(self, content, size, letter_spacing=0, numeric_spacing="proportional"):
            return sum(2 if char.isdigit() and numeric_spacing == "tabular" else 1 for char in content)

    proportional = fit_text_lines("11 11", available_inline=5, font_size=2,
                                  font_metrics=NumericFont(), wrap="allow")
    tabular = fit_text_lines("11 11", available_inline=5, font_size=2,
                             font_metrics=NumericFont(), wrap="allow", numeric_spacing="tabular")
    assert proportional.lines == ("11 11",)
    assert tabular.lines == ("11", "11") and tabular.inline_size == 4


def test_ellipsized_multiline_fit_preserves_the_original_source_in_placement():
    theme, font = Theme(), Font()
    treatment = theme.text_treatment("text")
    source = "AA ABCDEFGHIJKLM BB"
    fit = fit_text_lines(source, available_inline=5, font_size=float(treatment.font_size),
                         font_metrics=metric_for_role(theme, "text", font), wrap="allow",
                         letter_spacing=float(treatment.letter_spacing))
    placed = place_text(placement_id="cell:one", source_ref="one", content=fit.content, lines=fit.lines,
                        source_content=source, inline=0, baseline_block=2, typography_role="text",
                        theme_tokens=theme, font_metrics=font, overflow="ellipsized",
                        available_inline_start=0, available_inline_size=5)
    assert fit.ellipsized and placed.overflow == "ellipsized"
    assert placed.source_content == source and placed.source_ref == "one"
    assert float(placed.bounds.inline_size) == fit.inline_size <= 5
    # Match the existing placement's native float-to-Decimal arithmetic;
    # this component does not change baseline or line-box geometry.
    assert placed.bounds.block_size == Decimal(str(
        float(treatment.font_size) * float(treatment.line_height) * len(fit.lines)))
