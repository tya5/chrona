"""Reject closing keywords in PR titles and in the commit messages a PR carries (#631).

GitHub closes an issue when a merged PR's title or body, or any commit message
that reaches the default branch, says ``closes #n``. #592 was closed twice by
the same accident: once by a PR title and once by a commit body that only
*described* the first accident. A partial PR must use ``Refs #n``; an issue
is closed deliberately after its literal acceptance review (AGENTS.md). Only
a PR labelled ``closes-issue`` may carry a closing keyword.
"""
from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path

CLOSING_REFERENCE = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b\s*:?\s+(?:[\w.-]+/[\w.-]+)?#\d+", re.IGNORECASE)


def closing_reference(text: str) -> str | None:
    """Return the first ``<keyword> #n`` phrase in ``text``, or ``None``."""
    match = CLOSING_REFERENCE.search(text)
    return match.group(0) if match else None


def commit_closing_references(messages: Iterable[str]) -> list[tuple[str, str]]:
    """Return ``(commit subject, phrase)`` for every commit message with a closing keyword."""
    found = []
    for message in messages:
        phrase = closing_reference(message)
        if phrase is not None:
            found.append((message.splitlines()[0] if message else "", phrase))
    return found


def main(argv: list[str]) -> int:
    args = argv[1:]
    allow = "--allow-closing" in args
    commits_path = None
    if "--commits" in args:
        position = args.index("--commits")
        if position + 1 >= len(args):
            print("usage: check_pr_title.py TITLE [--allow-closing] [--commits FILE]", file=sys.stderr)
            return 2
        commits_path = args[position + 1]
        del args[position:position + 2]
    args = [item for item in args if item != "--allow-closing"]
    if len(args) != 1:
        print("usage: check_pr_title.py TITLE [--allow-closing] [--commits FILE]", file=sys.stderr)
        return 2
    problems = []
    title_phrase = closing_reference(args[0])
    if title_phrase is not None:
        problems.append(f"E_PR_TITLE_CLOSING_KEYWORD: the title says {title_phrase!r}.")
    if commits_path is not None:
        messages = json.loads(Path(commits_path).read_text(encoding="utf-8"))
        for subject, phrase in commit_closing_references(messages):
            problems.append(f"E_PR_COMMIT_CLOSING_KEYWORD: commit {subject!r} says {phrase!r}.")
    if not problems or allow:
        return 0
    print("\n".join(problems), file=sys.stderr)
    print("A merged PR's title, and any commit message that reaches main, closes the issue. Use 'Refs #n', and "
          "when describing an earlier accident write the number without '#'. Label the PR 'closes-issue' if "
          "it really closes the issue.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
