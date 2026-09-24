import argparse

import pytest

from tools.check_documented_commands import DocumentedCommand, DocumentedCommandError, render_reference, validate, validate_surface


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
