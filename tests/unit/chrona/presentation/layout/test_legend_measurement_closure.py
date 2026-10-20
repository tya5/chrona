"""Legend source measurement and completed placement share finite geometry (#1826)."""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.sources import measure_sources
from chrona.presentation.layout.surface_legend import (
    LegendArrangement, SurfaceLegendContext, legend_source_input, place_legend, wrapped_legend_line_block,
)
from chrona.presentation.layout.surface_quality import SlotPlacement, SurfaceLayoutRequest
from chrona.presentation.model.surface_content import SurfaceLegendEntry
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.layout.test_legend_sizing import _Metrics
from tests.unit.chrona.presentation.layout.test_sources import theme


def _legend(entries, *, direction, columns=None, origin="0", width_delta=0, item_min=None):
    resource, metrics = theme(), _Metrics()
    tokens = ThemeTokenView(resource)
    arrangement = LegendArrangement(direction=direction, columns=columns, item_min_inline_size=item_min,
                                    overflow="ellipsize-with-source")
    source = legend_source_input(entries, tokens=tokens, mark_block_size=8, font_metrics=metrics,
                                 arrangement=arrangement)
    measured = measure_sources({"legend": source}, resource, font_metrics=metrics)
    width = measured.measurements["legend"].preferred_inline + Decimal(width_delta)
    slot = SlotPlacement("legend", "legend", Rect(Decimal(origin), Decimal("7.3"), width, Decimal(500)),
                         direction=direction, columns=columns, item_min_inline_size=item_min,
                         overflow="ellipsize-with-source")
    request = SurfaceLayoutRequest(surface_content=SimpleNamespace(legend_entries=entries), theme_tokens=tokens,
                                   font_metrics=metrics)
    batch = place_legend(SurfaceLegendContext(request, slot, {"timeline.mark.blockSize": 8}, lambda _: metrics))
    return source, measured, batch


@pytest.mark.parametrize("direction,columns", [("block", None), ("inline", None), ("block", 2)])
@pytest.mark.parametrize("origin", ["0", "113.7", "1000000.1"])
def test_natural_content_width_never_ellipsizes_an_exact_fit(direction, columns, origin):
    entries = tuple(SurfaceLegendEntry(f"unknown-{index}", label) for index, label in enumerate(("Plan", "Actual")))
    _source, _measured, batch = _legend(entries, direction=direction, columns=columns, origin=origin)
    assert [item.content for item in batch.text] == ["Plan", "Actual"]
    assert all(item.overflow == "fit" for item in batch.text)
    assert not batch.warnings


@pytest.mark.parametrize("direction,columns", [("block", None), ("inline", None), ("block", 1)])
def test_real_shortage_still_ellipsizes_and_reports_source(direction, columns):
    entry = SurfaceLegendEntry("unknown", "Plan")
    _source, _measured, batch = _legend((entry,), direction=direction, columns=columns, width_delta=-1)
    text, = batch.text
    assert text.content.endswith("…")
    assert text.source_content == "Plan"
    warning, = batch.warnings
    assert warning.code == "W_LAYOUT_TEXT_ELLIPSIZED"
    assert warning.required_inline > warning.available_inline


def test_wrapping_and_completed_positions_use_the_same_decimal_row_offsets():
    entries = tuple(SurfaceLegendEntry(f"unknown-{index}", label) for index, label in enumerate(("Plan", "Actual", "Gate")))
    source, measured, batch = _legend(entries, direction="inline", item_min=Decimal(50), width_delta=-40)
    run_sizes = tuple(run.inline_size for run in measured.run_measurements["legend"])
    needed = wrapped_legend_line_block(run_sizes, gap=source.run_gap, row_block=source.row_block,
                                       item_min_inline=Decimal(50), available_inline=batch.allocated_slot.bounds.inline_size)
    assert needed == source.row_block * 2 + source.run_gap
    assert batch.text[0].baseline[1] == batch.text[1].baseline[1]
    assert batch.text[2].baseline[1] - batch.text[0].baseline[1] == pytest.approx(float(source.row_block + source.run_gap))
    assert not batch.warnings
