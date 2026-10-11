"""Fail-closed classification of pull-request changes for CI routing."""
from __future__ import annotations

import re
import subprocess
import sys

if __package__:
    from tools.derived_report_inventory import REPORTS
else:  # The no-install classify-pr job executes this file directly.
    from derived_report_inventory import REPORTS


_SHA = re.compile(r"[0-9a-fA-F]{40}\Z")


def classify_paths(paths: tuple[str, ...]) -> str:
    if not paths:
        return "code"
    for path in paths:
        if path in REPORTS:
            return "code"
        if path.startswith("docs/") and len(path) > len("docs/"):
            continue
        if path in {"AGENTS.md", ".ignore"} or ("/" not in path and path.startswith("README")):
            continue
        return "code"
    return "docs"


def classify_diff(base: str, head: str) -> str:
    if not _SHA.fullmatch(base) or not _SHA.fullmatch(head):
        return "code"
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--no-renames", "-z", base, head],
            check=True,
            capture_output=True,
        )
        paths = tuple(path.decode("utf-8") for path in result.stdout.split(b"\0") if path)
    except (OSError, UnicodeError, subprocess.CalledProcessError):
        return "code"
    return classify_paths(paths)


def main() -> int:
    if len(sys.argv) != 3:
        print("code")
    else:
        print(classify_diff(sys.argv[1], sys.argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
