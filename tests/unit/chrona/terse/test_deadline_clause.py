"""The terse `deadline D` clause (#822, I822-1; Spec 65 sections 1.1, 3.1 and 4).

A deadline is a promise, never a bound: the clause maps to `objects.NAME.deadline` and nothing else changes, so
every rule here is proven on small synthetic plans through the compiler, Core and the scheduler.
"""
from __future__ import annotations

import pytest

from chrona.core.deadlines import deadline_warnings
from chrona.core.validation import validate_project
from chrona.scheduling.scheduler import schedule
from chrona.terse import locate
from tests.support.terse_plans import FIXTURES, compile_fixture, compile_text, schedule_summary

HEAD = 'project p "P"\ncalendar std mon-fri\nqa "QA" task 2027-03-01..2027-03-08\n'


def _compile(body: str, head: str = HEAD):
    compiled = compile_text(head + body)
    assert compiled.ok, [item.as_dict() for item in compiled.diagnostics]
    return compiled


def _codes(body: str, head: str = HEAD) -> list[str]:
    compiled = compile_text(head + body)
    assert not compiled.ok
    return [item.id for item in compiled.diagnostics]


def test_the_clause_maps_to_the_object_deadline_on_every_kind_and_nothing_else():
    compiled = _compile(
        'dev "Dev" task 5d after qa deadline 2027-03-20\n'
        'ready "Ready" gate 2027-03-25 deadline 2027-03-26\n'
        'derived "Derived" gate after qa +1d deadline 2027-03-30\n'
        'phase "Phase" group deadline 2027-04-30\n'
        '  inner "Inner" task 2d after dev deadline 2027-04-01\n')
    objects = compiled.project["objects"]
    assert {key: objects[key].get("deadline") for key in ("qa", "dev", "ready", "derived", "phase", "inner")} == {
        "qa": None, "dev": "2027-03-20", "ready": "2027-03-26", "derived": "2027-03-30", "phase": "2027-04-30",
        "inner": "2027-04-01"}
    assert objects["dev"]["schedule"] == {"mode": "scheduled", "amount": "5d"}  # the schedule is untouched
    assert validate_project(compiled.project) == []


def test_the_emitted_yaml_quotes_the_date_after_the_schedule_in_fixed_key_order():
    text = _compile('dev "Dev" task 5d calendar std after qa deadline 2027-03-20\n').yaml.decode("utf-8")
    block = text[text.index("  dev:"):].splitlines()[:7]
    assert block == ["  dev:", "    type: task", "    title: Dev", "    calendar: std",
                     "    schedule: {mode: scheduled, amount: 5d}", "    deadline: '2027-03-20'", "relations:"]


def test_the_source_map_positions_the_clause_so_a_finding_at_the_pointer_has_a_line_and_column():
    compiled = _compile('dev "Dev" task 5d after qa deadline 2027-03-20\n')
    where = locate(compiled.source_map, "/objects/dev/deadline")
    assert where is not None and where.line == 4
    text = (HEAD + 'dev "Dev" task 5d after qa deadline 2027-03-20\n').splitlines()[3]
    assert text[where.column - 1:where.end_column - 1] == "deadline 2027-03-20"
    # an object without the clause falls back to the nearest ancestor, never to the clause of another object
    assert locate(compiled.source_map, "/objects/qa/deadline") == locate(compiled.source_map, "/objects/qa")


def test_a_deadline_moves_nothing_and_schedule_lists_exactly_the_missed_promises():
    bare = _compile('dev "Dev" task 5d after qa\ngo "Go" gate after dev +1d\nlate "Late" task 2d after go\n')
    promised = _compile('dev "Dev" task 5d after qa deadline 2027-03-12\ngo "Go" gate after dev +1d deadline 2027-03-14\n'
                        'late "Late" task 2d after go deadline 2027-03-30\n')
    placed, plain = schedule(promised.project), schedule(bare.project)
    assert placed.ok and placed.placements == plain.placements  # dev ends 03-13, go is 03-14, late ends 03-16
    assert schedule_summary(promised.project) == schedule_summary(bare.project)
    warned = deadline_warnings(promised.project, placed.placements)
    assert [item.path for item in warned] == ["/objects/dev/deadline"]  # go is on its date (kept); late has slack
    assert warned[0].details["daysLate"] == 1


