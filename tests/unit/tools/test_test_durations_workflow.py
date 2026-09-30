"""The `.test_durations` refresh is automated, bounded, and documented (#657 row 4)."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
WORKFLOW_PATH = ROOT / ".github/workflows/test-durations.yml"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_the_refresh_runs_weekly_and_on_demand_but_never_on_push_or_pull_request():
    triggers = _workflow()[True]  # PyYAML reads the bare key `on` as True
    assert set(triggers) == {"schedule", "workflow_dispatch"}
    assert triggers["schedule"] and "cron" in triggers["schedule"][0]


def test_the_refresh_measures_every_test_and_opens_a_pull_request_not_a_push_to_main():
    workflow = _workflow()
    runs = "\n".join(step.get("run", "") for step in workflow["jobs"]["refresh"]["steps"])
    assert "pytest -n 4 --store-durations --clean-durations" in runs
    assert "-m " not in runs.split("pytest", 1)[1].split("\n", 1)[0], "corpus tests need durations too"
    assert "gh pr create" in runs and "--base main" in runs
    assert "push --force origin \"$BRANCH\"" in runs and "origin main" not in runs
    assert workflow["permissions"] == {"contents": "write", "pull-requests": "write"}


def test_the_refresh_measures_a_synced_main_commit_not_the_raw_tip():
    """A pre-sync main tip has stale derived evidence, so the corpus reproduction test fails on it (first run, 2026-09-30)."""
    steps = _workflow()["jobs"]["refresh"]["steps"]
    synced = next(step for step in steps if step.get("id") == "synced")
    assert "check_name=derived-main" in synced["run"] and "completed:success" in synced["run"]
    checkout = next(step for step in steps if str(step.get("uses", "")).startswith("actions/checkout"))
    assert checkout["with"]["ref"] == "${{ steps.synced.outputs.sha }}"
    assert steps.index(synced) < steps.index(checkout)


def test_the_refresh_is_documented_in_agents_md():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert ".test_durations" in text and "test-durations.yml" in text
    assert "--store-durations --clean-durations" in text


def test_the_committed_file_is_pytest_split_json():
    data = json.loads((ROOT / ".test_durations").read_text(encoding="utf-8"))
    assert data and all(isinstance(key, str) and "::" in key for key in data)
    assert all(isinstance(value, (int, float)) and value >= 0 for value in data.values())
