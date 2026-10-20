"""Literal legend values share one measured/placed treatment (#1811)."""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.sources import measure_sources
from chrona.presentation.layout.surface_legend import (
    LegendArrangement, SurfaceLegendContext, entry_swatch_extent, legend_item_gap, legend_source_input, place_legend,
)
from chrona.presentation.layout.surface_quality import SlotPlacement, SurfaceLayoutRequest
from chrona.presentation.layout.text import TextSegment, measure_text_segments
from chrona.presentation.model.surface_content import SurfaceLegendEntry
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.style import StyleLegendScope
from tests.unit.chrona.presentation.layout.test_sources import theme


class CaseSensitiveMetrics:
    content_identity = "sha256:legend-case-metrics"

    def width(self, text, size, *, letter_spacing=0, **_kwargs):
        return sum(2 if char.isupper() else 1 for char in text) * size / 2 + max(0, len(text) - 1) * letter_spacing

    def baseline(self, top, size, _line_height):
        return top + size


def _setup():
    resource = theme()
    resource["body"]["values"]["voice"] = {"type": "textTransform", "value": "lowercase"}
    resource["body"]["roles"]["legend"]["textTransform"] = "voice"
    return resource, ThemeTokenView(resource), CaseSensitiveMetrics()


def _entry(value="Aiko", *, folded=False):
    return SurfaceLegendEntry("scale:owner:a", value, view_scale_id="owner", view_scale_domain_value=value,
                              encoding_value_is_wording=folded)


def _place(entries, tokens, metrics, *, direction="block", columns=None, width=1000, overflow="visible-overflow"):
    request = SurfaceLayoutRequest(surface_content=SimpleNamespace(legend_entries=entries),
                                   theme_tokens=tokens, font_metrics=metrics)
    slot = SlotPlacement("legend", "legend", Rect(Decimal(0), Decimal(0), Decimal(width), Decimal(500)),
                         direction=direction, columns=columns, overflow=overflow)
    return place_legend(SurfaceLegendContext(request, slot, {"timeline.mark.blockSize": 8}, lambda _role: metrics))


@pytest.mark.parametrize("direction,columns", [("block", None), ("inline", None), ("block", 2)])
def test_data_case_source_size_equals_placed_ink_in_each_arrangement(direction, columns):
    resource, tokens, metrics = _setup()
    entries = (_entry(), SurfaceLegendEntry("authored", "Authored WORDING"))
    source = legend_source_input(entries, tokens=tokens, mark_block_size=8, font_metrics=metrics,
                                 arrangement=LegendArrangement(direction=direction, columns=columns))
    measured = measure_sources({"legend": source}, resource, font_metrics=metrics)
    batch = _place(entries, tokens, metrics, direction=direction, columns=columns)

    assert [run.content for run in measured.run_measurements["legend"]] == ["Aiko", "authored wording"]
    assert [text.content for text in batch.text] == ["Aiko", "authored wording"]
    for run, placed, source_run in zip(measured.run_measurements["legend"], batch.text, source.runs):
        assert float(run.inline_size - source_run.inline_advance) == pytest.approx(float(placed.bounds.inline_size))
        assert float(placed.bounds.inline_size) == pytest.approx(metrics.width(placed.content, placed.font_size))
    if direction == "inline" or columns is not None:
        first, second = batch.text
        size = first.font_size
        gap = legend_item_gap(None, size)
        assert float(second.bounds.inline - first.bounds.inline) == pytest.approx(
            float(first.bounds.inline_size) + entry_swatch_extent(entries[0], tokens, 8, size)[0] + 2 * gap)


def test_folded_other_is_wording_but_a_real_other_domain_value_is_data():
    _resource, tokens, metrics = _setup()
    assert _place((_entry("Other"),), tokens, metrics).text[0].content == "Other"
    assert _place((_entry("Other", folded=True),), tokens, metrics).text[0].content == "other"


def test_ellipsis_preserves_the_case_and_full_source_of_the_remaining_data_prefix():
    _resource, tokens, metrics = _setup()
    batch = _place((_entry("Aiko Research"),), tokens, metrics, width=65, overflow="ellipsize-with-source")
    placed, = batch.text
    assert placed.content.startswith("A") and placed.content.endswith("…")
    assert placed.source_content == "Aiko Research"
    assert placed.overflow == "ellipsized"
    assert float(placed.bounds.inline_size) <= placed.available_inline_size
    assert any(warning.code == "W_LAYOUT_TEXT_ELLIPSIZED" for warning in batch.warnings)


def test_a_slot_too_narrow_for_even_an_ellipsis_does_not_draw_outside_the_slot():
    _resource, tokens, metrics = _setup()
    placed, = _place((_entry(),), tokens, metrics, width=17, overflow="ellipsize-with-source").text
    assert placed.content == ""
    assert float(placed.bounds.inline_size) == 0


def test_style_scope_selector_data_is_not_case_transformed():
    _resource, tokens, metrics = _setup()
    entry = SurfaceLegendEntry("scale:style:owner", "unused", style_value="Aiko", style_scope=StyleLegendScope(
        "style", "rule", "owners", '{"objectId":"BuildAPI"}', "OWNER", True))
    placed, = _place((entry,), tokens, metrics).text
    assert placed.content == 'owner: Aiko when {"objectId":"BuildAPI"}'


def test_segment_width_uses_correctly_rounded_geometry_accumulation():
    class WidelySeparatedWidths(CaseSensitiveMetrics):
        def width(self, text, size, **kwargs):
            return {"a": 1e16, "b": 1.0, "c": 1.0}[text]

    _painted, width, _runs = measure_text_segments(
        tuple(TextSegment(char) for char in "abc"), font_size=14, font_metrics=WidelySeparatedWidths())
    assert width == 1.0000000000000002e16
