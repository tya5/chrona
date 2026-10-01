"""#497: a content-sized legend is measured as drawn and bounded by its container.

Synthetic only: no `examples/` input. Text is measured with a fixed-advance font
(7 px a character at the 14 px legend size) so every width below is exact.
"""
from decimal import Decimal

import pytest

from chrona.presentation.layout.engine import solve_layout
from chrona.presentation.layout.model import Measurement
from chrona.presentation.layout.profile import resolve_layout_profile
from chrona.presentation.layout.sources import SourceInput, measure_sources
from chrona.presentation.layout.surface_legend import (
    LegendArrangement, legend_arrangement, legend_source_input, swatch_extent,
)
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.layout.test_sources import theme as measuring_theme

ADVANCE = 7.0  # one character at 14 px
SWATCH = 11.2  # the fixed square of an unregistered role: max(2, 0.8 * 14)
GAP = 5.6  # an undeclared gap is half a swatch


class _Metrics:
    content_identity = "sha256:test"

    def width(self, value, size):
        return len(value) * size / 2

    def baseline(self, top, size, line_height):
        return top + size


def _tokens():
    return ThemeTokenView(measuring_theme())


def _measure(entries, arrangement=LegendArrangement()) -> Measurement:
    source = legend_source_input(entries, tokens=_tokens(), mark_block_size=8.0,
                                 font_metrics=_Metrics(), arrangement=arrangement)
    return measure_sources({"legend": source}, measuring_theme(), font_metrics=_Metrics()).measurements["legend"]


def _entry(label: str) -> float:
    return SWATCH + GAP + len(label) * ADVANCE


def _close(value: Decimal, expected: float) -> bool:
    return float(value) == pytest.approx(expected)


# --- the natural size is the widest entry as drawn ---------------------------------------------------------


def test_a_block_legend_is_as_wide_as_its_widest_entry_with_swatch_and_gap():
    short = _measure((("a", "Plan"), ("b", "Act")))
    long = _measure((("a", "Plan"), ("b", "Assembly, integration and test")))
    mixed = _measure((("a", "Plan"), ("b", "Assembly, integration and test"), ("c", "Act")))

    assert _close(short.preferred_inline, _entry("Plan"))
    assert _close(long.preferred_inline, _entry("Assembly, integration and test"))
    assert _close(mixed.preferred_inline, _entry("Assembly, integration and test"))


def test_the_swatch_and_gap_are_part_of_the_entry_not_an_extra_on_the_label():
    # Before #497 the slot was the widest label: swatch plus gap short of the widest entry.
    measured = _measure((("a", "Spacecraft bus"),))

    assert _close(measured.preferred_inline, len("Spacecraft bus") * ADVANCE + SWATCH + GAP)
    assert measured.preferred_inline > Decimal(len("Spacecraft bus") * ADVANCE)


def test_a_declared_gap_widens_every_entry():
    measured = _measure((("a", "Plan"),), LegendArrangement(gap=Decimal(10)))

    assert _close(measured.preferred_inline, SWATCH + 10 + 4 * ADVANCE)


def test_an_inline_legend_is_the_whole_line_of_entries():
    arrangement = LegendArrangement(direction="inline", gap=Decimal(10))
    measured = _measure((("a", "Plan"), ("b", "Actual")), arrangement)

    assert _close(measured.preferred_inline, (SWATCH + 10 + 4 * ADVANCE) + 10 + (SWATCH + 10 + 6 * ADVANCE))


def test_an_empty_legend_measures_like_before():
    source = legend_source_input((), tokens=_tokens(), mark_block_size=8.0, font_metrics=_Metrics(),
                                 arrangement=LegendArrangement())

    assert source == SourceInput(("legend",), typography_role="legend")


def test_every_swatch_bucket_has_a_declared_extent():
    tokens = _tokens()

    legacy = swatch_extent("scale:owner:bus", tokens, 8.0, 14.0)
    line = swatch_extent("dependency", tokens, 8.0, 14.0)

    assert legacy[2] == "legacy"
    assert legacy[0] == pytest.approx(SWATCH) and legacy[1] == pytest.approx(SWATCH)
    assert line[2] == "line" and line[0] == pytest.approx(SWATCH)


# --- what the content can shrink to ------------------------------------------------------------------------


def test_an_ellipsizing_block_legend_can_shrink_to_a_swatch_a_gap_and_one_ellipsis():
    measured = _measure((("a", "Plan"), ("b", "Assembly, integration and test")),
                        LegendArrangement(overflow="ellipsize-with-source"))

    assert _close(measured.min_inline, SWATCH + GAP + ADVANCE)
    assert measured.min_inline < measured.preferred_inline


def test_a_legend_that_may_not_shrink_never_measures_below_its_content():
    measured = _measure((("a", "Plan"), ("b", "Assembly, integration and test")),
                        LegendArrangement(overflow="visible-overflow"))

    assert measured.min_inline == measured.preferred_inline


