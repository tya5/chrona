from decimal import Decimal
from dataclasses import replace

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.sources import MeasuredLegend, MeasuredLegendEntry
from chrona.presentation.layout.source_use import (
    CompletedSourceUse,
    SourceConsumer,
    SourceTextUse,
)
from chrona.presentation.layout.surface_quality import TextPlacement


def _text(*, inline=10, block=20, content="shown", lines=("shown",), placement_id="note:1"):
    return TextPlacement(
        placement_id=placement_id,
        source_ref="annotation-1",
        content=content,
        bounds=Rect(Decimal(inline), Decimal(block), Decimal(42), Decimal(12)),
        typography_role="annotation",
        lines=lines,
        font_family="Test Sans",
        font_weight=500,
        font_size=12,
        line_height=1.25,
        letter_spacing=0.2,
        text_transform="uppercase",
        numeric_spacing="tabular",
        horizontal_scale=0.9,
        font_asset_identity="font:test-sans:500",
    )


def test_source_text_use_retains_shown_text_typography_and_lines_but_not_anchor():
    first = SourceTextUse.from_placement(_text(inline=10, block=20))
    moved = SourceTextUse.from_placement(_text(inline=900, block=700))

    assert first == moved
    assert first.placement_id == "note:1"
    assert first.measurement.content == "shown"
    assert first.measurement.lines == ("shown",)
    assert first.measurement.typography_role == "annotation"
    assert first.measurement.font_family == "Test Sans"
    assert first.measurement.font_size == 12
    assert first.measurement.font_asset_identity == "font:test-sans:500"
    assert first.measurement.inline_size == Decimal(42)
    assert first.measurement.block_size == Decimal(12)


def test_source_text_use_retains_allocated_inline_and_allocation_changes_finite_state():
    first = SourceTextUse.from_placement(_text(), available_inline=Decimal(80))
    second = SourceTextUse.from_placement(_text(), available_inline=Decimal(120))

    assert first.measurement == second.measurement
    assert first.available_inline == Decimal(80)
    assert second.available_inline == Decimal(120)
    consumer_a = SourceConsumer("row:1", "list", Decimal(42), Decimal(12), (first,))
    consumer_b = SourceConsumer("row:1", "list", Decimal(42), Decimal(12), (second,))
    assert consumer_a.finite_state() != consumer_b.finite_state()


def test_source_text_use_reads_allocated_inline_from_placement_when_not_overridden():
    placement = replace(_text(), available_inline_size=96.5)

    use = SourceTextUse.from_placement(placement)

    assert use.available_inline == Decimal("96.5")


def test_annotation_source_measurement_sums_intrinsic_consumers_without_gaps():
    consumers = (
        SourceConsumer("card:a", "card", Decimal(80), Decimal(30),
                       (SourceTextUse.from_placement(_text(content="Card A")),)),
        SourceConsumer("list:b", "list", Decimal(60), Decimal(15),
                       (SourceTextUse.from_placement(_text(content="List B")),)),
    )

    source = CompletedSourceUse(annotations=consumers).annotation_input()

    assert source.content_present
    assert source.completed.measurement.preferred_inline == Decimal(80)
    assert source.completed.measurement.preferred_block == Decimal(45)
    assert tuple(run.content for run in source.completed.runs) == ("Card A", "List B")


def test_empty_selected_annotation_consumers_make_source_absent():
    source = CompletedSourceUse().annotation_input()

    assert not source.content_present
    assert source.text_runs() == ()
    assert source.completed is None


def test_same_finite_content_state_does_not_hide_changing_block_demand():
    short = SourceConsumer("list:1", "list", Decimal(42), Decimal(12),
                           (SourceTextUse.from_placement(_text()),))
    tall = SourceConsumer("list:1", "list", Decimal(42), Decimal(19),
                          (SourceTextUse.from_placement(_text()),))

    assert short.finite_state() == tall.finite_state()
    assert short != tall
