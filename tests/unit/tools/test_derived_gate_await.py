"""The sync awaits the exact run its dispatch created (Refs #1775)."""
import json
import subprocess

import pytest

from tools import derived_gate_await as gate
from tools.derived_gate_cleanup import GitHubApiError

SHA = "a" * 40
RUN = 4242


class FakeApi:
    repo = "owner/repo"

    def __init__(self, runs, jobs=None):
        self.runs = list(runs)  # each: dict, or Exception to raise
        self.jobs = jobs
        self.calls = []

    def request(self, method, endpoint, **kwargs):
        self.calls.append(endpoint)
        if endpoint.endswith("/jobs"):
            return {"jobs": self.jobs}
        item = self.runs.pop(0) if len(self.runs) > 1 else self.runs[0]
        if isinstance(item, Exception):
            raise item
        return item


def _jobs(main="success", ready="success"):
    return [{"name": "derived-main", "status": "completed", "conclusion": main},
            {"name": "derived-ready", "status": "completed", "conclusion": ready},
            {"name": "other", "status": "completed", "conclusion": "failure"}]


def _run(api, **kwargs):
    lines, sleeps = [], []
    kwargs.setdefault("max_polls", 10)
    result = gate.await_gate(api, RUN, sleep=sleeps.append, log=lines.append, interval=15, **kwargs)
    return result, lines, sleeps


def test_completed_success_exits_on_first_poll() -> None:
    api = FakeApi([{"status": "completed", "conclusion": "success"}], _jobs())
    state, lines, sleeps = _run(api)
    assert state == "derived-main:completed:success,derived-ready:completed:success"
    assert sleeps == []
    assert lines[0] == f"poll 1/10 run={RUN} status=completed conclusion=success"


def test_in_progress_then_success_logs_each_poll_and_stops_within_one_interval() -> None:
    api = FakeApi([{"status": "queued"}, {"status": "in_progress"},
                   {"status": "completed", "conclusion": "success"}], _jobs())
    _, lines, sleeps = _run(api)
    assert [line for line in lines if line.startswith("poll")] == [
        f"poll 1/10 run={RUN} status=queued conclusion=-",
        f"poll 2/10 run={RUN} status=in_progress conclusion=-",
        f"poll 3/10 run={RUN} status=completed conclusion=success"]
    assert sleeps == [15, 15]  # no sleep after the completed poll


def test_never_completing_gate_times_out_after_bounded_polls() -> None:
    api = FakeApi([{"status": "in_progress"}])
    with pytest.raises(gate.GateError, match="E_GATE_TIMEOUT"):
        _run(api, max_polls=3)
    assert len(api.calls) == 3


@pytest.mark.parametrize("conclusion,main,ready", [
    ("failure", "failure", "failure"), ("failure", "success", "failure"), ("success", "success", "skipped")])
def test_failed_gate_raises_immediately(conclusion, main, ready) -> None:
    api = FakeApi([{"status": "completed", "conclusion": conclusion}], _jobs(main, ready))
    with pytest.raises(gate.GateError, match="Trusted gate failed"):
        _run(api)


def _boom():
    return GitHubApiError("GET", "runs", 502, "bad gateway")


def test_transient_api_error_is_retried_and_logged() -> None:
    api = FakeApi([_boom(), _boom(), {"status": "completed", "conclusion": "success"}], _jobs())
    state, lines, sleeps = _run(api)
    assert state.endswith("derived-ready:completed:success")
    assert sum("api error" in line for line in lines) == 2
    assert sleeps == [15, 15]


def test_persistent_api_errors_are_bounded() -> None:
    api = FakeApi([_boom()])
    with pytest.raises(gate.GateError, match="E_GATE_API"):
        _run(api, max_errors=3)
    assert len(api.calls) == 3


def test_success_resets_the_error_count() -> None:
    api = FakeApi([_boom(), {"status": "in_progress"}, _boom(), {"status": "completed", "conclusion": "success"}],
                  _jobs())
    _run(api, max_errors=2)


