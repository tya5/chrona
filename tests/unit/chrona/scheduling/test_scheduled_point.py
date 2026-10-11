"""Golden scheduling cases of the derived point, `schedule.mode: scheduled-point` (#788 slice 1, design 11.2).

Calendar `std` is Monday to Friday with 2027-05-03 off; `six` is Monday to Saturday.
"""
import copy
from datetime import date

import pytest

from chrona.core.validation import validate_project
from chrona.scheduling.scheduler import schedule

POINT = {"mode": "scheduled-point"}


def rel(rel_id, source, source_endpoint, target, target_endpoint, lag=None):
    relation = {"id": rel_id, "type": "dependency", "from": {"object": source, "endpoint": source_endpoint},
                "to": {"object": target, "endpoint": target_endpoint}}
    if lag is not None:
        relation["lag"] = lag
    return relation


def proj(objects, relations):
    return {
        "version": "timeline/v0.7", "project": {"id": "p", "calendar": "std"},
        "calendars": {"std": {"working_days": ["mon", "tue", "wed", "thu", "fri"],
                              "exceptions": [{"date": "2027-05-03", "working": False}]},
                      "six": {"working_days": ["mon", "tue", "wed", "thu", "fri", "sat"]}},
        "objects": objects, "relations": relations,
    }


def span(start, end):
    return {"type": "task", "schedule": {"mode": "fixed-span", "start": start, "end": end}}


def gate(**schedule_fields):
    return {"type": "gate", "schedule": {**POINT, **schedule_fields}}


def floor(value):
    return {"constraints": {"at": {"min": value}}}


def twin(project, result):
    """Replace every derived point by a fixed point at its derived date."""
    out = copy.deepcopy(project)
    for object_id, item in out["objects"].items():
        if item["schedule"]["mode"] == "scheduled-point":
            item["schedule"] = {"mode": "fixed-point", "at": result.placements[object_id]["at"].isoformat()}
    return out


def codes(result):
    return sorted(item.id for item in result.diagnostics)


def g1_project():
    objects = {"build": span("2027-04-26", "2027-05-07"),
               "qa": {"type": "task", "schedule": {"mode": "scheduled", "amount": "5wd"}},
               "launch": gate()}
    return proj(objects, [rel("b-q", "build", "end", "qa", "start", "0d"), rel("q-l", "qa", "end", "launch", "at", "2wd")])


def test_g1_gate_behind_a_duration_task_and_its_fixed_twin():
    project = g1_project()
    result = schedule(project)
    assert result.ok
    assert result.placements["qa"] == {"start": date(2027, 5, 7), "end": date(2027, 5, 14)}
    assert result.placements["launch"] == {"at": date(2027, 5, 18)}
    twinned = twin(project, result)
    accepted = schedule(twinned)
    assert accepted.ok and accepted.placements == result.placements
    twinned["objects"]["launch"]["schedule"]["at"] = "2027-05-17"
    early = schedule(twinned)
    assert codes(early) == ["E_FIXED_TARGET_VIOLATION"]
    assert early.diagnostics[0].details["earliest"] == "2027-05-18"


@pytest.mark.parametrize("reverse", [False, True])
def test_g2_two_predecessors_take_the_latest_and_the_driving_relation_is_that_ones(reverse):
    relations = [rel("a-g", "a", "end", "g", "at", "1d"), rel("b-g", "b", "end", "g", "at", "0d")]
    project = proj({"a": span("2027-04-26", "2027-05-10"), "b": span("2027-04-26", "2027-05-14"), "g": gate()},
                   relations[::-1] if reverse else relations)
    result = schedule(project)
    assert result.ok and result.placements["g"] == {"at": date(2027, 5, 14)}
    assert result.analysis.driving_relations == frozenset({"relation:%d:b-g" % (0 if reverse else 1)})


