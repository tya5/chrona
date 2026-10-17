"""Closed Context profile declarations reach projection as typed source facts."""
from __future__ import annotations

from copy import deepcopy

import pytest
import yaml

from chrona.presentation.contracts.resources import ClosureIdentity, parse_contract
from chrona.presentation.model.field_roles import FieldDescriptor
from chrona.presentation.model.semantic_registry import semantic_binding
from chrona.presentation.model.style_rules import StyleEvaluationError
from chrona.usecases import render_review as render_review_usecase
from tests.integration.test_declared_field_color_encoding import _project, _render


_ORIGINAL_BUILD_REVIEW_PROJECTION = render_review_usecase.build_review_projection
_ORIGINAL_NORMALIZE_V05_SURFACE_CONTENT = render_review_usecase.normalize_v05_surface_content


def _style_rules(rules):
    value = {"version": "chrona/style/v0.2", "kind": "style", "id": "typed-field-style",
             "body": {"rules": rules}}
    return parse_contract(
        ClosureIdentity("style", "typed-field-style", "test-v1", "sha256:" + "0" * 64),
        value,
    ).rules


def _render_with_style(tmp_path, monkeypatch, project, rules):
    def normalize(*args, **kwargs):
        return _ORIGINAL_NORMALIZE_V05_SURFACE_CONTENT(
            *args, **kwargs, style_rules=rules, gate_declared=False,
        )

    monkeypatch.setattr(render_review_usecase, "normalize_v05_surface_content", normalize)
    return _render(tmp_path, project, field="acme.risk", domain=["low", "medium", "high"],
                   slots={"low": "#2e7d32", "medium": "#f9a825", "high": "#c62828"})


def test_closed_context_preserves_declared_field_descriptors_and_alias_reads(tmp_path, monkeypatch):
    project = _project({
        "alpha": {"acme.risk": "low", "acme.reviewed": True},
        "beta": {"acme.risk": "medium"},
    })
    project["fieldRoles"] = {"responsible": "acme.risk", "phase": "acme.reviewed"}
    original_extensions = list(project["extensions"])
    original_fields = {key: dict(value["fields"]) for key, value in project["objects"].items()}
    captured = []

    def capture_projection(*args, **kwargs):
        projection = _ORIGINAL_BUILD_REVIEW_PROJECTION(*args, **kwargs)
        captured.append((kwargs, projection))
        return projection

    monkeypatch.setattr(render_review_usecase, "build_review_projection", capture_projection)
    _render(tmp_path, project, field="acme.risk", domain=["low", "medium", "high"],
            slots={"low": "#2e7d32", "medium": "#f9a825", "high": "#c62828"})

    assert len(captured) == 1
    kwargs, projection = captured[0]
    bindings = kwargs["field_bindings"]
    assert bindings.field_for("responsible") == "acme.risk"
    assert bindings.field_for("phase") == "acme.reviewed"
    assert bindings.descriptor_for("alpha", "acme.risk") == FieldDescriptor(
        "acme.risk", "enum", "one", ("low", "medium", "high"))
    assert bindings.descriptor_for("alpha", "acme.reviewed") == FieldDescriptor(
        "acme.reviewed", "boolean", "one", ())
    assert bindings.descriptor_for("beta", "acme.reviewed") == FieldDescriptor(
        "acme.reviewed", "boolean", "one", ())

    items = {item.object_id: item for item in projection.items}
    assert set(items) == {"alpha", "beta"}
    for object_id, item in items.items():
        assert item.fields == original_fields[object_id]
        assert item.field_bindings is bindings

    alpha_risk = items["alpha"].field_bindings.read_result(
        items["alpha"].fields, {"fieldRole": "responsible"}, object_id="alpha")
    alpha_reviewed = items["alpha"].field_bindings.read_result(
        items["alpha"].fields, {"fieldRole": "phase"}, object_id="alpha")
    beta_reviewed = items["beta"].field_bindings.read_result(
        items["beta"].fields, {"fieldRole": "phase"}, object_id="beta")
    assert (alpha_risk.field_name, alpha_risk.present, alpha_risk.value, alpha_risk.descriptor) == (
        "acme.risk", True, "low", bindings.descriptor_for("alpha", "acme.risk"))
    assert (alpha_reviewed.field_name, alpha_reviewed.present, alpha_reviewed.value) == (
        "acme.reviewed", True, True)
    assert (beta_reviewed.field_name, beta_reviewed.present, beta_reviewed.value) == (
        "acme.reviewed", False, None)
    assert beta_reviewed.descriptor == bindings.descriptor_for("beta", "acme.reviewed")

    # Context packaging leaves the caller's raw Project field map and declared extension edge intact.
    assert project["extensions"] == original_extensions
    assert {key: value["fields"] for key, value in project["objects"].items()} == original_fields


