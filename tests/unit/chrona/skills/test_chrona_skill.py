"""Shape, link, example and command guards for the chrona agent skill (#142, D1.3)."""
from __future__ import annotations

import json
import re
import shutil

import pytest
import yaml

from chrona.usecases.preset_library import list_builtin_presets
from chrona.usecases.skill_library import copy_skill
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

    assert (status, json.loads(out)) == (0, {"status": "ok", "diagnostics": []})


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

    assert {command.path.name for command in commands} == {"SKILL.md", "typed-fields.md"}  # the page runs its own (#1683)
    assert any(command.tokens[:2] == ("chrona", "init") for command in commands)
    assert any("launch.yaml" in token for command in commands for token in command.tokens)
    assert all(command.skip_reason is None for command in commands), "a skill command must be run, not skipped"


def _launch_with(tmp_path, schedule: str):
    path = tmp_path / "launch.yaml"
    path.write_text(EXAMPLE.read_text(encoding="utf-8").replace("schedule: {mode: fixed-point, at: 2026-12-14}", schedule), encoding="utf-8")
    return path


def test_the_derived_gate_the_skill_teaches_places_where_it_says_and_a_floor_and_a_cap_do_what_it_says(monkeypatch, capsys, tmp_path):
    rules = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    model = (SKILL_DIR / "references" / "authoring-model.md").read_text(encoding="utf-8")
    assert "Never compute a date by hand" in rules and "`scheduled-point`" in rules and "five modes" in rules
    assert "2026-12-01" in model and "min: 2026-12-07" in model and "E_CONTRADICTORY_BOUNDS" in model

    def launch(schedule):
        status, out, _err = run_cli(monkeypatch, capsys, "schedule", str(_launch_with(tmp_path, schedule)))
        return status, json.loads(out)

    status, result = launch("schedule: {mode: scheduled-point}")
    assert status == 0 and result["placements"]["launch"] == {"at": "2026-12-01"}
    status, result = launch("schedule: {mode: scheduled-point, constraints: {at: {min: 2026-12-07}}}")
    assert status == 0 and result["placements"]["launch"] == {"at": "2026-12-07"}
    status, result = launch("schedule: {mode: scheduled-point, constraints: {at: {max: 2026-11-30}}}")
    assert status == 1 and [item["code"] for item in result["diagnostics"]] == ["E_CONTRADICTORY_BOUNDS"]
    status, result = launch("schedule: {mode: fixed-point, at: 2026-11-30}")
    assert status == 1 and [item["code"] for item in result["diagnostics"]] == ["E_FIXED_TARGET_VIOLATION"]
    assert "2026-12-01" in result["diagnostics"][0]["message"]  # the rejection names the date to write


def _named_paths(text: str) -> set[str]:
    return set(re.findall(r"(?<![\w/.-])((?:examples|references|docs|skills)/[\w./-]*[\w])", text))


def test_every_path_the_skill_names_exists_in_a_copied_skill(tmp_path):
    copied = copy_skill(tmp_path / "copy")
    named = {path for document in skill_documents() for path in _named_paths(document.read_text(encoding="utf-8"))}

    assert {"examples/launch.yaml", "examples/actual.yaml"} <= named
    assert [path for path in sorted(named) if not (copied / path).exists()] == []


def test_the_update_loop_runs_on_the_shipped_files_from_inside_a_copy(tmp_path, monkeypatch, capsys):
    copied = copy_skill(tmp_path / "copy")
    monkeypatch.chdir(copied)
    plan = copied / "plan.yaml"
    plan.write_text((copied / "examples" / "launch.yaml").read_text(encoding="utf-8").replace(
        "to: {object: build, endpoint: start}\n    lag: 0d", "to: {object: build, endpoint: start}\n    lag: 3d"), encoding="utf-8")
    argv = ("render", "plan.yaml", "--actual", "examples/actual.yaml", "--snapshot", "examples/launch.yaml",
            "--preset", "target-b", "--output", "update.svg")

    status, out, _err = run_cli(monkeypatch, capsys, *argv)

    assert status == 0 and json.loads(out)["status"] == "ok"
    assert 'data-purpose="snapshot"' in (copied / "update.svg").read_text(encoding="utf-8")


