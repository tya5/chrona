"""Legend source measurement and completed placement share finite geometry (#1826)."""
from decimal import Decimal
from dataclasses import replace
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.sources import measure_sources
from chrona.presentation.layout.surface_legend import (
    LegendArrangement, SurfaceLegendContext, complete_legend_layout, legend_source_input, place_legend,
    wrapped_legend_line_block,
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


def test_inline_entry_wraps_its_label_instead_of_collapsing_it_to_empty():
    entry = SurfaceLegendEntry("unknown", "A long readable legend label")
    source = legend_source_input((entry,), tokens=ThemeTokenView(theme()), mark_block_size=8,
                                 font_metrics=_Metrics(),
                                 arrangement=LegendArrangement(direction="inline", item_min_inline_size=Decimal(20)))
    measured = measure_sources({"legend": source}, theme(), font_metrics=_Metrics())
    width = Decimal(64)
    measured = replace(measured, legend_layout=complete_legend_layout(
        (entry,), available_inline=width, item_min_inline=Decimal(20), gap=source.run_gap,
        tokens=ThemeTokenView(theme()), mark_block_size=8, font_metrics=_Metrics()))
    slot = SlotPlacement("legend", "legend", Rect(Decimal(0), Decimal(0), width, Decimal(100)),
                         direction="inline", item_min_inline_size=Decimal(20),
                         overflow="ellipsize-with-source")
    request = SurfaceLayoutRequest(surface_content=SimpleNamespace(legend_entries=(entry,)),
                                   theme_tokens=ThemeTokenView(theme()), font_metrics=_Metrics(),
                                   measured_sources=measured)

    batch = place_legend(SurfaceLegendContext(request, slot, {"timeline.mark.blockSize": 8}, lambda _: _Metrics()))

    label, = batch.text
    assert label.content
    assert len(label.lines) > 1
    assert label.bounds.inline >= float(slot.bounds.inline + Decimal("11.2"))


def test_indivisible_word_keeps_visible_label_and_reports_its_real_shortage():
    entry = SurfaceLegendEntry("unknown", "unbreakable")
    source = legend_source_input((entry,), tokens=ThemeTokenView(theme()), mark_block_size=8,
                                 font_metrics=_Metrics(),
                                 arrangement=LegendArrangement(direction="inline", item_min_inline_size=Decimal(10)))
    measured = measure_sources({"legend": source}, theme(), font_metrics=_Metrics())
    width = Decimal(40)
    layout = complete_legend_layout((entry,), available_inline=width,
                                           item_min_inline=Decimal(10), gap=source.run_gap,
                                           tokens=ThemeTokenView(theme()), mark_block_size=8,
                                           font_metrics=_Metrics())
    measured = replace(measured, legend_layout=layout)
    slot = SlotPlacement("legend", "legend", Rect(Decimal(0), Decimal(0), width, Decimal(100)),
                         direction="inline", item_min_inline_size=Decimal(10),
                         overflow="ellipsize-with-source")
    request = SurfaceLayoutRequest(surface_content=SimpleNamespace(legend_entries=(entry,)),
                                   theme_tokens=ThemeTokenView(theme()), font_metrics=_Metrics(),
                                   measured_sources=measured)

    batch = place_legend(SurfaceLegendContext(request, slot, {"timeline.mark.blockSize": 8}, lambda _: _Metrics()))

    label, = batch.text
    assert label.content == "unbreakable"
    assert label.overflow == "visible-overflow"
    warning = next(item for item in batch.warnings if item.code == "W_LAYOUT_VISIBLE_OVERFLOW"
                   and item.placement_id == label.placement_id)
    assert warning.code == "W_LAYOUT_VISIBLE_OVERFLOW"
    assert warning.placement_id == label.placement_id
    track_warning = next(item for item in batch.warnings if item.code == "W_LAYOUT_VISIBLE_OVERFLOW"
                         and item.failure_kind == "layout-track")
    assert track_warning.required_inline > track_warning.available_inline
    assert batch.slot.bounds.inline_size >= label.bounds.inline + label.bounds.inline_size


def test_spread_grid_wraps_inside_allocated_columns_without_reordering():
    labels = ("Long readable label", "Second readable label", "Third readable label")
    entries = tuple(SurfaceLegendEntry(f"unknown-{index}", label) for index, label in enumerate(labels))
    arrangement = LegendArrangement(gap=Decimal(10), columns=3, column_distribution="spread",
                                    overflow="ellipsize-with-source")
    source = legend_source_input(entries, tokens=ThemeTokenView(theme()), mark_block_size=8,
                                 font_metrics=_Metrics(), arrangement=arrangement)
    measured = measure_sources({"legend": source}, theme(), font_metrics=_Metrics())
    assert source.min_inline is not None
    assert measured.measurements["legend"].min_inline == source.min_inline
    layout = complete_legend_layout(
        entries, available_inline=Decimal(320), item_min_inline=None, gap=source.run_gap,
        tokens=ThemeTokenView(theme()), mark_block_size=8, font_metrics=_Metrics(),
        direction="stack", columns=3, column_distribution="spread")
    measured = replace(measured, legend_layout=layout)
    slot = SlotPlacement("legend", "legend", Rect(Decimal(0), Decimal(0), Decimal(320), Decimal(100)),
                         columns=3, column_distribution="spread", overflow="ellipsize-with-source")
    request = SurfaceLayoutRequest(surface_content=SimpleNamespace(legend_entries=entries),
                                   theme_tokens=ThemeTokenView(theme()), font_metrics=_Metrics(),
                                   measured_sources=measured)

    batch = place_legend(SurfaceLegendContext(request, slot, {"timeline.mark.blockSize": 8}, lambda _: _Metrics()))

    assert tuple(text.source_content for text in batch.text) == labels
    assert all(text.content and len(text.lines) > 1 for text in batch.text)
    assert len({entry.label_available_inline for entry in layout.entries}) == 1
    assert all(text.bounds.inline + text.bounds.inline_size <= float(slot.bounds.inline + slot.bounds.inline_size)
               for text in batch.text)
    assert [text.source_ref for text in batch.text] == [entry.source_identity for entry in entries]


def test_grid_indivisible_minimum_grows_legend_bounds_and_names_the_shortage():
    entries = (SurfaceLegendEntry("unknown-a", "unbreakable"), SurfaceLegendEntry("unknown-b", "unbreakable"))
    arrangement = LegendArrangement(gap=Decimal(10), columns=2, column_distribution="spread",
                                    overflow="ellipsize-with-source")
    source = legend_source_input(entries, tokens=ThemeTokenView(theme()), mark_block_size=8,
                                 font_metrics=_Metrics(), arrangement=arrangement)
    measured = measure_sources({"legend": source}, theme(), font_metrics=_Metrics())
    width = Decimal(40)
    layout = complete_legend_layout(entries, available_inline=width, item_min_inline=None, gap=source.run_gap,
                                    tokens=ThemeTokenView(theme()), mark_block_size=8,
                                    font_metrics=_Metrics(), direction="stack", columns=2,
                                    column_distribution="spread")
    measured = replace(measured, legend_layout=layout)
    slot = SlotPlacement("legend", "legend", Rect(Decimal(0), Decimal(0), width, Decimal(100)),
                         columns=2, column_distribution="spread", overflow="ellipsize-with-source")
    request = SurfaceLayoutRequest(surface_content=SimpleNamespace(legend_entries=entries),
                                   theme_tokens=ThemeTokenView(theme()), font_metrics=_Metrics(),
                                   measured_sources=measured)

    batch = place_legend(SurfaceLegendContext(request, slot, {"timeline.mark.blockSize": 8}, lambda _: _Metrics()))

    assert [text.content for text in batch.text] == ["unbreakable", "unbreakable"]
    assert batch.slot.bounds.inline_size > width
    assert all(text.bounds.inline + text.bounds.inline_size <= batch.slot.bounds.inline
               + batch.slot.bounds.inline_size for text in batch.text)
    assert any(warning.failure_kind == "layout-track" and warning.required_inline > warning.available_inline
               for warning in batch.warnings)


def test_final_same_count_legend_content_recloses_instead_of_reusing_positional_lines():
    potential = (SurfaceLegendEntry("unknown-a", "Planned"), SurfaceLegendEntry("unknown-b", "Actual"))
    final = (SurfaceLegendEntry("unknown-a", "A longer planned key label"), SurfaceLegendEntry("unknown-b", "Actual now"))
    tokens, metrics = ThemeTokenView(theme()), _Metrics()
    arrangement = LegendArrangement(gap=Decimal(8), columns=2, column_distribution="spread",
                                    overflow="ellipsize-with-source")
    source = legend_source_input(potential, tokens=tokens, mark_block_size=8, font_metrics=metrics,
                                 arrangement=arrangement)
    measured = measure_sources({"legend": source}, theme(), font_metrics=metrics)
    old_layout = complete_legend_layout(potential, available_inline=Decimal(220), item_min_inline=None,
                                        gap=source.run_gap, tokens=tokens, mark_block_size=8,
                                        font_metrics=metrics, direction="stack", columns=2,
                                        column_distribution="spread")
    measured = replace(measured, legend_layout=old_layout)
    slot = SlotPlacement("legend", "legend", Rect(Decimal(0), Decimal(0), Decimal(220), Decimal(100)),
                         columns=2, column_distribution="spread", overflow="ellipsize-with-source")
    request = SurfaceLayoutRequest(surface_content=SimpleNamespace(legend_entries=final), theme_tokens=tokens,
                                   font_metrics=metrics, measured_sources=measured)

    batch = place_legend(SurfaceLegendContext(request, slot, {"timeline.mark.blockSize": 8}, lambda _: metrics))

    assert [text.source_content for text in batch.text] == [entry.label for entry in final]
    assert [" ".join(text.content.splitlines()) for text in batch.text] == [entry.label for entry in final]


def test_final_filtered_grid_recloses_to_the_realized_entry_count():
    potential = tuple(SurfaceLegendEntry(f"potential-{index}", label)
                      for index, label in enumerate(("One", "Two", "Three")))
    final = (SurfaceLegendEntry("final-a", "First current key"), SurfaceLegendEntry("final-b", "Second current key"))
    tokens, metrics = ThemeTokenView(theme()), _Metrics()
    arrangement = LegendArrangement(gap=Decimal(8), columns=3, column_distribution="spread",
                                    overflow="ellipsize-with-source")
    source = legend_source_input(potential, tokens=tokens, mark_block_size=8, font_metrics=metrics,
                                 arrangement=arrangement)
    measured = measure_sources({"legend": source}, theme(), font_metrics=metrics)
    old_layout = complete_legend_layout(potential, available_inline=Decimal(320), item_min_inline=None,
                                        gap=source.run_gap, tokens=tokens, mark_block_size=8,
                                        font_metrics=metrics, direction="stack", columns=3,
                                        column_distribution="spread")
    measured = replace(measured, legend_layout=old_layout)
    slot = SlotPlacement("legend", "legend", Rect(Decimal(0), Decimal(0), Decimal(320), Decimal(100)),
                         columns=3, column_distribution="spread", overflow="ellipsize-with-source")
    request = SurfaceLayoutRequest(surface_content=SimpleNamespace(legend_entries=final), theme_tokens=tokens,
                                   font_metrics=metrics, measured_sources=measured)

    batch = place_legend(SurfaceLegendContext(request, slot, {"timeline.mark.blockSize": 8}, lambda _: metrics))

    assert [text.source_ref for text in batch.text] == [entry.source_identity for entry in final]
    assert [text.source_content for text in batch.text] == [entry.label for entry in final]
    assert [" ".join(text.content.splitlines()) for text in batch.text] == [entry.label for entry in final]