def test_a_word_deadline_is_a_contextual_keyword_so_it_still_names_objects_and_dependencies():
    named = _compile('deadline "A name" task 3d after qa\nship "Ship" gate after deadline\n')
    renamed = _compile('dl "A name" task 3d after qa\nship "Ship" gate after dl\n')
    assert named.project["objects"]["deadline"] == renamed.project["objects"]["dl"]
    assert [(r["from"], r["to"]) for r in named.project["relations"][1:]] == [
        ({"object": "deadline", "endpoint": "end"}, {"object": "ship", "endpoint": "at"})]
    both = _compile('deadline "A name" task 3d after qa\nship "Ship" gate after deadline deadline 2027-09-01\n')
    assert both.project["objects"]["ship"]["deadline"] == "2027-09-01"
    assert both.project["relations"][1]["from"] == {"object": "deadline", "endpoint": "end"}
    assert "deadline" not in both.project["objects"]["deadline"]


def test_every_plan_that_compiled_before_the_clause_compiles_to_the_same_project():
    for plan in sorted(FIXTURES.glob("*.chrona")):
        if "deadline" in plan.read_text(encoding="utf-8"):
            continue
        compiled = compile_fixture(plan.name)
        assert compiled.ok and compiled.yaml == (FIXTURES / f"{plan.stem}.project.yaml").read_bytes()
        assert all("deadline" not in entry for entry in compiled.project["objects"].values())


def test_a_second_clause_a_missing_or_impossible_date_and_a_misplaced_clause_are_stable_errors():
    assert _codes('d "D" task 5d after qa deadline 2027-03-20 deadline 2027-03-21\n') == ["E_TERSE_CLAUSE_DUPLICATE"]
    assert _codes('d "D" task 5d after qa deadline\n') == ["E_TERSE_LINE_INCOMPLETE"]
    assert _codes('d "D" task 5d after qa deadline 2027-02-30\n') == ["E_TERSE_DATE_INVALID"]
    assert _codes('d "D" task 5d after qa deadline 2027-3-5\n') == ["E_TERSE_DATE_INVALID"]
    assert _codes('d "D" task 5d deadline 2027-03-20 after qa\n') == ["E_TERSE_TOKEN_UNEXPECTED"]
    assert _codes('d "D" task 5d calendar std deadline 2027-03-20 calendar std\n') == ["E_TERSE_TOKEN_UNEXPECTED"]
    assert _codes('d "D" gate deadline 2027-03-20\n') == ["E_TERSE_SCHEDULE_REQUIRED"]
    assert _codes('d "D" task deadline 2027-03-20\n') == ["E_TERSE_SCHEDULE_REQUIRED"]


def test_a_deadline_alone_is_not_a_schedule_and_each_kind_gets_its_own_hint():
    gate = compile_text(HEAD + 'd "D" gate deadline 2027-03-20\n').diagnostics[0]
    task = compile_text(HEAD + 'd "D" task deadline 2027-03-20\n').diagnostics[0]
    assert "a gate needs a date, or `after X`" in gate.hint and "a task needs a duration" in task.hint
    line = (HEAD + 'd "D" gate deadline 2027-03-20\n').splitlines()[3]
    assert line[gate.range.column - 1:gate.range.end_column - 1] == "deadline"  # the diagnostic is positioned on the word


def test_the_misplaced_clause_hint_names_the_rule_and_other_leftovers_keep_their_hint():
    late = compile_text(HEAD + 'd "D" task 5d deadline 2027-03-20 after qa\n').diagnostics[0]
    assert "last clause" in late.hint
    plain = compile_text(HEAD + 'd "D" task 5d after qa calendar std\n').diagnostics[0]
    assert "last clause" not in plain.hint


@pytest.mark.parametrize("line", ['g "G" group deadline 2027-03-20 after qa', 'g "G" group deadline 2027-03-20 calendar std',
                                  'g "G" group deadline 2027-03-20 5d'])
def test_a_group_keeps_refusing_a_schedule_a_calendar_and_after_even_with_a_deadline(line):
    assert _codes(line + "\n") == ["E_TERSE_TOKEN_UNEXPECTED"]
