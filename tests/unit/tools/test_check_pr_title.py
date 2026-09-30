from pathlib import Path

import pytest
import yaml

from tools.check_pr_title import closing_reference, commit_closing_references, main

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("title", [
    "docs: close #592 pattern owner gap and sequence I592-5",
    "fix #590: candidate output",
    "Fixes #12",
    "feat: resolved #3 in place",
    "chore: closes tya5/chrona#44",
    "docs: fix: #5",
])
def test_a_closing_keyword_before_an_issue_number_is_found(title: str) -> None:
    assert closing_reference(title) is not None


@pytest.mark.parametrize("title", [
    "refactor: extract surface marks and visuals (#592 I3)",
    "fix: keep derived candidate commit log out of Actions outputs",
    "docs: record the #590 protection finding",
    "ci: close the gap in derived-sync",
    "docs: Refs #592 note",
    "feat: unclosed 5",
])
def test_partial_titles_are_accepted(title: str) -> None:
    assert closing_reference(title) is None


def test_the_cli_fails_on_a_keyword_unless_the_pr_is_a_closing_pr() -> None:
    assert main(["check_pr_title.py", "docs: close #592 x"]) == 1
    assert main(["check_pr_title.py", "docs: close #592 x", "--allow-closing"]) == 0
    assert main(["check_pr_title.py", "docs: refs #592 x"]) == 0
    assert main(["check_pr_title.py"]) == 2


def test_the_workflow_runs_on_title_edits_with_read_only_permissions() -> None:
    workflow = yaml.load((ROOT / ".github/workflows/pr-title.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert "edited" in workflow["on"]["pull_request"]["types"]
    assert workflow["permissions"] == {"contents": "read", "pull-requests": "read"}
    job = workflow["jobs"]["pr-title"]
    assert "permissions" not in job
    fetch = next(step for step in job["steps"] if step.get("name", "").startswith("Fetch the commit messages"))
    assert "pulls/$PR_NUMBER/commits" in fetch["run"] and "--paginate" in fetch["run"]
    run = next(step["run"] for step in job["steps"] if step.get("name", "").startswith("Reject closing keywords"))
    assert "tools/check_pr_title.py" in run and "--allow-closing" in run and "--commits" in run


def test_a_commit_body_that_describes_an_accident_with_a_keyword_is_found(tmp_path) -> None:
    """#592 was closed by exactly this: a commit body explaining the first accident (#631)."""
    messages = [
        "ci: reject closing keywords in PR titles\n\nA merged PR's title closes an issue: PR #623 closed #592 mid-work.",
        "docs: note\n\nRefs #592 and the description without a hash: closed issue 592.",
    ]
    found = commit_closing_references(messages)
    assert [subject for subject, _ in found] == ["ci: reject closing keywords in PR titles"]
    assert found[0][1] == "closed #592"
    path = tmp_path / "commits.json"
    import json
    path.write_text(json.dumps(messages), encoding="utf-8")
    assert main(["check_pr_title.py", "ci: fine title", "--commits", str(path)]) == 1
    assert main(["check_pr_title.py", "ci: fine title", "--commits", str(path), "--allow-closing"]) == 0
    path.write_text(json.dumps([messages[1]]), encoding="utf-8")
    assert main(["check_pr_title.py", "ci: fine title", "--commits", str(path)]) == 0
