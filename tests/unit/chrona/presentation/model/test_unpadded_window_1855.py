"""Derived projections retain the selected half-open envelope before padding (#1855)."""
from datetime import date

from chrona.presentation.model.projection import build_review_projection
from tests.unit.chrona.presentation.model.test_projection_rows import typed_view


def _view(mode="selected-planned"):
    window = {"mode": mode}
    if mode == "explicit":
        window.update(start="2026-10-01", end="2026-11-01")
    return typed_view({"body": {
        "comparison": {"actual": "optional", "facets": []},
        "window": window,
        "rows": {"mode": "automatic"},
    }})


def test_span_envelope_precedes_selected_planned_padding():
    project = {"objects": {"task": {"title": "Task", "fields": {}}}, "entities": {}}
    placements = {"task": {"start": date(2026, 10, 5), "end": date(2027, 5, 13)}}

    projection = build_review_projection(project, placements, _view(), None)

    assert projection.unpadded_window == (date(2026, 10, 5), date(2027, 5, 13))
    assert projection.window == (date(2026, 9, 13), date(2027, 6, 4))


def test_point_envelope_covers_its_date_day_before_padding():
    project = {"objects": {"gate": {"type": "milestone", "title": "Gate", "fields": {}}},
               "entities": {}}

    projection = build_review_projection(
        project, {"gate": {"at": date(2026, 10, 5)}}, _view(), None)

    assert projection.unpadded_window == (date(2026, 10, 5), date(2026, 10, 6))
    assert projection.window[0] <= date(2026, 10, 5) < projection.window[1]


def test_selected_comparison_envelope_includes_actual_dates_but_explicit_does_not():
    project = {"objects": {"task": {"title": "Task", "fields": {}}}, "entities": {}}
    placements = {"task": {"start": date(2026, 10, 5), "end": date(2026, 10, 15)}}
    actual = {"body": {"asOf": "2026-10-12", "observations": [{
        "id": "obs", "projectObjectId": "task", "sequence": 1,
        "actual": {"start": "2026-09-28", "finish": "2026-10-20"},
    }]}}

    comparison = build_review_projection(project, placements, _view("selected-comparison"), actual)
    explicit = build_review_projection(project, placements, _view("explicit"), actual)

    assert comparison.unpadded_window == (date(2026, 9, 28), date(2026, 10, 20))
    assert explicit.unpadded_window is None
