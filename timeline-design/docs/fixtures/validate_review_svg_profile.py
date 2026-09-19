#!/usr/bin/env python3
"""Validate the M14 review SVG profile fixture."""
from pathlib import Path
import sys
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent
schema = yaml.safe_load((ROOT.parent / "schemas" / "review-svg-profile-v0.1.schema.yaml").read_text())
profile = yaml.safe_load((ROOT / "review-svg-profile-v0.1.yaml").read_text())
errors = list(Draft202012Validator(schema).iter_errors(profile))
if errors:
    print("Review SVG profile: FAIL", file=sys.stderr)
    print("\n".join(error.message for error in errors), file=sys.stderr)
    raise SystemExit(1)
print("Review SVG profile: PASS")
