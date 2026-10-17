"""Explicit forecasts keep canonical facts and reuse normal dependency solving."""
from copy import deepcopy
from datetime import date

import pytest

from chrona.core.observations import latest_observations
from chrona.core.ports import ScheduleOutcome
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.forecast_schedule import forecast_schedule


def span(start="2026-10-05", end="2026-10-07", **extra):
    return {"type": "task", "schedule": {"mode": "fixed-span", "start": start, "end": end}, **extra}


def task(amount="2wd", **schedule):
    return {"type": "task", "schedule": {"mode": "scheduled", "amount": amount, **schedule}}


def project(objects, relations=(), calendar=True):
    value = {"version": "timeline/v0.7", "project": {"id": "forecast-test"},
             "objects": objects, "relations": list(relations)}
    if calendar:
        value["project"]["calendar"] = "weekdays"
        value["calendars"] = {"weekdays": {"working_days": ["mon", "tue", "wed", "thu", "fri"]}}
    return value


def relation(source, target, endpoint="start"):
    return {"id": f"{source}-{target}", "type": "dependency", "from": {"object": source, "endpoint": "end"},
            "to": {"object": target, "endpoint": endpoint}, "lag": "0d"}


def actual(as_of="2026-10-09", **observations):
    return {"body": {"asOf": as_of, "observations": [
        {"id": f"obs-{key}", "projectObjectId": key, "sequence": 1, "actual": value}
        for key, value in observations.items()]}}


def evaluate(source, observed):
    scheduler = ReferenceScheduler()
    ordinary = scheduler.schedule(source)
    assert ordinary.ok, ordinary.diagnostics
    before = deepcopy((source, observed, ordinary.placements))
    result = forecast_schedule(source, ordinary, observed, scheduler)
    assert (source, observed, ordinary.placements) == before
    return result


def dates(result, key):
    return {name: value.isoformat() for name, value in result.items[key].placement.items()}


def test_working_day_states_and_successor_chain():
    source = project({
        "finished": span(),
        "late": task(anchor={"start": "2026-10-07"}),
        "overrun": task(anchor={"start": "2026-10-05"}),
        "next": task("1wd"),
    }, [relation("overrun", "next")])
    result = evaluate(source, actual("2026-10-12", finished={"start": "2026-10-06", "finish": "2026-10-08"},
                                     late={"start": "2026-10-09"}, overrun={"start": "2026-10-06"}))
    assert result.ok, result.diagnostics
    assert dates(result, "finished") == {"start": "2026-10-06", "end": "2026-10-08"}
    assert dates(result, "late") == {"start": "2026-10-09", "end": "2026-10-13"}
    assert dates(result, "overrun") == {"start": "2026-10-06", "end": "2026-10-12"}
    assert dates(result, "next") == {"start": "2026-10-12", "end": "2026-10-13"}
    assert result.items["finished"].completed
    assert not any(result.items[key].completed for key in ("late", "overrun", "next"))
    assert result.moved_count == 4
    assert result.findings[-1].details == {"count": 4}
    with pytest.raises(TypeError):
        result.items["next"].placement["start"] = date(2000, 1, 1)


@pytest.mark.parametrize("amount,end", [("2d", "2026-10-10"), ("1w", "2026-10-15"), ("2wd", "2026-10-12")])
def test_declared_duration_unit_is_preserved(amount, end):
    source = project({"a": task(amount, anchor={"start": "2026-10-05"})})
    result = evaluate(source, actual("2026-10-08", a={"start": "2026-10-08"}))
    assert result.ok
    assert dates(result, "a")["end"] == end


@pytest.mark.parametrize("calendar,end", [(True, "2026-10-14"), (False, "2026-10-16")])
def test_fixed_span_effort_is_inferred_from_effective_calendar(calendar, end):
    source = project({"a": span("2026-10-09", "2026-10-13")}, calendar=calendar)
    result = evaluate(source, actual("2026-10-12"))
    assert result.ok
    assert dates(result, "a") == {"start": "2026-10-12", "end": end}


def test_zero_work_fixed_span_is_not_given_an_invented_minimum():
    result = evaluate(project({"a": span("2026-10-10", "2026-10-11")}), actual())
    assert not result.ok and not result.items
    assert [item.id for item in result.diagnostics] == ["E_FORECAST_DURATION_UNAVAILABLE"]


def test_nonworking_actual_start_is_literal_and_end_is_at_least_asof():
    source = project({"a": task(anchor={"start": "2026-10-05"}), "b": task("1wd")}, [relation("a", "b")])
    result = evaluate(source, actual("2026-10-15", a={"start": "2026-10-10", "progress": 1}))
    assert result.ok, result.diagnostics
    assert dates(result, "a") == {"start": "2026-10-10", "end": "2026-10-15"}
    assert dates(result, "b")["start"] == "2026-10-15"
    assert not result.items["a"].completed


