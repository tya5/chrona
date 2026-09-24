import argparse
from pathlib import Path
import sys

import pytest

from tools.check_documented_commands import (
    DocumentedCommand, DocumentedCommandError, discover, execute, render_reference, validate, validate_surface,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(required=True)
    render = commands.add_parser("render")
    render.add_argument("--format", choices=("svg", "png"))
    icon = commands.add_parser("icon")
    icon_sub = icon.add_subparsers(required=True)
    icon_sub.add_parser("import").add_argument("--output")
    return parser


def test_nested_documented_command_is_validated_against_nested_parser():
    validate(DocumentedCommand(__import__("pathlib").Path("guide.md"), 1, ("chrona", "icon", "import", "--output", "icons.yaml")), _parser())


def test_unknown_documented_option_and_choice_fail():
    with pytest.raises(DocumentedCommandError, match="E_DOCUMENTED_COMMAND_OPTION"):
        validate(DocumentedCommand(__import__("pathlib").Path("guide.md"), 1, ("chrona", "render", "--unknown")), _parser())
    with pytest.raises(DocumentedCommandError, match="E_DOCUMENTED_COMMAND_VALUE"):
        validate(DocumentedCommand(__import__("pathlib").Path("guide.md"), 1, ("chrona", "render", "--format", "pdf")), _parser())


def test_surface_gate_rejects_an_undocumented_public_option():
    parser = _parser()
    command = DocumentedCommand(__import__("pathlib").Path("guide.md"), 1, ("chrona", "render"))
    with pytest.raises(DocumentedCommandError, match="option=chrona render --format"):
        validate_surface((command,), parser)
    assert "chrona icon import --output" in render_reference(parser)


def _document_root(tmp_path: Path, content: str) -> Path:
    (tmp_path / "docs" / "guides").mkdir(parents=True, exist_ok=True)
    (tmp_path / "README.md").write_text(content, encoding="utf-8")
    return tmp_path


def test_discovery_limits_commands_to_fenced_blocks_and_preserves_continuations(tmp_path):
    content = "\n".join(("chrona render --ignored", "", "```console", "$ chrona render --format \\", "svg", "```")) + "\n"
    root = _document_root(tmp_path, content)

    commands = discover(root)

    assert commands == (DocumentedCommand(Path("README.md"), 4, ("chrona", "render", "--format", "svg")),)


def test_skip_marker_is_local_and_requires_a_reason_and_command_block(tmp_path):
    root = _document_root(tmp_path, "<!-- chrona:doc-check skip: needs author asset -->\n```sh\nchrona render project.yaml\n```\n")
    assert discover(root)[0].skip_reason == "needs author asset"

    root = _document_root(tmp_path, "<!-- chrona:doc-check skip: -->\n```sh\nchrona render project.yaml\n```\n")
    with pytest.raises(DocumentedCommandError, match="E_DOCUMENTED_COMMAND_SKIP:README.md:1"):
        discover(root)

    root = _document_root(tmp_path, "<!-- chrona:doc-check skip: needs author asset -->\ntext\n```sh\nchrona render project.yaml\n```\n")
    with pytest.raises(DocumentedCommandError, match="E_DOCUMENTED_COMMAND_SKIP:README.md:1"):
        discover(root)


def test_executor_runs_only_unskipped_commands_in_disposable_workspace(tmp_path):
    root = _document_root(tmp_path, "```sh\nchrona render project.yaml\n```\n<!-- chrona:doc-check skip: requires author state -->\n```sh\nchrona schedule project.yaml\n```\n")
    (root / "examples").mkdir()
    commands = discover(root)
    program = "from pathlib import Path; Path('executed.txt').write_text('ok')"

    execute(commands, root, executable=(sys.executable, "-c", program))

    assert not (root / "executed.txt").exists()


def test_executor_reports_document_anchor_and_output_on_failure(tmp_path):
    root = _document_root(tmp_path, "```sh\nchrona render project.yaml\n```\n")
    commands = discover(root)
    program = "import sys; print('problem', file=sys.stderr); sys.exit(7)"

    with pytest.raises(DocumentedCommandError, match="E_DOCUMENTED_COMMAND_EXECUTION:README.md:2:exit=7") as error:
        execute(commands, root, executable=(sys.executable, "-c", program))

    assert "problem" in str(error.value)
