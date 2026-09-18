#!/usr/bin/env python3
"""Validate IDP-1 vocabulary fixtures without assigning workflow semantics."""
from pathlib import Path
import sys
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent
DOCS = ROOT.parent
SCHEMA = yaml.safe_load((DOCS / "schemas" / "profile-v0.1.schema.yaml").read_text())
EXPECTED = {
    "implementation-delivery.work-item": "task",
    "implementation-delivery.delivery-gate": "milestone",
    "implementation-delivery.person": "entity",
    "implementation-delivery.team": "entity",
}
DELIVERY_FIELDS = {"assignees", "workflowState", "artifacts", "acceptanceEvidence", "reuseClassification"}


def diagnose(data):
    diagnostics = []
    profiles = data.get("profiles", {})
    for profile_id, expected_parent in EXPECTED.items():
        profile = profiles.get(profile_id)
        if not isinstance(profile, dict) or profile.get("extends") != expected_parent:
            diagnostics.append("IDP-PROFILE-006")
            continue
        fields = profile.get("fields", {})
        if profile_id.endswith(("work-item", "delivery-gate")):
            if not {"workflowState", "reuseClassification"}.issubset(fields):
                diagnostics.append("IDP-PROFILE-001")
            if set(fields) != DELIVERY_FIELDS:
                diagnostics.append("IDP-PROFILE-006")
            assignees = fields.get("assignees", {})
            if assignees.get("cardinality") != "many" or set(assignees.get("targetProfiles", [])) != {
                "implementation-delivery.person", "implementation-delivery.team"
            }:
                diagnostics.append("IDP-PROFILE-003")
            for name in ("workflowState", "reuseClassification"):
                if fields.get(name, {}).get("cardinality") != "one":
                    diagnostics.append("IDP-PROFILE-004")
            for name in ("artifacts", "acceptanceEvidence"):
                field = fields.get(name, {})
                if field.get("type") != "resourceReference" or field.get("cardinality") != "many":
                    diagnostics.append("IDP-PROFILE-005")
    return sorted(set(diagnostics))


def fixture_diagnostics(name):
    data = yaml.safe_load((ROOT / name).read_text())
    schema_errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    if schema_errors:
        raise AssertionError("schema failure: " + "; ".join(error.message for error in schema_errors))
    return diagnose(data)


def main():
    positive = fixture_diagnostics("implementation-delivery-profile-v0.1.yaml")
    if positive:
        raise AssertionError(f"positive fixture diagnostics: {positive}")
    negative = fixture_diagnostics("implementation-delivery-profile-invalid-field-v0.1.yaml")
    expected = {"IDP-PROFILE-003", "IDP-PROFILE-004", "IDP-PROFILE-005"}
    if set(negative) != expected:
        raise AssertionError(f"negative fixture diagnostics: {negative}")
    print("Implementation-delivery profile vocabulary: PASS")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print(f"Implementation-delivery profile vocabulary: FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