def test_typed_fields_fences_equal_their_example_files_and_the_example_runs(tmp_path, monkeypatch, capsys):
    """#1683: the typed-fields page shows each example file verbatim (fence info `yaml PATH`); the files run."""
    page = SKILL_DIR / "references" / "typed-fields.md"
    shown = dict(re.findall(r"^```yaml (examples/typed-fields/\S+)\n(.*?)^```", page.read_text(encoding="utf-8"),
                            flags=re.DOTALL | re.MULTILINE))

    assert set(shown) == {"examples/typed-fields/team.yaml", "examples/typed-fields/plan.yaml",
                          "examples/typed-fields/risk-view.yaml",
                          "examples/typed-fields/style.yaml", "examples/typed-fields/executive-scheme.yaml",
                          "examples/typed-fields/executive-theme.yaml"}
    for path, body in shown.items():
        assert body == (SKILL_DIR / path).read_text(encoding="utf-8"), path
    plan = str(SKILL_DIR / "examples" / "typed-fields" / "plan.yaml")
    status, out, _err = run_cli(monkeypatch, capsys, "validate", plan)
    assert (status, json.loads(out)) == (0, {"status": "ok", "diagnostics": []})
    examples = SKILL_DIR / "examples" / "typed-fields"
    output = tmp_path / "typed.svg"
    status, out, _err = run_cli(monkeypatch, capsys, "render", plan, "--preset", "wallboard-dark", "--view",
                                str(examples / "risk-view.yaml"), "--output", str(output))
    assert status == 0 and json.loads(out)["status"] == "ok"
    painted = output.read_text(encoding="utf-8")
    assert len(set(re.findall(r'fill="(#[0-9A-F]{6})"', painted))) >= 4
    # #1726: the guide example shows axis labels and a legend naming the values
    assert "Nov 2026" in painted and all(f">{value}<" in painted for value in ("low", "medium", "high"))
    styled = tmp_path / "styled.svg"
    status, out, _err = run_cli(monkeypatch, capsys, "render", plan, "--preset", "wallboard-dark", "--style",
                                str(examples / "style.yaml"), "--output", str(styled))
    assert status == 0 and json.loads(out)["status"] == "ok"
    assert "Platform risk: low" in styled.read_text(encoding="utf-8")


def test_typed_fields_colour_recipe_works_on_executive_light_and_target_b(tmp_path, monkeypatch, capsys):
    """#1756 row 3: user Scheme + derived Theme add the `series` scale; heading title and subtitle render."""
    examples = SKILL_DIR / "examples" / "typed-fields"
    plan, view = str(examples / "plan.yaml"), str(examples / "risk-view.yaml")
    for preset, stem in (("executive-light", "executive"), ("target-b", "target-b")):
        bare = tmp_path / f"{stem}-bare.svg"
        status, out, _err = run_cli(monkeypatch, capsys, "render", plan, "--preset", preset, "--view", view, "--output", str(bare))
        assert status == 1 and json.loads(out)["diagnostics"][0]["code"] == "E_PRESENTATION_SCALE_MAPPING"
        # the derived Theme's `extends.path` is relative to the Theme file, so the copied preset sits beside it
        status, _out, _err = run_cli(monkeypatch, capsys, "preset", "copy", preset, "--output", str(tmp_path / "looks" / preset))
        assert status == 0
        for name in ("theme", "scheme"):
            shutil.copy(examples / f"{stem}-{name}.yaml", tmp_path / f"{stem}-{name}.yaml")
        output = tmp_path / f"{stem}.svg"
        status, out, _err = run_cli(monkeypatch, capsys, "render", plan, "--preset", preset, "--view", view, "--theme",
                                    str(tmp_path / f"{stem}-theme.yaml"), "--scheme", str(tmp_path / f"{stem}-scheme.yaml"),
                                    "--output", str(output))
        assert status == 0 and json.loads(out)["status"] == "ok", out
        painted = output.read_text(encoding="utf-8")
        assert all(colour in painted.upper() for colour in ("#2E7D5B", "#B7791F", "#B91C1C"))
        assert all(f">{value}<" in painted for value in ("low", "medium", "high"))
        assert "Typed fields demo: delivery risk" in painted and "Bars coloured by risk" in painted


def test_style_example_failures_name_what_to_change(tmp_path, monkeypatch, capsys):
    """#1726: target-b has no `series` scale mapping and a rule without `semantic: planned` hits labels."""
    examples = SKILL_DIR / "examples" / "typed-fields"
    plan, style = str(examples / "plan.yaml"), examples / "style.yaml"
    status, out, _err = run_cli(monkeypatch, capsys, "render", plan, "--preset", "target-b", "--style", str(style),
                                "--output", str(tmp_path / "tb.svg"))
    message = json.loads(out)["diagnostics"][0]["message"]
    assert status == 1 and "no scale->slot mapping" in message and "colorScales.series.slots" in message
    loose = tmp_path / "loose.yaml"
    loose.write_text(style.read_text(encoding="utf-8").replace("semantic: planned, ", ""), encoding="utf-8")
    status, out, _err = run_cli(monkeypatch, capsys, "render", plan, "--preset", "wallboard-dark", "--style",
                                str(loose), "--output", str(tmp_path / "loose.svg"))
    assert status == 1 and json.loads(out)["diagnostics"][0]["code"] == "E_STYLE_TARGET"
