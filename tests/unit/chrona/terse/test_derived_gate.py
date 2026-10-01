"""The terse spelling of a derived gate (#788 slice 2; design 8.1 rules T1 to T6, Spec 65 sections 3 and 4)."""
from __future__ import annotations

import pytest

from chrona.core.validation import validate_project
from chrona.scheduling.scheduler import schedule
from chrona.terse import locate
from tests.support.terse_plans import FIXTURES, compile_text, schedule_summary

HEAD = 'project p "P"\nqa "QA" task 2027-03-01..2027-03-08\n'


def _compile(body: str):
    compiled = compile_text(HEAD + body)
    assert compiled.ok, [item.as_dict() for item in compiled.diagnostics]
    return compiled


def _rejected(body: str, head: str = HEAD):
    compiled = compile_text(head + body)
    assert not compiled.ok
    return compiled.diagnostics


def _placed(project) -> dict:
    result = schedule(project)
    assert result.ok, [(item.id, item.path) for item in result.diagnostics]
    return {name: {key: value.isoformat() for key, value in place.items()} for name, place in result.placements.items()}


# T1: a gate with no schedule words and an `after` clause is a derived point.
def test_t1_a_gate_with_after_and_no_date_compiles_to_scheduled_point():
    compiled = _compile('launch "Launch" gate after qa +2d\n')
    assert compiled.project["objects"]["launch"]["schedule"] == {"mode": "scheduled-point"}
    (relation,) = compiled.project["relations"]
    assert relation["from"] == {"object": "qa", "endpoint": "end"} and relation["to"] == {"object": "launch", "endpoint": "at"}
    assert relation["lag"] == "2d"
    assert validate_project(compiled.project) == []
    assert _placed(compiled.project)["launch"] == {"at": "2027-03-10"}  # the issue's case: end 03-08 plus 2d, nothing computed by hand


def test_t1_the_calendar_clause_may_sit_between_the_kind_and_after():
    text = 'project p "P"\ncalendar std mon-fri\nqa "QA" task 2027-03-01..2027-03-08\nl "L" gate calendar std after qa +2wd\n'
    compiled = compile_text(text)
    assert compiled.ok and compiled.project["objects"]["l"] == {
        "type": "gate", "title": "L", "calendar": "std", "schedule": {"mode": "scheduled-point"}}
    assert _placed(compiled.project)["l"] == {"at": "2027-03-10"}


# T1 and the twin: a derived gate placed on the date it derives is the fixed gate the author would have written by hand.
def test_a_derived_gate_and_its_fixed_twin_place_and_schedule_identically():
    derived = _compile('launch "Launch" gate after qa +2d\nnext "Next" task 3d after launch\n')
    twin = _compile('launch "Launch" gate 2027-03-10 after qa +2d\nnext "Next" task 3d after launch\n')
    assert schedule_summary(derived.project) == schedule_summary(twin.project)


# T2: bounds.
def test_t2_a_floor_is_constraints_at_min_and_a_cap_is_constraints_at_max():
    compiled = _compile('floor gate at >= 2027-05-07 after qa +2d\ncap gate at <= 2027-06-30 after qa\n'
                        'both gate at <= 2027-06-30 at >= 2027-05-07 after qa\n')
    objects = compiled.project["objects"]
    assert objects["floor"]["schedule"] == {"mode": "scheduled-point", "constraints": {"at": {"min": "2027-05-07"}}}
    assert objects["cap"]["schedule"] == {"mode": "scheduled-point", "constraints": {"at": {"max": "2027-06-30"}}}
    assert objects["both"]["schedule"] == {"mode": "scheduled-point", "constraints": {"at": {"min": "2027-05-07", "max": "2027-06-30"}}}
    placed = _placed(compiled.project)
    assert placed["floor"] == {"at": "2027-05-07"} and placed["cap"] == {"at": "2027-03-08"} and placed["both"] == {"at": "2027-05-07"}


def test_t2_a_cap_the_dependencies_pass_is_the_schedulers_contradictory_bounds_at_the_clause():
    compiled = _compile('launch "Launch" gate at <= 2027-03-09 after qa +3d\n')
    result = schedule(compiled.project)
    assert [item.id for item in result.diagnostics] == ["E_CONTRADICTORY_BOUNDS"]
    assert locate(compiled.source_map, result.diagnostics[0].path).as_dict() == {
        "line": 3, "column": 22, "endLine": 3, "endColumn": 38}  # `at <= 2027-03-09`


# T3: E_TERSE_SCHEDULE_REQUIRED is narrowed, not retired.
def test_t3_a_task_with_no_schedule_keeps_its_error_and_hint():
    (item,) = _rejected("t task\n")
    assert item.id == "E_TERSE_SCHEDULE_REQUIRED" and "a task needs a duration" in item.hint


