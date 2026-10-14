"""Freeze and validate the source SHA used by scheduled full conformance."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


_SHA = re.compile(r"[0-9a-f]{40}\Z")
_CHECK_NAME = "derived-main"


class ReadinessSelectionError(ValueError):
    """The requested immutable CI source could not be safely selected."""


def _validated_sha(value: object, *, source: str) -> str:
    if not isinstance(value, str) or _SHA.fullmatch(value) is None:
        raise ReadinessSelectionError(f"{source} did not provide a full lowercase commit SHA")
    return value


def _latest_trusted_check(checks_payload: Mapping[str, Any]) -> Mapping[str, Any]:
    check_runs = checks_payload.get("check_runs")
    if not isinstance(check_runs, list):
        raise ReadinessSelectionError("derived-main check response has no check_runs list")
    total_count = checks_payload.get("total_count")
    if isinstance(total_count, bool) or not isinstance(total_count, int) or total_count < 0:
        raise ReadinessSelectionError("derived-main check response has an invalid total_count")
    if total_count > len(check_runs):
        raise ReadinessSelectionError(
            "derived-main check response is incomplete; refusing to infer the latest readiness run"
        )
    trusted = [
        check for check in check_runs
        if isinstance(check, Mapping)
        and check.get("name") == _CHECK_NAME
        and isinstance(check.get("app"), Mapping)
        and check["app"].get("slug") == "github-actions"
    ]
    if not trusted:
        raise ReadinessSelectionError("current main SHA has no trusted derived-main check run")

    def key(check: Mapping[str, Any]) -> tuple[str, int]:
        timestamp = check.get("started_at") or check.get("created_at") or ""
        try:
            run_id = int(check.get("id", -1))
        except (TypeError, ValueError):
            run_id = -1
        return str(timestamp), run_id

    return max(trusted, key=key)


def resolve_ci_sha(
    event_name: str,
    event_sha: str,
    *,
    repository: str,
    select_ready_main: bool,
    expected_sha: str = "",
    api_read: Callable[[str], Mapping[str, Any]],
) -> str:
    """Return event SHA or one frozen, exact-SHA ready main commit.

    ``api_read`` is called only twice in ready-main mode: once to resolve the
    main ref and once to inspect that immutable commit's checks. This function
    never polls or searches ancestor commits.
    """
    event_sha = _validated_sha(event_sha, source="GitHub event")
    ready_mode = event_name == "schedule" or (event_name == "workflow_dispatch" and select_ready_main)
    if event_name == "workflow_dispatch" and select_ready_main and expected_sha:
        raise ReadinessSelectionError("select_ready_main cannot be combined with expected_sha")
    if event_name == "schedule" and expected_sha:
        raise ReadinessSelectionError("scheduled selection cannot accept expected_sha")
    if not ready_mode:
        return event_sha

    main_ref = api_read(f"repos/{repository}/git/ref/heads/main")
    object_value = main_ref.get("object") if isinstance(main_ref, Mapping) else None
    main_sha = _validated_sha(
        object_value.get("sha") if isinstance(object_value, Mapping) else None,
        source="current main ref",
    )
    checks = api_read(
        f"repos/{repository}/commits/{main_sha}/check-runs"
    )
    latest = _latest_trusted_check(checks)
    if latest.get("status") != "completed" or latest.get("conclusion") != "success":
        state = f"{latest.get('status', 'missing')}:{latest.get('conclusion') or 'none'}"
        raise ReadinessSelectionError(
            f"current main SHA {main_sha} is not ready: latest trusted derived-main is {state}"
        )
    return main_sha


def _gh_read(repository_path: str) -> Mapping[str, Any]:
    # Supplying -f/-F fields otherwise makes gh api default to POST.
    command = ["gh", "api", "--method", "GET", repository_path]
    if repository_path.endswith("/check-runs"):
        command.extend(("-f", f"check_name={_CHECK_NAME}", "-f", "filter=all", "-F", "per_page=100"))
    try:
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, timeout=30
        )
        value = json.loads(result.stdout)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired,
            json.JSONDecodeError) as error:
        raise ReadinessSelectionError(
            f"GitHub readiness lookup failed ({type(error).__name__})"
        ) from error
    if not isinstance(value, Mapping):
        raise ReadinessSelectionError("GitHub readiness lookup returned a non-object response")
    return value


def main() -> int:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    selected = os.environ.get("SELECT_READY_MAIN", "").lower() == "true"
    try:
        sha = resolve_ci_sha(
            event_name,
            os.environ.get("GITHUB_SHA", ""),
            repository=os.environ.get("GITHUB_REPOSITORY", ""),
            select_ready_main=selected,
            expected_sha=os.environ.get("EXPECTED_SHA", ""),
            api_read=_gh_read,
        )
        output_path = os.environ.get("GITHUB_OUTPUT")
        if not output_path:
            raise ReadinessSelectionError("GITHUB_OUTPUT is not available")
        with Path(output_path).open("a", encoding="utf-8") as output:
            output.write(f"sha={sha}\n")
    except ReadinessSelectionError as error:
        print(f"E_SCHEDULED_READINESS: {error}", file=sys.stderr)
        return 1
    print(f"CI source SHA frozen: {sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
