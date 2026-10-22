from dataclasses import replace
from datetime import date

from chrona.presentation.contracts.resources import (
    ViewComparison, ViewInput, ViewRow, ViewRowItem, ViewRows, ViewVisibility, ViewWindow,
)
from chrona.presentation.model.projection import build_review_projection
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.forecast_schedule import forecast_schedule


def _view(*, delta_unit="calendar-days", baseline_marks=None):
    return ViewInput(
        None, None, None,
        ViewWindow("selected-planned", None, None, 0),
        ViewComparison("snapshot", "optional", None, delta_unit, (),
                       baseline_marks=baseline_marks),
        ViewVisibility(False, "none", "none"), (), (), ViewRows("automatic", ()),
        None, (), None, None, None,
    )


def _project(*, span_end="2026-01-12", point_at="2026-01-12", project_id="delta",
             calendar=None):
    value = {
        "version": "timeline/v0.7", "project": {"id": project_id},
        "objects": {
            "span": {"type": "task", "schedule": {
                "mode": "fixed-span", "start": "2026-01-05", "end": span_end}},
            "point": {"type": "gate", "schedule": {
                "mode": "fixed-point", "at": point_at}},
        },
    }
    if calendar is not None:
        value["project"]["calendar"] = "work"
        value["calendars"] = {"work": calendar}
    return value


def _placements(project):
    result = ReferenceScheduler().schedule(project)
    assert result.ok, result.diagnostics
    return result.placements


def test_snapshot_finish_delta_uses_matching_span_and_point_endpoints_independent_of_actual():
    current = _project()
    snapshot = _project(span_end="2026-01-09", point_at="2026-01-09")
    actual = {"body": {"asOf": "2026-01-16", "observations": [
        {"id": "span-actual", "sequence": 1, "projectObjectId": "span",
         "actual": {"start": "2026-01-06", "finish": "2026-01-16"}},
        {"id": "point-actual", "sequence": 1, "projectObjectId": "point",
         "actual": {"at": "2026-01-15"}},
    ]}}

    projection = build_review_projection(
        current, _placements(current), _view(), actual,
        snapshot_project=snapshot, snapshot_placements=_placements(snapshot),
    )
    items = {item.object_id: item for item in projection.items}

    assert items["span"].snapshot_finish_delta == 3
    assert items["point"].snapshot_finish_delta == 3
    assert items["span"].finish_delta == 4
    assert items["point"].finish_delta is None
    assert not items["span"].new_vs_baseline


def test_snapshot_finish_delta_uses_current_item_calendar_and_selected_delta_unit():
    calendar = {"working_days": ["mon", "tue", "wed", "thu", "fri"]}
    current = _project(span_end="2026-01-12", point_at="2026-01-12", calendar=calendar)
    # The Snapshot's own calendar differs; the fact uses the selected primary item's date basis.
    snapshot = _project(span_end="2026-01-09", point_at="2026-01-09", calendar={"working_days": ["mon"]})

    projected = build_review_projection(
        current, _placements(current), _view(delta_unit="working-days"), None,
        snapshot_project=snapshot, snapshot_placements=_placements(snapshot),
    )

    assert {item.snapshot_finish_delta for item in projected.items} == {1}


def test_snapshot_finish_delta_is_absent_without_snapshot_counterpart_or_endpoint():
    current = _project()
    placements = _placements(current)
    ordinary = build_review_projection(current, placements, _view(), None)
    assert all(item.snapshot_finish_delta is None for item in ordinary.items)

    unmatched = _project(project_id="delta")
    unmatched["objects"] = {
        "other": {"type": "task", "schedule": {
            "mode": "fixed-span", "start": "2026-01-05", "end": "2026-01-09"}},
    }
    unmatched_projection = build_review_projection(
        current, placements, _view(), None,
        snapshot_project=unmatched, snapshot_placements=_placements(unmatched),
    )
    assert all(item.snapshot_finish_delta is None for item in unmatched_projection.items)

    missing_endpoint = build_review_projection(
        current, placements, _view(), None, snapshot_project=current,
        snapshot_placements={"span": {"start": date(2026, 1, 5)},
                             "point": {"at": date(2026, 1, 9)}},
    )
    assert {item.object_id: item.snapshot_finish_delta for item in missing_endpoint.items} == {
        "span": None, "point": 3,
    }


def test_snapshot_finish_delta_is_primary_only_in_explicit_rows():
    current = _project()
    snapshot = _project(span_end="2026-01-09", point_at="2026-01-09")
    actual = {"body": {"asOf": "2026-01-16", "observations": [
        {"id": "span-actual", "sequence": 1, "projectObjectId": "span",
         "actual": {"start": "2026-01-06", "finish": "2026-01-16"}},
    ]}}
    view = replace(_view(), rows=ViewRows("explicit", (
        ViewRow("span-row", None, 0, None, None, "primary-span", (
            ViewRowItem("primary-span", "primary", "span", "shared"),
            ViewRowItem("actual-span", "actual", "span", "shared"),
        )),
    )))

    projection = build_review_projection(
        current, _placements(current), view, actual,
        snapshot_project=snapshot, snapshot_placements=_placements(snapshot),
    )
    items = {item.item_id: item for item in projection.rows[0].items}

    assert items["primary-span"].source_kind == "primary"
    assert items["primary-span"].snapshot_finish_delta == 3
    assert items["actual-span"].source_kind == "actual"
    assert items["actual-span"].snapshot_finish_delta is None


def test_snapshot_finish_delta_is_unchanged_by_forecast_or_baseline_mark_policy():
    current = _project(span_end="2026-01-10", point_at="2026-01-12")
    snapshot = _project(span_end="2026-01-08", point_at="2026-01-09")
    actual = {"body": {"asOf": "2026-01-12", "observations": [
        {"id": "span-open", "sequence": 1, "projectObjectId": "span",
         "actual": {"start": "2026-01-08"}},
    ]}}
    scheduler = ReferenceScheduler()
    scheduled = scheduler.schedule(current)
    forecast = forecast_schedule(current, scheduled, actual, scheduler)
    assert forecast.ok

    baseline = _placements(snapshot)
    without_forecast = build_review_projection(
        current, scheduled.placements, _view(), actual,
        snapshot_project=snapshot, snapshot_placements=baseline,
    )
    with_forecast = build_review_projection(
        current, scheduled.placements, _view(baseline_marks="ghost-when-changed"), actual,
        snapshot_project=snapshot, snapshot_placements=baseline, forecast=forecast,
    )
    plain = {item.object_id: item for item in without_forecast.items}
    predicted = {item.object_id: item for item in with_forecast.items}

    assert predicted["span"].forecast is not None
    assert predicted["span"].snapshot_finish_delta == plain["span"].snapshot_finish_delta == 2
    assert predicted["point"].snapshot_finish_delta == plain["point"].snapshot_finish_delta == 3
    assert predicted["span"].finish_delta == plain["span"].finish_delta