@pytest.mark.parametrize("lag,expected", [("3wd", date(2027, 5, 12)), ({"value": "3wd", "calendar": "six"}, date(2027, 5, 11))])
def test_g3_a_lag_is_read_on_its_own_calendar(lag, expected):
    project = proj({"a": span("2027-05-03", "2027-05-07"), "g": gate()}, [rel("a-g", "a", "end", "g", "at", lag)])
    result = schedule(project)
    assert result.ok and result.placements["g"] == {"at": expected}
    assert schedule(twin(project, result)).ok


@pytest.mark.parametrize("fields,expected,driving", [
    (floor("2027-05-21"), date(2027, 5, 21), frozenset()),
    (floor("2027-05-08"), date(2027, 5, 12), frozenset({"relation:0:a-g"})),
])
def test_g4_the_floor_raises_the_date_only_when_it_is_later(fields, expected, driving):
    project = proj({"a": span("2027-05-03", "2027-05-07"), "g": gate(**fields)}, [rel("a-g", "a", "end", "g", "at", "3wd")])
    result = schedule(project)
    assert result.ok and result.placements["g"] == {"at": expected}
    assert result.analysis.driving_relations == driving


def test_g4_a_floor_alone_places_the_point_and_nothing_to_derive_from_is_e_derivation_in_both_commands():
    alone = proj({"g": gate(**floor("2027-05-21"))}, [])
    assert schedule(alone).placements["g"] == {"at": date(2027, 5, 21)}
    nothing = proj({"g": gate()}, [])
    expected = [("E_DERIVATION", "/objects/g/schedule", "Scheduled point has no predecessor and no minimum date")]
    for diagnostics in (validate_project(nothing), schedule(nothing).diagnostics):
        assert [(item.id, item.path, item.message) for item in diagnostics] == expected
    only_cap = proj({"g": gate(constraints={"at": {"max": "2027-06-01"}})}, [])
    assert codes(schedule(only_cap)) == ["E_DERIVATION"]


def test_g5_chained_derived_gates():
    objects = {"a": span("2027-04-26", "2027-05-07"), "g1": gate(),
               "t": {"type": "task", "schedule": {"mode": "scheduled", "amount": "3wd"}}, "g2": gate()}
    project = proj(objects, [rel("a-g1", "a", "end", "g1", "at", "1wd"), rel("g1-t", "g1", "at", "t", "start", "0d"),
                             rel("t-g2", "t", "end", "g2", "at", "1d")])
    result = schedule(project)
    assert result.ok
    assert result.placements["g1"] == {"at": date(2027, 5, 10)}
    assert result.placements["t"] == {"start": date(2027, 5, 10), "end": date(2027, 5, 13)}
    assert result.placements["g2"] == {"at": date(2027, 5, 14)}
    assert schedule(twin(project, result)).placements == result.placements


@pytest.mark.parametrize("lag,code", [("0d", "E_UNSUPPORTED_CYCLE"), ("1d", "E_UNSATISFIABLE_DEPENDENCIES")])
def test_g6_a_cycle_through_derived_gates_is_found_by_schedule_with_the_span_codes(lag, code):
    project = proj({"g1": gate(**floor("2027-05-07")), "g2": gate()},
                   [rel("x", "g1", "at", "g2", "at", lag), rel("y", "g2", "at", "g1", "at", "0d")])
    assert validate_project(project) == []
    result = schedule(project)
    assert [(item.id, item.path) for item in result.diagnostics] == [(code, "/objects/g1"), (code, "/objects/g2")]


def test_g7_the_cap_rejects_with_details_and_still_returns_the_placement():
    project = proj({"a": span("2027-05-03", "2027-05-07"), "g": gate(constraints={"at": {"max": "2027-05-10"}})},
                   [rel("a-g", "a", "end", "g", "at", "3wd")])
    result = schedule(project)
    item, = result.diagnostics
    assert (item.id, item.path) == ("E_CONTRADICTORY_BOUNDS", "/objects/g/schedule/constraints/at/max")
    assert item.details == {"object": "g", "endpoint": "at", "derived": "2027-05-12", "max": "2027-05-10", "forcedBy": "a-g"}
    assert result.placements["g"] == {"at": date(2027, 5, 12)} and result.analysis is None


