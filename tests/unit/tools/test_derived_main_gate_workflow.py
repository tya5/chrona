from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github/workflows/derived-main.yml"


def test_derived_main_gate_is_dispatch_only_and_read_only() -> None:
    workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)

    assert workflow["name"] == "derived-main"
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["on"]["workflow_dispatch"]["inputs"]["expected_sha"]["required"] == "true"
    assert workflow["permissions"] == {"contents": "read"}
    assert "push" not in workflow["on"]
    assert "pull_request" not in workflow["on"]


def test_derived_main_gate_checks_the_exact_temp_ref_commit() -> None:
    workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    job = workflow["jobs"]["derived-main"]
    steps = job["steps"]
    checkout = next(step for step in steps if step.get("uses", "").startswith("actions/checkout@"))
    verification = next(step for step in steps if step.get("name") == "Verify immutable gate ref and exact dispatched commit")
    evidence = next(step for step in steps if step.get("name") == "Check every committed derived output")

    assert job["name"] == "derived-main"
    assert job["permissions"] == {"contents": "read"}
    assert checkout["with"]["ref"] == "${{ github.sha }}"
    assert "refs/heads/derived-gate/$EXPECTED_SHA" in verification["run"]
    assert 'test "$GITHUB_SHA" = "$EXPECTED_SHA"' in verification["run"]
    assert 'git rev-parse HEAD' in verification["run"]
    assert "python -m tools.derived_evidence --check --jobs 4" in evidence["run"]


def test_derived_ready_fails_closed_when_derived_main_fails() -> None:
    workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    ready = workflow["jobs"]["derived-ready"]
    assert ready["needs"] == "derived-main"
    assert ready["if"] == "${{ always() }}"
    assert ready["steps"][0]["env"]["GATE_RESULT"] == "${{ needs.derived-main.result }}"
    assert 'test "$GATE_RESULT" = "success"' in ready["steps"][0]["run"]
    assert 'test "$GITHUB_SHA" = "$EXPECTED_SHA"' in ready["steps"][0]["run"]


def test_derived_ready_marks_only_the_verified_sha_with_a_commit_status() -> None:
    workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    ready = workflow["jobs"]["derived-ready"]
    assert workflow["permissions"] == {"contents": "read"}
    assert ready["permissions"] == {"contents": "read", "statuses": "write"}
    verify, publish = ready["steps"]
    # The status step follows the verification step, with no `if` that could run it after a failure.
    assert "if" not in publish
    assert publish["env"]["EXPECTED_SHA"] == "${{ inputs.expected_sha }}"
    assert 'statuses/$EXPECTED_SHA' in publish["run"]
    assert "context=derived-ready" in publish["run"] and "state=success" in publish["run"]
    assert 'test "$GITHUB_SHA" = "$EXPECTED_SHA"' in verify["run"]
    # No other job may write statuses.
    assert "statuses" not in workflow["jobs"]["derived-main"]["permissions"]
