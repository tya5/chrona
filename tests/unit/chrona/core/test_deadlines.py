"""`deadline` is a promise that is read, never a bound (#792, #788 slice 3; Spec 04 Section 10, Q-SCHED-2).

`deadline_warnings` judges placements the scheduler already produced. These tests pin the rule (the finish of a
point is `at`, of a span `end`; strictly later warns, equal does not), the `details` contract, and the inertness
of `deadline` in the scheduler: no placement, verdict or analysis changes with it.
"""
from __future__ import annotations

import copy
from datetime import date
from pathlib import Path

import pytest

from chrona.core.deadlines import deadline_warnings
from chrona.core.validation import load_yaml, validate_project
from chrona.scheduling.scheduler import schedule

REPO = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())

# The issue's case: a fixed-span task and a derived gate behind it, both promised before they finish.
PROJECT = {
    "version": "timeline/v0.7", "project": {"id": "dl", "title": "Deadlines", "calendar": "std"},
    "calendars": {"std": {"working_days": ["mon", "tue", "wed", "thu", "fri"]}},
    "objects": {
        "qa": {"type": "task", "title": "QA", "deadline": "2026-10-05",
               "schedule": {"mode": "fixed-span", "start": "2026-10-01", "end": "2026-10-08"}},
        "launch": {"type": "gate", "title": "Launch", "deadline": "2026-10-11",
                   "schedule": {"mode": "scheduled-point"}},
    },
    "relations": [
        {"id": "qa-launch", "type": "dependency", "from": {"object": "qa", "endpoint": "end"},
         "to": {"object": "launch", "endpoint": "at"}, "lag": "2wd"},
    ],
}


def _project(**deadlines):
    project = copy.deepcopy(PROJECT)
    for object_id, value in deadlines.items():
        if value is None:
            project["objects"][object_id].pop("deadline", None)
        else:
            project["objects"][object_id]["deadline"] = value
    return project


def _warnings(project):
    result = schedule(project)
    assert result.ok, result.diagnostics
    return deadline_warnings(project, result.placements)


def test_a_fixed_span_and_a_derived_gate_past_their_deadlines_each_warn_with_details():
    assert schedule(PROJECT).placements["launch"] == {"at": date(2026, 10, 12)}
    first, second = _warnings(PROJECT)
    assert (first.id, first.path) == ("W_DEADLINE", "/objects/qa/deadline")
    assert first.message == "qa finishes 2026-10-08, 3 days after its deadline 2026-10-05"
    assert dict(first.details) == {"object": "qa", "endpoint": "end", "finish": "2026-10-08",
                                   "deadline": "2026-10-05", "daysLate": 3}
    assert (second.id, second.path) == ("W_DEADLINE", "/objects/launch/deadline")
    assert second.message == "launch finishes 2026-10-12, 1 day after its deadline 2026-10-11"
    assert dict(second.details) == {"object": "launch", "endpoint": "at", "finish": "2026-10-12",
                                    "deadline": "2026-10-11", "daysLate": 1}


def test_the_derived_gate_finish_is_its_computed_date():
    project = _project(qa=None, launch="2026-10-09")
    (warning,) = _warnings(project)
    assert warning.details["finish"] == "2026-10-12" and warning.details["endpoint"] == "at"
    assert warning.details["daysLate"] == 3
    assert warning.message == "launch finishes 2026-10-12, 3 days after its deadline 2026-10-09"


def test_a_finish_equal_to_the_deadline_keeps_the_promise_and_one_day_later_breaks_it():
    on_time = _project(qa="2026-10-08", launch="2026-10-12")
    assert _warnings(on_time) == ()
    one_late = _project(qa="2026-10-07", launch="2026-10-12")
    (warning,) = _warnings(one_late)
    assert warning.details["daysLate"] == 1 and warning.message.endswith("1 day after its deadline 2026-10-07")


def test_a_point_is_judged_by_at_and_a_span_by_end_never_by_start():
    only_start_early = _project(qa="2026-10-02", launch=None)
    (warning,) = _warnings(only_start_early)
    assert warning.details["endpoint"] == "end" and warning.details["finish"] == "2026-10-08"


def test_a_rollup_is_judged_by_its_end():
    project = copy.deepcopy(PROJECT)
    project["objects"]["phase"] = {"type": "phase", "title": "Phase", "deadline": "2026-10-07",
                                   "schedule": {"mode": "rollup"}}
    project["objects"]["qa"]["parent"] = "phase"
    project["objects"]["qa"].pop("deadline")
    project["objects"]["launch"].pop("deadline")
    (warning,) = _warnings(project)
    assert warning.path == "/objects/phase/deadline" and warning.details["endpoint"] == "end"
    assert warning.details["finish"] == "2026-10-08"


def test_objects_without_a_deadline_or_a_placement_are_skipped_and_order_is_project_order():
    assert _warnings(_project(qa=None, launch=None)) == ()
    project = _project()
    result = schedule(project)
    assert [item.path for item in deadline_warnings(project, result.placements)] == [
        "/objects/qa/deadline", "/objects/launch/deadline"]
    assert deadline_warnings(project, {}) == ()
    assert [item.path for item in deadline_warnings(project, {"launch": result.placements["launch"]})] == [
        "/objects/launch/deadline"]


def test_a_deadline_changes_no_placement_verdict_or_analysis():
    """Q-SCHED-2: the scheduler never reads `deadline`, with or without a violation."""
    bare = _project(qa=None, launch=None)
    late = _project(qa="2026-09-01", launch="2026-09-01")
    on_time = _project(qa="2027-01-01", launch="2027-01-01")
    results = [schedule(item) for item in (bare, late, on_time)]
    assert all(result.ok for result in results)
    assert results[0].placements == results[1].placements == results[2].placements
    assert results[0].analysis == results[1].analysis == results[2].analysis
    assert [list(result.diagnostics) for result in results] == [[], [], []]


def test_a_deadline_is_a_promise_not_a_bound_so_it_never_rejects_a_plan():
    project = _project(qa="2026-09-01", launch="2026-09-01")
    project["objects"]["launch"]["schedule"] = {"mode": "fixed-point", "at": "2026-10-20"}
    assert schedule(project).ok and validate_project(project) == []


def test_a_deadline_that_is_not_a_calendar_date_is_rejected_where_it_is_written():
    project = _project(qa="2026-02-30")
    (diagnostic,) = validate_project(project)
    assert (diagnostic.id, diagnostic.path) == ("E_SCHEMA", "/objects/qa/deadline")
    assert schedule(project).diagnostics[0].path == "/objects/qa/deadline"
    assert validate_project(_project(qa="2026-02-28")) == []


def _committed_projects():
    roots = [*sorted((REPO / "examples").glob("**/project.yaml")), *sorted((REPO / "skills" / "chrona" / "examples").glob("*.yaml")),
             *sorted((REPO / "tests" / "fixtures").glob("**/project.yaml"))]
    return [path for path in roots if "deadline" in path.read_text(encoding="utf-8")]


@pytest.mark.corpus  # PR-path twin: the synthetic cases above; this sweep is evidence that no committed deadline slips
@pytest.mark.parametrize("path", _committed_projects(), ids=lambda path: str(path.relative_to(REPO)))
def test_no_committed_project_warns(path):
    project = load_yaml(path)
    result = schedule(project)
    assert result.ok, result.diagnostics
    assert deadline_warnings(project, result.placements) == ()
