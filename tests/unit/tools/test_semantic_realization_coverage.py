import json
from pathlib import Path

import pytest

import tools.semantic_realization_coverage as realization_coverage
from chrona.presentation.model.semantic_realization import RealizationFamily, realization_family, realization_families, validate_realization_families
from tools.presentation_coverage import Slide
from tools.semantic_realization_coverage import SemanticRealizationCoverageError, _evidence, render


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
    for slide in ("target-b", "yuya", "titlecard", "marquee", "sunday"):
        assert f"halcyon-1/{slide}" in report


def _synthetic_annotation_slide(tmp_path, view_body, primitives):
    tmp_path.mkdir(parents=True, exist_ok=True)
    view_path = tmp_path / "view.yaml"
    layout_path = tmp_path / "layout.yaml"
    scene_path = tmp_path / "scene.json"
    view_path.write_text("synthetic view", encoding="utf-8")
    layout_path.write_text("synthetic layout", encoding="utf-8")
    scene_path.write_text(json.dumps({"surfaces": [{"primitives": primitives}]}), encoding="utf-8")
    resources = (
        ("view", view_path, {"body": view_body}),
        ("layout-profile", layout_path, {"viewDefaults": {}}),
        ("theme", tmp_path / "theme.yaml", {}),
        ("color-scheme", tmp_path / "scheme.yaml", {}),
    )
    return Slide("synthetic/slide", tmp_path, resources, scene_path)


def test_annotation_bindings_require_the_matching_completed_scene_role(tmp_path):
    family = realization_family("annotation-purpose")
    bound = _synthetic_annotation_slide(
        tmp_path / "bound",
        {"annotationBindings": [{"kind": "note", "temporalKind": "point", "purpose": "note"}]},
        [{"sourceRef": "project-note-1", "purpose": "annotation-box", "visualRole": "annotation-note-box"}],
    )
    assert _evidence(family, (bound,)) == (("note",), ("annotation-note-box",), ("synthetic/slide",))

    mismatched = _synthetic_annotation_slide(
        tmp_path / "mismatched",
        {"annotationBindings": [{"kind": "risk", "temporalKind": "span", "purpose": "callout"}]},
        [{"sourceRef": "project-risk-1", "purpose": "annotation-box", "visualRole": "annotation-note-box"}],
    )
    assert _evidence(family, (mismatched,)) == (("callout",), (), ("synthetic/slide",))


def test_annotation_purpose_coverage_keeps_original_per_id_scene_evidence(tmp_path):
    slide = _synthetic_annotation_slide(
        tmp_path,
        {"annotations": [{"id": "legacy-callout", "purpose": "callout"}]},
        [{"sourceRef": "legacy-callout", "purpose": "annotation-box", "visualRole": "annotation-callout-box"}],
    )
    assert _evidence(realization_family("annotation-purpose"), (slide,)) == (
        ("callout",), ("annotation-callout-box",), ("synthetic/slide",))


def test_annotation_purpose_coverage_rejects_malformed_binding_source(tmp_path):
    slide = _synthetic_annotation_slide(
        tmp_path, {"annotationBindings": ["not-a-binding"]},
        [{"purpose": "annotation-box", "visualRole": "annotation-note-box"}],
    )
    with pytest.raises(SemanticRealizationCoverageError,
                       match="E_PRESENTATION_REALIZATION_ANNOTATION_SOURCE:annotationBindings\\[0\\]"):
        _evidence(realization_family("annotation-purpose"), (slide,))


def test_realization_coverage_discovers_the_corpus_once_per_report(monkeypatch):
    calls = 0
    original = realization_coverage.discover

    def counted(root):
        nonlocal calls
        calls += 1
        return original(root)

    monkeypatch.setattr(realization_coverage, "discover", counted)
    realization_coverage.render(_root())
    assert calls == 1


def test_realization_coverage_does_not_inspect_renderers_or_svg():
    source = (_root() / "tools/semantic_realization_coverage.py").read_text(encoding="utf-8")
    assert "renderers" not in source
    assert ".svg" not in source
