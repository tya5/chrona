#!/usr/bin/env python3
"""Check the structural contract of marked literal issue-acceptance reviews."""
from __future__ import annotations

import re
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
REVIEWS = ROOT / "docs" / "reviews" / "current"
MARKER = "<!-- chrona:literal-acceptance/v1 -->"
DISPOSITIONS = frozenset({"met", "not met", "narrowed", "deferred"})
ISSUE_HEADING = re.compile(r"^### Issue #(?P<number>[1-9][0-9]*)\s*$")
LINK = re.compile(r"\[[^][]+\]\([^()]+\)|https?://\S+")


def _error(path: Path, line: int, code: str) -> str:
    return f"{code}:{path.as_posix()}:{line}"


def _cells(line: str) -> tuple[str, ...] | None:
    if not line.startswith("|") or not line.endswith("|"):
        return None
    return tuple(cell.strip() for cell in line[1:-1].split("|"))


def _is_separator(cells: tuple[str, ...]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) is not None for cell in cells)


def validate_review(path: Path) -> tuple[str, ...]:
    """Return stable structural violations for one explicitly marked review."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if MARKER not in lines:
        return ()
    errors: list[str] = []
    literal_heading = next((index for index, line in enumerate(lines, 1)
                            if line == "## Literal issue acceptance"), None)
    programme_heading = next((index for index, line in enumerate(lines, 1)
                              if line == "## Programme-level criteria (optional)"), None)
    if literal_heading is None:
        return (_error(path, 1, "E_LITERAL_ACCEPTANCE_SECTION"),)
    if programme_heading is None or programme_heading < literal_heading:
        errors.append(_error(path, literal_heading, "E_LITERAL_ACCEPTANCE_PROGRAMME_SECTION"))
        programme_heading = len(lines) + 1

    issue_lines = [(index, ISSUE_HEADING.match(line)) for index, line in enumerate(lines, 1)
                   if literal_heading < index < programme_heading and ISSUE_HEADING.match(line)]
    if not issue_lines:
        errors.append(_error(path, literal_heading, "E_LITERAL_ACCEPTANCE_ISSUE"))
        return tuple(errors)

    for offset, (issue_line, _match) in enumerate(issue_lines):
        end = issue_lines[offset + 1][0] if offset + 1 < len(issue_lines) else programme_heading
        source = next((line for line in range(issue_line + 1, end)
                       if lines[line - 1].startswith("- Source: ")), None)
        observed = next((line for line in range(issue_line + 1, end)
                         if re.fullmatch(r"- Observed: [0-9]{4}-[0-9]{2}-[0-9]{2}", lines[line - 1])), None)
        if source is None or not LINK.search(lines[source - 1]):
            errors.append(_error(path, issue_line, "E_LITERAL_ACCEPTANCE_SOURCE"))
        if observed is None:
            errors.append(_error(path, issue_line, "E_LITERAL_ACCEPTANCE_OBSERVED"))

        table_header = next((line for line in range(issue_line + 1, end)
                             if _cells(lines[line - 1]) == ("#", "Literal acceptance criterion", "Disposition", "Evidence", "Successor")), None)
        if table_header is None:
            errors.append(_error(path, issue_line, "E_LITERAL_ACCEPTANCE_TABLE"))
            continue
        row_count = 0
        for line in range(table_header + 2, end):
            cells = _cells(lines[line - 1])
            if cells is None:
                if row_count:
                    break
                continue
            if _is_separator(cells):
                continue
            if len(cells) != 5:
                errors.append(_error(path, line, "E_LITERAL_ACCEPTANCE_ROW"))
                continue
            row_count += 1
            ordinal, criterion, disposition, evidence, successor = cells
            if not ordinal.isdecimal() or not criterion or criterion.startswith("["):
                errors.append(_error(path, line, "E_LITERAL_ACCEPTANCE_CRITERION"))
            if disposition not in DISPOSITIONS:
                errors.append(_error(path, line, "E_LITERAL_ACCEPTANCE_DISPOSITION"))
            if not evidence or not LINK.search(evidence):
                errors.append(_error(path, line, "E_LITERAL_ACCEPTANCE_EVIDENCE"))
            if disposition in {"narrowed", "deferred"} and not LINK.search(successor):
                errors.append(_error(path, line, "E_LITERAL_ACCEPTANCE_SUCCESSOR"))
        if not row_count:
            errors.append(_error(path, table_header, "E_LITERAL_ACCEPTANCE_ROW"))
    return tuple(errors)


def violations(reviews: Path = REVIEWS) -> tuple[str, ...]:
    """Validate every marked release review without synchronizing GitHub prose."""
    return tuple(error for path in sorted(reviews.glob("*.md")) for error in validate_review(path))


def main() -> int:
    errors = violations()
    if errors:
        print("\n".join(errors))
        return 1
    print("Literal issue acceptance reviews: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
