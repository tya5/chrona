"""A legend explanation without a painted swatch measures and places as text only."""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_legend import SurfaceLegendContext, legend_source_input, place_legend
from chrona.presentation.layout.surface_quality import SlotPlacement, SurfaceLayoutRequest
from chrona.presentation.layout.text import place_text
from chrona.presentation.layout.sources import measure_sources
from chrona.presentation.model.projection import is_estimated_finish_delta
from chrona.presentation.model.surface_content import SurfaceLegendEntry
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.layout.surface_legend import LegendArrangement
from tests.unit.chrona.presentation.layout.test_sources import theme as measuring_theme


class _Metrics:
    content_identity = "sha256:test"

    def width(self, value, size):
        return len(value) * size / 2

    def baseline(self, top, size, line_height):
        return top + size


def test_text_only_forecast_explanation_has_no_swatch_or_swatch_gap():
    entry = SurfaceLegendEntry("forecast", "Forecast (* estimated)", swatch_visible=False)
    tokens = ThemeTokenView(measuring_theme())
    metrics = _Metrics()
    source = legend_source_input((entry,), tokens=tokens, mark_block_size=8,
                                 font_metrics=metrics, arrangement=LegendArrangement())
    measured = measure_sources({"legend": source}, measuring_theme(), font_metrics=metrics).measurements["legend"]
    request = SurfaceLayoutRequest(
        surface_content=SimpleNamespace(legend_entries=(entry,)), theme_tokens=tokens,
        font_metrics=metrics)
    slot = SlotPlacement("legend", "legend", Rect(Decimal(10), Decimal(20), Decimal(240), Decimal(40)))

    batch = place_legend(SurfaceLegendContext(
        request, slot, {"timeline.mark.blockSize": 8.0}, lambda _role: metrics))

    assert source.runs[0].inline_advance == 0
    assert float(measured.preferred_inline) == len(entry.label) * 7
    assert batch.marks == ()
    assert batch.shapes == ()
    assert batch.relations == ()
    (placement,) = batch.text
    assert placement.content == entry.label
    assert placement.bounds.inline == Decimal(10)


@pytest.mark.parametrize(
    "arrangement,flow",
    [
        (LegendArrangement(direction="block"), "stack"),
        (LegendArrangement(direction="inline"), "line"),
        (LegendArrangement(columns=2), "grid"),
    ],
)
def test_text_only_explanation_is_measured_without_swatch_in_every_arrangement(arrangement, flow):
    entry = SurfaceLegendEntry("forecast", "Forecast (* estimated)", swatch_visible=False)
    tokens = ThemeTokenView(measuring_theme())
    metrics = _Metrics()
    source = legend_source_input((entry,), tokens=tokens, mark_block_size=8,
                                 font_metrics=metrics, arrangement=arrangement)
    measurement = measure_sources({"legend": source}, measuring_theme(),
                                  font_metrics=metrics).measurements["legend"]

    assert source.run_flow == flow
    assert source.runs[0].inline_advance == 0
    assert float(measurement.preferred_inline) == len(entry.label) * 7


@pytest.mark.parametrize(
    "arrangement",
    [
        LegendArrangement(direction="block"),
        LegendArrangement(direction="inline"),
        LegendArrangement(columns=2),
    ],
)
def test_text_only_explanation_places_at_slot_start_in_every_arrangement(arrangement):
    entry = SurfaceLegendEntry("forecast", "Forecast (* estimated)", swatch_visible=False)
    tokens = ThemeTokenView(measuring_theme())
    metrics = _Metrics()
    request = SurfaceLayoutRequest(
        surface_content=SimpleNamespace(legend_entries=(entry,)), theme_tokens=tokens,
        font_metrics=metrics)
    slot = SlotPlacement("legend", "legend", Rect(Decimal(10), Decimal(20), Decimal(240), Decimal(80)),
                         direction=arrangement.direction, gap=arrangement.gap,
                         item_min_inline_size=arrangement.item_min_inline_size,
                         columns=arrangement.columns)

    batch = place_legend(SurfaceLegendContext(
        request, slot, {"timeline.mark.blockSize": 8.0}, lambda _role: metrics))

    assert batch.marks == ()
    assert batch.shapes == ()
    assert batch.relations == ()
    (placement,) = batch.text
    assert placement.bounds.inline == slot.bounds.inline
    assert placement.content == entry.label


def test_estimated_delta_witness_is_source_fact_not_text_inference():
    incomplete = SimpleNamespace(finish_delta=2, schedule=SimpleNamespace(completed=False))
    complete = SimpleNamespace(finish_delta=0, schedule=SimpleNamespace(completed=True))
    no_delta = SimpleNamespace(finish_delta=None, schedule=SimpleNamespace(completed=False))
    assert is_estimated_finish_delta(SimpleNamespace(forecast=SimpleNamespace(
        finish_delta=incomplete.finish_delta, schedule=incomplete.schedule)))
    assert not is_estimated_finish_delta(SimpleNamespace(forecast=SimpleNamespace(
        finish_delta=complete.finish_delta, schedule=complete.schedule)))
    assert not is_estimated_finish_delta(SimpleNamespace(forecast=SimpleNamespace(
        finish_delta=no_delta.finish_delta, schedule=no_delta.schedule)))
    assert not is_estimated_finish_delta(SimpleNamespace(forecast=None))

    placed = place_text(placement_id="delta", source_ref="task-a", content="+2d*", inline=0,
                        baseline_block=14, typography_role="legend", theme_tokens=ThemeTokenView(measuring_theme()),
                        font_metrics=_Metrics(), estimated_delta=True)
    assert placed.estimated_delta is True
    assert placed.content == "+2d*"