def test_g7_a_cap_on_the_date_is_accepted_and_a_floor_after_the_cap_is_contradictory():
    ok = proj({"a": span("2027-05-03", "2027-05-07"), "g": gate(constraints={"at": {"max": "2027-05-12"}})},
              [rel("a-g", "a", "end", "g", "at", "3wd")])
    assert schedule(ok).ok
    crossed = proj({"g": gate(constraints={"at": {"min": "2027-05-20", "max": "2027-05-10"}})}, [])
    item, = schedule(crossed).diagnostics
    assert item.id == "E_CONTRADICTORY_BOUNDS" and item.details["forcedBy"] == "/objects/g/schedule/constraints/at/min"


def test_g8_a_derived_gate_that_ends_a_chain_keeps_total_float_meaningful():
    objects = {"a": span("2027-04-26", "2027-05-07"),
               "b": {"type": "task", "schedule": {"mode": "scheduled", "amount": "3wd"}},
               "c": {"type": "task", "schedule": {"mode": "scheduled", "amount": "8wd"}}, "g": gate()}
    relations = [rel("a-b", "a", "end", "b", "start", "0d"), rel("a-c", "a", "end", "c", "start", "0d"),
                 rel("b-g", "b", "end", "g", "at", "0d"), rel("c-g", "c", "end", "g", "at", "0d")]
    derived = schedule(proj(objects, relations))
    assert derived.analysis.critical == frozenset({"a", "c", "g"})
    assert derived.analysis.total_float["b"].value == 5
    slack = copy.deepcopy(objects)
    slack["g"]["schedule"] = {"mode": "fixed-point", "at": "2027-06-30"}
    fixed = schedule(proj(slack, relations))
    assert fixed.analysis.critical == frozenset()
    assert (fixed.analysis.total_float["b"].value, fixed.analysis.total_float["c"].value) == (35, 30)


def test_g8_the_latest_date_of_a_derived_gate_honours_its_cap():
    project = proj({"a": span("2027-04-26", "2027-05-07"),
                    "t": {"type": "task", "schedule": {"mode": "scheduled", "amount": "3wd"}},
                    "g": gate(constraints={"at": {"max": "2027-06-30"}}),
                    "far": span("2027-08-02", "2027-08-06")},
                   [rel("a-t", "a", "end", "t", "start", "0d"), rel("t-g", "t", "end", "g", "at", "0d"),
                    rel("g-far", "g", "at", "far", "start", "0d")])
    result = schedule(project)
    assert result.ok
    assert result.analysis.latest_placements["g"] == {"at": date(2027, 6, 30)}


def test_g9_a_start_or_end_endpoint_on_a_derived_gate_is_an_endpoint_mismatch():
    for side in ("to", "from"):
        relation = rel("a-g", "a", "end", "g", "at", "0d")
        relation[side]["endpoint"] = "start"
        if side == "from":
            relation = rel("g-a", "g", "start", "a", "start", "0d")
        project = proj({"a": span("2027-04-26", "2027-05-07"), "g": gate(**floor("2027-05-10"))}, [relation])
        diagnostics = validate_project(project)
        assert [item.id for item in diagnostics] == ["E_ENDPOINT_MODE_MISMATCH"]
    mismatched = proj({"a": span("2027-04-26", "2027-05-07"), "g": gate()}, [rel("a-g", "a", "end", "g", "start", "0d")])
    assert [(i.id, i.path) for i in validate_project(mismatched)] == [
        ("E_DERIVATION", "/objects/g/schedule"), ("E_ENDPOINT_MODE_MISMATCH", "/relations/0/to/endpoint")]


