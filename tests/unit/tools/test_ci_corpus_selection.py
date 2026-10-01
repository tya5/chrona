"""The `corpus` marker keeps PR shards fast and the full matrix complete (#657).

Corpus-marked tests are deselected from the PR shards and must run on the schedule, on
manual dispatch, after each push to `main`, and, for the one whole-corpus reproduction test,
on every code PR. This test reads the workflow so neither side can drift silently.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

import yaml

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
WORKFLOW = yaml.safe_load((ROOT / ".github/workflows/conformance.yml").read_text(encoding="utf-8"))


def _pytest_commands(job: str) -> list[str]:
    return [step["run"] for step in WORKFLOW["jobs"][job]["steps"] if "pytest " in step.get("run", "")]


def test_the_corpus_marker_is_registered():
    markers = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["pytest"]["ini_options"]["markers"]
    assert any(item.split(":", 1)[0].strip() == "corpus" for item in markers)


def test_pr_shards_deselect_corpus_tests():
    commands = _pytest_commands("pr-pytest")
    assert len(commands) == 1
    assert '-m "not corpus"' in commands[0]
    assert "--splits 3 --group ${{ matrix.shard }}" in commands[0]
    assert "--dist worksteal" in commands[0]


def test_the_full_matrix_runs_every_test_including_corpus():
    commands = _pytest_commands("full-matrix")
    assert commands, "the full matrix must run pytest"
    for command in commands:
        assert " -m " not in f" {command} " and "--deselect" not in command, command
    assert not (ROOT / "pytest.ini").exists(), "a root pytest.ini could override the marker selection"


def test_the_whole_corpus_reproduction_still_runs_on_every_code_pr():
    commands = _pytest_commands("reproduction-newest-python")
    assert any("test_declared_examples_reproduce_by_public_cli" in command and " -m " not in f" {command} "
               for command in commands)
    job = WORKFLOW["jobs"]["reproduction-newest-python"]
    assert "needs.classify-pr.outputs.path == 'code'" in job["if"]


def test_the_options_table_has_no_marker_expression():
    options = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["pytest"]["ini_options"]
    assert "-m" not in str(options.get("addopts", "")).split(), "addopts must not deselect corpus tests everywhere"

# throwaway sample 5 for the shard-time measurement of issue 721; do not merge
