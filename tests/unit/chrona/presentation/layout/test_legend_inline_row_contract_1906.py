"""Inline legend rows wrap only when the slot declares a wrapping threshold."""
from decimal import Decimal

from chrona.presentation.layout.surface_legend import (
    LegendArrangement, complete_legend_layout, legend_source_input,
)
from chrona.presentation.model.surface_content import SurfaceLegendEntry
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.layout.test_legend_sizing import _Metrics
from tests.unit.chrona.presentation.layout.test_sources import theme


def _complete(entries, *, width, item_min=None):
    resource = theme()
    tokens = ThemeTokenView(resource)
    metrics = _Metrics()
    arrangement = LegendArrangement(direction="inline", item_min_inline_size=item_min)
    source = legend_source_input(entries, tokens=tokens, mark_block_size=8,
                                 font_metrics=metrics, arrangement=arrangement)
    return complete_legend_layout(
        entries, available_inline=Decimal(width), item_min_inline=item_min,
        gap=source.run_gap, tokens=tokens, mark_block_size=8,
        font_metrics=metrics, direction="inline")


def test_inline_legend_without_item_minimum_does_not_gain_an_undeclared_row_wrap():
    entries = (SurfaceLegendEntry("unknown-a", "Plan"), SurfaceLegendEntry("unknown-b", "Act"))

    no_declared_minimum = _complete(entries, width=70)
    declared_minimum = _complete(entries, width=70, item_min=Decimal(40))

    assert [entry.block_offset for entry in no_declared_minimum.entries] == [Decimal(0), Decimal(0)]
    assert declared_minimum.entries[0].block_offset == Decimal(0)
    assert declared_minimum.entries[1].block_offset > Decimal(0)


