"""`validate` reports the dependency cycles `schedule` rejects, through one use case (#780).

Every case runs both checks on the same Project mapping, so the two commands, and the MCP tools that call the same
use-case functions, cannot drift apart.
"""
import copy

import pytest

from chrona.usecases.project_checks import schedule_project_mapping, validate_project_mapping

CYCLE_CODES = {"E_UNSUPPORTED_CYCLE", "E_UNSATISFIABLE_DEPENDENCIES"}


def rel(source, source_endpoint, target, target_endpoint, lag="0d"):
    return {"type": "dependency", "from": {"object": source, "endpoint": source_endpoint},
            "to": {"object": target, "endpoint": target_endpoint}, "lag": lag}


def project(objects, relations):
    return {"version": "timeline/v0.7", "project": {"id": "p", "title": "P"}, "objects": objects, "relations": relations}


def fixed(start, end):
    return {"type": "task", "schedule": {"mode": "fixed-span", "start": start, "end": end}}


def duration(amount="2d"):
    return {"type": "task", "schedule": {"mode": "scheduled", "amount": amount}}


POINT = {"type": "gate", "schedule": {"mode": "scheduled-point", "constraints": {"at": {"min": "2026-10-01"}}}}


def starter_cycle():
    """The issue's reproduction: the starter's two fixed spans plus the two relations that close a loop."""
    return project(
        {"design": fixed("2026-10-01", "2026-10-31"), "build": fixed("2026-11-03", "2026-12-15")},
        [rel("design", "end", "build", "start"), rel("build", "end", "design", "start")])


def duration_cycle():
    return project({"a": duration(), "b": duration()}, [rel("a", "end", "b", "start"), rel("b", "end", "a", "start")])


def point_cycle():
    return project({"p": copy.deepcopy(POINT), "q": copy.deepcopy(POINT)}, [rel("p", "at", "q", "at"), rel("q", "at", "p", "at")])


def fixed_and_duration_cycle():
    return project({"design": fixed("2026-10-01", "2026-10-31"), "build": duration("5d")},
                   [rel("design", "end", "build", "start"), rel("build", "end", "design", "start")])


def wait_cycle_acyclic_by_endpoint():
    """Start-to-start and finish-to-finish: no loop between endpoints, yet the scheduler waits on both."""
    return project({"a": duration(), "b": duration()}, [rel("a", "start", "b", "start"), rel("b", "end", "a", "end")])


def self_relation():
    return project({"a": duration()}, [rel("a", "end", "a", "start")])


def rollup_waits_on_its_own_child():
    return project(
        {"group": {"type": "group", "schedule": {"mode": "rollup"}}, "child": {**duration(), "parent": "group"}},
        [rel("group", "end", "child", "start")])


CYCLES = [
    ("fixed-span (the issue's reproduction)", starter_cycle, "/relations/1", ["design", "build"], "E_UNSUPPORTED_CYCLE"),
    ("duration", duration_cycle, "/relations/1", ["a", "b"], "E_UNSUPPORTED_CYCLE"),
    ("point", point_cycle, "/relations/1", ["p", "q"], "E_UNSUPPORTED_CYCLE"),
    ("fixed and duration", fixed_and_duration_cycle, "/relations/1", ["design", "build"], "E_UNSUPPORTED_CYCLE"),
    ("start-to-start and finish-to-finish", wait_cycle_acyclic_by_endpoint, "/relations/1", ["a", "b"], "E_UNSUPPORTED_CYCLE"),
    ("self relation", self_relation, "/relations/0", ["a"], "E_UNSUPPORTED_CYCLE"),
    ("rollup on its own child", rollup_waits_on_its_own_child, "/relations/0", ["group", "child"], "E_UNSUPPORTED_CYCLE"),
]


@pytest.mark.parametrize("build,path,objects,code", [case[1:] for case in CYCLES], ids=[case[0] for case in CYCLES])
def test_validate_names_the_cycle_and_schedule_agrees(build, path, objects, code):
    plan = build()

    validated = validate_project_mapping(plan)
    scheduled = schedule_project_mapping(plan)

    assert not validated.ok
    [finding] = validated.diagnostics
    assert (finding.id, finding.path) == (code, path)
    assert all(name in finding.message for name in objects)
    assert [name for name in objects if name in finding.message] == objects  # Project order, each named once
    assert scheduled.diagnostics == validated.diagnostics
    assert scheduled.placements == {} and scheduled.analysis is None


