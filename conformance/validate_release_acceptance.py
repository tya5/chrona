#!/usr/bin/env python3
"""Validate the release-acceptance contract and evidence references."""
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
schema = yaml.safe_load((REPO / "schemas" / "release-acceptance-v0.2.schema.yaml").read_text())
manifest = yaml.safe_load((ROOT / "current-profile-release-acceptance-v0.2.yaml").read_text())
errors = list(Draft202012Validator(schema).iter_errors(manifest))
if errors:
    raise SystemExit("Release acceptance: FAIL: " + "; ".join(error.message for error in errors))

expected = {f"UC-{number:02d}" for number in range(1, 16)}
entries = manifest["useCases"]
actual = [entry["id"] for entry in entries]
if set(actual) != expected or len(actual) != len(set(actual)):
    raise SystemExit("Release acceptance: FAIL: use cases must cover UC-01 through UC-15 exactly once")
for entry in entries:
    for evidence in entry.get("evidence", []):
        if not (REPO / evidence).is_file():
            raise SystemExit(f"Release acceptance: FAIL: missing evidence {evidence}")
print("Release acceptance: PASS (15 use cases; explicit exclusions retained)")
