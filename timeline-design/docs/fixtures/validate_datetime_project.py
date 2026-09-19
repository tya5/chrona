#!/usr/bin/env python3
"""Validate DateTime Project successor fixtures without runtime scheduling."""
from pathlib import Path
from datetime import date, datetime
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent
schema = yaml.safe_load((ROOT.parent / "schemas" / "project-v0.2.schema.yaml").read_text())

def json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, list):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    return value

for filename, valid in (("datetime-project-v0.2.yaml", True), ("datetime-project-invalid-v0.2.yaml", False)):
    value = json_value(yaml.safe_load((ROOT / filename).read_text()))
    errors = list(Draft202012Validator(schema).iter_errors(value))
    if bool(errors) != (not valid):
        raise SystemExit(f"DateTime Project: FAIL: {filename}")
print("DateTime Project: PASS")
