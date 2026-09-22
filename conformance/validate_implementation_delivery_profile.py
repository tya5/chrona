#!/usr/bin/env python3
"""Validate IDP-1 vocabulary fixtures without assigning workflow semantics."""
from copy import deepcopy
from pathlib import Path
import sys
import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))
from chrona.scheduling.scheduler import schedule

ROOT = Path(__file__).resolve().parent
SCHEMA = yaml.safe_load((REPO_ROOT / "schemas" / "profile-v0.2.schema.yaml").read_text())
RESOURCE_SCHEMA = yaml.safe_load((REPO_ROOT / "schemas" / "revision-store-resource-ref-v0.1.schema.yaml").read_text())
EXPECTED = {
    "implementation-delivery.work-item": "task",
    "implementation-delivery.delivery-gate": "milestone",
    "implementation-delivery.person": "entity",
    "implementation-delivery.team": "entity",
}
DELIVERY_FIELDS = {"assignees", "workflowState", "artifacts", "acceptanceEvidence", "reuseClassification"}
WORKFLOW_STATES = {"planned", "active", "blocked", "completed", "cancelled"}
REUSE_CLASSES = {"core", "shared-service", "adapter", "experimental"}


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
            if fields.get("artifacts", {}).get("resourceKinds") != ["delivery-artifact"] or fields.get("acceptanceEvidence", {}).get("resourceKinds") != ["delivery-acceptance-evidence"]:
                diagnostics.append("IDP-PROFILE-005")
            if set(fields.get("workflowState", {}).get("enumValues", [])) != WORKFLOW_STATES or len(fields.get("workflowState", {}).get("enumValues", [])) != len(WORKFLOW_STATES):
                diagnostics.append("IDP-STATE-001")
            if set(fields.get("reuseClassification", {}).get("enumValues", [])) != REUSE_CLASSES or len(fields.get("reuseClassification", {}).get("enumValues", [])) != len(REUSE_CLASSES):
                diagnostics.append("IDP-STATE-001")
    return sorted(set(diagnostics))


def fixture_diagnostics(name):
    data = yaml.safe_load((ROOT / name).read_text())
    schema_errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    if schema_errors:
        raise AssertionError("schema failure: " + "; ".join(error.message for error in schema_errors))
    return diagnose(data)


def check_state_isolation():
    data = yaml.safe_load((ROOT / "implementation-delivery-state-isolation-v0.1.yaml").read_text())
    expected = data["expectedPlacement"]
    placements = []
    for state in data["states"]:
        project = deepcopy(data["project"])
        project["objects"]["build"]["fields"] = {"workflowState": state}
        result = schedule(project)
        if not result.ok or result.placements["build"] != expected["build"]:
            raise AssertionError(f"state isolation failed for {state}: {result.placements}, {result.diagnostics}")
        placements.append(result.placements)
    if any(placement != placements[0] for placement in placements[1:]):
        raise AssertionError("workflow state changed the schedule")


def check_evidence_references():
    cases = yaml.safe_load((ROOT / "implementation-delivery-evidence-v0.1.yaml").read_text())["cases"]
    allowed_kinds = {"artifacts": "delivery-artifact", "acceptanceEvidence": "delivery-acceptance-evidence"}
    for case in cases:
        diagnostics = []
        ref = case["reference"]
        if list(Draft202012Validator(RESOURCE_SCHEMA).iter_errors(ref)):
            diagnostics.append("IDP-EVIDENCE-001")
        verification = case["verification"]
        if not all(verification.values()):
            diagnostics.append("IDP-EVIDENCE-001")
        if ref["kind"] != allowed_kinds[case["field"]]:
            diagnostics.append("IDP-EVIDENCE-002")
        if diagnostics != case["diagnostics"]:
            raise AssertionError(f"evidence {case['id']}: {diagnostics}")


def check_self_hosted_roadmap():
    project = yaml.safe_load((ROOT / "implementation-delivery-roadmap-v0.1.yaml").read_text())
    expected = project.pop("expectedPlacements")
    if project["extensions"][0]["packageId"] != "implementation-delivery":
        raise AssertionError("roadmap does not resolve the standard package")
    for object_id, item in project["objects"].items():
        if item["type"] not in {"implementation-delivery.work-item", "implementation-delivery.delivery-gate"}:
            raise AssertionError(f"roadmap object {object_id} uses an unknown profile")
        if set(item["fields"]) != DELIVERY_FIELDS:
            raise AssertionError(f"roadmap object {object_id} has wrong delivery fields")
    evidence = project["objects"]["idp-4"]["fields"]["acceptanceEvidence"][0]
    if list(Draft202012Validator(RESOURCE_SCHEMA).iter_errors(evidence)) or evidence["kind"] != "delivery-acceptance-evidence":
        raise AssertionError("roadmap acceptance evidence is not immutable delivery evidence")
    result = schedule(project)
    if not result.ok or any(result.placements[key] != value for key, value in expected.items()):
        raise AssertionError(f"roadmap scheduling failed: {result.placements}, {result.diagnostics}")


def main():
    positive = fixture_diagnostics("implementation-delivery-profile-v0.2.yaml")
    if positive:
        raise AssertionError(f"positive fixture diagnostics: {positive}")
    negative = fixture_diagnostics("implementation-delivery-profile-invalid-field-v0.2.yaml")
    expected = {"IDP-PROFILE-003", "IDP-PROFILE-004", "IDP-PROFILE-005"}
    if set(negative) != expected:
        raise AssertionError(f"negative fixture diagnostics: {negative}")
    invalid_state = fixture_diagnostics("implementation-delivery-profile-invalid-state-v0.2.yaml")
    if invalid_state != ["IDP-STATE-001"]:
        raise AssertionError(f"invalid state fixture diagnostics: {invalid_state}")
    check_state_isolation()
    check_evidence_references()
    check_self_hosted_roadmap()
    print("Implementation-delivery profile vocabulary: PASS")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print(f"Implementation-delivery profile vocabulary: FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
