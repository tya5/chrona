"""Working-day policy closes display values, never scheduled geometry."""
from copy import deepcopy
from datetime import date

import pytest

from chrona.presentation.contracts.resources import _view_input, freeze
from chrona.presentation.model.projection import build_review_projection, _snapshot_items
from chrona.presentation.review.v05_content import normalize_v05_table_content
from chrona.scheduling.scheduler import schedule


def _project(amount="5wd"):
    return {
        "version": "timeline/v0.7", "project": {"id": "work", "calendar": "office"},
        "calendars": {"office": {"working_days": ["mon", "tue", "wed", "thu", "fri"]}},
        "objects": {"work": {"type": "task", "title": "Work", "schedule": {
            "mode": "scheduled", "amount": amount, "anchor": {"start": "2026-10-05"}}}},
        "relations": [],
    }


def _view(unit="working-days"):
    columns = [{"id": name, "source": {"facet": facet}, "format": "dateRange",
                "endDisplay": "inclusive", "align": "start", "width": "content",
                "headerOrientation": "horizontal", "missing": "blank"}
               for name, facet in (("Plan", "planned"), ("Actual", "actual"))]
    return _view_input(freeze({
        "surface": "table-timeline", "rows": {"mode": "automatic"},
        "window": {"mode": "selected-planned"}, "comparison": {"actual": "optional", "deltaUnit": unit},
        "visibility": {"labels": False, "relations": "none", "annotations": "none"},
        "tableColumns": columns,
    }), "chrona/view/v0.28")


def test_work_period_table_and_canonical_variance_keep_raw_endpoints():
    project = _project()
    placed = schedule(project)
    assert not placed.diagnostics
    actual = {"body": {"asOf": "2026-10-16", "observations": [{
        "id": "done", "sequence": 1, "projectObjectId": "work",
        "actual": {"start": "2026-10-05", "finish": "2026-10-10"},
    }]}}
    before = deepcopy((project, placed.placements, actual))
    projection = build_review_projection(project, placed.placements, _view(), actual)
    item = projection.items[0]
    table = normalize_v05_table_content(projection, project, _view(), actual_set=actual)

    assert item.finish_delta == 0
    assert "variance-on-track" in item.roles
    assert [cell.content for cell in table.cells] == ["05 Oct – 09 Oct", "05 Oct – 09 Oct"]
    assert item.planned["end"] == date(2026, 10, 12)
    assert item.actual["finish"] == date(2026, 10, 10)
    assert (project, placed.placements, actual) == before
    legacy = build_review_projection(project, placed.placements, _view("calendar-days"), actual)
    assert legacy.items[0].finish_delta == -2
    assert "variance-ahead" in legacy.items[0].roles


def test_actual_weekend_work_retains_civil_inclusive_finish():
    project = _project()
    actual = {"body": {"observations": [{"id": "done", "sequence": 1,
        "projectObjectId": "work", "actual": {"start": "2026-10-10", "finish": "2026-10-11"}}]}}
    projection = build_review_projection(project, schedule(project).placements, _view(), actual)
    table = normalize_v05_table_content(projection, project, _view(), actual_set=actual)
    assert table.cells[1].content == "10 Oct"


def test_point_comparison_uses_the_same_declared_working_day_policy():
    project = _project()
    project["objects"]["work"]["type"] = "gate"
    project["objects"]["work"]["schedule"] = {"mode": "fixed-point", "at": "2026-10-10"}
    actual = {"body": {"observations": [{"id": "done", "sequence": 1,
        "projectObjectId": "work", "actual": {"at": "2026-10-12"}}]}}
    placements = schedule(project).placements
    projected = build_review_projection(project, placements, _view(), actual)
    legacy = build_review_projection(project, placements, _view("calendar-days"), actual)
    assert projected.items[0].at_delta == 0
    assert legacy.items[0].at_delta == 2


@pytest.mark.parametrize("source_kind", ["snapshot", "scenario"])
def test_comparison_source_resolves_its_own_working_calendar(source_kind):
    source = _project()
    source["calendars"]["office"]["working_days"] = ["tue", "wed", "thu", "fri", "sat"]
    placements = {"work": {"start": date(2026, 10, 6), "end": date(2026, 10, 13)}}
    item = _snapshot_items(source, placements, source_kind=source_kind)["work"]
    assert item.date_basis.calendar.working_days == frozenset({"tue", "wed", "thu", "fri", "sat"})
    assert item.date_basis.work_period
