from pathlib import Path

from tools.corpus_coverage import CorpusProject, PROBES, render


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_repository_coverage_is_deterministic_and_lists_all_registers():
    root = _root()

    first = render(root)

    assert first == render(root)
    assert "| Project | `deadline` |" in first
    assert "examples/halcyon-1/snapshots/baseline-2027-06.yaml" in first
    assert "examples/orion-asic/extensions/semiconductor-development.yaml" in first


def test_register_predicates_do_not_count_undeclared_resource_kinds(tmp_path):
    project = CorpusProject("empty", tmp_path, (("project", tmp_path / "project.yaml", {"objects": {}}),))

    assert all(not probe.predicate(project) for probe in PROBES)