def test_finish_only_keeps_planned_start_and_propagates_observed_finish():
    source = project({"a": span(), "b": task("1d")}, [relation("a", "b")])
    result = evaluate(source, actual(a={"finish": "2026-10-09"}))
    assert result.ok, result.diagnostics
    assert dates(result, "a") == {"start": "2026-10-05", "end": "2026-10-09"}
    assert dates(result, "b") == {"start": "2026-10-09", "end": "2026-10-10"}
    assert result.items["a"].completed
    assert "I_FORECAST_START_UNOBSERVED" in {item.id for item in result.findings}


def test_invalid_finish_only_is_not_clamped():
    result = evaluate(project({"a": span()}), actual(a={"finish": "2026-10-04"}))
    assert not result.ok and not result.items
    assert "E_INVALID_SPAN" in {item.id for item in result.diagnostics}


@pytest.mark.parametrize("group_actual,conflict", [({}, False), ({"finish": "2026-10-10"}, False),
                                                   ({"finish": "2026-10-08"}, True)])
def test_rollup_uses_children_and_only_checks_supplied_group_endpoints(group_actual, conflict):
    source = project({"g": {"type": "group", "schedule": {"mode": "rollup"}},
                      "a": span(parent="g"), "b": span("2026-10-09", "2026-10-10", parent="g")}, calendar=False)
    result = evaluate(source, actual("2026-10-09", a={"start": "2026-10-07", "finish": "2026-10-08"}, g=group_actual))
    assert result.ok, result.diagnostics
    assert dates(result, "g") == {"start": "2026-10-07", "end": "2026-10-10"}
    assert not result.items["g"].completed
    findings = [item for item in result.findings if item.id == "I_FORECAST_ROLLUP_OBSERVATION_CONFLICT"]
    assert len(findings) == int(conflict)
    if conflict:
        assert findings[0].details == {"object": "g", "observation": "obs-g"}


def test_fixed_gate_miss_is_reported_without_moving_or_suppressing_it():
    source = project({"a": span(), "gate": {"type": "milestone", "schedule": {"mode": "fixed-point", "at": "2026-10-08"}}},
                     [relation("a", "gate", "at")], calendar=False)
    result = evaluate(source, actual(a={"start": "2026-10-08"}))
    assert result.ok, result.diagnostics
    assert dates(result, "gate") == {"at": "2026-10-08"}
    assert not result.items["gate"].completed
    finding = next(item for item in result.findings if item.id == "E_FIXED_TARGET_VIOLATION")
    assert finding.details["object"] == "gate" and finding.details["relation"] == "a-gate"
    assert result.analysis is None


def test_completed_observed_endpoint_miss_is_reported_without_moving_facts():
    source = project({"p": span("2026-10-01", "2026-10-02"), "a": span()}, [relation("p", "a")], calendar=False)
    result = evaluate(source, actual(p={"start": "2026-10-07", "finish": "2026-10-09"},
                                     a={"start": "2026-10-07", "finish": "2026-10-08"}))
    assert result.ok
    assert dates(result, "a") == {"start": "2026-10-07", "end": "2026-10-08"}
    assert any(item.id == "E_FIXED_TARGET_VIOLATION" and item.details["object"] == "a" for item in result.findings)
    assert result.analysis is None


def test_latest_selector_preserves_first_tie_and_unmatched_input_order():
    observations = [{"id": "old", "projectObjectId": "a", "sequence": 1, "actual": {}},
                    {"id": "new", "projectObjectId": "a", "sequence": 3, "actual": {}},
                    {"id": "tie", "projectObjectId": "a", "sequence": 3, "actual": {}},
                    {"id": "z", "projectObjectId": "unknown", "sequence": 1},
                    {"id": "x", "projectObjectId": "unknown", "sequence": 1}]
    latest, unmatched = latest_observations(observations, {"a": {}})
    assert latest["a"] is observations[1]
    assert unmatched == ["z", "x"]
    assert latest_observations([], {}) == ({}, [])


def test_forecast_uses_same_latest_observation_and_does_not_filter_by_cutoff():
    observed = actual(a={"start": "2026-10-06"})
    observed["body"]["observations"].append({"id": "later", "projectObjectId": "a", "sequence": 2,
                                             "actual": {"start": "2026-10-12"}})
    result = evaluate(project({"a": span()}), observed)
    assert result.ok
    assert dates(result, "a")["start"] == "2026-10-12"


@pytest.mark.parametrize("observed,code", [(None, "E_FORECAST_ACTUAL_REQUIRED"), ({"body": {}}, "E_FORECAST_ASOF_REQUIRED")])
def test_forecast_requires_explicit_actual_and_cutoff(observed, code):
    result = evaluate(project({"a": span()}), observed)
    assert not result.ok and result.diagnostics[0].id == code


def test_original_plan_must_succeed_before_forecast():
    from chrona.core.diagnostics import Diagnostic
    error = Diagnostic("E_UNSUPPORTED_CYCLE", "Unsupported", "/relations/0")
    result = forecast_schedule({}, ScheduleOutcome({}, (error,)), None, ReferenceScheduler())
    assert result.diagnostics == (error,) and not result.ok


