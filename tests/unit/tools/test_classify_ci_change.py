from subprocess import CalledProcessError

from tools.classify_ci_change import classify_diff, classify_paths


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
