"""The scheduled selector freezes one exact current-main SHA or fails closed."""
from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace

import pytest

from tools import scheduled_readiness
from tools.scheduled_readiness import ReadinessSelectionError, resolve_ci_sha


EVENT_SHA = "1" * 40
READY_SHA = "2" * 40
ADVANCED_SHA = "3" * 40


def _check(run_id: int, *, status: str, conclusion: str | None,
           name: str = "derived-main", app: str = "github-actions",
           created: str = "2026-10-14T00:00:00Z") -> dict:
    return {
        "id": run_id,
        "name": name,
        "app": {"slug": app},
        "status": status,
        "conclusion": conclusion,
        "created_at": created,
        "started_at": created,
    }


def _api_for(checks, *, sha=READY_SHA, on_ref=None):
    calls: list[str] = []

    def read(path: str):
        calls.append(path)
        if len(calls) == 1:
            ref_sha = sha
            if on_ref is not None:
                on_ref()
            return {"object": {"sha": ref_sha}}
        return {"total_count": len(checks), "check_runs": checks}

    return read, calls


def test_non_schedule_and_default_dispatch_preserve_the_event_sha_without_api_reads():
    for event, select in (("push", False), ("pull_request", False), ("workflow_dispatch", False)):
        read, calls = _api_for([])
        assert resolve_ci_sha(event, EVENT_SHA, repository="owner/repo",
                              select_ready_main=select, api_read=read) == EVENT_SHA
        assert calls == []


def test_schedule_freezes_current_main_only_after_its_latest_trusted_check_succeeds():
    older_success = _check(10, status="completed", conclusion="success",
                           created="2026-10-13T00:00:00Z")
    latest_success = _check(11, status="completed", conclusion="success",
                            created="2026-10-14T00:00:00Z")
    untrusted_newer = _check(12, status="completed", conclusion="failure",
                             app="other-app", created="2026-10-15T00:00:00Z")
    read, calls = _api_for([older_success, latest_success, untrusted_newer])

    assert resolve_ci_sha("schedule", EVENT_SHA, repository="owner/repo",
                           select_ready_main=False, api_read=read) == READY_SHA
    assert calls == [
        "repos/owner/repo/git/ref/heads/main",
        f"repos/owner/repo/commits/{READY_SHA}/check-runs",
    ]


def test_schedule_started_during_sync_rejects_the_current_source_only_tip_without_fallback():
    source_only_tip = ADVANCED_SHA
    read, calls = _api_for([], sha=source_only_tip)

    with pytest.raises(ReadinessSelectionError, match="no trusted derived-main"):
        resolve_ci_sha("schedule", EVENT_SHA, repository="owner/repo",
                       select_ready_main=False, api_read=read)

    assert calls == [
        "repos/owner/repo/git/ref/heads/main",
        f"repos/owner/repo/commits/{source_only_tip}/check-runs",
    ]


def test_incomplete_latest_check_response_fails_closed_instead_of_using_page_success():
    checks = [_check(1, status="completed", conclusion="success")]
    read, _calls = _api_for(checks)

    def incomplete(path: str):
        value = read(path)
        if path.endswith("/check-runs"):
            return {**value, "total_count": 101}
        return value

    with pytest.raises(ReadinessSelectionError, match="response is incomplete"):
        resolve_ci_sha("schedule", EVENT_SHA, repository="owner/repo",
                       select_ready_main=False, api_read=incomplete)


@pytest.mark.parametrize(
    "checks",
    [
        [],
        [_check(1, status="queued", conclusion=None)],
        [
            _check(1, status="completed", conclusion="success", created="2026-10-13T00:00:00Z"),
            _check(2, status="completed", conclusion="failure", created="2026-10-14T00:00:00Z"),
        ],
    ],
)
def test_pending_missing_or_failed_latest_readiness_never_falls_back_to_older_sha(checks):
    read, calls = _api_for(checks)
    with pytest.raises(ReadinessSelectionError, match="not ready|no trusted"):
        resolve_ci_sha("schedule", EVENT_SHA, repository="owner/repo",
                       select_ready_main=False, api_read=read)
    assert len(calls) == 2
    assert calls[1].endswith(f"/commits/{READY_SHA}/check-runs")


