#!/usr/bin/env python3
"""Validate that the whole-design recompletion gate has all required evidence."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
DOCS = REPO / "docs"
plan = (DOCS / "archive" / "planning" / "whole-design-recompletion-plan-2026-09-19.md").read_text()
required = {
    "WD-1": "docs/archive/reviews/wd-1-wd-4-delivery-state-review-2026-09-19.md",
    "WD-2a": "docs/archive/reviews/wd-2a-command-registry-closure-review-2026-09-19.md",
    "WD-2b": "docs/archive/reviews/wd-2b-ai-authorization-design-review-2026-09-19.md",
    "WD-3": "docs/archive/reviews/wd-3-release-package-design-review-2026-09-19.md",
    "WD-4": "docs/planning/active/milestone-status-ledger-v0.1.md",
    "WD-5": "docs/archive/reviews/wd-5-profile-compatibility-review-2026-09-19.md",
    "WD-6": "docs/archive/reviews/whole-system-design-reauthorization-review-2026-09-19.md",
}
for item, evidence in required.items():
    if f"| {item} |" not in plan or "**Complete.**" not in next(line for line in plan.splitlines() if f"| {item} |" in line):
        raise SystemExit(f"Design recompletion: FAIL: {item} is not complete")
    if not (REPO / evidence).is_file():
        raise SystemExit(f"Design recompletion: FAIL: missing {evidence}")
print("Design recompletion: PASS (WD-1 through WD-6)")
