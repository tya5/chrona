#!/usr/bin/env python3
"""Validate the immutable M13 successor-release acceptance closure."""
from pathlib import Path
import sys

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
EXPECTED = {"UC-16", "UC-17", "UC-18", "UC-19", "UC-20", "UC-21"}

schema = yaml.safe_load((ROOT.parent / "schemas" / "successor-release-acceptance-v0.3.schema.yaml").read_text())
manifest = yaml.safe_load((ROOT / "successor-release-acceptance-v0.3.yaml").read_text())
errors = sorted(Draft202012Validator(schema).iter_errors(manifest), key=lambda error: list(error.path))
if errors:
    print("Successor release acceptance: FAIL", file=sys.stderr)
    print("\n".join(error.message for error in errors), file=sys.stderr)
    raise SystemExit(1)

rows = manifest["useCases"]
if {row["id"] for row in rows} != EXPECTED or len(rows) != len(EXPECTED):
    print("Successor release acceptance: FAIL (UC closure)", file=sys.stderr)
    raise SystemExit(1)
for row in rows:
    for evidence in row["evidence"]:
        if not (REPO / evidence).is_file():
            print(f"Successor release acceptance: FAIL (missing evidence: {evidence})", file=sys.stderr)
            raise SystemExit(1)
print("Successor release acceptance: PASS")
