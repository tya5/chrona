"""Bounded, actionable reports for stale committed derived artifacts."""
from __future__ import annotations

from difflib import unified_diff
from pathlib import Path
from typing import Iterable
import json
import os


DIFF_LINE_LIMIT = 120
DIFF_CHARACTER_LIMIT = 12_000


def _bounded(lines: Iterable[str]) -> tuple[str, bool]:
    kept: list[str] = []
    characters = 0
    for line in lines:
        if len(kept) >= DIFF_LINE_LIMIT or characters + len(line) > DIFF_CHARACTER_LIMIT:
            return "".join(kept), True
        kept.append(line)
        characters += len(line)
    return "".join(kept), False


def report_stale_artifact(*, output: Path, generated: str, code: str,
                          refresh_argv: tuple[str, ...], root: Path) -> None:
    """Print a deterministic stale report without writing the derived output."""
    relative = output.resolve().relative_to(root.resolve())
    committed = output.read_text(encoding="utf-8") if output.is_file() else ""
    diff, truncated = _bounded(unified_diff(committed.splitlines(keepends=True), generated.splitlines(keepends=True),
                                            fromfile=f"committed/{relative}", tofile=f"generated/{relative}"))
    print(f"{code}: {relative}")
    if diff:
        print(diff, end="" if diff.endswith("\n") else "\n")
    if truncated:
        print(f"... diff truncated after {DIFF_LINE_LIMIT} lines or {DIFF_CHARACTER_LIMIT} characters ...")
    print("Refresh: " + json.dumps(list(refresh_argv), ensure_ascii=False))
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::error file={relative}::{code}; refresh with " + json.dumps(list(refresh_argv), ensure_ascii=False))
