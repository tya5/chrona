"""Execute the actual workflow gate with offline gh/git/sleep stand-ins."""
import os
from pathlib import Path
import subprocess

import pytest
import yaml

from tools.classify_ci_change import classify_paths
from tools.derived_report_inventory import REPORTS

BASE, HEAD, TIP = "a" * 40, "b" * 40, "c" * 40


def _run(tmp_path, **overrides):
    root = Path(__file__).resolve().parents[3]
    workflow = yaml.safe_load((root / ".github/workflows/conformance.yml").read_text())
    script = next(step["run"] for step in workflow["jobs"]["derived-ready"]["steps"] if "run" in step)
    assert '.app.slug == "github-actions"' in script
    assert "sort_by([.started_at // .created_at, .id])" in script
    calls = tmp_path / "calls"
    programs = {
        "gh": '''#!/bin/sh
printf '%s\\n' "gh $*" >> "$CALLS"
case "$*" in
  */pulls/*)
    case "$*" in
      *@tsv*) printf '%s\\t%s\\t%s\\n' "$CURRENT_HEAD" "$CURRENT_REF" "$MERGEABLE";;
      *) printf '%s\\n' "$CURRENT_HEAD";;
    esac;;
  */check-runs*) printf '%s\\n' "$TRUSTED";;
  *) exit 9;;
esac
''',
        "git": '''#!/bin/sh
printf '%s\\n' "git $*" >> "$CALLS"
printf '%s\\trefs/heads/main\\n' "$CURRENT_TIP"
''',
        "sleep": '''#!/bin/sh
printf '%s\\n' "sleep $*" >> "$CALLS"
exit 98
''',
    }
    for name, content in programs.items():
        path = tmp_path / name
        path.write_text(content)
        path.chmod(0o755)
    env = {**os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"],
        "CALLS": str(calls), "EVENT_NAME": "pull_request", "PR_BASE_SHA": BASE,
        "PR_BASE_REF": "main", "PR_NUMBER": "42", "PR_HEAD_SHA": HEAD,
        "GITHUB_REPOSITORY": "tya5/chrona", "PR_KIND": "docs", "PREVIEW": "success",
        "CONFORMANCE": "success", "PYTEST": "skipped", "NEWEST": "skipped",
        "CURRENT_HEAD": HEAD, "CURRENT_REF": "main", "MERGEABLE": "true",
        "TRUSTED": "completed:success", "CURRENT_TIP": TIP, **overrides}
    result = subprocess.run(["bash", "-euo", "pipefail", "-c", script], env=env,
                            capture_output=True, text=True, timeout=5)
    return result, calls.read_text() if calls.exists() else ""


def test_docs_on_ready_non_tip_base_pass_without_sync_wait_or_tip_query(tmp_path):
    result, calls = _run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "no new sync wait" in result.stdout
    assert "sleep" not in calls and "git ls-remote" not in calls
    assert calls.count("/check-runs") == 1


@pytest.mark.parametrize("path", ["src/core.py", *REPORTS])
def test_code_and_every_generated_doc_still_require_ready_tip(tmp_path, path):
    kind = classify_paths((path,))
    assert kind == "code"
    result, calls = _run(tmp_path, PR_KIND=kind, PYTEST="success", NEWEST="success")
    assert result.returncode != 0
    assert "git ls-remote" in calls


def test_code_on_exact_ready_tip_still_passes(tmp_path):
    result, calls = _run(tmp_path, PR_KIND="code", PYTEST="success", NEWEST="success", CURRENT_TIP=BASE)
    assert result.returncode == 0, result.stderr
    assert "git ls-remote" in calls


@pytest.mark.parametrize("overrides", [
    {"TRUSTED": ""}, {"TRUSTED": "in_progress:"}, {"TRUSTED": "completed:failure"},
    {"MERGEABLE": "false"}, {"MERGEABLE": "null"}, {"CURRENT_HEAD": TIP},
    {"CURRENT_REF": "other"}, {"PR_BASE_REF": "other"}, {"PR_KIND": "unknown"},
    {"PREVIEW": "failure"}, {"CONFORMANCE": "failure"}, {"PYTEST": "failure"},
    {"NEWEST": "failure"},
])
def test_docs_fail_closed_without_polling_when_evidence_is_missing_or_failed(tmp_path, overrides):
    result, calls = _run(tmp_path, **overrides)
    assert result.returncode != 0
    assert "sleep" not in calls and "git ls-remote" not in calls
