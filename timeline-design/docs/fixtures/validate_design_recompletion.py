#!/usr/bin/env python3
"""Validate that the whole-design recompletion gate has all required evidence."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT.parent
plan = (DOCS / "planning" / "whole-design-recompletion-plan-2026-09-19.md").read_text()
required = {
    "WD-1": "reviews/wd-1-wd-4-delivery-state-review-2026-09-19.md",
    "WD-2a": "reviews/wd-2a-command-registry-closure-review-2026-09-19.md",
    "WD-2b": "reviews/wd-2b-ai-authorization-design-review-2026-09-19.md",
    "WD-3": "reviews/wd-3-release-package-design-review-2026-09-19.md",
    "WD-4": "planning/milestone-status-ledger-v0.1.md",
    "WD-5": "reviews/wd-5-profile-compatibility-review-2026-09-19.md",
    "WD-6": "reviews/whole-system-design-reauthorization-review-2026-09-19.md",
}
for item, evidence in required.items():
    if f"| {item} |" not in plan or "**Complete.**" not in next(line for line in plan.splitlines() if f"| {item} |" in line):
        raise SystemExit(f"Design recompletion: FAIL: {item} is not complete")
    if not (DOCS / evidence).is_file():
        raise SystemExit(f"Design recompletion: FAIL: missing {evidence}")
print("Design recompletion: PASS (WD-1 through WD-6)")