def test_g10_a_gate_inside_a_group_waits_for_a_sibling_but_not_for_the_groups_own_end():
    def group(dependency):
        objects = {"grp": {"type": "group", "schedule": {"mode": "rollup"}},
                   "sib": {**span("2027-05-03", "2027-05-07"), "parent": "grp"},
                   "g": {**gate(), "parent": "grp"}}
        return proj(objects, [dependency])

    placed = schedule(group(rel("s-g", "sib", "end", "g", "at", "1d")))
    assert placed.ok and placed.placements["g"] == {"at": date(2027, 5, 8)}
    assert placed.placements["grp"] == {"start": date(2027, 5, 3), "end": date(2027, 5, 8)}
    cyclic = schedule(group(rel("grp-g", "grp", "end", "g", "at", "0d")))
    assert "E_UNSUPPORTED_CYCLE" in codes(cyclic)


def test_g11_a_derived_point_attaches_to_a_host_and_a_derived_host_is_rejected():
    objects = {"host": span("2027-05-03", "2027-05-07"), "a": span("2027-05-03", "2027-05-07"),
               "g": {**gate(), "attachesTo": "host"}}
    project = proj(objects, [rel("a-g", "a", "end", "g", "at", "3wd")])
    assert validate_project(project) == [] and schedule(project).ok
    broken = copy.deepcopy(project)
    broken["objects"]["a"]["attachesTo"] = "g"
    assert [item.id for item in validate_project(broken)] == ["E_PROJECT_ATTACH_SOURCE_NOT_POINT"]
    broken = copy.deepcopy(project)
    broken["objects"]["g"]["attachesTo"] = "g2"
    broken["objects"]["g2"] = gate(**floor("2027-05-10"))
    assert [item.id for item in validate_project(broken)] == ["E_PROJECT_ATTACH_TARGET_NOT_SPAN"]


def test_g12_a_calendar_day_lag_from_a_friday_lands_on_a_sunday_without_snapping():
    project = proj({"a": span("2027-05-04", "2027-05-07"), "g": gate()}, [rel("a-g", "a", "end", "g", "at", "2d")])
    result = schedule(project)
    assert result.ok and result.placements["g"] == {"at": date(2027, 5, 9)}
    assert result.placements["g"]["at"].weekday() == 6
    assert schedule(twin(project, result)).ok


def test_a_scenario_that_adds_a_dependency_moves_the_derived_gate_and_rejects_its_fixed_twin():
    project = g1_project()
    project["objects"]["late"] = span("2027-05-10", "2027-05-31")
    project["scenarios"] = {"slip": {"title": "A late task gates the launch", "relations": {
        "add": [rel("late-launch", "late", "end", "launch", "at", "0d")]}}}
    from chrona.scheduling.scheduler import schedule_scenario

    base = schedule(project)
    assert base.placements["launch"] == {"at": date(2027, 5, 18)}
    resolved, moved = schedule_scenario(project, "slip")
    assert moved.ok and moved.placements["launch"] == {"at": date(2027, 5, 31)}
    twinned = twin(project, base)
    assert schedule_scenario(twinned, "slip")[1].diagnostics[0].id == "E_FIXED_TARGET_VIOLATION"


def test_a_bound_that_is_not_a_real_date_is_a_schema_diagnostic_not_a_crash():
    project = proj({"g": gate(constraints={"at": {"min": "2027-02-30"}})}, [])
    for diagnostics in (validate_project(project), schedule(project).diagnostics):
        assert [(item.id, item.path) for item in diagnostics] == [("E_SCHEMA", "/objects/g/schedule")]


def test_the_point_branch_accepts_only_mode_and_at_bounds():
    for fields in ({"amount": "1d"}, {"anchor": {"start": "2027-05-07"}}, {"at": "2027-05-07"},
                   {"constraints": {"start": {"min": "2027-05-07"}}}):
        project = proj({"g": gate(**fields)}, [])
        assert [item.id for item in validate_project(project)] == ["E_SCHEMA"], fields