def test_main_advancing_after_ref_read_cannot_change_the_frozen_sha():
    live_main = {"sha": READY_SHA}

    def advance_main():
        live_main["sha"] = ADVANCED_SHA

    read, calls = _api_for([_check(1, status="completed", conclusion="success")],
                           sha=live_main["sha"], on_ref=advance_main)
    frozen = resolve_ci_sha("schedule", EVENT_SHA, repository="owner/repo",
                            select_ready_main=False, api_read=read)

    assert live_main["sha"] == ADVANCED_SHA
    assert frozen == READY_SHA
    assert len(calls) == 2
    assert calls[1].endswith(f"/commits/{frozen}/check-runs")


def test_cli_reads_json_responses_twice_and_writes_one_immutable_output(tmp_path, monkeypatch):
    calls: list[str] = []

    def read(path: str):
        calls.append(path)
        if len(calls) == 1:
            return {"object": {"sha": READY_SHA}}
        checks = [_check(1, status="completed", conclusion="success")]
        return {"total_count": len(checks), "check_runs": checks}

    output = tmp_path / "github-output"
    for key, value in {
        "GITHUB_EVENT_NAME": "schedule",
        "GITHUB_SHA": EVENT_SHA,
        "GITHUB_REPOSITORY": "owner/repo",
        "SELECT_READY_MAIN": "false",
        "EXPECTED_SHA": "",
        "GITHUB_OUTPUT": str(output),
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(scheduled_readiness, "_gh_read", read)

    assert scheduled_readiness.main() == 0
    assert output.read_text(encoding="utf-8") == f"sha={READY_SHA}\n"
    assert len(calls) == 2


def test_opt_in_manual_ready_selection_uses_same_rule_and_rejects_exact_sha_conflict():
    read, calls = _api_for([_check(1, status="completed", conclusion="success")])
    assert resolve_ci_sha("workflow_dispatch", EVENT_SHA, repository="owner/repo",
                          select_ready_main=True, api_read=read) == READY_SHA
    assert len(calls) == 2

    read, calls = _api_for([])
    with pytest.raises(ReadinessSelectionError, match="cannot be combined"):
        resolve_ci_sha("workflow_dispatch", EVENT_SHA, repository="owner/repo",
                       select_ready_main=True, expected_sha=EVENT_SHA, api_read=read)
    assert calls == []


def test_gh_transport_for_check_runs_is_an_explicit_bounded_get(monkeypatch):
    observed = {}

    def run(command, **kwargs):
        observed["command"] = command
        observed["kwargs"] = kwargs
        return SimpleNamespace(stdout=json.dumps({"total_count": 0, "check_runs": []}))

    monkeypatch.setattr(subprocess, "run", run)
    response = scheduled_readiness._gh_read("repos/owner/repo/commits/" + READY_SHA + "/check-runs")

    assert response == {"total_count": 0, "check_runs": []}
    assert observed["command"] == [
        "gh", "api", "--method", "GET",
        f"repos/owner/repo/commits/{READY_SHA}/check-runs",
        "-f", "check_name=derived-main", "-f", "filter=all", "-F", "per_page=100",
    ]
    assert observed["kwargs"]["timeout"] == 30


@pytest.mark.parametrize(
    "failure",
    [
        subprocess.TimeoutExpired("gh api", 30),
        subprocess.CalledProcessError(1, "gh api"),
        SimpleNamespace(stdout="not-json"),
    ],
    ids=["timeout", "http-or-cli-failure", "invalid-json"],
)
def test_gh_transport_failures_become_typed_readiness_errors(monkeypatch, failure):
    def run(_command, **_kwargs):
        if isinstance(failure, SimpleNamespace):
            return failure
        raise failure

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(ReadinessSelectionError, match="GitHub readiness lookup failed"):
        scheduled_readiness._gh_read("repos/owner/repo/git/ref/heads/main")
