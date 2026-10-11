#!/usr/bin/env python3
"""Check documented chrona invocations against the live argparse grammar."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sysconfig
import tempfile
from typing import Iterable


@dataclass(frozen=True, order=True)
class DocumentedCommand:
    path: Path
    line: int
    tokens: tuple[str, ...]
    skip_reason: str | None = None


class DocumentedCommandError(ValueError):
    """A documented command cannot be represented by the live CLI."""


@dataclass(frozen=True)
class TersePlan:
    """A fenced block with the info string `chrona`: a terse plan (Spec 65), compiled rather than run as a command."""

    path: Path
    line: int
    text: str
    skip_reason: str | None = None
    expect_error: str | None = None
    expect_yaml: bool = False
    yaml_text: str | None = None  # the next fence when it is a `yaml` fence; `None` with `expect_yaml` means it is missing
    yaml_line: int | None = None


def _is_terse_fence(info: str) -> bool:
    return info.split()[:1] == ["chrona"]


FENCE = re.compile(r"^\s*(?P<fence>`{3,}|~{3,})(?P<info>[^`~]*)$")
SKIP = re.compile(r"^<!-- chrona:doc-check skip: (?P<reason>.+) -->$")
# `requires: clone <reason>`: the command reads files only a repository clone has (examples/, skills/). It runs in the clone
# workspace and is skipped in the wheel workspace; an unmarked command that names such a path is rejected (#1301).
REQUIRES_CLONE = re.compile(r"^<!-- chrona:doc-check requires: clone (?P<reason>.+) -->$")
REQUIRES_PREFIX = "requires: clone "
# `<!-- chrona:doc-check file: NAME -->` before a fence: the fence body is a file the later commands of the checked
# document read. It is written into the execution workspace, never executed (#1307).
FILE = re.compile(r"^<!-- chrona:doc-check file: (?P<name>[A-Za-z0-9._-]+) -->$")
CLONE_ONLY_ROOTS = ("examples/",)
# The skill's own commands name `skills/chrona/...`, the copy `chrona skill copy` writes; they run in the clone workspace
# (the skill is not rewritten for this check) and are skipped in the wheel workspace, which has no such copy.
SKILL_ROOT = "skills/"
EXPECT_ERROR = re.compile(r"^<!-- chrona:doc-check expect-error: (?P<code>E_[A-Z0-9_]+) -->$")
EXPECT_YAML = re.compile(r"^<!-- chrona:doc-check expect-yaml: next -->$")
SKIP_PREFIX = "<!-- chrona:doc-check"
COMMAND = re.compile(r"^\s*(?:\$\s*)?(chrona(?:\s+.*)?)$")
DEFAULT_TIMEOUT_SECONDS = 30


def documents(root: Path) -> Iterable[Path]:
    yield root / "README.md"
    yield from sorted((root / "docs" / "guides").glob("*.md"))
    skill = root / "skills" / "chrona"
    if skill.is_dir():
        yield from sorted(skill.glob("SKILL.md"))
        yield from sorted((skill / "references").glob("*.md"))


def _error(code: str, path: Path, line: int) -> DocumentedCommandError:
    return DocumentedCommandError(f"{code}:{path}:{line}")


def _block_commands(path: Path, start: int, lines: list[str], skip_reason: str | None) -> list[DocumentedCommand]:
    result: list[DocumentedCommand] = []
    index = 0
    while index < len(lines):
        match = COMMAND.fullmatch(lines[index])
        if match is None:
            index += 1
            continue
        text, end = match.group(1).rstrip(), index
        while text.endswith("\\"):
            if end + 1 >= len(lines):
                raise _error("E_DOCUMENTED_COMMAND_SHELL", path, start + end)
            end += 1
            text = text[:-1] + " " + lines[end].strip()
        try:
            tokens = tuple(shlex.split(text))
        except ValueError as error:
            raise _error("E_DOCUMENTED_COMMAND_SHELL", path, start + index) from error
        result.append(DocumentedCommand(path, start + index, tokens, skip_reason))
        index = end + 1
    return result


def discover(root: Path) -> tuple[DocumentedCommand, ...]:
    result: list[DocumentedCommand] = []
    for path in documents(root):
        relative = path.relative_to(root)
        lines = path.read_text(encoding="utf-8").splitlines()
        index = 0
        pending_skip: tuple[str, int] | None = None
        pending_file: int | None = None
        while index < len(lines):
            line = lines[index]
            if FILE.fullmatch(line) is not None:
                if pending_skip is not None or pending_file is not None:
                    raise _error("E_DOCUMENTED_COMMAND_SKIP", relative, index + 1)
                pending_file = index + 1
                index += 1
                continue
            marker = SKIP.fullmatch(line)
            expected = EXPECT_ERROR.fullmatch(line)
            emitted = EXPECT_YAML.fullmatch(line)
            cloned = REQUIRES_CLONE.fullmatch(line)
            if marker is not None or expected is not None or emitted is not None or cloned is not None:
                reason = (marker["reason"].strip() if marker is not None
                          else "expect-error " + expected["code"] if expected is not None
                          else REQUIRES_PREFIX + cloned["reason"].strip() if cloned is not None else "expect-yaml next")
                if pending_skip is not None or not reason:
                    raise _error("E_DOCUMENTED_COMMAND_SKIP", relative, index + 1)
                pending_skip = (reason, index + 1)
                index += 1
                continue
            if line.startswith(SKIP_PREFIX):
                raise _error("E_DOCUMENTED_COMMAND_SKIP", relative, index + 1)
            opening = FENCE.fullmatch(line)
            if opening is None:
                if pending_skip is not None:
                    raise _error("E_DOCUMENTED_COMMAND_SKIP", relative, pending_skip[1])
                if pending_file is not None:
                    raise _error("E_DOCUMENTED_COMMAND_SKIP", relative, pending_file)
                index += 1
                continue
            fence = opening["fence"]
            end = index + 1
            closing = re.compile(rf"^\s*{re.escape(fence)}\s*$")
            while end < len(lines) and closing.fullmatch(lines[end]) is None:
                end += 1
            if end >= len(lines):
                raise _error("E_DOCUMENTED_COMMAND_SHELL", relative, index + 1)
            if pending_file is not None:  # a file fence: never scanned for commands
                pending_file = None
                index = end + 1
                continue
            if _is_terse_fence(opening["info"]):  # a terse plan is compiled by discover_plans, never scanned for commands
                pending_skip = None
                index = end + 1
                continue
            commands = _block_commands(relative, index + 2, lines[index + 1:end], pending_skip[0] if pending_skip else None)
            if pending_skip is not None and not commands:
                raise _error("E_DOCUMENTED_COMMAND_SKIP", relative, pending_skip[1])
            result.extend(commands)
            pending_skip = None
            index = end + 1
        if pending_skip is not None:
            raise _error("E_DOCUMENTED_COMMAND_SKIP", relative, pending_skip[1])
    return tuple(result)


def discover_files(root: Path) -> tuple[tuple[Path, int, str, str], ...]:
    """The `file:` fences of the checked documents: (document, line, workspace file name, text)."""
    found: list[tuple[Path, int, str, str]] = []
    for path in documents(root):
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            marker = FILE.fullmatch(line)
            if marker is None:
                continue
            opening = FENCE.fullmatch(lines[index + 1]) if index + 1 < len(lines) else None
            if opening is None:
                raise _error("E_DOCUMENTED_COMMAND_SKIP", path.relative_to(root), index + 1)
            closing = re.compile(rf"^\s*{re.escape(opening['fence'])}\s*$")
            end = index + 2
            while end < len(lines) and closing.fullmatch(lines[end]) is None:
                end += 1
            found.append((path.relative_to(root), index + 3, marker["name"], "\n".join(lines[index + 2:end]) + "\n"))
    return tuple(found)


def discover_plans(root: Path) -> tuple[TersePlan, ...]:
    """Every ```chrona fence, with the marker that precedes it (`skip`, `expect-error`, `expect-yaml: next`).

    `expect-yaml: next` binds the next fence of the document, which must be a ```yaml fence holding the
    Project the plan compiles to (checked by `check_plans`).
    """
    plans: list[TersePlan] = []
    for path in documents(root):
        relative = path.relative_to(root)
        lines = path.read_text(encoding="utf-8").splitlines()
        skip: str | None = None
        expect: str | None = None
        expect_yaml = False
        index = 0
        while index < len(lines):
            line = lines[index]
            marker, expected = SKIP.fullmatch(line), EXPECT_ERROR.fullmatch(line)
            if marker is not None:
                skip = marker["reason"].strip()
            elif expected is not None:
                expect = expected["code"]
            elif EXPECT_YAML.fullmatch(line) is not None:
                expect_yaml = True
            opening = FENCE.fullmatch(line)
            if opening is None:
                index += 1
                continue
            end = index + 1
            closing = re.compile(rf"^\s*{re.escape(opening['fence'])}\s*$")
            while end < len(lines) and closing.fullmatch(lines[end]) is None:
                end += 1
            if _is_terse_fence(opening["info"]):
                yaml_text, yaml_line = _next_yaml_fence(lines, end + 1) if expect_yaml else (None, None)
                plans.append(TersePlan(relative, index + 2, "\n".join(lines[index + 1:end]) + "\n", skip, expect,
                                       expect_yaml, yaml_text, yaml_line))
            skip = expect = None
            expect_yaml = False
            index = end + 1
    return tuple(plans)


def _next_yaml_fence(lines: list[str], start: int) -> tuple[str | None, int | None]:
    """The body of the first fence at or after `start` when it is a `yaml` fence, else `(None, None)`."""
    for index in range(start, len(lines)):
        opening = FENCE.fullmatch(lines[index])
        if opening is None:
            continue
        if opening["info"].split()[:1] != ["yaml"]:
            return None, None
        end = index + 1
        closing = re.compile(rf"^\s*{re.escape(opening['fence'])}\s*$")
        while end < len(lines) and closing.fullmatch(lines[end]) is None:
            end += 1
        return "\n".join(lines[index + 1:end]) + "\n", index + 2
    return None, None


def check_plans(plans: tuple[TersePlan, ...]) -> None:
    """Compile each documented plan: it must compile, or (with `expect-error: CODE`) be rejected with that code."""
    from chrona.terse import HEADER
    from chrona.usecases.terse_compile import compile_plan

    for plan in plans:
        if plan.skip_reason is not None:
            continue
        result = compile_plan(plan.text.encode("utf-8"), f"{plan.path}:{plan.line}")
        codes = [item.id for item in result.diagnostics]
        if plan.expect_error is None and codes:
            raise DocumentedCommandError(f"E_DOCUMENTED_PLAN_REJECTED:{plan.path}:{plan.line}:{','.join(codes)}")
        if plan.expect_error is not None and plan.expect_error not in codes:
            raise DocumentedCommandError(f"E_DOCUMENTED_PLAN_EXPECTED_ERROR:{plan.path}:{plan.line}:{plan.expect_error}")
        if plan.expect_yaml:
            if plan.yaml_text is None:
                raise DocumentedCommandError(f"E_DOCUMENTED_PLAN_YAML_MISSING:{plan.path}:{plan.line}")
            if result.yaml is None or result.yaml.decode("utf-8").removeprefix(HEADER + "\n") != plan.yaml_text:
                raise DocumentedCommandError(f"E_DOCUMENTED_PLAN_YAML_MISMATCH:{plan.path}:{plan.line}:{plan.yaml_line}")


def _subparsers(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    return next((action.choices for action in parser._actions if isinstance(action, argparse._SubParsersAction)), {})


def _options(parser: argparse.ArgumentParser) -> dict[str, argparse.Action]:
    return {option: action for action in parser._actions for option in action.option_strings}


def _command_path(tokens: tuple[str, ...], parser: argparse.ArgumentParser) -> tuple[str, ...]:
    if not tokens or tokens[0] != "chrona":
        return ()
    current, result = parser, ["chrona"]
    for token in tokens[1:]:
        child = _subparsers(current).get(token)
        if child is None:
            break
        result.append(token); current = child
    return tuple(result)


def surface(parser: argparse.ArgumentParser | None = None) -> dict[tuple[str, ...], tuple[str, ...]]:
    if parser is None:
        from chrona.app.cli import _parser
        parser = _parser()
    result: dict[tuple[str, ...], tuple[str, ...]] = {}

    def visit(current: argparse.ArgumentParser, path: tuple[str, ...]) -> None:
        children = _subparsers(current)
        if path:
            result[("chrona", *path)] = tuple(sorted(option for option in _options(current) if option not in {"-h", "--help"}))
        for name, child in sorted(children.items()):
            visit(child, (*path, name))

    visit(parser, ())
    return result


def validate(command: DocumentedCommand, parser: argparse.ArgumentParser) -> None:
    tokens = list(command.tokens)
    if not tokens or tokens.pop(0) != "chrona":
        raise DocumentedCommandError(f"E_DOCUMENTED_COMMAND_PREFIX:{command.path}:{command.line}")
    if not tokens:
        raise DocumentedCommandError(f"E_DOCUMENTED_COMMAND_COMMAND:{command.path}:{command.line}")
    current = parser
    index = 0
    while index < len(tokens):
        token = tokens[index]
        children = _subparsers(current)
        if token in children:
            current = children[token]; index += 1; continue
        if token.startswith("-"):
            option, _, inline = token.partition("=")
            action = _options(current).get(option)
            if action is None:
                raise DocumentedCommandError(f"E_DOCUMENTED_COMMAND_OPTION:{command.path}:{command.line}:{option}")
            if action.choices and inline:
                if inline not in action.choices:
                    raise DocumentedCommandError(f"E_DOCUMENTED_COMMAND_VALUE:{command.path}:{command.line}:{option}={inline}")
            elif action.choices and index + 1 < len(tokens) and not tokens[index + 1].startswith("-"):
                index += 1
                if tokens[index] not in action.choices:
                    raise DocumentedCommandError(f"E_DOCUMENTED_COMMAND_VALUE:{command.path}:{command.line}:{option}={tokens[index]}")
            index += 1; continue
        index += 1


def requires_clone(command: DocumentedCommand) -> bool:
    return command.skip_reason is not None and command.skip_reason.startswith(REQUIRES_PREFIX)


def unshipped_paths(commands: tuple[DocumentedCommand, ...]) -> list[str]:
    """Commands that name a clone-only path (`examples/...`) without a `requires: clone` marker.

    A wheel ships `examples/halcyon-1` and the skill under `chrona/resources`, not at those paths in the user's directory,
    so such a command fails after `pip install` unless it says it needs a clone."""
    found: list[str] = []
    for command in commands:
        if command.skip_reason is not None:
            continue
        for token in command.tokens[1:]:
            value = token.partition("=")[2] if token.startswith("--") else token
            if value.startswith(CLONE_ONLY_ROOTS):
                found.append(f"{command.path}:{command.line}:{value}")
                break
    return found


def _names_skill_copy(command: DocumentedCommand) -> bool:
    return any((token.partition("=")[2] if token.startswith("--") else token).startswith(SKILL_ROOT) for token in command.tokens[1:])


def check_shipped(commands: tuple[DocumentedCommand, ...]) -> None:
    found = unshipped_paths(commands)
    if found:
        raise DocumentedCommandError("E_DOCUMENTED_COMMAND_UNSHIPPED_PATH\n" + "\n".join(found))


def _installed_chrona() -> tuple[str, ...]:
    scripts = sysconfig.get_path("scripts")
    executable = Path(scripts or ".") / ("chrona.exe" if os.name == "nt" else "chrona")
    if not executable.is_file():
        raise DocumentedCommandError("E_DOCUMENTED_COMMAND_EXECUTABLE")
    return (str(executable),)


def execute(commands: tuple[DocumentedCommand, ...], root: Path, *, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
            executable: tuple[str, ...] | None = None, wheel: bool = False,
            files: tuple[tuple[Path, int, str, str], ...] = ()) -> None:
    """Run non-skipped documented commands in a disposable workspace.

    The default workspace is a clone's: it holds the repository's `examples/` and `skills/`. With `wheel` it is empty, as
    a user's directory after `pip install`, and the commands marked `requires: clone` are skipped (#1301)."""
    if executable is None:
        executable = _installed_chrona()
    with tempfile.TemporaryDirectory(prefix="chrona-doc-check-") as temporary:
        workspace = Path(temporary)
        examples = root / "examples"
        if examples.is_dir() and not wheel:
            shutil.copytree(examples, workspace / "examples")
        skills = root / "skills"
        if skills.is_dir() and not wheel:
            shutil.copytree(skills, workspace / "skills")
        for _document, _line, name, text in files:
            (workspace / name).write_text(text, encoding="utf-8")
        environment = {**os.environ, "PYTHONUTF8": "1"}
        for command in commands:
            if command.skip_reason is not None and not (requires_clone(command) and not wheel):
                continue
            if wheel and _names_skill_copy(command):
                continue
            try:
                completed = subprocess.run(
                    (*executable, *command.tokens[1:]), cwd=workspace, env=environment,
                    capture_output=True, text=True, timeout=timeout_seconds, check=False,
                )
            except subprocess.TimeoutExpired as error:
                output = (error.stdout or "") + (error.stderr or "")
                raise DocumentedCommandError(
                    f"E_DOCUMENTED_COMMAND_EXECUTION:{command.path}:{command.line}:timeout\n{output}"
                ) from error
            if completed.returncode != 0:
                raise DocumentedCommandError(
                    f"E_DOCUMENTED_COMMAND_EXECUTION:{command.path}:{command.line}:exit={completed.returncode}\n"
                    f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
                )


