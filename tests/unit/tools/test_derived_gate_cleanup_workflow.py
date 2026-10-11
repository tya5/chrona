from pathlib import Path
import os
import subprocess

import pytest
import yaml
from tests.support.workflow_shell import workflow_bash


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
    assert "Trusted gate failed:" in steps[gate]["run"]
    assert 'test "$gate_run_status" = completed' in steps[gate]["run"]
    assert 'test "$current" = "$SOURCE_SHA"' in steps[forward]["run"]


def test_release_matrix_checks_out_sha_not_retired_gate_branch() -> None:
    full = workflow("conformance.yml")["jobs"]["full-matrix"]
    checkout = next(step for step in full["steps"] if step.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["ref"] == "${{ github.sha }}"
    verify = next(step for step in full["steps"] if step.get("name") == "Verify exact full-CI SHA when supplied")
    assert 'test "$(git rev-parse HEAD)" = "$EXPECTED_SHA"' in verify["run"]


@pytest.mark.parametrize("failure,terminal,expected", [(False, True, 0), (True, True, 1), (False, False, 1)])
def test_gate_consumption_waits_for_terminal_workflow_without_weakening_result(tmp_path, failure, terminal, expected) -> None:
    steps = workflow("derived-sync.yml")["jobs"]["synchronize"]["steps"]
    script = next(step["run"] for step in steps if step.get("id") == "gate")
    script = script[script.index('gate_state=""'):]
    prefix = '''
    run_id=123
    GITHUB_REPOSITORY=owner/repo
    gh() {
      if [[ "$2" == */jobs ]]; then
        printf '%s\\n' "$CHRONATEST_JOB_STATE"
      elif [[ "$CHRONATEST_TERMINAL" == yes && -f "$CHRONATEST_SEEN" ]]; then
        printf 'completed\\n'
      else
        touch "$CHRONATEST_SEEN"
        printf 'in_progress\\n'
      fi
    }
    sleep() { :; }
    seq() { printf '1\\n2\\n'; }
    '''
    state = "derived-main:completed:failure,derived-ready:completed:failure" if failure else "derived-main:completed:success,derived-ready:completed:success"
    marker = tmp_path / "run-observed"
    result = subprocess.run([workflow_bash(), "-e", "-c", prefix + script], text=True, capture_output=True,
                            env={**os.environ, "CHRONATEST_JOB_STATE": state,
                                 "CHRONATEST_TERMINAL": "yes" if terminal else "no", "CHRONATEST_SEEN": marker.as_posix()})
    assert result.returncode == expected, result.stderr
    assert marker.exists()