def test_closed_context_style_predicates_match_typed_fields_and_keep_legacy_encoding(tmp_path, monkeypatch):
    project = _project({
        "alpha": {"acme.risk": "low", "acme.reviewed": True},
        "beta": {"acme.risk": "high", "acme.reviewed": False},
        "gamma": {"acme.risk": "medium"},
    })
    project["fieldRoles"] = {"phase": "acme.reviewed"}
    original = deepcopy(project)
    rules = _style_rules((
        {"id": "low-risk", "when": {"semantic": "planned", "fields": [
            {"source": {"field": "acme.risk"}, "equals": "low"},
        ]}, "then": {"role": "planned"}},
        {"id": "unreviewed", "when": {"semantic": "planned", "fields": [
            {"source": {"fieldRole": "phase"}, "equals": False},
        ]}, "then": {"role": "planned"}},
    ))

    rendered = _render_with_style(tmp_path, monkeypatch, project, rules)

    planned = {item.source_ref: item for item in rendered.surface.primitives
               if item.scene_id.startswith("planned:")}
    assert set(planned) == {"alpha", "beta", "gamma"}
    assert planned["alpha"].theme_role == "planned"
    assert planned["beta"].theme_role == "planned"
    assert planned["gamma"].theme_role is None
    assert planned["gamma"].semantic_id is None
    for object_id in ("alpha", "beta"):
        primitive = planned[object_id]
        assert primitive.semantic_id == "planned"
        binding = semantic_binding(primitive.semantic_id)
        assert primitive.purpose == binding.purpose
        assert primitive.visual_role == binding.scene_role
        assert primitive.paint.fill is not None
    assert {source: item.paint.fill for source, item in planned.items()} == {
        "alpha": "#2e7d32", "beta": "#c62828", "gamma": "#f9a825",
    }
    assert {key: value["fields"] for key, value in project["objects"].items()} == {
        key: value["fields"] for key, value in original["objects"].items()
    }
    assert project == original


def test_style_bool_predicate_rejects_numeric_zero_for_absent_or_false_bool_field(tmp_path, monkeypatch):
    project = _project({"alpha": {"acme.risk": "low", "acme.reviewed": False}})
    project["fieldRoles"] = {"phase": "acme.reviewed"}
    rules = _style_rules((
        {"id": "numeric-zero", "when": {"fields": [
            {"source": {"fieldRole": "phase"}, "equals": 0},
        ]}, "then": {"role": "planned"}},
    ))

    with pytest.raises(StyleEvaluationError) as caught:
        _render_with_style(tmp_path, monkeypatch, project, rules)

    assert caught.value.diagnostic_id == "E_STYLE_FACT_TYPE"
    assert caught.value.source_ref.endswith("/when/fields/0")


def test_style_unknown_field_predicate_is_rejected_even_when_no_object_has_a_value(tmp_path, monkeypatch):
    project = _project({"alpha": {"acme.risk": "low"}, "beta": {"acme.risk": "high"}})
    rules = _style_rules((
        {"id": "unknown", "when": {"semantic": "planned", "fields": [
            {"source": {"field": "acme.neverDeclared"}, "equals": "present"},
        ]}, "then": {"role": "planned"}},
    ))

    with pytest.raises(StyleEvaluationError) as caught:
        _render_with_style(tmp_path, monkeypatch, project, rules)

    assert caught.value.diagnostic_id == "E_STYLE_FACT_UNKNOWN"
