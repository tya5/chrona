#!/usr/bin/env python3
"""Check documented chrona invocations against the live argparse grammar."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import shlex
import tempfile
from typing import Iterable


@dataclass(frozen=True, order=True)
class DocumentedCommand:
    path: Path
    line: int
    tokens: tuple[str, ...]


class DocumentedCommandError(ValueError):
    """A documented command cannot be represented by the live CLI."""


COMMAND = re.compile(r"(?:^\$?\s*|`)(chrona\s+[^`\n]+)")


def documents(root: Path) -> Iterable[Path]:
    yield root / "README.md"
    yield from sorted((root / "docs" / "guides").glob("*.md"))


def discover(root: Path) -> tuple[DocumentedCommand, ...]:
    result: list[DocumentedCommand] = []
    for path in documents(root):
        lines = path.read_text(encoding="utf-8").splitlines()
        index = 0
        while index < len(lines):
            match = COMMAND.search(lines[index])
            if match is None:
                index += 1; continue
            text, end = match.group(1).rstrip(), index
            while text.endswith("\\") and end + 1 < len(lines):
                end += 1; text = text[:-1] + " " + lines[end].strip()
            try:
                tokens = tuple(shlex.split(text))
            except ValueError as error:
                raise DocumentedCommandError(f"E_DOCUMENTED_COMMAND_SHELL:{path.relative_to(root)}:{index + 1}") from error
            result.append(DocumentedCommand(path.relative_to(root), index + 1, tokens))
            index = end + 1
    return tuple(result)


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


def render_reference(parser: argparse.ArgumentParser | None = None) -> str:
    lines = ["# CLI reference", "", "Generated by `tools/check_documented_commands.py` from the live argparse grammar.", ""]
    for path, options in surface(parser).items():
        lines.extend([f"## {' '.join(path)}", "", f"`{' '.join((*path, *options))}`", ""])
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
    args = parser.parse_args(); root = args.root.resolve()
    from chrona.app.cli import _parser
    live = _parser(); commands = discover(root)
    for command in commands:
        validate(command, live)
    output = args.output if args.output.is_absolute() else root / args.output
    content = render_reference(live)
    if args.check:
        validate_surface(commands, live)
        if not output.is_file() or output.read_text(encoding="utf-8") != content:
            raise SystemExit("E_DOCUMENTED_COMMAND_REFERENCE_STALE")
        return
    write(output, content)


if __name__ == "__main__":
    main()
