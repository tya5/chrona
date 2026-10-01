"""One negative fixture per compiler-owned code, with expected (code, sourceRange) and a hint check (#148)."""
from __future__ import annotations

import json

import pytest

from chrona.terse import CODES
from chrona.terse.diagnostics import RESERVED_CODES, nearest, suggest_name
from chrona.usecases.terse_compile import compile_plan
from tests.support.terse_plans import FIXTURES

ERRORS = FIXTURES / "errors"
EXPECTED = json.loads((ERRORS / "expected.json").read_text(encoding="utf-8"))
CORE_CODES = {"E_INVALID_SPAN", "E_CALENDAR_REQUIRED", "E_ROLLUP_EMPTY", "E_ENDPOINT_MODE_MISMATCH"}

# Codes whose input is not a text fixture, and the test that proves each one.
ELSEWHERE = {
    "E_TERSE_ENCODING": "test_invalid_utf8_is_positioned",
    "E_TERSE_OUTPUT_EXISTS": "tests/cli/test_compile.py::test_compile_output_refuses_an_existing_file",
    "E_TERSE_INPUT_IO": "tests/cli/test_compile.py::test_compile_unreadable_input_is_exit_two",
    "E_TERSE_COMPILER_DEFECT": "test_a_structurally_invalid_compile_is_reported_as_a_defect",
}


def test_the_codes_proved_elsewhere_name_tests_that_exist():
    from pathlib import Path
    for code, where in ELSEWHERE.items():
        path, _, name = where.rpartition("::")
        source = (Path(__file__) if not path else Path(__file__).resolve().parents[4] / path).read_text(encoding="utf-8")
        assert f"def {name or where}(" in source, code


def test_every_fixture_has_an_expected_entry_and_back():
    assert {path.stem for path in ERRORS.glob("*.chrona")} == set(EXPECTED)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_fixture_reports_exactly_the_expected_codes_and_positions(name):
    result = compile_plan((ERRORS / f"{name}.chrona").read_bytes(), f"{name}.chrona")
    assert not result.ok and result.yaml is None and result.project is None
    got = [{"code": item.id, "sourceRange": item.range.as_dict(), "hint": item.hint is not None} for item in result.diagnostics]
    assert got == EXPECTED[name]
    for item in result.diagnostics:
        assert item.message and item.message != item.id  # no bare codes (#371)
        assert item.source == f"{name}.chrona"
        assert item.range.end_line == item.range.line and item.range.end_column > item.range.column


def test_catalogue_and_fixtures_agree_both_ways():
    used = {entry["code"] for entries in EXPECTED.values() for entry in entries}
    assert used - set(CODES) <= CORE_CODES, "a fixture names a code that is neither catalogued nor a Core code"
    assert CORE_CODES <= used, "every Core code the design promises to position needs a fixture"
    missing = set(CODES) - used - set(ELSEWHERE)
    assert not missing, f"catalogue codes without a fixture: {sorted(missing)}"
    assert set(ELSEWHERE) <= set(CODES) and not set(RESERVED_CODES) & set(CODES)


def test_every_terse_diagnostic_is_positioned_and_has_a_hint_where_a_fix_exists():
    for name, entries in EXPECTED.items():
        for entry in entries:
            if entry["code"] in ("E_TERSE_TAB", "E_TERSE_CONTROL_CHARACTER"):
                continue
            assert entry["hint"], (name, entry["code"])


def test_the_ten_mistakes_of_the_design_are_literal_fixtures():
    codes = {
        "m01-title-unquoted": "E_TERSE_TITLE_UNQUOTED", "m02-kind-misspelt": "E_TERSE_KIND_UNKNOWN",
        "m03-kind-first": "E_TERSE_NAME_RESERVED", "m04-name-not-slug": "E_TERSE_NAME_INVALID",
        "m05-duplicate-name": "E_TERSE_NAME_DUPLICATE", "m06-unknown-reference": "E_TERSE_REFERENCE_UNKNOWN",
        "m07-amount-no-unit": "E_TERSE_AMOUNT_INVALID", "m08-date-not-padded": "E_TERSE_DATE_INVALID",
        "m09-schedule-required": "E_TERSE_SCHEDULE_REQUIRED", "m10-calendar-required": "E_CALENDAR_REQUIRED",
    }
    for name, code in codes.items():
        assert [entry["code"] for entry in EXPECTED[name]] == [code], name


