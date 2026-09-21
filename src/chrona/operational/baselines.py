"""Immutable named-baseline comparison and automation result construction."""
from __future__ import annotations

from typing import Any

from chrona.app.review import review_projects
from chrona.operational.references import ImmutableReader, verify_reference
from chrona.operational.resources import content_identity


def compare_baseline(
    baseline_reader: ImmutableReader,
    baseline_reference: dict[str, Any],
    candidate_reader: ImmutableReader,
    candidate_reference: dict[str, Any],
) -> dict[str, Any]:
    """Compare a verified named baseline with a separately verified Project."""
    request = {"baseline": baseline_reference, "candidate": candidate_reference}
    try:
        baseline = verify_reference(baseline_reader, baseline_reference, kind="snapshot-ref")
        project_reference = baseline.value.get("body", {}).get("project")
        if not isinstance(project_reference, dict):
            raise ValueError("E_BASELINE_REFERENCE")
        before = verify_reference(candidate_reader, project_reference, kind="project")
        candidate = verify_reference(candidate_reader, candidate_reference, kind="project")
    except ValueError as error:
        code = str(error)
        if code == "E_AUTOMATION_TARGET_CLOSURE":
            code = "E_BASELINE_REFERENCE"
        return {
            "version": "chrona/automation-result/v0.1", "operation": "baseline-compare", "status": "rejected",
            "requestContentIdentity": content_identity(request), "inputs": [baseline_reference, candidate_reference],
            "diagnostics": [{"code": code}], "artifacts": [],
        }
    comparison = review_projects(before.value, candidate.value)
    if comparison["status"] != "accepted":
        return {
            "version": "chrona/automation-result/v0.1", "operation": "baseline-compare", "status": "rejected",
            "requestContentIdentity": content_identity(request), "inputs": [baseline_reference, project_reference, candidate_reference],
            "diagnostics": comparison["diagnostics"], "artifacts": [],
        }
    return {
        "version": "chrona/automation-result/v0.1", "operation": "baseline-compare", "status": "accepted",
        "requestContentIdentity": content_identity(request), "inputs": [baseline_reference, project_reference, candidate_reference],
        "diagnostics": [], "artifacts": [], "comparison": comparison,
    }
