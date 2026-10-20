"""Block legends measure and place the same per-entry row envelope (#1830)."""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.sources import SourceInput, measure_sources
from chrona.presentation.layout.surface_legend import (
    LegendArrangement,
    SurfaceLegendContext,
    legend_source_input,
    place_legend,
)
from chrona.presentation.layout.surface_quality import SlotPlacement, SurfaceLayoutRequest
from chrona.presentation.model.surface_content import SurfaceLegendEntry
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.layout.test_legend_sizing import _Metrics
from tests.unit.chrona.presentation.layout.test_sources import theme


def _resource():
    value = theme()
    value["body"]["values"]["swatch-block"] = {"type": "number", "value": 30}
    value["body"]["roles"]["legend-swatch"] = {"swatchBlockSize": "swatch-block"}
    return value


def _compose(entries, *, origin=Decimal(0), available_block=None):
    resource = _resource()
    tokens = ThemeTokenView(resource)
    metrics = _Metrics()
    source = legend_source_input(
        entries, tokens=tokens, mark_block_size=8, font_metrics=metrics,
        arrangement=LegendArrangement(),
    )
    measured = measure_sources({"legend": source}, resource, font_metrics=metrics)
    required = measured.measurements["legend"].preferred_block
    slot = SlotPlacement(
        "legend", "legend", Rect(Decimal(7), origin, Decimal(500),
                                  required if available_block is None else available_block),
    )
    request = SurfaceLayoutRequest(
        surface_content=SimpleNamespace(legend_entries=entries),
        theme_tokens=tokens, font_metrics=metrics,
    )
    batch = place_legend(SurfaceLegendContext(
        request, slot, {"timeline.mark.blockSize": 8}, lambda _role: metrics,
    ))
    return source, measured.measurements["legend"], batch


def test_block_measurement_reserves_real_swatch_rows_and_only_inter_entry_gaps():
    entries = (SurfaceLegendEntry("swatch-a", "Plan"), SurfaceLegendEntry("swatch-b", "Actual"))
    source, measured, batch = _compose(entries)

    assert source.run_flow == "stack"
    assert source.run_block_minima == (Decimal(30), Decimal(30))
    assert source.run_gap == Decimal("5.6")
    assert measured.preferred_block == Decimal("65.6")
    assert measured.min_block == measured.preferred_block
    # Generic stacks continue to ignore run_gap unless a producer explicitly
    # supplies row minima; this keeps unrelated sources unchanged.
    generic = measure_sources(
        {"legend": SourceInput(runs=source.runs, run_gap=source.run_gap)},
        _resource(), font_metrics=_Metrics(),
    ).measurements["legend"]
    assert generic.preferred_block == Decimal("39.2")
    assert generic.min_block == Decimal("39.2")
    assert batch.allocated_slot.bounds.block_size == Decimal("65.6")
    swatches = sorted(batch.shapes, key=lambda shape: shape.bounds.block)
    assert [shape.bounds.block for shape in swatches] == [Decimal(0), Decimal("35.6")]
    assert batch.slot.bounds.block + batch.slot.bounds.block_size == Decimal("65.6")


def test_mixed_heights_text_only_rows_and_nonzero_origin_share_one_envelope():
    entries = (
        SurfaceLegendEntry("tall", "Tall"),
        SurfaceLegendEntry("dependency", "Small"),
        SurfaceLegendEntry("text-only", "Explanation", swatch_visible=False),
    )
    source, measured, batch = _compose(entries, origin=Decimal("13.25"))

    # 30 + gap + one text-height row + gap + one text-only label row.
    assert source.run_block_minima[0] == Decimal("30.0")
    assert float(source.run_block_minima[1]) == pytest.approx(19.6)
    assert source.run_block_minima[2] == Decimal(0)
    assert measured.preferred_block == Decimal("80.4")
    assert measured.min_block == measured.preferred_block
    assert batch.slot.bounds.block == Decimal("13.25")
    assert batch.slot.bounds.block_size == Decimal("80.4")
    assert batch.slot.bounds.block + batch.slot.bounds.block_size == Decimal("93.65")
    assert len(batch.shapes) + len(batch.relations) == 2
    assert batch.text[-1].baseline[1] == pytest.approx(13.25 + 30 + 5.6 + 19.6 + 5.6 + 14)


def test_short_allocated_slot_reports_completed_extent_without_a_trailing_gap():
    entries = (SurfaceLegendEntry("a", "Plan"), SurfaceLegendEntry("b", "Actual"))
    source, _measured, batch = _compose(entries, available_block=Decimal("40"))

    assert source.run_gap == Decimal("5.6")
    assert batch.allocated_slot.bounds.block_size == Decimal("40")
    assert batch.slot.bounds.block_size == Decimal("65.6")
    assert batch.slot.bounds.block + batch.slot.bounds.block_size == Decimal("65.6")


def test_empty_block_legend_keeps_legacy_empty_source_shape():
    resource = _resource()
    source = legend_source_input(
        (), tokens=ThemeTokenView(resource), mark_block_size=8, font_metrics=_Metrics(),
        arrangement=LegendArrangement(),
    )

    assert source == SourceInput(("legend",), typography_role="legend")


def test_per_run_block_minima_must_match_the_closed_run_sequence():
    with pytest.raises(ValueError, match="must align"):
        measure_sources(
            {"legend": SourceInput(runs=(), run_block_minima=(Decimal(1),))},
            _resource(), font_metrics=_Metrics(),
        )
