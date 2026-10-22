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
from chrona.presentation.layout.surface_quality import TextRunPlacement
from chrona.presentation.model.color_separability import ScaleCollision
from chrona.presentation.model.legend_paint import RealizedGlyphInk, RealizedLegendKey
from chrona.presentation.model.surface_content import SurfaceLegendEntry


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


def test_source_text_use_retains_allocated_inline_as_exact_witness_not_finite_state():
    first = SourceTextUse.from_placement(_text(), available_inline=Decimal(80))
    second = SourceTextUse.from_placement(_text(), available_inline=Decimal(120))

    assert first.measurement == second.measurement
    assert first.available_inline == Decimal(80)
    assert second.available_inline == Decimal(120)
    consumer_a = SourceConsumer("row:1", "list", Decimal(42), Decimal(12), (first,))
    consumer_b = SourceConsumer("row:1", "list", Decimal(42), Decimal(12), (second,))
    assert consumer_a.finite_state() == consumer_b.finite_state()
    assert consumer_a != consumer_b


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


def test_previous_allocation_overflow_is_not_intrinsic_source_demand():
    placement = replace(_text(), overflow="visible-overflow")
    use = SourceTextUse.from_placement(placement)
    observed = CompletedSourceUse(annotations=(SourceConsumer(
        "status:1", "status", Decimal(42), Decimal(12), (use,)),))

    measured = observed.annotation_input().completed.runs[0]

    assert measured == replace(use.measurement, overflow="fit")
    assert observed.annotations[0].text[0].measurement.overflow == "visible-overflow"
    assert measured.content == placement.content
    assert measured.lines == placement.lines


def test_same_finite_content_state_does_not_hide_changing_block_demand():
    short = SourceConsumer("list:1", "list", Decimal(42), Decimal(12),
                           (SourceTextUse.from_placement(_text()),))
    tall = SourceConsumer("list:1", "list", Decimal(42), Decimal(19),
                          (SourceTextUse.from_placement(_text()),))

    assert short.finite_state() == tall.finite_state()
    assert short != tall


def test_same_finite_content_state_does_not_hide_changing_inline_allocation_or_chrome():
    text = SourceTextUse.from_placement(_text())
    base = SourceConsumer("card:1", "card", Decimal(42), Decimal(12), (text,),
                          geometry_witness=("content-insets", Decimal(2), Decimal(3)))
    wider = replace(base, inline_size=Decimal(48))
    different_chrome = replace(base, geometry_witness=("content-insets", Decimal(4), Decimal(3)))

    assert base.finite_state() == wider.finite_state() == different_chrome.finite_state()
    assert base != wider
    assert base != different_chrome


def test_fallback_run_advance_drift_is_not_a_new_finite_state_but_face_and_partition_are():
    def consumer(runs):
        use = SourceTextUse.from_placement(replace(_text(), runs=runs))
        return SourceConsumer("status:1", "status", Decimal(42), Decimal(12), (use,))

    first = consumer(((TextRunPlacement("shown", 12, 30, "Test Sans", 500, "asset:a"),),))
    width_drift = consumer(((TextRunPlacement("shown", 12, 30.25, "Test Sans", 500, "asset:a"),),))
    different_face = consumer(((TextRunPlacement("shown", 12, 30, "Other Sans", 500, "asset:b"),),))
    different_partition = consumer(((TextRunPlacement("show", 12, 20, "Test Sans", 500, "asset:a"),
                                     TextRunPlacement("n", 12, 10, "Test Sans", 500, "asset:a")),))

    assert first != width_drift
    assert first.finite_state() == width_drift.finite_state()
    assert first.finite_state() != different_face.finite_state()
    assert first.finite_state() != different_partition.finite_state()


def test_legend_finite_key_normalizes_only_glyph_footprint_and_collision_delta():
    def completed(*, footprint=(4.0, 6.0), delta=12.5, geometry=("glyph",), collision_first="A"):
        key = RealizedLegendKey("state", "planned", None,
                                glyph=RealizedGlyphInk("planned", geometry, (), footprint))
        collision = ScaleCollision("scale", collision_first, "B", "normal", delta)
        entry = SurfaceLegendEntry("planned", "Plan", realized_key=key,
                                   scale_collisions=(collision,))
        run = TextRunPlacement("Plan", 12, 20, "Test Sans", 500, "asset:a")
        legend_entry = MeasuredLegendEntry(("Plan",), Decimal(0), Decimal(0), Decimal(20), Decimal(15),
                                           Decimal(30), Decimal(15), source_text="Plan",
                                           painted_lines=("Plan",), segment_runs=((run,),))
        return CompletedSourceUse(legend_entries=(entry,),
                                  legend_layout=MeasuredLegend((legend_entry,), Decimal(15), (entry,),
                                                              Decimal(100), Decimal(100)))

    base = completed()
    numeric_drift = completed(footprint=(4.1, 6.2), delta=12.7)
    different_glyph = completed(geometry=("different-glyph",))
    different_collision = completed(collision_first="C")

    assert base != numeric_drift
    assert base.finite_state() == numeric_drift.finite_state()
    assert base.finite_state() != different_glyph.finite_state()
    assert base.finite_state() != different_collision.finite_state()


def test_legend_segment_run_advance_is_exact_but_not_finite_state():
    def completed(width):
        entry = SurfaceLegendEntry("unknown", "Plan")
        run = TextRunPlacement("Plan", 12, width, "Test Sans", 500, "asset:a")
        measured = MeasuredLegendEntry(("Plan",), Decimal(0), Decimal(0), Decimal(20), Decimal(15),
                                      Decimal(30), Decimal(15), source_text="Plan",
                                      painted_lines=("Plan",), segment_runs=((run,),))
        return CompletedSourceUse(legend_entries=(entry,),
                                  legend_layout=MeasuredLegend((measured,), Decimal(15), (entry,),
                                                              Decimal(100), Decimal(100)))

    first, drift = completed(20), completed(20.25)

    assert first != drift
    assert first.finite_state() == drift.finite_state()