def test_a_wrapping_inline_legend_needs_only_its_widest_entry():
    arrangement = LegendArrangement(direction="inline", overflow="ellipsize-with-source",
                                    item_min_inline_size=Decimal(80))
    measured = _measure((("a", "Plan"), ("b", "Assembly, integration and test"), ("c", "Act")), arrangement)

    assert _close(measured.min_inline, _entry("Assembly, integration and test"))
    assert measured.preferred_inline > measured.min_inline


# --- the arrangement is read from the legend slot ----------------------------------------------------------


def _profile(legend: dict, *, legend_source: str = "legend"):
    slot = {"id": "legend", "kind": "slot", "source": legend_source, "inlineSize": "content",
            "blockSize": "content", "place": {"inline": "start", "block": "start", "safety": "safe"},
            "priority": "preferred", "overflow": "ellipsize-with-source"} | legend
    raw = {
        "version": "chrona/layout-profile/v0.10", "id": "legend-column", "flowDirection": "horizontal",
        "dependencyNetworkFlowDirection": "horizontal", "requiredThemeTokens": ["spacing.m", "spacing.none"],
        "reviewSurface": {"rowDistribution": "pack", "backgroundExtents": {
            "rowBand": "table", "groupBand": "timeline", "groupHeaderBand": "both", "calendarClosed": "timeline"},
            "annotationRouting": {"maxBends": 4, "maxDetourRatio": 2}},
        "root": {"id": "page", "kind": "column", "inlineSize": "fill", "blockSize": "fill",
                 "gap": {"token": "spacing.m"}, "padding": {"token": "spacing.none"},
                 "alignItems": "start", "justifyContent": "start", "children": [
                     {"id": "summary", "kind": "slot", "source": "summary", "inlineSize": "content",
                      "blockSize": "content", "place": {"inline": "start", "block": "start", "safety": "safe"},
                      "priority": "preferred", "overflow": "ellipsize-with-source"},
                     slot]},
    }
    values = {"spacing.m": {"type": "number", "value": 16}, "spacing.none": {"type": "number", "value": 0}}
    return resolve_layout_profile(raw, available_sources={"summary", "legend"}, theme={"body": {"values": values}})


def test_the_arrangement_is_the_legend_slots_declared_direction_gap_and_overflow():
    resolved = _profile({"direction": "inline", "gap": {"token": "spacing.m"},
                         "itemMinInlineSize": {"token": "spacing.m"}})

    assert legend_arrangement(resolved) == LegendArrangement(
        "inline", Decimal(16), Decimal(16), "ellipsize-with-source")


def test_an_undeclared_legend_slot_is_a_block_legend_with_the_legacy_gap():
    assert legend_arrangement(_profile({})) == LegendArrangement("block", None, None, "ellipsize-with-source")


# --- a content slot is bounded by its container ------------------------------------------------------------


def _legend_width(resolved, container: int, natural: int) -> Decimal:
    measurements = {
        "summary": Measurement(Decimal(10), Decimal(10), Decimal(20), Decimal(10), Decimal(10), Decimal(20), None, None),
        "legend": Measurement(Decimal(natural) / 4, Decimal(natural), Decimal(natural) * 2,
                              Decimal(20), Decimal(20), Decimal(40), None, None),
    }
    manifest = solve_layout(resolved, viewport_inline=container, viewport_block=400, measurements=measurements)
    return next(item.bounds.inline_size for item in manifest.decisions if item.node_id == "legend")


@pytest.mark.parametrize(("container", "natural", "expected"), [
    (400, 150, 150),   # wider container: exactly the natural width
    (150, 150, 150),   # equal
    (100, 150, 100),   # narrower container: bounded by the space it offers
])
def test_a_shrinkable_content_legend_is_its_natural_width_up_to_its_container(container, natural, expected):
    assert _legend_width(_profile({}), container, natural) == Decimal(expected)


def test_a_legend_that_does_not_shrink_keeps_growing_past_its_container():
    resolved = _profile({"overflow": "visible-overflow"})

    assert _legend_width(resolved, 100, 150) == Decimal(150)


def test_a_slot_whose_composer_does_not_shrink_is_not_bounded_even_if_it_declares_ellipsis():
    # `summary` declares ellipsize-with-source in the corpus but its composer never shrinks;
    # bounding it would trade a visible-overflow warning for silent overflow.
    resolved = _profile({})
    measurements = {
        "summary": Measurement(Decimal(10), Decimal(150), Decimal(300), Decimal(10), Decimal(10), Decimal(20), None, None),
        "legend": Measurement(Decimal(10), Decimal(50), Decimal(100), Decimal(20), Decimal(20), Decimal(40), None, None),
    }
    manifest = solve_layout(resolved, viewport_inline=100, viewport_block=400, measurements=measurements)

    summary = next(item for item in manifest.decisions if item.node_id == "summary")
    assert summary.bounds.inline_size == Decimal(150)
    assert any(warning.placement_id == "summary" for warning in manifest.fit_warnings)