def validate_surface(commands: tuple[DocumentedCommand, ...], parser: argparse.ArgumentParser) -> None:
    documented_paths = {_command_path(command.tokens, parser) for command in commands}
    documented_options = {
        (_command_path(command.tokens, parser), token.partition("=")[0])
        for command in commands for token in command.tokens if token.startswith("-")
    }
    missing: list[str] = []
    for path, options in surface(parser).items():
        if path not in documented_paths:
            missing.append("command=" + " ".join(path))
        missing.extend("option=" + " ".join((*path, option)) for option in options if (path, option) not in documented_options)
    if missing:
        raise DocumentedCommandError("E_DOCUMENTED_COMMAND_SURFACE\n" + "\n".join(missing))


def _commands(parser: argparse.ArgumentParser, path: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], argparse.ArgumentParser]]:
    for name, child in sorted(_subparsers(parser).items()):
        yield (*path, name), child
        yield from _commands(child, (*path, name))


def render_reference(parser: argparse.ArgumentParser | None = None) -> str:
    """The CLI reference: each command with its description, its flag list and the help text of every flag and argument."""
    if parser is None:
        from chrona.app.cli import _parser
        parser = _parser()
    lines = ["# CLI reference", "", "Generated by `tools/check_documented_commands.py` from the live argparse grammar.", ""]
    for path, command in _commands(parser):
        options = tuple(sorted(option for option in _options(command) if option not in {"-h", "--help"}))
        lines.extend([f"## {' '.join(('chrona', *path))}", ""])
        if command.description:
            lines.extend([command.description, ""])
        lines.extend([f"`{' '.join(('chrona', *path, *options))}`", ""])
        for action in command._actions:
            if isinstance(action, (argparse._HelpAction, argparse._SubParsersAction)) or not action.help:
                continue
            name = ", ".join(action.option_strings) if action.option_strings else action.dest
            lines.append(f"- `{name}`: {' '.join(str(action.help).split())}")
        if lines[-1] != "":
            lines.append("")
    return "\n".join(lines)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        temporary.write(content); temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("docs/guides/cli-reference.md"))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--wheel", action="store_true",
                        help="execute in an empty workspace (an installed wheel), skipping `requires: clone` commands")
    args = parser.parse_args(); root = args.root.resolve()
    from chrona.app.cli import _parser
    live = _parser(); commands = discover(root)
    for command in commands:
        validate(command, live)
    check_shipped(commands)
    check_plans(discover_plans(root))
    output = args.output if args.output.is_absolute() else root / args.output
    content = render_reference(live)
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != content:
            raise SystemExit("E_DOCUMENTED_COMMAND_REFERENCE_STALE")
    else:
        write(output, content)
    if args.execute:
        execute(commands, root, wheel=args.wheel, files=discover_files(root))


if __name__ == "__main__":
    main()
