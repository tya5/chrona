"""Every diagnostic row an agent can see has a message that says something (#782)."""
import functools
import json
from pathlib import Path

import pytest

from chrona.usecases.diagnostic_messages import CURATED_MESSAGES, derived_message, error_message, is_bare
from chrona.usecases.failure_report import StableFailure, diagnostic_record, report_failure
from tools.diagnostic_inventory import discover

ROOT = Path(__file__).resolve().parents[4]
GOLDEN = ROOT / "tests" / "fixtures" / "cli_characterization" / "golden.json"


@functools.lru_cache(maxsize=1)
def _inventory_codes() -> list[str]:
    return sorted({site.code for site in discover(ROOT)})


def test_the_inventory_scan_finds_the_codes_this_test_is_about():
    codes = _inventory_codes()
    assert len(codes) > 400 and "E_BUILTIN_PRESET_UNKNOWN" in codes and "E_PRESENTATION_PRIMITIVE_INVALID" in codes


@pytest.mark.parametrize("bare", ["", "   ", None, "{code}", " {code} ", "{code} source=/", "{code}: ", "{code} source=/objects/a"])
def test_no_code_the_source_can_raise_leaves_a_row_with_a_bare_message(bare):
    for code in _inventory_codes():
        message = bare.format(code=code) if isinstance(bare, str) else bare
        row = diagnostic_record(code, message, "cli")
        assert row["message"].strip(), code
        assert not is_bare(code, row["message"]), code
        assert row["message"] != code, code


def test_every_code_in_the_inventory_survives_the_failure_ladder_with_a_message():
    for code in _inventory_codes():
        if not code.startswith("E_"):
            continue
        row = report_failure(ValueError(code)).diagnostics[0]
        assert row["code"] == code and not is_bare(code, row["message"]), code


def test_a_message_that_names_something_passes_through_unchanged():
    for message in ("unknown builtin preset 'x'", "E_X: no such object 'a'", "cannot read E_X at line 3", "icon=mdi:home source=/"):
        assert diagnostic_record("E_X", message, "cli")["message"] == message


@pytest.mark.parametrize(("message", "bare"), [
    ("", True), ("E_X", True), ("E_X source=/", True), ("E_X: ", True), ("E_X E_X", True),
    ("E_X: unknown id 'a'", False), ("E_X icon=mdi:home source=/", False), ("a", False),
])
def test_what_counts_as_bare(message, bare):
    assert is_bare("E_X", message) is bare


def test_the_derived_sentence_is_honest_and_never_the_code():
    sentence = derived_message("E_THEME_TOKEN_TYPE")
    assert sentence == "theme token type: no further detail is recorded for this code (E_THEME_TOKEN_TYPE)"
    assert error_message("E_THEME_TOKEN_TYPE", "") == sentence


def test_curated_sentences_are_real_codes_with_real_sentences():
    codes = set(_inventory_codes())
    for code, sentence in CURATED_MESSAGES.items():
        assert code in codes, f"{code} is no longer a code the source raises; delete its sentence"
        assert not is_bare(code, sentence) and len(sentence.split()) >= 6, code
        assert error_message(code, code) == sentence


def test_a_stable_failure_with_an_empty_message_gets_one():
    row = report_failure(StableFailure("E_SOMETHING_NEW", "")).diagnostics[0]
    assert row["message"] == derived_message("E_SOMETHING_NEW")


def test_the_cli_golden_has_no_bare_row():
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    rows = 0
    for name, case in golden.items():
        try:
            document = json.loads(case["stdout"])
        except (TypeError, ValueError):
            continue
        for row in document.get("diagnostics", []) if isinstance(document, dict) else []:
            if isinstance(row, dict) and "code" in row:
                rows += 1
                assert not is_bare(row["code"], row.get("message")), (name, row["code"])
    assert rows > 40


def test_core_and_scheduler_never_construct_a_diagnostic_with_an_empty_message():
    """The plan-level findings reach an agent through ``Diagnostic.message`` (review F3); read them, do not edit them."""
    import ast

    constructed = 0
    for package in ("core", "scheduling"):
        for path in sorted((ROOT / "src" / "chrona" / package).rglob("*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "Diagnostic"):
                    continue
                constructed += 1
                message = node.args[1] if len(node.args) > 1 else next(
                    (keyword.value for keyword in node.keywords if keyword.arg == "message"), None)
                assert message is not None, f"{path.name}:{node.lineno} has no message"
                if isinstance(message, ast.Constant):
                    assert isinstance(message.value, str) and message.value.strip(), f"{path.name}:{node.lineno}"
                    code = node.args[0]
                    if isinstance(code, ast.Constant):
                        assert not is_bare(code.value, message.value), f"{path.name}:{node.lineno}"
    assert constructed > 10
