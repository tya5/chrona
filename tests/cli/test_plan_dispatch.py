"""`.chrona` plans accepted by `render`, `validate` and `schedule` (#148 slice 3, design 9.2 and 9.3).

The adapter dispatches on the suffix of the project argument and nothing else: `render` goes through a temporary
Project file holding the compiler's bytes (the `--preset <id>` pattern), `validate` and `schedule` load the same
bytes. Every other command still reads YAML. Tests run `main()` in a scratch directory with relative paths, so no
host path is asserted.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

from chrona.app.cli import _is_plan_path, main
from tests.support.terse_plans import FIXTURES

CHARACTERIZATION = Path(__file__).resolve().parents[1] / "fixtures" / "cli_characterization"
MINIMAL = "minimal-starter.chrona"
HALCYON = "halcyon-1-core.chrona"
BAD_PLAN = FIXTURES / "errors" / "m02-kind-misspelt.chrona"

# A gate dated before the predecessor ends, a two-object loop and a bound that the dependencies cannot meet.
GATE_TOO_EARLY = 'project p "P"\na "A" task 2026-10-01..2026-10-20\ng "Gate" gate 2026-10-05 after a\n'
CYCLE = 'project p "P"\na "A" task 3d after b\nb "B" task 3d after a\n'
BOUND_VIOLATED = ('project p "P"\ncalendar standard mon-fri\n'
                  'a "A" task 10wd from 2026-10-01\nb "B" task 3wd end <= 2026-10-05 after a\n')


@pytest.fixture
def scratch(tmp_path, monkeypatch):
    """A scratch working directory holding the fixtures; `tempfile` is redirected into an observable directory."""
    import tempfile
    work = tmp_path / "work"
    work.mkdir()
    temporary = tmp_path / "tmp"
    temporary.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temporary))
    monkeypatch.chdir(work)
    for source in FIXTURES.glob("*.chrona"):
        shutil.copyfile(source, work / source.name)
    shutil.copyfile(BAD_PLAN, work / "bad.chrona")
    shutil.copyfile(CHARACTERIZATION / "starter-actual.yaml", work / "starter-actual.yaml")
    shutil.copytree(CHARACTERIZATION / "halcyon-1", work / "halcyon-1")
    for name, text in (("gate.chrona", GATE_TOO_EARLY), ("cycle.chrona", CYCLE), ("bound.chrona", BOUND_VIOLATED)):
        (work / name).write_text(text, encoding="utf-8", newline="\n")
    return work


def _run(monkeypatch, capsys, *arguments: str) -> tuple[int, str, str]:
    monkeypatch.setattr(sys, "argv", ["chrona", *arguments])
    code = 0
    try:
        main()
    except SystemExit as exit_:
        code = exit_.code if isinstance(exit_.code, int) else (0 if exit_.code is None else 1)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _temporary_entries(work: Path) -> list[str]:
    """What the process left in the redirected temporary directory (a sibling of the working directory)."""
    return sorted(path.name for path in (work.parent / "tmp").iterdir())


# --- the suffix rule --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("path, expected", [
    ("plan.chrona", True), ("dir/plan.chrona", True), ("PLAN.CHRONA", True), ("my.plan.chrona", True),
    (".chrona", False), ("dir/.chrona", False), (".chrona/store.yaml", False), ("plan.chrona.yaml", False),
    ("plan.yaml", False), ("plan", False), ("", False), (None, False),
])
def test_the_suffix_of_the_file_argument_alone_selects_a_plan(path, expected):
    assert _is_plan_path(path) is expected


# --- render: byte identity with compile-then-render -------------------------------------------------------------

# name: (plan, flags, expected exit code). The two rejections are the presentation stage refusing a resource that does not
# fit the project; the plan path must report them exactly as the YAML path does.
RENDERS = {
    "default": (MINIMAL, (), 0),
    "halcyon-default": (HALCYON, (), 0),
    "actual": (MINIMAL, ("--actual", "starter-actual.yaml"), 0),
    "builtin-preset": (MINIMAL, ("--preset", "editorial"), 0),
    "viewport": (MINIMAL, ("--viewport", "900x700"), 0),
    "view-theme-scheme-layout-detail": (MINIMAL, ("--view", "pc/view.yaml", "--theme", "pc/theme.yaml", "--scheme", "pc/scheme.yaml",
                                                  "--layout", "pc/layout.yaml", "--detail", "pc/detail.yaml"), 0),
    "preset-with-view-and-theme": (MINIMAL, ("--preset", "pc/preset.yaml", "--view", "pc/view.yaml", "--theme", "pc/theme.yaml"), 0),
    "halcyon-view-needs-an-actual-set": (HALCYON, ("--view", "halcyon-1/view.yaml"), 1),
    "copied-preset-path": (MINIMAL, ("--preset", "pc/preset.yaml"), 0),
    "copied-preset-path-and-scheme": (MINIMAL, ("--preset", "pc/preset.yaml", "--scheme", "halcyon-1/scheme.yaml"), None),
    "png": (MINIMAL, ("--format", "png"), 0),
    "scene": (MINIMAL, ("--emit-scene", "SCENE"), 0),
    "theme-only-rejected": (MINIMAL, ("--theme", "halcyon-1/theme.yaml"), 1),
    "layout-only-rejected": (MINIMAL, ("--layout", "halcyon-1/layout.yaml"), 1),
}


@pytest.mark.parametrize("case", sorted(RENDERS))
def test_rendering_a_plan_is_byte_identical_to_compile_then_render(case, scratch, monkeypatch, capsys):
    plan, flags, expected = RENDERS[case]
    assert _run(monkeypatch, capsys, "preset", "copy", "editorial", "--output", "pc")[0] == 0
    suffix = "png" if "png" in flags else "svg"

    def outputs(project: str, label: str) -> tuple[tuple[int, str, str], bytes | None, bytes | None]:
        scene = f"{label}-scene.json"
        arguments = tuple(scene if flag == "SCENE" else flag for flag in flags)
        result = _run(monkeypatch, capsys, "render", project, *arguments, "-o", f"{label}.{suffix}")
        picture = scratch / f"{label}.{suffix}"
        scene_path = scratch / scene
        return result, (picture.read_bytes() if picture.exists() else None), (scene_path.read_bytes() if scene_path.exists() else None)

    direct = outputs(plan, "direct")
    assert _run(monkeypatch, capsys, "compile", plan, "-o", "compiled.yaml")[0] == 0
    staged = outputs("compiled.yaml", "staged")
    assert direct == staged
    if expected is not None:
        assert direct[0][0] == expected
    if direct[0][0] == 0:
        assert direct[1] is not None and len(direct[1]) > 100
        assert ("SCENE" not in flags) or direct[2]
    assert _temporary_entries(scratch) == []


def test_a_plan_render_leaves_no_temporary_directory_after_a_failed_render(scratch, monkeypatch, capsys):
    code, out, _err = _run(monkeypatch, capsys, "render", "gate.chrona", "-o", "out.svg")
    assert code == 1 and json.loads(out)["status"] == "rejected"
    assert _temporary_entries(scratch) == [] and not (scratch / "out.svg").exists()
    assert str(scratch.parent / "tmp") not in out


@pytest.mark.parametrize("plan, expected_exit", [(MINIMAL, 0), ("gate.chrona", 1)])
def test_the_temporary_directory_is_cleaned_up_explicitly_not_left_to_the_garbage_collector(plan, expected_exit, scratch, monkeypatch, capsys):
    import tempfile
    cleaned: list[str] = []

    class Recording(tempfile.TemporaryDirectory):
        def cleanup(self):
            cleaned.append(self.name)
            super().cleanup()

    monkeypatch.setattr(tempfile, "TemporaryDirectory", Recording)
    assert _run(monkeypatch, capsys, "render", plan, "-o", "out.svg")[0] == expected_exit
    assert len(cleaned) == 1 and not Path(cleaned[0]).exists()


def test_a_plan_render_failing_in_the_presentation_stage_cleans_up_and_hides_the_temporary_path(scratch, monkeypatch, capsys):
    code, out, _err = _run(monkeypatch, capsys, "render", MINIMAL, "--theme", "nowhere/theme.yaml", "-o", "out.svg")
    assert code != 0 and _temporary_entries(scratch) == []
    assert str(scratch.parent / "tmp") not in out
    assert "chrona-plan-" not in out


# --- validate and schedule ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("plan", [MINIMAL, HALCYON, "groups.chrona"])
@pytest.mark.parametrize("command", ["validate", "schedule"])
def test_validate_and_schedule_of_a_plan_equal_the_same_commands_on_its_compiled_yaml(plan, command, scratch, monkeypatch, capsys):
    assert _run(monkeypatch, capsys, "compile", plan, "-o", "compiled.yaml")[0] == 0
    direct = _run(monkeypatch, capsys, command, plan)
    staged = _run(monkeypatch, capsys, command, "compiled.yaml")
    assert direct[0] == 0 and direct == staged
    if command == "validate":
        assert direct[1] == "{\"status\": \"ok\", \"diagnostics\": []}\n"
    else:
        assert json.loads(direct[1])["placements"]


# --- the compile-error path --------------------------------------------------------------------------------------

@pytest.mark.parametrize("command", [("validate",), ("schedule",), ("render", "-o", "out.svg")])
def test_a_rejected_plan_reports_the_compilers_diagnostics_and_never_partially_renders(command, scratch, monkeypatch, capsys):
    name, *rest = command
    code, out, err = _run(monkeypatch, capsys, name, "bad.chrona", *rest)
    compiled_code, compiled_out, _ = _run(monkeypatch, capsys, "compile", "bad.chrona", "-o", "never.yaml")
    assert (code, err) == (1, "") and code == compiled_code
    payload = json.loads(out)
    assert payload == json.loads(compiled_out)  # the same JSON shape and content as `chrona compile`
    assert payload["status"] == "rejected"
    diagnostic = payload["diagnostics"][0]
    assert diagnostic["code"].startswith("E_TERSE_") and diagnostic["source"] == "bad.chrona"
    assert diagnostic["sourceRange"]["line"] >= 1 and diagnostic["hint"]
    assert not (scratch / "out.svg").exists() and not (scratch / "never.yaml").exists()
    assert _temporary_entries(scratch) == []


@pytest.mark.parametrize("name", ["validate", "schedule", "render"])
def test_a_plan_that_cannot_be_read_fails_with_exit_two(name, scratch, monkeypatch, capsys):
    extra = ("-o", "out.svg") if name == "render" else ()
    code, out, _err = _run(monkeypatch, capsys, name, "absent.chrona", *extra)
    payload = json.loads(out)
    assert code == 2 and payload["status"] == "failed"
    assert payload["diagnostics"][0]["code"] == "E_TERSE_INPUT_IO"


def test_a_plan_with_invalid_utf8_is_a_compile_rejection_not_a_crash(scratch, monkeypatch, capsys):
    (scratch / "latin.chrona").write_bytes(b'project p "caf\xe9"\n')
    code, out, _err = _run(monkeypatch, capsys, "validate", "latin.chrona")
    assert code == 1 and json.loads(out)["diagnostics"][0]["code"] == "E_TERSE_ENCODING"


# --- positioned scheduler errors ---------------------------------------------------------------------------------

# (file, code, line for `schedule`, line for `render`). A cycle is named by the use case `schedule` shares with `validate`
# (#780): at the relation that closes it (line 3, `b ... after a`). `render` still reports the scheduler's own finding,
# at the first object that waits (line 2); making `render` name the cycle too is not part of #780.
POSITIONED = [
    ("gate.chrona", "E_FIXED_TARGET_VIOLATION", 3, 3),
    ("cycle.chrona", "E_UNSUPPORTED_CYCLE", 3, 2),
    ("bound.chrona", "E_CONTRADICTORY_BOUNDS", 4, 4),
]


@pytest.mark.parametrize("command", [("schedule",), ("render", "-o", "out.svg")])
@pytest.mark.parametrize("name, code, schedule_line, render_line", POSITIONED)
def test_scheduler_findings_on_a_plan_carry_the_line_and_a_hint(name, code, schedule_line, render_line, command, scratch, monkeypatch, capsys):
    verb, *rest = command
    line = schedule_line if verb == "schedule" else render_line
    exit_code, out, _err = _run(monkeypatch, capsys, verb, name, *rest)
    payload = json.loads(out)
    assert exit_code == 1 and payload["status"] == "rejected"
    first = payload["diagnostics"][0]
    assert first["code"] == code and first["source"] == name
    assert first["sourceRange"]["line"] == line and first["hint"]
    assert _temporary_entries(scratch) == []
    assert not (scratch / "out.svg").exists()


def test_core_findings_on_a_plan_are_positioned_at_compile_time(scratch, monkeypatch, capsys):
    (scratch / "empty-span.chrona").write_text('project p "P"\na "A" task 2026-10-05..2026-10-05\n', encoding="utf-8", newline="\n")
    (scratch / "empty-group.chrona").write_text('project p "P"\ng "G" group\n', encoding="utf-8", newline="\n")
    for name, code in (("empty-span.chrona", "E_INVALID_SPAN"), ("empty-group.chrona", "E_ROLLUP_EMPTY")):
        exit_code, out, _err = _run(monkeypatch, capsys, "validate", name)
        diagnostic = json.loads(out)["diagnostics"][0]
        assert exit_code == 1 and diagnostic["code"] == code
        assert diagnostic["sourceRange"]["line"] == 2 and diagnostic["hint"]


def test_a_plan_finding_does_not_leak_into_the_next_yaml_command_of_the_same_process(scratch, monkeypatch, capsys):
    assert _run(monkeypatch, capsys, "schedule", "gate.chrona")[0] == 1
    assert _run(monkeypatch, capsys, "compile", "gate.chrona", "-o", "gate.yaml")[0] == 0
    code, out, _err = _run(monkeypatch, capsys, "schedule", "gate.yaml")
    diagnostic = json.loads(out)["diagnostics"][0]
    assert code == 1 and diagnostic["code"] == "E_FIXED_TARGET_VIOLATION"
    assert not {"source", "sourceRange", "hint"} & set(diagnostic)  # a YAML Project keeps its exact legacy shape


# --- where a plan is not accepted --------------------------------------------------------------------------------

def _terse_codes(out: str, err: str) -> list[str]:
    codes = []
    for text in (out, err):
        for line in text.splitlines():
            try:
                payload = json.loads(line)
            except ValueError:
                continue
            if isinstance(payload, dict):
                codes.extend(item["code"] for item in payload.get("diagnostics", []) if item["code"].startswith("E_TERSE_"))
    return codes


NOT_ACCEPTED = {
    "render-review": ("render-review", "--context-reference", MINIMAL, "--snapshot-root", "s", "--store-identity", "i", "-o", "o.svg"),
    "render-review-gallery": ("render-review-gallery", "--context-reference", MINIMAL, "--context-reference", MINIMAL,
                              "--snapshot-root", "s", "--store-identity", "i", "--output-directory", "g"),
    "materialize": ("materialize", MINIMAL, "--slide", "x", "-o", "m"),
    "review": ("review", MINIMAL, MINIMAL, "--snapshot-root", "s", "--store-identity", "i"),
    "baseline-compare": ("baseline-compare", "--baseline-reference", MINIMAL, "--candidate-reference", MINIMAL, "--result", "r.json"),
    "baseline-capture": ("baseline-capture", "--command", MINIMAL, "--result", "r.json"),
    "command-check": ("command-check", "--command", MINIMAL, "--result", "r.json"),
    "command-apply": ("command-apply", "--command", MINIMAL, "--result", "r.json"),
    "actual-intake": ("actual-intake", "--command", MINIMAL, "--result", "r.json"),
    "actual-resolve": ("actual-resolve", "--command", MINIMAL, "--result", "r.json"),
    "render-workspace": ("render-workspace", MINIMAL, "-o", "o.svg"),
    "workspace": ("workspace", "revision", MINIMAL),
    "authoring-command-apply": ("authoring-command-apply", "--workspace", MINIMAL, "--command", MINIMAL, "--result", "r.json"),
    "identity-document": ("identity", "document", MINIMAL),
    "validate-snapshot-reference": ("validate", "--snapshot-reference", MINIMAL, "--snapshot-root", "s", "--store-identity", "i"),
    "schedule-snapshot-reference": ("schedule", "--snapshot-reference", MINIMAL, "--snapshot-root", "s", "--store-identity", "i"),
    "render-actual-set": ("render", "minimal-starter.chrona", "--actual", MINIMAL, "-o", "o.svg"),
    "render-view": ("render", "minimal-starter.chrona", "--view", MINIMAL, "-o", "o.svg"),
}


@pytest.mark.parametrize("name", sorted(NOT_ACCEPTED))
def test_every_other_command_still_reads_yaml_and_never_compiles_a_plan(name, scratch, monkeypatch, capsys):
    code, out, err = _run(monkeypatch, capsys, *NOT_ACCEPTED[name])
    assert code != 0, name
    assert _terse_codes(out, err) == [], (name, out)
    assert not list(scratch.glob("*.svg")) and not list(scratch.glob("r.json"))
    assert _temporary_entries(scratch) == []


def test_the_snapshot_flags_reject_a_raw_plan_argument_without_compiling_it(scratch, monkeypatch, capsys):
    code, out, err = _run(monkeypatch, capsys, "schedule", MINIMAL, "--snapshot-reference", "r.yaml",
                          "--snapshot-root", "s", "--store-identity", "i")
    assert code == 2 and json.loads(out)["diagnostics"][0]["code"] == "E_COMMAND_SYNTAX"
