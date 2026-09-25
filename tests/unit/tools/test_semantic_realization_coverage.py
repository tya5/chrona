from pathlib import Path

import pytest

from chrona.presentation.model.semantic_realization import RealizationFamily, realization_family, realization_families, validate_realization_families
from tools.semantic_realization_coverage import render


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_realization_registry_is_finite_and_resolvable():
    assert tuple(item.family_id for item in realization_families()) == ("table-finish-variance", "annotation-purpose", "table-missing-observation")
    annotation = realization_family("annotation-purpose")
    assert annotation.admitted_states == ("callout", "highlight", "note", "explanatory-arrow")
    assert annotation.primitive_purpose == "annotation-box"


def test_realization_registry_rejects_ambiguous_or_undeclared_equivalence():
    with pytest.raises(ValueError, match="E_PRESENTATION_REALIZATION_INVALID"):
        validate_realization_families((RealizationFamily("same", "x", "text", ("a", "a")),))
    with pytest.raises(ValueError, match="E_PRESENTATION_REALIZATION_INVALID"):
        validate_realization_families((RealizationFamily("same", "x", "text", ("a",), (("missing", "why"),)),))


def test_realization_coverage_is_deterministic_and_reports_completed_annotation_evidence():
    report = render(_root())
    assert report == render(_root())
    assert "# Semantic realization coverage" in report
    assert "`table-finish-variance`" in report and "**realized**" in report
    assert "`annotation-purpose`" in report
    assert "`annotation-arrow-box`, `annotation-callout-box`, `annotation-highlight-box`, `annotation-note-box`" in report


def test_realization_coverage_does_not_inspect_renderers_or_svg():
    source = (_root() / "tools/semantic_realization_coverage.py").read_text(encoding="utf-8")
    assert "renderers" not in source
    assert ".svg" not in source