def test_messages_and_hints_of_the_ten_mistakes_say_what_to_do():
    def first(name):
        return compile_plan((ERRORS / f"{name}.chrona").read_bytes()).diagnostics[0]

    assert "needs double quotes" in first("m01-title-unquoted").message
    assert "did you mean `task`?" == first("m02-kind-misspelt").hint
    assert "write the name first" in first("m03-kind-first").message and "design task" in first("m03-kind-first").hint
    assert "try `build-phase`" == first("m04-name-not-slug").hint
    assert "already defined on line 2" in first("m05-duplicate-name").message
    assert "did you mean `structure`?" == first("m06-unknown-reference").hint
    assert "20d" in first("m07-amount-no-unit").message and "'3 days'" in first("m07-amount-spelled-unit").message
    assert "not a calendar date" in first("m08-date-not-real").message
    assert "a gate needs a date" in first("m09-schedule-required").hint
    assert first("m10-calendar-required").component == "core" and "calendar" in first("m10-calendar-required").hint


def test_a_lag_with_a_space_names_the_attached_sign():
    (item,) = compile_plan(b"project p\na task 5d\nb task 5d after a + 1wd\n").diagnostics
    assert item.id == "E_TERSE_LAG_INVALID" and "+1wd" in item.hint


def test_project_yaml_given_to_compile_says_so():
    result = compile_plan(b"version: timeline/v0.7\nproject:\n  id: x\n")
    assert any("Project YAML" in (item.hint or "") for item in result.diagnostics)


def test_invalid_utf8_is_positioned():
    result = compile_plan(b"project p\nd \"caf\xe9\" task 5d\n", "plan.chrona")
    (item,) = result.diagnostics
    assert item.id == "E_TERSE_ENCODING" and item.range.line == 2 and item.range.column == 7 and item.source == "plan.chrona"


def test_a_structurally_invalid_compile_is_reported_as_a_defect(monkeypatch):
    import chrona.usecases.terse_compile as use_case

    monkeypatch.setattr(use_case, "validate_project", lambda project: [__import__("chrona.core.diagnostics", fromlist=["Diagnostic"]).Diagnostic("E_SCHEMA", "boom", "/objects")])
    result = use_case.compile_plan(b"project p\na task 1d\n")
    assert result.defect and not result.ok


def test_more_than_fifty_errors_are_capped_with_a_marker():
    result = compile_plan((ERRORS / "too-many-errors.chrona").read_bytes())
    assert len(result.diagnostics) == 51 and result.diagnostics[-1].id == "E_TERSE_TOO_MANY_ERRORS"
    assert [item.id for item in result.diagnostics[:-1]] == ["E_TERSE_KIND_UNKNOWN"] * 50


def test_every_fixable_problem_is_reported_in_one_pass_and_a_bad_name_does_not_cascade():
    result = compile_plan(b"project p\nbad_name task 5d\nb tsak 5d\nc task 5d after bad_name\nd task x\n")
    assert [item.id for item in result.diagnostics] == ["E_TERSE_NAME_INVALID", "E_TERSE_KIND_UNKNOWN", "E_TERSE_REFERENCE_UNKNOWN", "E_TERSE_AMOUNT_INVALID"]
    # `bad_name` is not a slug so it can never be a reference target; but a failed line's slug name still registers
    result = compile_plan(b"project p\nb tsak 5d\nc task 5d after b\n")
    assert [item.id for item in result.diagnostics] == ["E_TERSE_KIND_UNKNOWN"]


def test_diagnostics_are_ordered_by_line_then_column():
    result = compile_plan(b"project p\na task 5d after zzz\nb tsak 1d\nc task 2\n")
    positions = [(item.range.line, item.range.column) for item in result.diagnostics]
    assert positions == sorted(positions)


def test_nearest_name_breaks_ties_by_declaration_order_and_stays_silent_when_far():
    assert nearest("tsak", ("task", "gate", "group")) == "task"
    assert nearest("gte", ("task", "gate", "group")) == "gate"
    assert nearest("zzzzzz", ("task", "gate", "group")) is None
    assert nearest("ab", ("ac", "ad")) == "ac"


def test_suggested_names_are_slugs():
    assert suggest_name("Build_Phase") == "build-phase" and suggest_name("9lives") == "n-9lives" and suggest_name("___") == "name"
