"""CI consumes the documented fresh-environment recipe verbatim."""
from pathlib import Path
import subprocess
import sys

import pytest

from tools import run_contributor_setup as setup


def test_documented_recipe_installs_the_local_required_provider():
    root = Path(__file__).resolve().parents[3]
    commands = setup.setup_commands((root / "CONTRIBUTING.md").read_text(encoding="utf-8"))
    assert commands == (("python", "-m", "venv", ".venv"),
                        (".venv/bin/python", "-m", "pip", "install", "-e", ".[dev,render]",
                         "-e", "packages/chrona-fonts-noto-cjk"))


def test_release_ci_runs_units_in_the_documented_environment_without_repeating_them():
    from chrona.resources import safe_load

    root = Path(__file__).resolve().parents[3]
    workflow = safe_load((root / ".github/workflows/conformance.yml").read_bytes())
    steps = workflow["jobs"]["full-matrix"]["steps"]
    recipe = next(step for step in steps if step.get("name") == "Verify literal contributor setup in a fresh venv")
    assert recipe["if"] == "${{ matrix.os == 'ubuntu-latest' }}"
    assert recipe["run"] == "python tools/run_contributor_setup.py"
    pytest_step = next(step for step in steps if step.get("id") == "pytest")
    assert ".venv/bin/python -m pytest tests/unit -n 4" in pytest_step["run"]
    assert "python -m pytest --ignore=tests/unit -n 4" in pytest_step["run"]
    assert pytest_step["shell"] == "bash"


def test_executes_the_document_commands_and_propagates_errors(tmp_path, monkeypatch):
    (tmp_path / "CONTRIBUTING.md").write_text(
        "<!-- contributor-setup -->\n```bash\npython -m venv .venv\n.venv/bin/python -m pip install x\n```",
        encoding="utf-8")
    calls = []

    def execute(argv, **kwargs):
        calls.append((argv, kwargs))
        if len(calls) == 2:
            raise subprocess.CalledProcessError(1, argv)

    monkeypatch.setattr(setup.subprocess, "run", execute)
    with pytest.raises(subprocess.CalledProcessError):
        setup.run_setup(tmp_path)
    assert calls == [((sys.executable, "-m", "venv", ".venv"), {"cwd": tmp_path, "check": True}),
                     ((".venv/bin/python", "-m", "pip", "install", "x"), {"cwd": tmp_path, "check": True})]


def test_refuses_a_nonfresh_environment(tmp_path):
    (tmp_path / ".venv").mkdir()
    with pytest.raises(ValueError, match="fresh checkout"):
        setup.run_setup(tmp_path)


@pytest.mark.parametrize("document", ["", "<!-- contributor-setup -->\n```bash\n\n```",
                                       ("<!-- contributor-setup -->\n```bash\npython x\n```\n") * 2])
def test_refuses_missing_empty_or_ambiguous_recipes(document):
    with pytest.raises(ValueError):
        setup.setup_commands(document)
