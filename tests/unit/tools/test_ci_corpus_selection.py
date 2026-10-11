"""The `corpus` marker keeps PR shards fast and the full matrix complete (#657).

Corpus-marked tests are deselected from the PR shards and must run on the schedule, on
manual dispatch, after each push to `main`, and, for the one whole-corpus reproduction test,
on every code PR. This test reads the workflow so neither side can drift silently.
"""
from __future__ import annotations

import tomllib
import shlex
from pathlib import Path

import pytest
import yaml

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
WORKFLOW = yaml.safe_load((ROOT / ".github/workflows/conformance.yml").read_text(encoding="utf-8"))


def _pytest_commands(job: str) -> list[str]:
    return [step["run"] for step in WORKFLOW["jobs"][job]["steps"] if "pytest " in step.get("run", "")]


def _pytest_arguments(command: str) -> tuple[tuple[str, ...], ...]:
    """Separate Python's module launcher from options passed to pytest."""
    invocations = []
    for line in command.splitlines():
        lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        tokens = tuple(lexer)
        for index, token in enumerate(tokens):
            if Path(token).name in {"pytest", "pytest.exe"}:
                end = next((position for position in range(index + 1, len(tokens))
                            if tokens[position] in {";", "&&", "||", "|", "&"}), len(tokens))
                invocations.append(tuple(tokens[index + 1:end]))
    return tuple(invocations)


def _selects_subset(arguments: tuple[str, ...]) -> bool:
    return any(option.startswith(("-m", "-k", "--markexpr", "--keyword", "--deselect"))
               for option in arguments)


@pytest.mark.parametrize("command", [
    "pytest -n 4", "python -m pytest -n 4", ".venv/bin/python -m pytest tests/unit -n 4",
    "python -m pytest --ignore=tests/unit -n 4 || remainder_status=$?",
    "python -m pytest tests/unit\npython -m pytest --ignore=tests/unit",
    "pytest -n 4 && python -m pytest -n 4",
    "python -m pytest -n 4; python -m pytest -n 4",
])
def test_launcher_is_not_a_pytest_marker_selection(command):
    arguments = _pytest_arguments(command)
    assert arguments
    assert not any(_selects_subset(args) for args in arguments)


@pytest.mark.parametrize("option", [
    '-m "not corpus"', "-mnot_corpus", '--markexpr="not corpus"',
    "--deselect=tests/a.py::test_corpus", "--deselect tests/a.py::test_corpus",
    "-k fast", "--keyword=fast",
])
@pytest.mark.parametrize("launcher", ["pytest", "python -m pytest"])
def test_real_pytest_filters_are_still_rejected(launcher, option):
    arguments = _pytest_arguments(f"{launcher} {option}")
    assert len(arguments) == 1
    assert _selects_subset(arguments[0])


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
        arguments = _pytest_arguments(command)
        assert arguments, command
        assert not any(_selects_subset(args) for args in arguments), command
    assert not (ROOT / "pytest.ini").exists(), "a root pytest.ini could override the marker selection"


def test_the_whole_corpus_reproduction_still_runs_on_every_code_pr():
    commands = _pytest_commands("reproduction-newest-python")
    assert any("test_declared_examples_reproduce_by_public_cli" in command
               and not any(_selects_subset(args) for args in _pytest_arguments(command))
               for command in commands)
    job = WORKFLOW["jobs"]["reproduction-newest-python"]
    assert "needs.classify-pr.outputs.path == 'code'" in job["if"]


def test_the_options_table_has_no_marker_expression():
    options = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["pytest"]["ini_options"]
    assert "-m" not in str(options.get("addopts", "")).split(), "addopts must not deselect corpus tests everywhere"
