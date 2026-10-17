"""Trial 3 gaps (#1630): quiet PDF stderr, Actual Set validation, import help columns."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from chrona.app.cli import main

ROOT = Path(__file__).resolve().parents[2]
SKILL_EXAMPLES = ROOT / "skills" / "chrona" / "examples"


def test_pdf_render_writes_nothing_to_stderr_and_json_to_stdout(tmp_path):
    output = tmp_path / "plan.pdf"
    done = subprocess.run(
        [sys.executable, "-m", "chrona", "render", str(SKILL_EXAMPLES / "launch.yaml"), "--output", str(output)],
        capture_output=True, text=True, check=False, cwd=tmp_path)
    assert done.returncode == 0, done.stderr
    assert done.stderr == ""
    assert json.loads(done.stdout)["status"] == "ok"
    assert output.read_bytes().startswith(b"%PDF")


def _run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["chrona", *argv])
    try:
        main()
    except SystemExit as raised:
        return raised.code
    return 0


def _validate(monkeypatch, capsys, path):
    code = _run(monkeypatch, "validate", str(path))
    return code, json.loads(capsys.readouterr().out)


def test_validate_accepts_an_actual_set_by_its_kind(monkeypatch, capsys):
    code, payload = _validate(monkeypatch, capsys, SKILL_EXAMPLES / "actual.yaml")
    assert code == 0
    assert payload == {"status": "ok", "diagnostics": [], "resource": "actual-set"}


def test_validate_rejects_a_bad_actual_set_with_its_own_diagnostic(tmp_path, monkeypatch, capsys):
    document = yaml.safe_load((SKILL_EXAMPLES / "actual.yaml").read_text(encoding="utf-8"))
    document["body"]["observations"][0]["actual"].update(start="2026-11-02", finish="2026-11-02")
    path = tmp_path / "actual.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    code, payload = _validate(monkeypatch, capsys, path)
    assert code == 1
    assert [item["code"] for item in payload["diagnostics"]] == ["E_ACTUAL_FINISH_NOT_AFTER_START"]
    assert payload["diagnostics"][0]["sourceRef"] == "/body/observations/0/actual/finish"


def test_validate_names_the_missing_part_of_an_actual_set(tmp_path, monkeypatch, capsys):
    path = tmp_path / "actual.yaml"
    path.write_text("version: chrona/actual-set/v0.3\nkind: actual-set\nid: x\nbody: {}\n", encoding="utf-8")
    code, payload = _validate(monkeypatch, capsys, path)
    assert code == 1
    assert payload["diagnostics"][0]["code"] == "E_SCHEMA"
    assert "observations" in payload["diagnostics"][0]["message"]


def test_import_help_names_the_columns_and_the_guide(monkeypatch, capsys):
    assert _run(monkeypatch, "import", "--help") == 0
    text = " ".join(capsys.readouterr().out.split())
    for column in ("predecessors", "actual_finish", "finish (inclusive)", "docs/guides/csv-import.md"):
        assert column in text
