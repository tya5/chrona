from subprocess import CalledProcessError

from tools.classify_ci_change import classify_diff, classify_paths
from tools.derived_report_inventory import REPORTS


def test_every_bot_owned_report_uses_strict_code_path():
    from tools.derived_evidence import REPORTS as generator_reports
    assert generator_reports is REPORTS
    for path in generator_reports:
        assert classify_paths(("docs/authored.md", path)) == "code"


def test_classifier_runs_without_installed_project_or_optional_dependencies():
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[3]
    result = subprocess.run([sys.executable, "-S", str(root / "tools/classify_ci_change.py"),
                             "not-a-sha", "b" * 40], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0 and result.stdout == "code\n"


def test_only_documentation_paths_use_fast_path():
    assert classify_paths(("docs/reviews/current/issue-1.md", "AGENTS.md", "README.md", ".ignore")) == "docs"


def test_any_code_or_unknown_path_uses_full_pr_path():
    for path in ("src/a.py", "tests/a.py", "tools/a.py", "schemas/a.json", "conformance/a.py",
                 "examples/a.yaml", "packages/a.py", "pyproject.toml", ".github/workflows/a.yml",
                 "config.txt", "nested/README.md"):
        assert classify_paths(("docs/a.md", path)) == "code"
    assert classify_paths(()) == "code"


def test_diff_classification_includes_deleted_and_rename_endpoints(monkeypatch):
    class Result:
        stdout = b"docs/old.md\0src/new.py\0"

    def fake_run(args, **kwargs):
        assert args[:4] == ["git", "diff", "--name-only", "--no-renames"]
        assert args[-2:] == ["a" * 40, "b" * 40]
        return Result()

    monkeypatch.setattr("tools.classify_ci_change.subprocess.run", fake_run)
    assert classify_diff("a" * 40, "b" * 40) == "code"


def test_diff_failure_and_invalid_sha_fail_closed(monkeypatch):
    def fail(*args, **kwargs):
        raise CalledProcessError(1, args[0])

    monkeypatch.setattr("tools.classify_ci_change.subprocess.run", fail)
    assert classify_diff("a" * 40, "b" * 40) == "code"
    assert classify_diff("not-a-sha", "b" * 40) == "code"