def test_t3_a_gate_with_neither_a_date_nor_after_says_to_write_either():
    (item,) = _rejected("g gate\n")
    assert item.id == "E_TERSE_SCHEDULE_REQUIRED" and "a gate needs a date, or `after X` to derive one" in item.hint
    (item,) = _rejected("g gate calendar std\n", 'project p\ncalendar std mon-fri\n')
    assert item.id == "E_TERSE_SCHEDULE_REQUIRED"


def test_t3_a_gate_with_bounds_but_no_after_says_a_floor_alone_is_a_fixed_date():
    (item,) = _rejected("g gate at >= 2027-05-07\n")
    assert item.id == "E_TERSE_SCHEDULE_REQUIRED" and "write `g gate DATE`" in item.hint
    assert item.range.as_dict() == {"line": 3, "column": 8, "endLine": 3, "endColumn": 24}  # the bound clause


# T4: there is no derived span.
def test_t4_a_task_with_after_and_no_schedule_is_still_rejected():
    (item,) = _rejected("t task after qa +1d\n")
    assert item.id == "E_TERSE_SCHEDULE_REQUIRED"
    (item,) = _rejected("t task at >= 2027-05-07 after qa\n")
    assert item.id == "E_TERSE_AMOUNT_INVALID"  # `at` bounds belong to a gate; a task takes a duration


@pytest.mark.parametrize("body, code", [
    ("g gate at >= 2027-05-07 at >= 2027-05-08 after qa\n", "E_TERSE_CLAUSE_DUPLICATE"),
    ("g gate at 2027-05-07 after qa\n", "E_TERSE_TOKEN_UNEXPECTED"),
    ("g gate at >=\n", "E_TERSE_LINE_INCOMPLETE"),
    ("g gate at >= 2027-02-30 after qa\n", "E_TERSE_DATE_INVALID"),
    ("g gate at >= 2027-5-7 after qa\n", "E_TERSE_DATE_INVALID"),
    ("g gate 2027-05-07 at >= 2027-05-01 after qa\n", "E_TERSE_TOKEN_UNEXPECTED"),
    ("g gate after qa at >= 2027-05-07\n", "E_TERSE_TOKEN_UNEXPECTED"),
    ("g gate after nobody\n", "E_TERSE_REFERENCE_UNKNOWN"),
])
def test_malformed_bounds_are_positioned_compiler_errors(body, code):
    diagnostics = _rejected(body)
    assert [item.id for item in diagnostics] == [code]
    assert diagnostics[0].range is not None and diagnostics[0].hint


# T5: default endpoints.
def test_t5_after_a_derived_gate_uses_its_at_and_a_derived_gate_targets_at():
    compiled = _compile('a1 gate after qa\nb1 gate after a1 +1d\nc1 task 2d after a1\n')
    by_id = {relation["id"]: relation for relation in compiled.project["relations"]}
    assert by_id["a1-b1"]["from"] == {"object": "a1", "endpoint": "at"} and by_id["a1-b1"]["to"]["endpoint"] == "at"
    assert by_id["a1-c1"]["from"] == {"object": "a1", "endpoint": "at"} and by_id["a1-c1"]["to"]["endpoint"] == "start"
    assert _placed(compiled.project)["c1"] == {"start": "2027-03-08", "end": "2027-03-10"}


def test_t5_start_on_a_derived_gate_is_cores_endpoint_mismatch_with_a_position():
    diagnostics = _rejected("l gate after qa\nz gate after l.start\n")
    assert [item.id for item in diagnostics] == ["E_ENDPOINT_MODE_MISMATCH"] and diagnostics[0].component == "core"
    assert diagnostics[0].range.line == 4


# T6: the source map.
def test_t6_the_schedule_maps_to_the_kind_word_and_to_the_bound_clauses_when_there_are_bounds():
    compiled = _compile('implicit "I" gate after qa\nbounded "B" gate at >= 2027-05-07 at <= 2027-06-30 after qa\n')
    smap = {key: value.as_dict() for key, value in compiled.source_map.items()}
    assert smap["/objects/implicit/schedule"] == smap["/objects/implicit/type"]  # the kind word `gate`
    assert smap["/objects/bounded/schedule/constraints/at/min"] == {"line": 4, "column": 18, "endLine": 4, "endColumn": 34}
    assert smap["/objects/bounded/schedule/constraints/at/max"] == {"line": 4, "column": 35, "endLine": 4, "endColumn": 51}
    assert smap["/objects/bounded/schedule"] == {"line": 4, "column": 18, "endLine": 4, "endColumn": 51}


def test_the_derived_gate_golden_plan_is_in_the_fixture_set():
    assert (FIXTURES / "derived-gates.chrona").is_file() and (FIXTURES / "derived-gates.project.yaml").is_file()
