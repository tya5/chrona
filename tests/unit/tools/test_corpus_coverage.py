from pathlib import Path

from tools.corpus_coverage import CorpusProject, PROBES, _values_at, render, vocabulary


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_repository_coverage_is_deterministic_and_lists_all_registers():
    root = _root()

    first = render(root)

    assert first == render(root)
    assert "| Project | `deadline` |" in first
    assert "examples/halcyon-1/snapshots/baseline-2027-06.yaml" in first
    assert "examples/orion-asic/extensions/semiconductor-development.yaml" in first
    assert "## Finite-schema vocabulary" in first
    assert "## Uncovered schema vocabulary" in first
    assert '`objects.*.schedule.mode` | `"rollup"`' in first


def test_vocabulary_is_sorted_and_matches_direct_wildcard_paths():
    root = _root()

    rows = vocabulary(root)

    assert rows == tuple(sorted(rows))
    assert any(row.path == ("objects", "*", "schedule", "mode") and row.value == '"scheduled"' for row in rows)
    assert list(_values_at({"objects": {"item": {"schedule": {"mode": "scheduled"}}}}, ("objects", "*", "schedule", "mode"))) == ["scheduled"]


def test_register_predicates_do_not_count_undeclared_resource_kinds(tmp_path):
    project = CorpusProject("empty", tmp_path, (("project", tmp_path / "project.yaml", {"objects": {}}),))

    assert all(not probe.predicate(project) for probe in PROBES)