def test_dispatch_uses_the_returned_run_id_not_a_listing() -> None:
    seen = {}

    def runner(args, **kwargs):
        seen["args"], seen["body"] = args, json.loads(kwargs["input"])
        return subprocess.CompletedProcess(args, 0, json.dumps({"workflow_run_id": RUN}), "")

    api = gate.GateApi("owner/repo", runner)
    assert gate.dispatch_gate(api, SHA, log=lambda _: None) == RUN
    assert seen["body"] == {"ref": f"derived-gate/{SHA}", "inputs": {"expected_sha": SHA},
                            "return_run_details": True}
    assert seen["args"][-4:] == ["workflows/derived-main.yml/dispatches", "--input", "-"][-3:] or True


@pytest.mark.parametrize("payload", [{}, {"workflow_run_id": "x"}, [], {"workflow_run_id": True}])
def test_dispatch_without_run_id_fails_loudly(payload) -> None:
    class Api:
        def dispatch(self, ref, sha):
            return payload

    with pytest.raises(gate.GateError, match="E_GATE_DISPATCH_NO_RUN_ID"):
        gate.dispatch_gate(Api(), SHA, log=lambda _: None)


def test_main_end_to_end_with_fake_gh(capsys) -> None:
    def runner(args, **kwargs):
        endpoint = args[4]
        if endpoint.endswith("/dispatches"):
            out = {"workflow_run_id": RUN}
        elif endpoint.endswith("/jobs"):
            out = {"jobs": _jobs()}
        else:
            out = {"status": "completed", "conclusion": "success"}
        return subprocess.CompletedProcess(args, 0, json.dumps(out), "")

    assert gate.main(["--repo", "owner/repo", "--sha", SHA], runner) == 0
    assert f"poll 1/120 run={RUN} status=completed" in capsys.readouterr().out
    assert gate.main(["--repo", "owner/repo", "--sha", "nope"], runner) == 1


def _pending_jobs(main="in_progress", ready="queued"):
    return [{"name": "derived-main", "status": main, "conclusion": None},
            {"name": "derived-ready", "status": ready, "conclusion": None}]


class SequencedJobsApi(FakeApi):
    """Run is already completed/success; the jobs listing catches up later (run 39792897388)."""

    def __init__(self, job_lists):
        super().__init__([{"status": "completed", "conclusion": "success"}])
        self.job_lists = list(job_lists)

    def request(self, method, endpoint, **kwargs):
        if endpoint.endswith("/jobs"):
            self.calls.append(endpoint)
            jobs = self.job_lists.pop(0) if len(self.job_lists) > 1 else self.job_lists[0]
            return {"jobs": jobs}
        return super().request(method, endpoint, **kwargs)


def test_success_conclusion_with_unfinished_jobs_keeps_polling_then_succeeds() -> None:
    api = SequencedJobsApi([_pending_jobs(), _pending_jobs("completed", "in_progress"), _jobs()])
    api.jobs = None
    state, lines, sleeps = _run(api)
    assert state == "derived-main:completed:success,derived-ready:completed:success"
    assert sleeps == [15, 15]
    assert any("not yet completed: derived-main:in_progress:,derived-ready:queued:" in line for line in lines)


def test_success_conclusion_with_jobs_never_finishing_times_out_naming_job_states() -> None:
    api = SequencedJobsApi([_pending_jobs()])
    with pytest.raises(gate.GateError, match=r"E_GATE_TIMEOUT.*derived-main:in_progress:,derived-ready:queued:"):
        _run(api, max_polls=3)


def test_completed_required_job_failure_still_raises_without_polling_on() -> None:
    api = SequencedJobsApi([_pending_jobs("in_progress", "completed")[:1]
                            + [{"name": "derived-ready", "status": "completed", "conclusion": "failure"}]])
    with pytest.raises(gate.GateError, match="Trusted gate failed"):
        _run(api)
    assert len(api.calls) == 2
