from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]


def workflow(name: str) -> dict:
    return yaml.load((ROOT / ".github/workflows" / name).read_text(), Loader=yaml.BaseLoader)


def test_cleanup_and_sync_share_a_non_cancelling_multi_pending_queue() -> None:
    sync = workflow("derived-sync.yml")
    assert sync["concurrency"] == {
        "group": "derived-main-sync", "cancel-in-progress": "false", "queue": "max",
    }
    assert sync["on"]["schedule"] == [{"cron": "0 3 * * *"}]
    assert sync["jobs"]["synchronize"]["if"] == "${{ github.event_name != 'schedule' }}"
    sweep = sync["jobs"]["sweep"]
    assert sweep["if"] == "${{ github.event_name == 'schedule' }}"
    assert sweep["steps"][0]["with"]["ref"] == "main"
    assert 'tools.derived_gate_cleanup --repo "$GITHUB_REPOSITORY" sweep' in sweep["steps"][1]["run"]


def test_candidate_cleanup_is_after_consumption_and_release_dispatch() -> None:
    steps = workflow("derived-sync.yml")["jobs"]["synchronize"]["steps"]
    publish = next(i for i, step in enumerate(steps) if step.get("id") == "publish")
    gate = next(i for i, step in enumerate(steps) if step.get("id") == "gate")
    forward = next(i for i, step in enumerate(steps) if step.get("name", "").startswith("Fast-forward main"))
    release = next(i for i, step in enumerate(steps) if step.get("name", "").startswith("Dispatch full three-OS"))
    cleanup = next(i for i, step in enumerate(steps) if step.get("name") == "Retire the consumed terminal gate ref")
    assert publish < gate < forward < release < cleanup
    assert cleanup == len(steps) - 1
    assert steps[cleanup]["if"] == "${{ !cancelled() && steps.publish.outcome == 'success' }}"
    assert steps[cleanup]["env"]["SHA"] == "${{ steps.candidate.outputs.candidate_sha }}"
    assert 'candidate --sha "$SHA"' in steps[cleanup]["run"]
    # Terminal failure cleanup does not weaken the original gate or fast-forward checks.
    assert steps[gate]["run"] == 'python -m tools.derived_gate_await --repo "$GITHUB_REPOSITORY" --sha "$SHA"'
    assert 'test "$current" = "$SOURCE_SHA"' in steps[forward]["run"]


def test_release_matrix_checks_out_sha_not_retired_gate_branch() -> None:
    jobs = workflow("conformance.yml")["jobs"]
    full = jobs["full-matrix"]
    checkout = next(step for step in full["steps"] if step.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["ref"] == "${{ needs.ready-sha.outputs.sha }}"
    admission = jobs["ready-sha"]
    resolve = next(step for step in admission["steps"] if step.get("id") == "resolve")
    assert resolve["env"]["GITHUB_SHA"] == "${{ github.sha }}"
    assert resolve["env"]["SELECT_READY_MAIN"] == "${{ inputs.select_ready_main }}"
    verify = next(step for step in full["steps"] if step.get("name") == "Verify exact full-CI SHA when supplied")
    assert 'test "$(git rev-parse HEAD)" = "$EXPECTED_SHA"' in verify["run"]
    assert 'test "$GITHUB_SHA" = "$EXPECTED_SHA"' in verify["run"]
