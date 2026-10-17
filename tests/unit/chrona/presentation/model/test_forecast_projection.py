from copy import deepcopy
from datetime import date
from types import SimpleNamespace

import pytest

from chrona.presentation.contracts.resources import ViewComparison, ViewInput, ViewRows, ViewVisibility, ViewWindow
from chrona.presentation.model.projection import active_placement, build_review_projection, display_finish_delta, finish_delta_text
from chrona.presentation.layout.semantic_mark_facets import select_item_mark_facets
from chrona.presentation.layout.mark_geometry import compose_item_marks
from chrona.presentation.layout.presentation import MarkBandFrame, MarkGeometry
from chrona.presentation.layout.surface_quality import ScalePlacement
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.forecast_schedule import forecast_schedule


def inputs():
    project = {"version": "timeline/v0.7", "project": {"id": "forecast"}, "objects": {
        "a": {"type": "task", "schedule": {"mode": "fixed-span", "start": "2026-01-01", "end": "2026-01-03"}},
        "b": {"type": "task", "schedule": {"mode": "fixed-span", "start": "2026-01-03", "end": "2026-01-05"}}}}
    actual = {"body": {"asOf": "2026-01-10", "observations": [
        {"id": "a-1", "sequence": 1, "projectObjectId": "a", "actual": {"start": "2026-01-02", "finish": "2026-01-04"}},
        {"id": "b-1", "sequence": 1, "projectObjectId": "b", "actual": {"start": "2026-01-09"}}]}}
    view = ViewInput(None, None, None, ViewWindow("selected-planned", None, None, 0),
                     ViewComparison("primary", "optional", None, None, ()), ViewVisibility(False, "none", "none"),
                     (), (), ViewRows("automatic", ()), None, (), None, None, None)
    scheduler = ReferenceScheduler()
    ordinary = scheduler.schedule(project)
    forecast = forecast_schedule(project, ordinary, actual, scheduler)
    assert forecast.ok
    return project, actual, view, ordinary, forecast


def test_forecast_has_separate_geometry_delta_and_completion_facts():
    project, actual, view, ordinary, forecast = inputs()
    before = deepcopy((project, actual, ordinary.placements))
    original = build_review_projection(project, ordinary.placements, view, actual)
    projected = build_review_projection(project, ordinary.placements, view, actual, forecast=forecast)
    a, b = projected.items
    assert a.planned == ordinary.placements["a"]
    assert b.finish_delta == original.items[1].finish_delta == 5
    assert display_finish_delta(b) == 6 and finish_delta_text(b) == "+6d*"
    assert finish_delta_text(a) == "+1d"
    assert active_placement(b) == {"start": date(2026, 1, 9), "end": date(2026, 1, 11)}
    assert projected.window[1] >= date(2026, 1, 11)
    assert (project, actual, ordinary.placements) == before
    selected = select_item_mark_facets(item=b, source_kind="combined", as_of=date(2026, 1, 10))
    primary = selected.facets[0]
    assert (primary.facet, primary.semantic_id) == ("forecast", "forecast")
    assert primary.placement_id("row:b") == "planned:row:b"
    assert (primary.start, primary.finish) == (date(2026, 1, 9), date(2026, 1, 11))


def test_snapshot_is_forecast_basis_and_ghost_even_with_primary_view_comparison():
    project, actual, view, ordinary, forecast = inputs()
    baseline = deepcopy(ordinary.placements)
    baseline["b"] = dict(forecast.items["b"].placement)
    projected = build_review_projection(project, ordinary.placements, view, actual,
                                        snapshot_project=project, snapshot_placements=baseline, forecast=forecast)
    b = projected.items[1]
    assert display_finish_delta(b) == 0 and finish_delta_text(b) == "+0d*"
    assert b.finish_delta == 5
    assert [item.source_kind for item in projected.rows[1].items] == ["combined", "snapshot"]
    assert projected.rows[1].items[1].forecast is None


def test_missing_snapshot_item_is_not_a_zero_or_primary_fallback():
    project, actual, view, ordinary, forecast = inputs()
    with pytest.raises(ValueError, match="E_FORECAST_BASELINE_UNAVAILABLE: b"):
        build_review_projection(project, ordinary.placements, view, actual,
                                snapshot_project=project, snapshot_placements={"a": ordinary.placements["a"]}, forecast=forecast)


def test_no_forecast_keeps_original_facets_and_values():
    project, actual, view, ordinary, _ = inputs()
    projected = build_review_projection(project, ordinary.placements, view, actual)
    b = projected.items[1]
    assert b.forecast is None and active_placement(b) is b.planned
    assert display_finish_delta(b) == b.finish_delta and finish_delta_text(b) == "+5d"
    assert select_item_mark_facets(item=b, source_kind="combined", as_of=date(2026, 1, 10)).facets[0].facet == "planned"


def test_layout_composes_forecast_coordinates_with_existing_planned_geometry():
    project, actual, view, ordinary, forecast = inputs()
    projected = build_review_projection(project, ordinary.placements, view, actual, forecast=forecast)
    item = projected.items[1]
    scale = ScalePlacement("surface", "scale", date(2026, 1, 1), date(2026, 2, 1), 0., 310., 0., 10.)
    roles = {role: MarkGeometry(.5, .25, 0, 0.) for role in ("planned", "snapshot", "actual", "missing-actual")}
    frame = MarkBandFrame.zero_origin(scale, 10., roles)
    result = compose_item_marks(item=item, instance_id="row:b", source_kind="primary", frame=frame,
                                as_of=date(2026, 1, 10), theme_tokens=SimpleNamespace(), slot_id="timeline")
    mark, = result.marks
    assert mark.semantic_id == "forecast" and mark.placement_id == "planned:row:b"
    assert (float(mark.bounds.inline), float(mark.bounds.inline_size)) == (80., 20.)
    assert mark.start_port[0] == 80. and mark.end_port[0] == 100.
