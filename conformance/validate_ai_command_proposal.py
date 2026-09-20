#!/usr/bin/env python3
"""Validate AI proposal and authorization exchange contracts."""
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator, RefResolver

ROOT = Path(__file__).resolve().parent
SCHEMAS = ROOT.parent / "schemas"
schemas = {yaml.safe_load(path.read_text())["$id"]: yaml.safe_load(path.read_text()) for path in SCHEMAS.glob("*.schema.yaml")}
fixture = yaml.safe_load((ROOT / "ai-command-proposal-v0.1.yaml").read_text())
for name, schema_id in (("proposal", "urn:chrona:ai-command-proposal-v0.1"), ("decision", "urn:chrona:authorization-decision-v0.1"), ("deniedDecision", "urn:chrona:authorization-decision-v0.1")):
    errors = list(Draft202012Validator(schemas[schema_id], resolver=RefResolver.from_schema(schemas[schema_id], store=schemas)).iter_errors(fixture[name]))
    if errors:
        raise SystemExit(f"AI proposal: FAIL: {name}: " + "; ".join(error.message for error in errors))
if fixture["proposal"]["proposalId"] != fixture["decision"]["proposalId"] or fixture["decision"]["proposalId"] != fixture["deniedDecision"]["proposalId"]:
    raise SystemExit("AI proposal: FAIL: decision must bind proposal")
print("AI proposal: PASS")
