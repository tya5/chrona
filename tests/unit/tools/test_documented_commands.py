import argparse
from pathlib import Path
import sys

import pytest

from tools import check_documented_commands
from tools.check_documented_commands import DocumentedCommand, DocumentedCommandError, discover, execute, render_reference, validate, validate_surface


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


def test_default_executor_uses_the_current_interpreter_scripts_directory(tmp_path, monkeypatch):
    scripts = tmp_path / "scripts"; scripts.mkdir()
    executable = scripts / ("chrona.exe" if check_documented_commands.os.name == "nt" else "chrona")
    executable.write_text("", encoding="utf-8")
    monkeypatch.setattr(check_documented_commands.sysconfig, "get_path", lambda _name: str(scripts))

    assert check_documented_commands._installed_chrona() == (str(executable),)


def test_skill_documents_are_discovered_and_the_skills_tree_reaches_the_fixture(tmp_path):
    root = _document_root(tmp_path, "text\n")
    skill = root / "skills" / "chrona"
    (skill / "references").mkdir(parents=True)
    (skill / "SKILL.md").write_text("```sh\nchrona validate skills/chrona/examples/p.yaml\n```\n", encoding="utf-8")
    (skill / "references" / "more.md").write_text("```sh\nchrona schedule skills/chrona/examples/p.yaml\n```\n", encoding="utf-8")
    (skill / "notes.md").write_text("```sh\nchrona render ignored.yaml\n```\n", encoding="utf-8")
    (skill / "examples").mkdir()
    (skill / "examples" / "p.yaml").write_text("id: p\n", encoding="utf-8")

    commands = discover(root)

    assert [(command.path.as_posix(), command.tokens[1]) for command in commands] == [
        ("skills/chrona/SKILL.md", "validate"), ("skills/chrona/references/more.md", "schedule")]
    program = "import sys; from pathlib import Path; sys.exit(0 if Path(sys.argv[2]).is_file() else 9)"
    execute(commands, root, executable=(sys.executable, "-c", program))


def test_a_broken_skill_command_fails_the_execute_gate(tmp_path):
    root = _document_root(tmp_path, "text\n")
    (root / "skills" / "chrona").mkdir(parents=True)
    (root / "skills" / "chrona" / "SKILL.md").write_text("```sh\nchrona validate skills/chrona/missing.yaml\n```\n", encoding="utf-8")
    program = "import sys; from pathlib import Path; sys.exit(0 if Path(sys.argv[2]).is_file() else 9)"

    with pytest.raises(DocumentedCommandError, match="E_DOCUMENTED_COMMAND_EXECUTION:" + __import__("re").escape(str(Path("skills/chrona/SKILL.md"))) + ":2:exit=9"):
        execute(discover(root), root, executable=(sys.executable, "-c", program))


# --- the wheel path (#1301) -------------------------------------------------------------------------------------------

CLONE_MARK = "<!-- chrona:doc-check requires: clone the Project is in examples/ -->\n"


def test_a_command_naming_an_unshipped_examples_path_fails_unless_it_is_marked(tmp_path):
    bare = discover(_document_root(tmp_path, "```sh\nchrona render examples/aster-ssd/project.yaml --output t.svg\n```\n"))
    with pytest.raises(DocumentedCommandError, match="E_DOCUMENTED_COMMAND_UNSHIPPED_PATH") as error:
        check_documented_commands.check_shipped(bare)
    assert "README.md:2:examples/aster-ssd/project.yaml" in str(error.value)

    marked = discover(_document_root(tmp_path, CLONE_MARK + "```sh\nchrona render examples/aster-ssd/project.yaml --output t.svg\n```\n"))
    check_documented_commands.check_shipped(marked)
    assert check_documented_commands.requires_clone(marked[0])
    # an option value counts too
    option = discover(_document_root(tmp_path, "```sh\nchrona render p.yaml --view=examples/a/v.yaml\n```\n"))
    with pytest.raises(DocumentedCommandError, match="UNSHIPPED_PATH"):
        check_documented_commands.check_shipped(option)


def test_the_wheel_workspace_is_empty_and_skips_the_clone_commands(tmp_path):
    root = _document_root(tmp_path, CLONE_MARK + "```sh\nchrona render examples/a/project.yaml\n```\n```sh\nchrona init p\n```\n")
    (root / "examples").mkdir()
    (root / "examples" / "seen.txt").write_text("x")
    commands = discover(root)
    probe = ("import os, sys; open('ran.log', 'a').write(' '.join(sys.argv[1:]) + ' ' + str(os.path.exists('examples')) + '\\n')")
    log = tmp_path / "ran.log"

    execute(commands, root, executable=(sys.executable, "-c", probe, "-"), wheel=True)  # nothing is copied; the clone command is skipped
    assert not log.exists()  # the workspace is disposable; the probe wrote there, not here


def test_every_documented_command_of_the_repository_is_shipped_or_marked():
    check_documented_commands.check_shipped(discover(Path(__file__).resolve().parents[3]))


def test_first_project_names_exactly_the_presets_chrona_lists():
    import re
    from chrona.usecases.preset_library import list_builtin_presets

    text = (Path(__file__).resolve().parents[3] / "docs" / "guides" / "first-project.md").read_text(encoding="utf-8")
    sentence = re.search(r"Available ids are\s+(.*?)`chrona preset list`", text, re.S)
    named = re.findall(r"`([a-z-]+)`", sentence.group(1))
    assert named == [item["id"] for item in list_builtin_presets()]


def test_the_first_shell_block_of_the_readme_is_the_user_path():
    import re

    text = (Path(__file__).resolve().parents[3] / "README.md").read_text(encoding="utf-8")
    block = re.search(r"```(?:bash|sh)\n(.*?)```", text, re.S).group(1)
    assert "pip install" in block and "chrona init" in block and "chrona render" in block
    assert " -e " not in block and "pytest" not in block


def test_a_file_fence_is_written_to_the_workspace_and_never_run_as_commands(tmp_path):
    content = ("<!-- chrona:doc-check file: plan.csv -->\n```csv\nid,title\nchrona,not a command\n```\n"
               "```sh\nchrona import plan.csv --output p.yaml\n```\n")
    root = _document_root(tmp_path, content)

    assert [command.tokens for command in discover(root)] == [("chrona", "import", "plan.csv", "--output", "p.yaml")]
    files = check_documented_commands.discover_files(root)
    assert files == ((Path("README.md"), 3, "plan.csv", "id,title\nchrona,not a command\n"),)
    probe = "import sys; open('seen.txt', 'w').write(open('plan.csv').read()); print(sys.argv[1:])"
    execute(discover(root), root, executable=(sys.executable, "-c", probe), files=files)  # the file exists for the command

    with pytest.raises(DocumentedCommandError, match="E_DOCUMENTED_COMMAND_SKIP"):
        discover(_document_root(tmp_path, "<!-- chrona:doc-check file: a.csv -->\ntext\n```csv\nx\n```\n"))
