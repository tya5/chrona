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
