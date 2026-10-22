from dataclasses import replace
from decimal import Decimal as D
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.engine import solve_layout
from chrona.presentation.layout.group_header_fit import GroupHeaderInlineDemand
from chrona.presentation.layout.model import LayoutError
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


def test_heading_remeasurement_reuses_closed_metrics_without_axis_inputs():
    declared = theme()
    value = SourceInput(("words " * 100,), typography_role="heading", text_wrap="allow")
    measured = measure_sources({"title": value}, declared, font_metrics=Metrics())
    metrics = dict(measured.metric_values)
    metrics["timeline.axis.blockSize"] = D(73)
    metrics["table.header.blockSize"] = D(73)
    measured = replace(measured, metric_values=metrics)
    # Candidate-local text is not a complete axis dependency closure.
    declared["body"]["metrics"].pop("timeline.axis.blockSize")
    declared["body"]["metrics"].pop("table.header.blockSize")
    resolved = profile(container("column", [slot("copy", share=None, source="title")]))
    session = SourceSizingSession(resolved, measured, theme=declared, font_metrics=Metrics(),
                                  content=SimpleNamespace(group_presentation="none"))
    closed = session._at_width("title", D(100))
    assert closed.metric_values == metrics
    assert closed.metric_values is not metrics
    assert len(closed.run_measurements["title"][0].lines) > 1
    assert measured.metric_values == metrics


def test_required_group_header_floor_survives_bounded_table_remeasurement():
    resolved = profile(container("row", [slot(inlineSize={"fr": 3}),
                                         slot("other", share=None, source="timeline", inlineSize={"fr": 7})]))
    measured = measure_sources({"table": SourceInput(item_count=2, column_count=2, table=content())},
                               theme(), font_metrics=Metrics())
    session = SourceSizingSession(resolved, measured, theme=theme(), font_metrics=Metrics(),
                                   content=SimpleNamespace(group_presentation="none"))
    floor = D(210)
    demand = GroupHeaderInlineDemand(group_id="IDENTITY_40", label="UNBREAKABLE", minimum_source_inline=floor,
                                     available_source_inline=D(160))

    widened = session.add_group_header_demand(demand)
    bounded = session._at_width("table", D(300))

    assert widened.inputs["table"].min_inline == floor
    assert widened.measurements["table"].min_inline >= floor
    assert bounded.bounded_tables["table"].measurement.min_inline >= floor
    assert bounded.bounded_tables["table"].available_inline == D(300)


def test_table_source_minimum_is_not_clamped_to_natural_column_preference():
    floor = D(5000)
    measured = measure_sources({"table": SourceInput(item_count=2, column_count=2,
                                                       table=content(), min_inline=floor)},
                               theme(), font_metrics=Metrics())

    assert measured.measurements["table"].min_inline >= floor
    assert measured.measurements["table"].preferred_inline >= floor


def test_group_header_floor_incompatible_with_table_share_is_named():
    resolved = profile(container("row", [slot(share=0.4),
                                         slot("other", share=None, source="timeline")]))
    measured = measure_sources({"table": SourceInput(item_count=2, column_count=2, table=content())},
                               theme(), font_metrics=Metrics())
    session = SourceSizingSession(resolved, measured, theme=theme(), font_metrics=Metrics(),
                                   content=SimpleNamespace(group_presentation="none"))
    demand = GroupHeaderInlineDemand(group_id="IDENTITY_40", label="UNBREAKABLE", minimum_source_inline=D(5000),
                                     available_source_inline=D(384))
    session.add_group_header_demand(demand)
    measurements = {"table": session.measured.measurements["table"], "other": measurement(30)}

    with pytest.raises(LayoutError) as caught:
        solve_layout(resolved, viewport_inline=1000, viewport_block=5000, measurements=measurements,
                     sizing=session.context(viewport_inline=1000, viewport_block=5000, measurements=measurements))

    assert caught.value.diagnostic_id == "E_LAYOUT_TABLE_OVERFLOW"
    assert "IDENTITY_40" in caught.value.path
    assert "5000" in caught.value.detail and "384" in caught.value.detail


def test_repeated_group_header_demand_fails_even_if_reported_minimum_changes():
    resolved = profile(container("column", [slot(share=None)]))
    measured = measure_sources({"table": SourceInput(item_count=2, column_count=2, table=content())},
                               theme(), font_metrics=Metrics())
    session = SourceSizingSession(resolved, measured, theme=theme(), font_metrics=Metrics(),
                                   content=SimpleNamespace(group_presentation="none"))
    session.add_group_header_demand(GroupHeaderInlineDemand(
        group_id="IDENTITY_40", label="UNBREAKABLE", minimum_source_inline=D(210),
        available_source_inline=D(160)))

    with pytest.raises(LayoutError) as caught:
        session.add_group_header_demand(GroupHeaderInlineDemand(
            group_id="IDENTITY_40", label="UNBREAKABLE", minimum_source_inline=D(220),
            available_source_inline=D(170)))

    assert caught.value.diagnostic_id == "E_LAYOUT_TABLE_OVERFLOW"
    assert "IDENTITY_40" in caught.value.path
    assert "170" in caught.value.detail
