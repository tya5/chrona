"""Remove only terminal temporary refs created by the derived-main gate."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import re
import subprocess
import sys
from typing import Any, Callable, Iterable


_SHA = re.compile(r"[0-9a-f]{40}\Z")
_GATE_PREFIX = "derived-gate/"
_WORKFLOW = "derived-main.yml"
_RUNS_API_LIMIT = 1000


class GitHubApiError(RuntimeError):
    """An API request failed; only a true missing ref is treated as absent."""

    def __init__(self, method: str, endpoint: str, status: int | None, detail: str):
        self.method = method
        self.endpoint = endpoint
        self.status = status
        self.detail = detail.strip()
        super().__init__(f"GitHub API {method} {endpoint} failed"
                         + (f" (HTTP {status})" if status is not None else "")
                         + (f": {self.detail}" if self.detail else ""))


class IncompleteListing(RuntimeError):
    """The API response cannot prove that every matching run was inspected."""


@dataclass(frozen=True)
class GateRef:
    ref: str
    sha: str


class GitHubApi:
    """Small injectable gh-api boundary used by the CLI and unit tests."""

    def __init__(self, repo: str, runner: Callable[..., Any] = subprocess.run):
        parts = repo.split("/")
        if (len(parts) != 2 or any(part in {"", ".", ".."} for part in parts)
                or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)):
            raise ValueError("repository must be OWNER/REPO")
        self.repo = repo
        self.runner = runner

    def request(self, method: str, endpoint: str, *, fields: Iterable[tuple[str, str]] = (),
                paginate: bool = False) -> Any:
        args = ["gh", "api", "--method", method]
        if paginate:
            args.extend(("--paginate", "--slurp"))
        args.append(endpoint)
        for key, value in fields:
            args.extend(("-f", f"{key}={value}"))
        result = self.runner(args, text=True, capture_output=True, check=False)
        if result.returncode:
            text = result.stderr or ""
            status_match = re.search(r"HTTP\s+(\d{3})", text)
            raise GitHubApiError(method, endpoint,
                                 int(status_match.group(1)) if status_match else None, text)
        if method == "DELETE" and not result.stdout.strip():
            return None
        try:
            return json.loads(result.stdout)
        except (TypeError, json.JSONDecodeError) as error:
            raise GitHubApiError(method, endpoint, None, "response was not valid JSON") from error

    def get_ref(self, sha: str) -> GateRef | None:
        endpoint = f"repos/{self.repo}/git/ref/heads/{_GATE_PREFIX}{sha}"
        try:
            payload = self.request("GET", endpoint)
        except GitHubApiError as error:
            if error.status == 404:
                return None
            raise
        ref = payload.get("ref") if isinstance(payload, dict) else None
        target = payload.get("object") if isinstance(payload, dict) else None
        if (ref != f"refs/heads/{_GATE_PREFIX}{sha}" or not isinstance(target, dict)
                or target.get("type") != "commit" or target.get("sha") != sha):
            return None
        return GateRef(ref, sha)

    def list_refs(self) -> tuple[GateRef, ...]:
        endpoint = f"repos/{self.repo}/git/matching-refs/heads/{_GATE_PREFIX}"
        pages = self.request("GET", endpoint, paginate=True)
        if not isinstance(pages, list):
            raise IncompleteListing("matching-ref response was not paginated JSON")
        refs: list[GateRef] = []
        prefix = f"refs/heads/{_GATE_PREFIX}"
        for page in pages:
            if not isinstance(page, list):
                raise IncompleteListing("matching-ref page was not a list")
            for item in page:
                if not isinstance(item, dict):
                    continue
                full_ref = item.get("ref")
                suffix = full_ref[len(prefix):] if isinstance(full_ref, str) and full_ref.startswith(prefix) else ""
                obj = item.get("object")
                if (_SHA.fullmatch(suffix) and isinstance(obj, dict)
                        and obj.get("type") == "commit" and obj.get("sha") == suffix):
                    refs.append(GateRef(full_ref, suffix))
        return tuple(refs)

    def matching_runs(self, sha: str) -> tuple[dict[str, Any], ...]:
        branch = f"{_GATE_PREFIX}{sha}"
        endpoint = f"repos/{self.repo}/actions/workflows/{_WORKFLOW}/runs"
        pages = self.request("GET", endpoint,
                             fields=(("event", "workflow_dispatch"), ("branch", branch), ("per_page", "100")),
                             paginate=True)
        if not isinstance(pages, list) or not pages:
            raise IncompleteListing("workflow run listing returned no pages")
        total: int | None = None
        runs: list[dict[str, Any]] = []
        for page in pages:
            if not isinstance(page, dict) or not isinstance(page.get("workflow_runs"), list):
                raise IncompleteListing("workflow run page has no workflow_runs list")
            page_total = page.get("total_count")
            if not isinstance(page_total, int) or page_total < 0:
                raise IncompleteListing("workflow run page has no valid total_count")
            if total is None:
                total = page_total
            elif page_total != total:
                raise IncompleteListing("workflow run total_count changed during pagination")
            runs.extend(item for item in page["workflow_runs"] if isinstance(item, dict))
        # GitHub caps workflow-run pagination at 1,000 results. At the cap we
        # cannot prove there is no unobserved active run, so fail closed.
        run_ids = [run.get("id") for run in runs]
        if (total is None or total >= _RUNS_API_LIMIT or len(runs) != total
                or any(not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0
                       for run_id in run_ids)
                or len(set(run_ids)) != len(run_ids)):
            raise IncompleteListing("workflow run listing may be truncated")
        return tuple(runs)

    def delete_ref(self, sha: str) -> None:
        endpoint = f"repos/{self.repo}/git/refs/heads/{_GATE_PREFIX}{sha}"
        try:
            self.request("DELETE", endpoint)
        except GitHubApiError as error:
            if error.status == 404:
                return
            raise


def _terminal_run_set(api: GitHubApi, sha: str) -> bool:
    try:
        runs = api.matching_runs(sha)
    except IncompleteListing:
        return False
    if not runs:
        return False
    branch = f"{_GATE_PREFIX}{sha}"
    return all(
        run.get("head_sha") == sha
        and run.get("head_branch") == branch
        and run.get("event") == "workflow_dispatch"
        and run.get("status") == "completed"
        for run in runs
    )


def cleanup_candidate(api: GitHubApi, sha: str, *, dry_run: bool = False) -> str:
    """Recheck candidate identity and all matching runs immediately before delete."""
    if not _SHA.fullmatch(sha):
        raise ValueError("candidate must be a lowercase 40-character commit SHA")
    first_ref = api.get_ref(sha)
    if first_ref is None or not _terminal_run_set(api, sha):
        return "kept"
    # Re-read both the immutable ref and run set; a stale selection is not authority.
    current_ref = api.get_ref(sha)
    if current_ref != first_ref or not _terminal_run_set(api, sha):
        return "kept"
    if dry_run:
        return "would-delete"
    api.delete_ref(sha)
    return "deleted"


def sweep(api: GitHubApi, *, dry_run: bool = False) -> tuple[tuple[str, str], ...]:
    """Apply candidate policy only to well-formed immutable gate refs."""
    return tuple((ref.sha, cleanup_candidate(api, ref.sha, dry_run=dry_run))
                 for ref in api.list_refs())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="GitHub repository OWNER/REPO")
    commands = parser.add_subparsers(dest="command", required=True)
    candidate = commands.add_parser("candidate", help="clean one exact derived-gate SHA")
    candidate.add_argument("--sha", required=True)
    candidate.add_argument("--dry-run", action="store_true")
    sweep_parser = commands.add_parser("sweep", help="clean terminal derived-gate refs")
    sweep_parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        api = GitHubApi(args.repo)
        if args.command == "candidate":
            result = cleanup_candidate(api, args.sha, dry_run=args.dry_run)
            print(f"{result}: {_GATE_PREFIX}{args.sha}")
        else:
            for sha, result in sweep(api, dry_run=args.dry_run):
                print(f"{result}: {_GATE_PREFIX}{sha}")
    except (GitHubApiError, IncompleteListing, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
