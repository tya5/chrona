from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import json
import subprocess

import pytest

from tools.derived_gate_cleanup import (
    GitHubApi,
    GitHubApiError,
    IncompleteListing,
    cleanup_candidate,
    sweep,
)


SHA = "a" * 40
OTHER = "b" * 40
REPO = "owner/repo"
REF_ENDPOINT = f"repos/{REPO}/git/ref/heads/derived-gate/{SHA}"
RUN_ENDPOINT = f"repos/{REPO}/actions/workflows/derived-main.yml/runs"
REFS_ENDPOINT = f"repos/{REPO}/git/matching-refs/heads/derived-gate/"


@dataclass(frozen=True)
class Response:
    payload: object | None = None
    status: int = 0
    stderr: str = ""
    empty: bool = False

    def process(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        stdout = "" if self.empty else json.dumps(self.payload)
        return subprocess.CompletedProcess(args, self.status, stdout, self.stderr)


def _ok(payload: object) -> Response:
    return Response(payload)


def _http(status: int) -> Response:
    return Response(status=1, stderr=f"gh: HTTP {status}: response")


def _ref(sha: str = SHA, *, object_sha: str | None = None, object_type: str = "commit") -> dict:
    return {
        "ref": f"refs/heads/derived-gate/{sha}",
        "object": {"sha": object_sha or sha, "type": object_type},
    }


def _run(sha: str = SHA, *, branch: str | None = None, event: str = "workflow_dispatch",
         status: str = "completed", conclusion: str = "success", run_id: int = 1) -> dict:
    return {
        "id": run_id,
        "head_sha": sha,
        "head_branch": branch or f"derived-gate/{sha}",
        "event": event,
        "status": status,
        "conclusion": conclusion,
    }


def _run_page(*runs: dict, total: int | None = None) -> dict:
    return {"total_count": len(runs) if total is None else total, "workflow_runs": list(runs)}


DELETE_ENDPOINT = f"repos/{REPO}/git/refs/heads/derived-gate/{SHA}"


class FakeGh:
    """Inject gh subprocess results by method/endpoint; a final response repeats."""

    def __init__(self) -> None:
        self.responses: dict[tuple[str, str], list[Response]] = defaultdict(list)
        self.calls: list[list[str]] = []

    def queue(self, method: str, endpoint: str, *responses: Response) -> None:
        self.responses[(method, endpoint)].extend(responses)

    def __call__(self, args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        method = args[args.index("--method") + 1]
        endpoint = next(value for value in args if value.startswith("repos/"))
        values = self.responses[(method, endpoint)]
        if not values:
            raise AssertionError(f"unexpected gh api call: {method} {endpoint}")
        response = values.pop(0) if len(values) > 1 else values[0]
        return response.process(args)


def _terminal_candidate(gh: FakeGh, *, run_pages: tuple[Response, ...] | None = None) -> None:
    gh.queue("GET", REF_ENDPOINT, _ok(_ref()), _ok(_ref()))
    gh.queue("GET", RUN_ENDPOINT, *(run_pages or (_ok([_run_page(_run())]),) * 2))
    gh.queue("DELETE", DELETE_ENDPOINT, Response(empty=True))


def test_candidate_deletes_only_after_all_exact_workflow_runs_are_completed() -> None:
    gh = FakeGh()
    pages = (_ok([_run_page(_run(conclusion="success", run_id=1),
                            _run(conclusion="failure", run_id=2))]),)
    _terminal_candidate(gh, run_pages=pages)

    assert cleanup_candidate(GitHubApi(REPO, runner=gh), SHA) == "deleted"
    assert sum(call[call.index("--method") + 1] == "DELETE" for call in gh.calls) == 1
    run_call = next(call for call in gh.calls if RUN_ENDPOINT in call)
    assert "--paginate" in run_call and "--slurp" in run_call
    assert {"event=workflow_dispatch", f"branch=derived-gate/{SHA}", "per_page=100"} <= set(
        run_call[index + 1] for index, value in enumerate(run_call[:-1]) if value == "-f"
    )


@pytest.mark.parametrize(
    "run,total",
    [
        (_run(status="queued"), None),
        (_run(status="in_progress"), None),
        (_run(status="unknown"), None),
        (_run(status="completed", branch=f"derived-gate/{OTHER}"), None),
        (_run(status="completed", event="push"), None),
        (_run(status="completed", sha=OTHER), None),
        (_run(status="completed"), 1000),
    ],
)
def test_candidate_keeps_active_mismatched_or_incomplete_run_evidence(run: dict, total: int | None) -> None:
    gh = FakeGh()
    gh.queue("GET", REF_ENDPOINT, _ok(_ref()), _ok(_ref()))
    page = _run_page(run, total=total)
    gh.queue("GET", RUN_ENDPOINT, _ok([page]))

    assert cleanup_candidate(GitHubApi(REPO, runner=gh), SHA) == "kept"
    assert not any(call[call.index("--method") + 1] == "DELETE" for call in gh.calls)


def test_candidate_keeps_when_no_exact_run_is_found() -> None:
    gh = FakeGh()
    gh.queue("GET", REF_ENDPOINT, _ok(_ref()))
    gh.queue("GET", RUN_ENDPOINT, _ok([_run_page()]))
    assert cleanup_candidate(GitHubApi(REPO, runner=gh), SHA) == "kept"


def test_candidate_rechecks_ref_and_run_state_before_delete() -> None:
    gh = FakeGh()
    gh.queue("GET", REF_ENDPOINT, _ok(_ref()), _http(404))
    gh.queue("GET", RUN_ENDPOINT, _ok([_run_page(_run())]))
    assert cleanup_candidate(GitHubApi(REPO, runner=gh), SHA) == "kept"
    assert not any(call[call.index("--method") + 1] == "DELETE" for call in gh.calls)

    gh = FakeGh()
    gh.queue("GET", REF_ENDPOINT, _ok(_ref()), _ok(_ref()))
    gh.queue("GET", RUN_ENDPOINT, _ok([_run_page(_run())]), _ok([_run_page(_run(status="queued"))]))
    assert cleanup_candidate(GitHubApi(REPO, runner=gh), SHA) == "kept"
    assert not any(call[call.index("--method") + 1] == "DELETE" for call in gh.calls)


def test_missing_ref_is_idempotent_but_other_api_errors_are_visible() -> None:
    missing = FakeGh()
    missing.queue("GET", REF_ENDPOINT, _http(404))
    assert cleanup_candidate(GitHubApi(REPO, runner=missing), SHA) == "kept"

    forbidden = FakeGh()
    forbidden.queue("GET", REF_ENDPOINT, _http(403))
    with pytest.raises(GitHubApiError, match="HTTP 403"):
        cleanup_candidate(GitHubApi(REPO, runner=forbidden), SHA)


def test_missing_ref_during_delete_is_idempotent() -> None:
    gh = FakeGh()
    gh.queue("GET", REF_ENDPOINT, _ok(_ref()), _ok(_ref()))
    gh.queue("GET", RUN_ENDPOINT, _ok([_run_page(_run())]))
    gh.queue("DELETE", DELETE_ENDPOINT, _http(404))
    assert cleanup_candidate(GitHubApi(REPO, runner=gh), SHA) == "deleted"


def test_malformed_or_unrelated_candidate_sha_is_refused_before_api_calls() -> None:
    gh = FakeGh()
    with pytest.raises(ValueError, match="lowercase 40-character"):
        cleanup_candidate(GitHubApi(REPO, runner=gh), "refs/heads/main")
    with pytest.raises(ValueError, match="OWNER/REPO"):
        GitHubApi("../repo", runner=gh)
    assert gh.calls == []


def test_run_pagination_must_be_complete_and_consistent() -> None:
    gh = FakeGh()
    gh.queue("GET", RUN_ENDPOINT,
             _ok([_run_page(_run(run_id=1), total=2), _run_page(_run(run_id=2), total=2)]))
    assert GitHubApi(REPO, runner=gh).matching_runs(SHA) == (_run(run_id=1), _run(run_id=2))

    for pages in (
        [_run_page(_run(), total=2)],
        [_run_page(_run(), total=1), _run_page(_run(), total=2)],
        [_run_page(_run(), total=1000)],
        [_run_page(_run(), _run(run_id=2), total=1)],
        [_run_page(_run(), _run(run_id=1))],
        [{"total_count": 1, "workflow_runs": [{"head_sha": SHA}]}],
        [_run_page({**_run(), "id": 0})],
    ):
        gh = FakeGh()
        gh.queue("GET", RUN_ENDPOINT, _ok(pages))
        with pytest.raises(IncompleteListing):
            GitHubApi(REPO, runner=gh).matching_runs(SHA)


def test_sweep_only_considers_well_formed_matching_gate_refs() -> None:
    other_ref_endpoint = f"repos/{REPO}/git/ref/heads/derived-gate/{OTHER}"
    gh = FakeGh()
    gh.queue("GET", REFS_ENDPOINT, _ok([[
        _ref(),
        _ref("not-a-sha"),
        _ref(OTHER, object_sha=SHA),
        _ref(OTHER, object_type="tree"),
    ]]))
    gh.queue("GET", REF_ENDPOINT, _ok(_ref()), _ok(_ref()))
    gh.queue("GET", RUN_ENDPOINT, _ok([_run_page(_run())]))
    gh.queue("DELETE", DELETE_ENDPOINT, Response(empty=True))

    assert sweep(GitHubApi(REPO, runner=gh)) == ((SHA, "deleted"),)
    assert not any(other_ref_endpoint in call for call in gh.calls)


def test_sweep_keeps_live_ref_and_dry_run_never_deletes() -> None:
    gh = FakeGh()
    gh.queue("GET", REFS_ENDPOINT, _ok([[_ref()]]))
    gh.queue("GET", REF_ENDPOINT, _ok(_ref()), _ok(_ref()))
    gh.queue("GET", RUN_ENDPOINT, _ok([_run_page(_run(status="in_progress"))]))
    assert sweep(GitHubApi(REPO, runner=gh)) == ((SHA, "kept"),)
    assert not any(call[call.index("--method") + 1] == "DELETE" for call in gh.calls)
    gh = FakeGh()
    gh.queue("GET", REF_ENDPOINT, _ok(_ref()), _ok(_ref()))
    gh.queue("GET", RUN_ENDPOINT, _ok([_run_page(_run())]))
    assert cleanup_candidate(GitHubApi(REPO, runner=gh), SHA, dry_run=True) == "would-delete"
    assert not any(call[call.index("--method") + 1] == "DELETE" for call in gh.calls)


def test_sweep_paginates_refs_and_deletes_terminal_but_keeps_active_candidate() -> None:
    other_ref = f"repos/{REPO}/git/ref/heads/derived-gate/{OTHER}"
    other_delete = f"repos/{REPO}/git/refs/heads/derived-gate/{OTHER}"
    gh = FakeGh()
    gh.queue("GET", REFS_ENDPOINT, _ok([[_ref()], [_ref(OTHER)]]))
    gh.queue("GET", REF_ENDPOINT, _ok(_ref()), _ok(_ref()))
    gh.queue("GET", other_ref, _ok(_ref(OTHER)), _ok(_ref(OTHER)))
    gh.queue("GET", RUN_ENDPOINT,
             _ok([_run_page(_run(SHA))]), _ok([_run_page(_run(SHA))]),
             _ok([_run_page(_run(OTHER, status="in_progress"))]),
             _ok([_run_page(_run(OTHER, status="in_progress"))]))
    gh.queue("DELETE", DELETE_ENDPOINT, Response(empty=True))

    assert sweep(GitHubApi(REPO, runner=gh)) == ((SHA, "deleted"), (OTHER, "kept"))
    assert any("--paginate" in call and REFS_ENDPOINT in call for call in gh.calls)
    deleted = [call for call in gh.calls if call[call.index("--method") + 1] == "DELETE"]
    assert len(deleted) == 1 and other_delete not in deleted[0]
