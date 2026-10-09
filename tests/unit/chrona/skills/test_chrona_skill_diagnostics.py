"""Every diagnostic code the skill names exists, and the plan-level ones are provoked (#142, D1.3)."""
from __future__ import annotations

import ast
import copy
import json
import re
from functools import cache
from pathlib import Path

import pytest
import yaml

from chrona.usecases.diagnostic_messages import is_bare
from tests.support.skill_files import EXAMPLE, ROOT, run_cli, skill_documents

TOKEN = re.compile(r"(?<![A-Z0-9_])[EWI]_[A-Z][A-Z0-9_]*")


@cache
def _source_codes() -> frozenset[str]:
    """Every code spelled in a string constant or f-string part of `src/chrona` (docstrings excluded)."""
    found: set[str] = set()
    for path in sorted((ROOT / "src" / "chrona").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = {id(node.value) for node in ast.walk(tree)
                      if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
                found.update(TOKEN.findall(node.value))
    return frozenset(found)


def _skill_codes() -> frozenset[str]:
    return frozenset(token for document in skill_documents() for token in TOKEN.findall(document.read_text(encoding="utf-8")))


def _provoked_only() -> dict[str, str]:
    """Codes the source composes at run time, so no literal exists; each is provoked below."""
    return {
        "E_PROJECT_SCHEMA": "built as 'E_' + kind + '_SCHEMA' in presentation/model/closure.py",
        "W_SCENE_TEXT_INTERSECTION": "the scene finding E_SCENE_TEXT_INTERSECTION re-labelled as a warning",
    }


def test_every_code_the_skill_names_is_constructed_in_the_source_or_provoked_here():
    missing = []
    for code in sorted(_skill_codes()):
        if code.endswith("_"):
            if not any(known.startswith(code) for known in _source_codes()):
                missing.append(code + "*")
        elif code not in _source_codes() and code not in _provoked_only():
            missing.append(code)

    assert missing == []


def _project(mutate=None) -> dict:
    data = copy.deepcopy(yaml.safe_load(EXAMPLE.read_text(encoding="utf-8")))
    if mutate is not None:
        mutate(data)
    return data


def _write(tmp_path: Path, name: str, data) -> str:
    path = tmp_path / name
    path.write_text(yaml.safe_dump(data, sort_keys=False) if not isinstance(data, str) else data, encoding="utf-8")
    return str(path)


def _unknown_relation_target(data):
    data["relations"][0]["to"]["object"] = "nope"


def _unknown_calendar(data):
    data["objects"]["design"]["calendar"] = "nocal"


def _gate_start(data):
    data["relations"][0]["from"]["endpoint"] = "start"


def _backwards_span(data):
    data["objects"]["design"]["schedule"] = {"mode": "fixed-span", "start": "2026-11-09", "end": "2026-11-02"}


def _no_calendar(data):
    del data["objects"]["design"]["calendar"]
    del data["project"]["calendar"]


def _bad_amount(data):
    data["objects"]["design"]["schedule"]["amount"] = "0wd"


def _cycle(data):
    data["relations"].append({"id": "back", "type": "dependency", "from": {"object": "build", "endpoint": "end"},
                              "to": {"object": "design", "endpoint": "start"}, "lag": "0d"})


def _positive_cycle(data):
    data["relations"] += [
        {"id": "late", "type": "dependency", "from": {"object": "design", "endpoint": "start"},
         "to": {"object": "build", "endpoint": "start"}, "lag": "1d"},
        {"id": "back", "type": "dependency", "from": {"object": "build", "endpoint": "start"},
         "to": {"object": "design", "endpoint": "start"}, "lag": "0d"}]


def _early_gate(data):
    data["objects"]["launch"]["schedule"]["at"] = "2026-11-03"


def _impossible_bound(data):
    data["objects"]["build"]["schedule"]["constraints"] = {"end": {"max": "2026-11-27"}}


# (id, mutation, command, expected status, status word, expected codes, JSON stream)
PLAN_CASES = [
    ("reference", _unknown_relation_target, "validate", 1, "rejected", {"E_REFERENCE"}),
    ("calendar-reference", _unknown_calendar, "schedule", 1, "rejected", {"E_REFERENCE"}),
    ("endpoint-mode", _gate_start, "validate", 1, "rejected", {"E_ENDPOINT_MODE_MISMATCH"}),
    ("invalid-span", _backwards_span, "validate", 1, "rejected", {"E_INVALID_SPAN"}),
    ("calendar-required", _no_calendar, "validate", 1, "rejected", {"E_CALENDAR_REQUIRED"}),
    ("schema", _bad_amount, "validate", 1, "rejected", {"E_SCHEMA"}),
    ("schema-schedule", _bad_amount, "schedule", 1, "rejected", {"E_SCHEMA"}),
    ("cycle-validate", _cycle, "validate", 1, "rejected", {"E_UNSUPPORTED_CYCLE"}),
    ("cycle-unsatisfiable", _positive_cycle, "validate", 1, "rejected", {"E_UNSATISFIABLE_DEPENDENCIES"}),
    ("cycle", _cycle, "schedule", 1, "rejected", {"E_UNSUPPORTED_CYCLE"}),
    ("cycle-render", _cycle, "render", 1, "rejected", {"E_UNSUPPORTED_CYCLE"}),
    ("fixed-target", _early_gate, "schedule", 1, "rejected", {"E_FIXED_TARGET_VIOLATION"}),
    ("bounds", _impossible_bound, "schedule", 1, "rejected", {"E_CONTRADICTORY_BOUNDS"}),
    ("project-schema", _bad_amount, "render", 1, "rejected", {"E_PROJECT_SCHEMA"}),
]


@pytest.mark.parametrize("mutate,command,status,word,codes", [case[1:] for case in PLAN_CASES], ids=[case[0] for case in PLAN_CASES])
def test_plan_codes_are_emitted_by_the_command_the_skill_names(tmp_path, monkeypatch, capsys, mutate, command, status, word, codes):
    argv = [command, _write(tmp_path, "plan.yaml", _project(mutate))]
    if command == "render":
        argv += ["--output", str(tmp_path / "plan.svg")]

    result, out, _err = run_cli(monkeypatch, capsys, *argv)

    payload = json.loads(out)
    assert (result, payload["status"]) == (status, word)
    assert codes <= {item["code"] for item in payload["diagnostics"]}
    assert all(not is_bare(item["code"], item["message"]) for item in payload["diagnostics"])


def _command_cases(tmp_path: Path):
    plan = _write(tmp_path, "plan.yaml", _project())
    return [
        ("E_INPUT_IO", 2, ["validate", str(tmp_path / "missing.yaml")]),
        ("E_INPUT_YAML", 2, ["validate", _write(tmp_path, "bad.yaml", "a: [unclosed\n")]),
        ("E_COMMAND_SYNTAX", 2, ["validate"]),
        ("E_RENDER_OUTPUT_EXTENSION", 2, ["render", plan, "--output", str(tmp_path / "plan.jpg")]),
        ("E_RENDER_OUTPUT_FORMAT_MISMATCH", 2, ["render", plan, "--format", "png", "--output", str(tmp_path / "plan.svg")]),
        ("E_BUILTIN_PRESET_UNKNOWN", 1, ["render", plan, "--preset", "nonesuch", "--output", str(tmp_path / "plan.svg")]),
    ]


def test_command_and_input_codes_are_emitted_with_the_exit_status_the_skill_states(tmp_path, monkeypatch, capsys):
    for code, status, argv in _command_cases(tmp_path):
        result, out, _err = run_cli(monkeypatch, capsys, *argv)

        assert result == status, code
        rows = json.loads(out)["diagnostics"]
        assert code in {item["code"] for item in rows}, code
        assert all(not is_bare(item["code"], item["message"]) for item in rows), code


def test_existing_output_directories_are_refused_by_init_preset_copy_and_skill_copy(tmp_path, monkeypatch, capsys):
    for argv, code in ((["init", str(tmp_path / "plan")], "E_INIT_OUTPUT_EXISTS"),
                       (["preset", "copy", "executive-light", "--output", str(tmp_path / "look")], "E_BUILTIN_PRESET_OUTPUT_EXISTS"),
                       (["skill", "copy", "--output", str(tmp_path / "skill")], "E_SKILL_OUTPUT_EXISTS")):
        assert run_cli(monkeypatch, capsys, *argv)[0] == 0
        result, out, _err = run_cli(monkeypatch, capsys, *argv)

        assert result == 1
        rows = json.loads(out)["diagnostics"]
        assert code in {item["code"] for item in rows}
        assert all(not is_bare(item["code"], item["message"]) for item in rows)


def test_a_cramped_viewport_prints_the_warnings_and_note_the_skill_lists_in_stdout_envelope(tmp_path, monkeypatch, capsys):
    plan = _write(tmp_path, "plan.yaml", _project())

    status, out, err = run_cli(monkeypatch, capsys, "render", plan, "--viewport", "300x200", "--output", str(tmp_path / "plan.svg"))

    assert status == 0 and err == ""
    envelope = json.loads(out)
    assert envelope["status"] == "ok" and envelope["diagnostics"] == []
    codes = {item["code"] for item in envelope["warnings"]}
    assert {"W_LAYOUT_LABEL_SUPPRESSED", "W_LAYOUT_LABEL_OVERFLOW", "W_SCENE_TEXT_INTERSECTION",
            "I_LAYOUT_PLOT_LABELS_SUPPRESSED"} <= codes
    assert (tmp_path / "plan.svg").is_file()


def test_every_code_this_file_provokes_is_named_by_the_skill():
    provoked = {code for case in PLAN_CASES for code in case[5]}
    provoked |= {"E_INPUT_IO", "E_INPUT_YAML", "E_COMMAND_SYNTAX", "E_RENDER_OUTPUT_EXTENSION", "E_RENDER_OUTPUT_FORMAT_MISMATCH",
                 "E_BUILTIN_PRESET_UNKNOWN", "E_INIT_OUTPUT_EXISTS", "E_BUILTIN_PRESET_OUTPUT_EXISTS", "E_SKILL_OUTPUT_EXISTS",
                 "W_LAYOUT_LABEL_SUPPRESSED", "W_LAYOUT_LABEL_OVERFLOW", "W_SCENE_TEXT_INTERSECTION", "I_LAYOUT_PLOT_LABELS_SUPPRESSED"}

    assert provoked <= _skill_codes()
