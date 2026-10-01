"""Shared helpers for tests that guard the packaged agent skill (#142)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
SKILL_DIR = ROOT / "skills" / "chrona"
EXAMPLE = SKILL_DIR / "examples" / "launch.yaml"


def skill_documents() -> tuple[Path, ...]:
    """Every Markdown file of the skill, in a stable order."""
    return tuple(sorted(SKILL_DIR.rglob("*.md")))


def fences(path: Path, language: str) -> list[str]:
    """Return the bodies of every fenced block of one language in a Markdown file."""
    text = path.read_text(encoding="utf-8")
    pattern = rf"^```{re.escape(language)}[ \t]*\n(.*?)^```[ \t]*$"
    return [match.group(1) for match in re.finditer(pattern, text, flags=re.DOTALL | re.MULTILINE)]


def run_cli(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    """Run `chrona.app.cli.main` in process; return exit status, stdout and stderr."""
    from chrona.app.cli import main

    monkeypatch.setattr(sys, "argv", ["chrona", *argv])
    status = 0
    try:
        main()
    except SystemExit as exit_request:
        status = exit_request.code if isinstance(exit_request.code, int) else (0 if exit_request.code is None else 1)
    captured = capsys.readouterr()
    return status, captured.out, captured.err
