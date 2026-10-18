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


def _scene_slide(tmp_path, name, primitives):
    return _synthetic_annotation_slide(tmp_path / name, {}, primitives)


def _prim(purpose, role, **extra):
    return {"purpose": purpose, "visualRole": role, **extra}


def _rows(slides, classifications, registered):
    from tools.semantic_realization_coverage import purpose_rows
    return purpose_rows(slides, registered=frozenset(registered), classifications=classifications,
                        registered_roles={}, families=())


def test_unclassified_single_role_purpose_fails_and_classified_passes(tmp_path):
    from chrona.presentation.model.semantic_realization import PurposeClassification as C
    slide = _scene_slide(tmp_path, "a", [_prim("one", "r1"), _prim("two", "r2"), _prim("two", "r3")])
    with pytest.raises(ValueError, match="E_PRESENTATION_PURPOSE_UNCLASSIFIED.*one"):
        _rows((slide,), (C("two", "distinct"),), {"one", "two"})
    rows = _rows((slide,), (C("one", "single-role", "one ink"), C("two", "distinct")), {"one", "two"})
    assert {row.purpose: len(row.roles) for row in rows} == {"one": 1, "two": 2}
    # A gap is an accepted classification of a single-role purpose too.
    assert _rows((slide,), (C("one", "gap", "states not distinguished"), C("two", "distinct")), {"one", "two"})


def test_classification_must_match_the_derived_role_count(tmp_path):
    from chrona.presentation.model.semantic_realization import PurposeClassification as C
    slide = _scene_slide(tmp_path, "a", [_prim("one", "r1")])
    with pytest.raises(SemanticRealizationCoverageError, match="E_PRESENTATION_PURPOSE_CLASSIFICATION_STALE.*one"):
        _rows((slide,), (C("one", "distinct"),), {"one"})
    with pytest.raises(SemanticRealizationCoverageError, match="E_PRESENTATION_PURPOSE_CLASSIFICATION_STALE"):
        _rows((slide,), (C("one", "unpainted", "never drawn"),), {"one"})


def test_unpainted_purposes_are_separate_rows_outside_the_denominator(tmp_path):
    from chrona.presentation.model.semantic_realization import PurposeClassification as C
    from tools.semantic_realization_coverage import _purpose_lines, single_role_figure
    slide = _scene_slide(tmp_path, "a", [_prim("one", "r1"), _prim("two", "r2"), _prim("two", "r3")])
    rows = _rows((slide,), (C("one", "single-role", "x"), C("two", "distinct"), C("idle", "unpainted", "not drawn")), {"one", "two", "idle"})
    assert single_role_figure(rows) == (1, 2)
    text = "\n".join(_purpose_lines(rows))
    assert "**1 of 2**" in text and "3 purposes are registered; 1 are registered but not drawn" in text
    assert "### Registered but unpainted purposes" in text and "| `idle` |" in text.split("### Registered but unpainted purposes")[1]
    assert "| `idle` |" not in text.split("### Registered but unpainted purposes")[0]


def test_effective_appearance_role_counts_theme_role_over_visual_role(tmp_path):
    from chrona.presentation.model.semantic_realization import PurposeClassification as C
    slide = _scene_slide(tmp_path, "a", [_prim("one", "same", themeRole="authored-a"), _prim("one", "same", themeRole="authored-b"), _prim("one", "same")])
    (row,) = _rows((slide,), (C("one", "distinct"),), {"one"})
    assert row.roles == ("authored-a", "authored-b", "same")


def test_drawn_purpose_outside_the_vocabulary_fails(tmp_path):
    from chrona.presentation.model.semantic_realization import PurposeClassification as C
    slide = _scene_slide(tmp_path, "a", [_prim("ghost", "r1")])
    with pytest.raises(SemanticRealizationCoverageError, match="E_PRESENTATION_PURPOSE_UNREGISTERED"):
        _rows((slide,), (C("one", "unpainted", "idle"),), {"one"})


def test_classification_registry_covers_every_registered_purpose_and_rejects_unknown():
    from chrona.presentation.model.semantic_realization import PurposeClassification as C, purpose_classifications, validate_purpose_classifications
    from chrona.presentation.model.semantic_registry import purposes
    assert set(validate_purpose_classifications(purpose_classifications(), purposes())) == set(purposes())
    with pytest.raises(ValueError, match="E_PRESENTATION_PURPOSE_CLASSIFICATION_UNKNOWN"):
        validate_purpose_classifications((C("nope", "distinct"),), frozenset())
    with pytest.raises(ValueError, match="E_PRESENTATION_PURPOSE_CLASSIFICATION_INVALID"):
        validate_purpose_classifications((C("a", "single-role"),), frozenset({"a"}))


def test_report_carries_the_headline_figure_for_the_committed_corpus():
    report = render(_root())
    assert "## Purpose coverage" in report and "drawn purposes resolve to exactly one realized appearance role" in report
    assert "### Registered but unpainted purposes" in report


def test_report_labels_observed_evidence_apart_from_admitted_cardinality_and_never_says_witnessed():
    report = render(_root())
    observed, admitted = report.index("## Observed realization evidence"), report.index("## Admitted-model cardinality (admitted, not observed)")
    assert observed < admitted < report.index("## Purpose coverage")
    assert "Admitted states" not in report[observed:admitted] and "Declared states" not in report
    assert "witness" not in report.replace("states no state-to-role pairing", "").lower()
    assert "Admitted model states (not observed)" in report