def test_scheduled_point_moves_by_dependencies_and_observed_point_becomes_complete():
    source = project({"a": span(), "p": {"type": "milestone", "schedule": {"mode": "scheduled-point"}}},
                     [relation("a", "p", "at")], calendar=False)
    moved = evaluate(source, actual(a={"finish": "2026-10-10"}))
    assert moved.ok and dates(moved, "p") == {"at": "2026-10-10"}
    assert not moved.items["p"].completed
    observed = evaluate(source, actual(a={"finish": "2026-10-08"}, p={"at": "2026-10-09"}))
    assert observed.ok and dates(observed, "p") == {"at": "2026-10-09"}
    assert observed.items["p"].completed


def test_fixed_point_observation_changes_completion_not_target():
    source = project({"p": {"type": "milestone", "schedule": {"mode": "fixed-point", "at": "2026-10-08"}}})
    result = evaluate(source, actual(p={"at": "2026-10-09"}))
    assert result.ok and result.items["p"].completed
    assert dates(result, "p") == {"at": "2026-10-08"} and result.moved_count == 0


def test_rollup_completion_comes_only_from_all_children():
    source = project({"g": {"type": "group", "schedule": {"mode": "rollup"}},
                      "a": span(parent="g"), "b": span(parent="g")})
    result = evaluate(source, actual(a={"finish": "2026-10-09"}, b={"finish": "2026-10-08"}, g={"progress": 0}))
    assert result.ok and result.items["g"].completed
    assert not any(item.id == "I_FORECAST_ROLLUP_OBSERVATION_CONFLICT" for item in result.findings)


@pytest.mark.parametrize("observed", [{"start": "2026-10-09"}, {"start": "2026-10-09", "finish": "2026-10-12"}, {}])
def test_original_scheduled_bounds_are_not_lost_in_effective_input(observed):
    source = project({"a": task("1d", anchor={"start": "2026-10-05"},
                                constraints={"start": {"max": "2026-10-07"}})})
    result = evaluate(source, actual("2026-10-09", a=observed))
    assert not result.ok
    assert any(item.id == "E_CONTRADICTORY_BOUNDS" for item in result.diagnostics)


def test_unstarted_keeps_future_original_floor_and_progress_is_not_a_start():
    source = project({"a": task("1d", anchor={"start": "2026-10-20"})})
    result = evaluate(source, actual(a={"progress": 1}))
    assert result.ok and not result.items["a"].completed
    assert dates(result, "a") == {"start": "2026-10-20", "end": "2026-10-21"}


def test_actual_kind_mismatch_is_forecast_only_and_points_at_observation_index():
    source = project({"a": span()})
    result = evaluate(source, actual(a={"at": "2026-10-09"}))
    assert not result.ok
    assert result.diagnostics[0].id == "E_FORECAST_ACTUAL_KIND"
    assert result.diagnostics[0].path == "/body/observations/0/actual"


def test_injected_scheduler_gets_one_effective_copy_and_no_partial_result_escapes():
    source = project({"a": span()})
    ordinary = ReferenceScheduler().schedule(source)

    class IncompleteScheduler:
        calls = 0

        def schedule(self, effective):
            self.calls += 1
            assert effective is not source
            assert effective["objects"]["a"]["schedule"]["mode"] == "scheduled"
            return ScheduleOutcome({}, ())

    scheduler = IncompleteScheduler()
    result = forecast_schedule(source, ordinary, actual(), scheduler)
    assert scheduler.calls == 1
    assert not result.ok and not result.items
    assert result.diagnostics[0].id == "E_DERIVATION"


def test_started_before_predecessor_finish_is_reported_and_successors_still_move():
    source = project({"p": span("2026-10-01", "2026-10-02"), "a": span(), "b": task("1d")},
                     [relation("p", "a"), relation("a", "b")], calendar=False)
    result = evaluate(source, actual(p={"start": "2026-10-07", "finish": "2026-10-09"},
                                     a={"start": "2026-10-08"}))
    assert result.ok, result.diagnostics
    assert dates(result, "a") == {"start": "2026-10-08", "end": "2026-10-10"}
    assert dates(result, "b") == {"start": "2026-10-10", "end": "2026-10-11"}
    assert any(item.id == "E_FIXED_TARGET_VIOLATION" and item.details["endpoint"] == "start" for item in result.findings)


@pytest.mark.parametrize("observation,endpoint", [({"finish": "2026-10-12"}, "start"),
                                                 ({"start": "2026-10-07"}, "end")])
def test_unobserved_retained_or_computed_endpoint_conflict_remains_fatal(observation, endpoint):
    edge = relation("p", "a", endpoint)
    source = project({"p": span("2026-10-01", "2026-10-02"), "a": span()}, [edge], calendar=False)
    result = evaluate(source, actual(p={"start": "2026-10-07", "finish": "2026-10-15"}, a=observation))
    assert not result.ok and not result.items
    assert any(item.id == "E_FIXED_TARGET_VIOLATION" and item.details["endpoint"] == endpoint for item in result.diagnostics)