def test_the_fixed_span_cycle_is_no_longer_only_a_date_symptom():
    codes = {item.id for item in schedule_project_mapping(starter_cycle()).diagnostics}

    assert codes == {"E_UNSUPPORTED_CYCLE"}  # was E_FIXED_TARGET_VIOLATION on main, and validate was clean


def test_a_positive_lag_cycle_is_unsatisfiable_not_merely_unsupported():
    plan = duration_cycle()
    plan["relations"][0]["lag"] = "1d"

    [finding] = validate_project_mapping(plan).diagnostics

    assert finding.id == "E_UNSATISFIABLE_DEPENDENCIES"
    assert schedule_project_mapping(plan).diagnostics == (finding,)


def test_only_the_objects_on_the_cycle_are_named_not_those_waiting_downstream():
    plan = duration_cycle()
    plan["objects"]["downstream"] = duration()
    plan["relations"].append(rel("b", "end", "downstream", "start"))

    [finding] = validate_project_mapping(plan).diagnostics

    assert "downstream" not in finding.message and finding.path == "/relations/1"


def test_two_separate_cycles_are_two_findings_in_project_order():
    plan = project({"a": duration(), "b": duration(), "x": duration(), "y": duration()},
                   [rel("x", "end", "y", "start"), rel("y", "end", "x", "start"),
                    rel("a", "end", "b", "start"), rel("b", "end", "a", "start")])

    findings = validate_project_mapping(plan).diagnostics

    assert [item.path for item in findings] == ["/relations/3", "/relations/1"]  # the cycle holding `a` first
    assert "a, b" in findings[0].message and "x, y" in findings[1].message


def test_the_closing_relation_is_the_one_declared_last_inside_the_cycle():
    plan = duration_cycle()
    plan["relations"].reverse()

    [finding] = validate_project_mapping(plan).diagnostics

    assert finding.path == "/relations/1"
    plan["relations"].insert(0, rel("a", "start", "b", "start"))  # an extra, non-cyclic-looking edge that is on the wait cycle too
    [again] = validate_project_mapping(plan).diagnostics
    assert again.path == "/relations/2"


def test_the_message_holds_no_host_path_and_is_stable():
    plan = starter_cycle()

    first = validate_project_mapping(plan).diagnostics
    second = validate_project_mapping(copy.deepcopy(plan)).diagnostics

    assert first == second and first[0].message == second[0].message
    assert "/" not in first[0].message.replace("/relations", "")


# --- what is not a cycle ----------------------------------------------------------------------------------------

def nested_start_to_start_and_finish_to_finish_in_a_fixed_span():
    return project({"outer": fixed("2026-10-01", "2026-10-31"), "inner": duration("3d")},
                   [rel("outer", "start", "inner", "start"), rel("inner", "end", "outer", "end")])


def negative_lag_loop_of_fixed_spans():
    return project({"design": fixed("2026-10-01", "2026-10-31"), "build": fixed("2026-11-03", "2026-12-15")},
                   [rel("design", "end", "build", "start"), rel("build", "end", "design", "start", lag="-90d")])


def chain():
    return project({"a": fixed("2026-10-01", "2026-10-31"), "b": duration("5d"), "c": duration("2d")},
                   [rel("a", "end", "b", "start"), rel("b", "end", "c", "start")])


@pytest.mark.parametrize("build", [nested_start_to_start_and_finish_to_finish_in_a_fixed_span, negative_lag_loop_of_fixed_spans, chain])
def test_what_the_scheduler_accepts_is_not_called_a_cycle(build):
    plan = build()

    assert not CYCLE_CODES & {item.id for item in validate_project_mapping(plan).diagnostics}
    assert not CYCLE_CODES & {item.id for item in schedule_project_mapping(plan).diagnostics}
    assert validate_project_mapping(plan).ok


def test_a_structurally_broken_project_reports_its_own_error_and_no_cycle_finding():
    plan = duration_cycle()
    plan["relations"][0]["to"]["object"] = "ghost"

    assert [item.id for item in validate_project_mapping(plan).diagnostics] == ["E_REFERENCE"]
