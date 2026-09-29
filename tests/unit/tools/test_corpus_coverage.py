import json
from pathlib import Path

from tools.corpus_coverage import (
    CorpusMagnitude, CorpusProject, LaneNameCoverage, PROBES, _values_at,
    lane_name_coverage, magnitude, render, vocabulary,
)


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
    assert "## Semantic corpus magnitude" in first
    assert "## Committed lane-name visibility" in first
    assert "| halcyon-1 | 29 | 29 | 24 | 29 |" in first
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


def test_magnitude_counts_declared_semantic_facts_only(tmp_path):
    project = CorpusProject("scale", tmp_path, (("project", tmp_path / "project.yaml", {
        "objects": {"a": {"schedule": {}}, "b": {}}, "relations": [{"id": "r"}],
    }),))

    assert magnitude(project) == CorpusMagnitude(objects=2, rows=2, relations=1, segments=1)


def test_every_unreferenced_example_presentation_file_has_a_declared_reason():
    """#434: an example View/Theme/Layout nobody renders is listed with a reason, or fails."""
    from pathlib import Path as _Path
    from tools.corpus_coverage import UNREFERENCED_REASONS, unreferenced_presentation_files, validate_unreferenced
    root = _Path(__file__).resolve().parents[3]
    validate_unreferenced(root)
    assert set(unreferenced_presentation_files(root)) == set(UNREFERENCED_REASONS)


def test_lane_name_coverage_deduplicates_members_and_excludes_group_or_synthetic_labels(tmp_path):
    project = tmp_path / "examples" / "sample"
    generated = project / "generated"
    generated.mkdir(parents=True)
    (project / "manifest.yaml").write_text(
        'id: sample\nslides:\n  - id: lanes\n    expectedScene: generated/lanes.scene.json\n', encoding="utf-8",
    )
    (generated / "lanes.scene.json").write_text(json.dumps({"surfaces": [{
        "laneMembers": [{"memberId": "a"}, {"memberId": "a"}, {"memberId": "b"}],
        "primitives": [
            {"kind": "Text", "purpose": "member-label", "laneMemberId": "a", "sourceRef": "a",
             "text": "A", "paint": {"opacity": 1}},
            {"kind": "Text", "purpose": "member-label", "laneMemberId": "a", "sourceRef": "a",
             "text": "A duplicate", "paint": {"opacity": 1}},
            {"kind": "Text", "purpose": "group-header", "laneMemberId": "b", "sourceRef": "b",
             "text": "B", "paint": {"opacity": 1}},
            {"kind": "Text", "purpose": "member-label", "laneMemberId": "b", "sourceRef": "synthetic",
             "text": "B", "paint": {"opacity": 1}},
        ],
    }]}), encoding="utf-8")

    assert lane_name_coverage(tmp_path) == (LaneNameCoverage("sample", "lanes", 1, 2),)
