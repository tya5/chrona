"""The first things a new user sees of the CLI: --version, bare `chrona`, --help, success results, the reference (#1304)."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys

from chrona.app.cli import COMMAND_GROUPS, _parser
from tools.check_documented_commands import _options, _subparsers, render_reference

ROOT = Path(__file__).resolve().parents[2]


def _chrona(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-c", "from chrona.app.cli import main; main()", *args], cwd=cwd,
                          capture_output=True, text=True, timeout=120)


def _walk(parser, path=()):
    for name, child in _subparsers(parser).items():
        yield (*path, name), child
        yield from _walk(child, (*path, name))


def test_version_prints_the_package_project_format_and_visual_profiles(tmp_path):
    result = _chrona(tmp_path, "--version")
    lines = result.stdout.splitlines()

    assert result.returncode == 0 and result.stderr == ""
    assert re.fullmatch(r"chrona \S+", lines[0])
    assert lines[1] == "project format: timeline/v0.7"
    assert lines[2].startswith("visual profiles: ") and "v0.7-svg" in lines[2]


def test_a_bare_chrona_prints_usage_to_stderr_and_exits_2_without_json(tmp_path):
    result = _chrona(tmp_path)

    assert result.returncode == 2 and result.stdout == ""
    assert result.stderr.startswith("usage: chrona") and "Author a plan" in result.stderr
    assert not result.stderr.lstrip().startswith("{")


def test_help_groups_every_command_by_task_and_leaves_none_ungrouped():
    parser = _parser()
    grouped = [name for _title, names in COMMAND_GROUPS for name in names]
    commands = set(_subparsers(parser))

    assert len(grouped) == len(set(grouped)) and set(grouped) == commands
    assert "More commands" not in parser.format_help()


def test_no_help_text_names_a_milestone_or_stage():
    parser = _parser()
    for path, command in [((), parser), *_walk(parser)]:
        text = command.format_help()
        assert not re.search(r"\bM\d+\b|Stage-\d", text), path


def test_every_command_and_flag_in_the_reference_has_a_description():
    parser = _parser()
    for path, command in _walk(parser):
        assert command.description, path
        for option, action in _options(command).items():
            if option not in {"-h", "--help"}:
                assert action.help, (path, option)
    for block in render_reference(parser).split("\n## ")[1:]:
        heading, _, body = block.partition("\n\n")
        assert body.split("\n\n")[0].strip() and not body.startswith("`"), heading  # a description precedes the flag list


def test_the_reference_file_is_what_the_generator_writes():
    assert (ROOT / "docs" / "guides" / "cli-reference.md").read_text(encoding="utf-8") == render_reference(_parser())


def test_validate_init_and_preset_copy_print_one_json_object_that_says_what_they_did(tmp_path):
    created = _chrona(tmp_path, "init", "starter")
    report = json.loads(created.stdout)
    assert created.returncode == 0 and report["status"] == "ok" and report["directory"] == "starter"
    assert "project.yaml" in report["created"] and report["created"] == sorted(report["created"])

    validated = _chrona(tmp_path, "validate", "starter/project.yaml")
    assert validated.returncode == 0 and json.loads(validated.stdout) == {"status": "ok", "diagnostics": []}

    copied = _chrona(tmp_path, "preset", "copy", "editorial", "--output", "looks")
    report = json.loads(copied.stdout)
    assert copied.returncode == 0 and report["status"] == "ok" and "preset.yaml" in report["created"]
