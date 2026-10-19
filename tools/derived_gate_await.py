"""Dispatch the trusted derived-main gate and await that exact run (Refs #1775).

The dispatch itself returns the id of the run it created, so the await never
searches run listings by ref, SHA or run number. Each poll logs one line and
transient API errors are retried a bounded number of times.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from typing import Any, Callable

from tools.derived_gate_cleanup import GitHubApi, GitHubApiError

_SHA = re.compile(r"[0-9a-f]{40}\Z")
_WORKFLOW = "derived-main.yml"
_REQUIRED_JOBS = ("derived-main", "derived-ready")
POLL_INTERVAL = 15
MAX_POLLS = 120
MAX_CONSECUTIVE_ERRORS = 5


def _log(message: str) -> None:
    print(message, flush=True)


class GateError(RuntimeError):
    """The gate failed, did not finish in time, or could not be observed."""


class GateApi(GitHubApi):
    def dispatch(self, ref: str, sha: str) -> Any:
        body = json.dumps({"ref": ref, "inputs": {"expected_sha": sha}, "return_run_details": True})
        result = self.runner(
            ["gh", "api", "--method", "POST",
             f"repos/{self.repo}/actions/workflows/{_WORKFLOW}/dispatches", "--input", "-"],
            text=True, capture_output=True, check=False, input=body)
        if result.returncode:
            raise GitHubApiError("POST", "dispatches", None, result.stderr or "")
        try:
            return json.loads(result.stdout)
        except (TypeError, json.JSONDecodeError) as error:
            raise GateError("E_GATE_DISPATCH_NO_RUN_ID: dispatch response was not JSON") from error


def dispatch_gate(api: Any, sha: str, log: Callable[[str], None] = _log) -> int:
    """Dispatch the gate for ``sha`` and return the run id the dispatch created."""
    if not _SHA.fullmatch(sha):
        raise ValueError("sha must be 40 lowercase hex characters")
    payload = api.dispatch(f"derived-gate/{sha}", sha)
    run_id = payload.get("workflow_run_id") if isinstance(payload, dict) else None
    if not isinstance(run_id, int) or isinstance(run_id, bool):
        raise GateError("E_GATE_DISPATCH_NO_RUN_ID: dispatch did not return workflow_run_id")
    log(f"dispatched {_WORKFLOW} for {sha} as run {run_id}")
    return run_id


def await_gate(api: Any, run_id: int, *, sleep: Callable[[float], None] = time.sleep,
               log: Callable[[str], None] = _log, interval: float = POLL_INTERVAL,
               max_polls: int = MAX_POLLS, max_errors: int = MAX_CONSECUTIVE_ERRORS) -> str:
    """Poll one known run. Return its job summary on success, raise GateError otherwise."""
    errors = 0
    for poll in range(1, max_polls + 1):
        try:
            run = api.request("GET", f"repos/{api.repo}/actions/runs/{run_id}")
            status = run.get("status") if isinstance(run, dict) else None
            conclusion = (run.get("conclusion") or "") if isinstance(run, dict) else ""
            log(f"poll {poll}/{max_polls} run={run_id} status={status} conclusion={conclusion or '-'}")
            if status == "completed":
                jobs = api.request("GET", f"repos/{api.repo}/actions/runs/{run_id}/jobs",
                                   fields=(("per_page", "100"),))
                state = _job_state(jobs)
                if conclusion != "success" or not all(f"{name}:completed:success" in state.split(",")
                                                      for name in _REQUIRED_JOBS):
                    raise GateError(f"Trusted gate failed: run={run_id} conclusion={conclusion} {state}")
                log(f"gate run {run_id} succeeded: {state}")
                return state
            errors = 0
        except GitHubApiError as error:
            errors += 1
            log(f"poll {poll}/{max_polls} run={run_id} api error {errors}/{max_errors}: {error}")
            if errors >= max_errors:
                raise GateError(f"E_GATE_API: {errors} consecutive API errors on run {run_id}") from error
            sleep(interval)
            continue
        sleep(interval)
    raise GateError(f"E_GATE_TIMEOUT: run {run_id} not completed after {max_polls} polls")


def _job_state(payload: Any) -> str:
    jobs = payload.get("jobs") if isinstance(payload, dict) else None
    if not isinstance(jobs, list):
        return ""
    return ",".join(sorted(f"{job.get('name')}:{job.get('status')}:{job.get('conclusion') or ''}"
                           for job in jobs if job.get("name") in _REQUIRED_JOBS))


def main(argv: list[str] | None = None, runner: Callable[..., Any] = subprocess.run) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--sha", required=True)
    args = parser.parse_args(argv)
    try:
        api = GateApi(args.repo, runner)
        run_id = dispatch_gate(api, args.sha)
        await_gate(api, run_id)
    except (GateError, GitHubApiError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
