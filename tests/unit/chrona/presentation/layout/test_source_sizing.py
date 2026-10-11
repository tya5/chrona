from dataclasses import replace
from decimal import Decimal as D
from types import SimpleNamespace

from chrona.presentation.layout.engine import solve_layout
from chrona.presentation.layout.source_sizing import SourceSizingSession
from chrona.presentation.layout.sources import SourceInput, measure_sources
from tests.unit.chrona.presentation.layout.test_bounded_table_measurement import content, Metrics
from tests.unit.chrona.presentation.layout.test_sources import theme
from tests.unit.chrona.presentation.layout.test_table_inline_budget import container, measurement, profile, slot


def test_wrapping_table_without_share_uses_full_independent_grid_cell_budget():
    resolved = profile(container("grid", [slot(share=None, cell={"row": 1, "column": 1})],
                                 columnTracks=[{"fixed": 400}], rowTracks=["content"]))
    measured = measure_sources({"table": SourceInput(item_count=2, column_count=2, table=content("Short"))},
                               theme(), font_metrics=Metrics())
    session = SourceSizingSession(resolved, measured, theme=theme(), font_metrics=Metrics(),
                                   content=SimpleNamespace(group_presentation="none"))
    measurements = {"table": measured.measurements["table"]}
    context = session.context(viewport_inline=1000, viewport_block=5000, measurements=measurements)
    assert context.source_budgets["table"].ceiling == 400
    manifest = solve_layout(resolved, viewport_inline=1000, viewport_block=5000,
                             measurements=measurements, sizing=context)
    ordinary = solve_layout(resolved, viewport_inline=1000, viewport_block=5000, measurements=measurements)
    assert manifest == ordinary
    assert session.close_manifest(manifest).bounded_tables["table"].available_inline == 400


def test_session_reuses_final_allocated_width_not_the_initial_ceiling():
    resolved = profile(container("row", [slot(inlineSize={"fr": 3}),
                                         slot("other", share=None, source="timeline", inlineSize={"fr": 7})]))
    inputs = {"table": SourceInput(item_count=2, column_count=2, table=content())}
    measured = measure_sources(inputs, theme(), font_metrics=Metrics())
    session = SourceSizingSession(resolved, measured, theme=theme(), font_metrics=Metrics(),
                                   content=SimpleNamespace(group_presentation="none"))
    measurements = {"table": measured.measurements["table"], "other": measurement(30)}
    context = session.context(viewport_inline=1000, viewport_block=5000, measurements=measurements)
    assert context.source_budgets["table"].ceiling == 384
    manifest = solve_layout(resolved, viewport_inline=1000, viewport_block=5000,
                             measurements=measurements, sizing=context)
    closed = session.close_manifest(manifest)
    assert closed.bounded_tables["table"].available_inline == 288
    assert len(closed.bounded_tables["table"].cells[0].fit.lines) > 1
    assert closed.inputs is measured.inputs
    assert not measured.bounded_tables
    assert session.close_manifest(manifest).bounded_tables["table"] is closed.bounded_tables["table"]


def test_absent_declarations_preserve_the_original_measured_object():
    resolved = profile(container("column", [slot("copy", share=None, source="title")]))
    measured = measure_sources({"title": SourceInput(("A title",), typography_role="heading")},
                               theme(), font_metrics=Metrics())
    session = SourceSizingSession(resolved, measured, theme=theme(), font_metrics=Metrics(), content=SimpleNamespace())
    assert not session.active
    manifest = solve_layout(resolved, viewport_inline=1000, viewport_block=500,
                             measurements={"copy": measured.measurements["title"]})
    assert session.close_manifest(manifest) is measured


def test_normalized_heading_intent_selects_only_its_real_slot_identity():
    resolved = profile(container("column", [slot("copy", share=None, source="title")]))
    measured = measure_sources({"title": SourceInput(("words " * 100,), typography_role="heading", text_wrap="allow")},
                               theme(), font_metrics=Metrics())
    session = SourceSizingSession(resolved, measured, theme=theme(), font_metrics=Metrics(),
                                   content=SimpleNamespace(group_presentation="none"))
    assert session.heading_slots == frozenset({"copy"})
    measurements = {"copy": measured.measurements["title"]}
    manifest = solve_layout(resolved, viewport_inline=1000, viewport_block=5000, measurements=measurements,
                             sizing=session.context(viewport_inline=1000, viewport_block=5000, measurements=measurements))
    closed = session.close_manifest(manifest)
    assert len(closed.run_measurements["title"][0].lines) > 1
    assert closed.inputs == measured.inputs


def test_nonterminating_track_width_retains_exact_budget_identity():
    resolved = profile(container("row", [slot(inlineSize={"fr": 1}),
                                         slot("other", share=None, source="timeline", inlineSize={"fr": 6})]))
    measured = measure_sources({"table": SourceInput(item_count=2, column_count=2, table=content())},
                               theme(), font_metrics=Metrics())
    session = SourceSizingSession(resolved, measured, theme=theme(), font_metrics=Metrics(),
                                   content=SimpleNamespace(group_presentation="none"))
    measurements = {"table": measured.measurements["table"], "other": measurement(30)}
    manifest = solve_layout(resolved, viewport_inline=1000, viewport_block=5000, measurements=measurements,
                             sizing=session.context(viewport_inline=1000, viewport_block=5000, measurements=measurements))
    width = next(item.bounds.inline_size for item in manifest.decisions if item.node_id == "table")
    assert width == D(960) / 7
    assert session.close_manifest(manifest).bounded_tables["table"].available_inline == width
