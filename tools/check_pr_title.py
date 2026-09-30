"""Reject closing keywords in PR titles (#631).

GitHub closes an issue when a merged PR's title or body says ``closes #n``. A
partial PR must use ``Refs #n``; an issue is closed deliberately after its
literal acceptance review (AGENTS.md). Only a PR labelled ``closes-issue``
may carry a closing keyword.
"""
from __future__ import annotations

import re
import sys

CLOSING_REFERENCE = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b\s*:?\s+(?:[\w.-]+/[\w.-]+)?#\d+", re.IGNORECASE)


def closing_reference(title: str) -> str | None:
    """Return the first ``<keyword> #n`` phrase in ``title``, or ``None``."""
    match = CLOSING_REFERENCE.search(title)
    return match.group(0) if match else None


def main(argv: list[str]) -> int:
    if len(argv) not in {2, 3} or (len(argv) == 3 and argv[2] != "--allow-closing"):
        print("usage: check_pr_title.py TITLE [--allow-closing]", file=sys.stderr)
        return 2
    found = closing_reference(argv[1])
    if found is None or len(argv) == 3:
        return 0
    print(f"E_PR_TITLE_CLOSING_KEYWORD: {found!r}. Use 'Refs #n' in a partial PR; a title keyword closes "
          "the issue when the PR merges. Label the PR 'closes-issue' if it really closes it.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
