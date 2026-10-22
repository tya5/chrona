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


def test_derived_ready_status_publish_is_retried_once() -> None:
    workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    publish = workflow["jobs"]["derived-ready"]["steps"][1]["run"]
    assert publish.count("gh api --method POST") == 1  # one definition, called twice
    assert "publish || {" in publish and publish.rstrip().endswith("publish; }")
    assert publish.count("publish") == 4  # function, first call, retry, echo message


def _run_publish_script(tmp_path, fail_first: int) -> tuple[int, int]:
    """Execute the real step script under bash with a fake `gh` that fails `fail_first` times."""
    import shutil
    import subprocess

    import sys

    import pytest

    bash = shutil.which("bash")
    if bash is None or sys.platform == "win32":
        pytest.skip("POSIX bash required")
    workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    script = workflow["jobs"]["derived-ready"]["steps"][1]["run"].replace("sleep 5", "true")
    counter = tmp_path / "count"
    counter.write_text("0")
    (tmp_path / "gh").write_text(
        '#!/bin/bash\nn=$(($(cat "%s")+1)); echo $n > "%s"\n'
        'if [ "$n" -le %d ]; then echo "unexpected end of JSON input" >&2; exit 1; fi\n' % (counter, counter, fail_first))
    (tmp_path / "gh").chmod(0o755)
    env = {"PATH": f"{tmp_path}:/usr/bin:/bin", "GITHUB_REPOSITORY": "o/r", "EXPECTED_SHA": "a" * 40,
           "GITHUB_SERVER_URL": "https://github.com", "GITHUB_RUN_ID": "1"}
    result = subprocess.run([bash, "-e", "-c", script], env=env, capture_output=True, text=True)
    return result.returncode, int(counter.read_text())


def test_status_publish_succeeds_after_one_transient_failure(tmp_path) -> None:
    assert _run_publish_script(tmp_path, 1) == (0, 2)


def test_status_publish_fails_after_second_failure(tmp_path) -> None:
    code, calls = _run_publish_script(tmp_path, 2)
    assert code != 0 and calls == 2
