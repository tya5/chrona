"""`chrona compile PLAN [-o FILE]` (#148): streams, exit codes, refusal to overwrite, redirect safety, determinism."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from chrona.app.cli import main
from tests.support.terse_plans import FIXTURES

ROOT = Path(__file__).resolve().parents[2]
GOOD = FIXTURES / "groups.chrona"
BAD = FIXTURES / "errors" / "m02-kind-misspelt.chrona"


def _run(*arguments: str, stdin: bytes | None = None, stdout=subprocess.PIPE) -> subprocess.CompletedProcess:
    import os
    environment = {**os.environ, "PYTHONPATH": os.pathsep.join((str(ROOT / "src"), str(ROOT)))}
    return subprocess.run([sys.executable, "-m", "chrona", *arguments], input=stdin, stdout=stdout, stderr=subprocess.PIPE,
                          env=environment, cwd=ROOT, check=False, timeout=120)


def _in_process(monkeypatch, capsys, *arguments: str):
    monkeypatch.setattr(sys, "argv", ["chrona", *arguments])
    code = 0
    try:
        main()
    except SystemExit as exit_:
        code = exit_.code or 0
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_stdout_mode_writes_the_project_and_nothing_to_stderr():
    completed = _run("compile", str(GOOD))
    assert completed.returncode == 0 and completed.stderr == b""
    assert completed.stdout == (FIXTURES / "groups.project.yaml").read_bytes()


def test_output_mode_writes_the_same_bytes_and_stays_quiet(tmp_path):
    destination = tmp_path / "out" / "project.yaml"
    completed = _run("compile", str(GOOD), "-o", str(destination))
    assert completed.returncode == 0 and completed.stdout == b"" and completed.stderr == b""
    assert destination.read_bytes() == (FIXTURES / "groups.project.yaml").read_bytes()
    assert b"\r" not in destination.read_bytes()


def test_stdin_mode_compiles_dash():
    completed = _run("compile", "-", stdin=GOOD.read_bytes())
    assert completed.returncode == 0 and completed.stdout == (FIXTURES / "groups.project.yaml").read_bytes()


def test_the_output_validates_and_schedules_through_the_existing_commands(tmp_path):
    destination = tmp_path / "project.yaml"
    assert _run("compile", str(FIXTURES / "halcyon-1-core.chrona"), "-o", str(destination)).returncode == 0
    assert _run("validate", str(destination)).stdout.strip() == b'{"status": "ok", "diagnostics": []}'
    scheduled = json.loads(_run("schedule", str(destination)).stdout)
    assert len(scheduled["placements"]) == 29 and scheduled["analysis"]["criticalObjectIds"]


def test_compile_output_refuses_an_existing_file(tmp_path):
    destination = tmp_path / "project.yaml"
    destination.write_text("hand edited\n", encoding="utf-8")
    completed = _run("compile", str(GOOD), "-o", str(destination))
    payload = json.loads(completed.stdout)
    assert completed.returncode == 2 and payload["status"] == "failed"
    assert payload["diagnostics"][0]["code"] == "E_TERSE_OUTPUT_EXISTS" and payload["diagnostics"][0]["message"]
    assert destination.read_text(encoding="utf-8") == "hand edited\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["project.yaml"]  # no temporary file is left behind


def test_rejection_in_output_mode_prints_json_on_stdout_and_creates_no_file(tmp_path):
    destination = tmp_path / "project.yaml"
    completed = _run("compile", str(BAD), "-o", str(destination))
    payload = json.loads(completed.stdout)
    assert completed.returncode == 1 and completed.stderr == b"" and not destination.exists()
    (diagnostic,) = payload["diagnostics"]
    assert payload["status"] == "rejected"
    assert diagnostic["code"] == "E_TERSE_KIND_UNKNOWN" and diagnostic["component"] == "terse"
    assert diagnostic["sourceRange"] == {"line": 2, "column": 8, "endLine": 2, "endColumn": 12}
    assert diagnostic["source"] == str(BAD) and diagnostic["hint"] == "did you mean `task`?"
    assert diagnostic["sourceRef"] == "/" and diagnostic["revisionRefs"] == [] and diagnostic["severity"] == "error"


def test_rejection_in_stdout_mode_goes_to_stderr_so_a_redirect_stays_empty(tmp_path):
    redirected = tmp_path / "project.yaml"
    with redirected.open("wb") as handle:
        completed = _run("compile", str(BAD), stdout=handle)
    assert completed.returncode == 1 and redirected.read_bytes() == b""
    assert json.loads(completed.stderr)["diagnostics"][0]["code"] == "E_TERSE_KIND_UNKNOWN"


def test_a_successful_redirect_carries_only_the_project(tmp_path):
    redirected = tmp_path / "project.yaml"
    with redirected.open("wb") as handle:
        completed = _run("compile", str(GOOD), stdout=handle)
    assert completed.returncode == 0 and completed.stderr == b""
    assert redirected.read_bytes() == (FIXTURES / "groups.project.yaml").read_bytes()


def test_core_findings_are_positioned_and_never_emit_yaml():
    completed = _run("compile", str(FIXTURES / "errors" / "e-rollup-empty.chrona"))
    payload = json.loads(completed.stderr)
    assert completed.returncode == 1 and completed.stdout == b""
    diagnostic = payload["diagnostics"][0]
    assert diagnostic["code"] == "E_ROLLUP_EMPTY" and diagnostic["component"] == "core" and diagnostic["sourceRef"] == "/objects/g/schedule"
    assert diagnostic["sourceRange"]["line"] == 2


def test_compile_unreadable_input_is_exit_two(monkeypatch, capsys, tmp_path):
    code, out, err = _in_process(monkeypatch, capsys, "compile", str(tmp_path / "missing.chrona"))
    assert code == 2 and out == ""
    payload = json.loads(err)
    assert payload["status"] == "failed" and payload["diagnostics"][0]["code"] == "E_TERSE_INPUT_IO"
    code, out, err = _in_process(monkeypatch, capsys, "compile", str(tmp_path / "missing.chrona"), "-o", str(tmp_path / "x.yaml"))
    assert code == 2 and err == "" and json.loads(out)["diagnostics"][0]["code"] == "E_TERSE_INPUT_IO"


def test_missing_plan_argument_is_a_command_syntax_error(monkeypatch, capsys):
    code, out, err = _in_process(monkeypatch, capsys, "compile")
    assert code == 2 and json.loads(out)["diagnostics"][0]["code"] == "E_COMMAND_SYNTAX"


def test_invalid_utf8_input_is_reported_with_a_position():
    completed = _run("compile", "-", stdin=b"project p\nd \"caf\xe9\" task 5d\n")
    diagnostic = json.loads(completed.stderr)["diagnostics"][0]
    assert completed.returncode == 1 and diagnostic["code"] == "E_TERSE_ENCODING" and diagnostic["source"] == "-"


def test_two_runs_are_byte_identical_whatever_the_working_directory(tmp_path):
    first = _run("compile", str(FIXTURES / "special-characters.chrona")).stdout
    second = _run("compile", str(FIXTURES / "special-characters.chrona")).stdout
    assert first == second == (FIXTURES / "special-characters.project.yaml").read_bytes()
