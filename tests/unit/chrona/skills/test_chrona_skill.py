"""Shape, link, example and command guards for the chrona agent skill (#142, D1.3)."""
from __future__ import annotations

import json
import re

import pytest
import yaml

from chrona.usecases.preset_library import list_builtin_presets
from tests.support.skill_files import EXAMPLE, ROOT, SKILL_DIR, fences, run_cli, skill_documents
from tools.check_documented_commands import discover

SKILL = SKILL_DIR / "SKILL.md"
FORBIDDEN = ("chrona mcp", "chrona compile", "--system-fonts", "--allow-missing-content-identity")


def _front_matter() -> dict:
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    block = text.split("\n---\n", 1)[0].removeprefix("---\n")
    return yaml.safe_load(block)


def test_front_matter_names_the_directory_and_stays_within_the_host_limit():
    front = _front_matter()

    assert set(front) == {"name", "description"}
    assert front["name"] == SKILL_DIR.name == "chrona"
    assert 0 < len(front["description"]) <= 1024
    for trigger in ("Gantt", "timeline", "dependencies", "working days", "plan versus actual"):
        assert trigger.lower() in front["description"].lower()


def test_skill_file_is_at_most_two_hundred_lines():
    assert len(SKILL.read_text(encoding="utf-8").splitlines()) <= 200


@pytest.mark.parametrize("document", skill_documents(), ids=lambda path: path.relative_to(SKILL_DIR).as_posix())
def test_every_relative_link_resolves_and_nothing_forbidden_is_taught(document):
    text = document.read_text(encoding="utf-8")

    for target in re.findall(r"\]\(([^)\s]+)\)", text):
        if re.match(r"[a-z][a-z0-9+.-]*:", target):
            continue
        assert (document.parent / target.partition("#")[0]).resolve().exists(), target
    for phrase in FORBIDDEN:
        assert phrase not in text


def test_yaml_fences_equal_the_example_file():
    example = EXAMPLE.read_text(encoding="utf-8")
    found = [body for document in skill_documents() for body in fences(document, "yaml")]

    assert found, "the worked example must be shown"
    assert all(body == example for body in found)


def test_schedule_fence_equals_what_chrona_schedule_prints(monkeypatch, capsys):
    status, out, _err = run_cli(monkeypatch, capsys, "schedule", str(EXAMPLE))
    shown = [json.loads(body) for document in skill_documents() for body in fences(document, "json")
             if "placements" not in body and "diagnostics" not in body]

    assert status == 0
    assert shown == [json.loads(out)["placements"]]


def test_the_example_validates_cleanly(monkeypatch, capsys):
    status, out, _err = run_cli(monkeypatch, capsys, "validate", str(EXAMPLE))

    assert (status, json.loads(out)) == (0, [])


def test_preset_ids_named_by_the_skill_are_builtin_ids():
    builtin = {entry["id"] for entry in list_builtin_presets()}
    named: set[str] = set()
    for document in skill_documents():
        text = document.read_text(encoding="utf-8")
        named.update(re.findall(r"--preset ([a-z][a-z0-9-]*)(?=\s|$)", text))
        named.update(re.findall(r"preset copy ([a-z][a-z0-9-]*)(?=\s|$)", text))

    assert named and named <= builtin


def test_the_doc_check_tool_discovers_and_will_run_every_skill_command():
    commands = [command for command in discover(ROOT) if command.path.parts[0] == "skills"]

    assert {command.path.name for command in commands} == {"SKILL.md"}
    assert any(command.tokens[:2] == ("chrona", "init") for command in commands)
    assert any("launch.yaml" in token for command in commands for token in command.tokens)
    assert all(command.skip_reason is None for command in commands), "a skill command must be run, not skipped"
