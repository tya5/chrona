"""A guided annotation yields a valid View and a rendered Scene that contains it (#709)."""
from pathlib import Path

import pytest
import yaml

from chrona.presentation.contracts import ContractError
from chrona.presentation.model.authoring import (
    AuthoringError, GUIDED_ANCHOR_DEFAULTS, _apply_view_overrides, normalize_authoring_workspace,
)
from chrona.presentation.model.closure import resolve_guided_draft_render
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review

from tests.unit.chrona.presentation.model.test_authoring import _contract, _preset, _resources, _workspace


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def _annotation(**anchor) -> dict:
    return {"id": "note-1", "purpose": "note", "anchor": {"kind": "object", "id": "firmware", **anchor},
            "placement": {"side": "above", "alignment": "center"}, "text": "Watch this"}


def _normalize(annotations: list) -> object:
    workspace = _workspace()
    overrides = workspace["body"]["presentation"]["binding"]["overrides"]["view"]
    overrides["annotations"] = annotations
    resources = _resources()
    return normalize_authoring_workspace(_contract("authoring-workspace", workspace),
                                         _contract("presentation-preset", _preset(resources)), resources)


def _plain(value) -> bool:
    if isinstance(value, dict):
        return type(value) is dict and all(type(key) is str and _plain(item) for key, item in value.items())
    if isinstance(value, list):
        return type(value) is list and all(_plain(item) for item in value)
    return value is None or type(value) in (str, int, float, bool)


def test_the_guided_annotation_anchor_defaults_are_planned_and_finish():
    assert GUIDED_ANCHOR_DEFAULTS == {"facet": "planned", "endpoint": "finish"}


def test_a_guided_annotation_without_facet_and_endpoint_normalizes_to_a_valid_view():
    result = _normalize([_annotation()])

    anchor = result.view_source["body"]["annotations"][-1]["anchor"]
    assert anchor == {"kind": "object", "id": "firmware", "facet": "planned", "endpoint": "finish"}
    assert result.view.view.annotations[-1]["anchor"] == anchor


@pytest.mark.parametrize("member", ["facet", "endpoint"])
def test_each_missing_anchor_member_is_defaulted_on_its_own(member):
    # The closed workspace schema carries no facet or endpoint today (design D3), so the rule is exercised on the
    # override mapping directly: it fills only what is absent and never replaces a member that is present.
    given = {"facet": "actual", "endpoint": "start"}
    kept = {key: value for key, value in given.items() if key != member}
    view = {"body": {"annotations": []}}

    _apply_view_overrides(view, {"annotations": [_annotation(**kept)]})

    anchor = view["body"]["annotations"][-1]["anchor"]
    assert anchor[member] == GUIDED_ANCHOR_DEFAULTS[member]
    assert all(anchor[key] == value for key, value in kept.items())


@pytest.mark.parametrize("member", ["facet", "endpoint"])
def test_the_closed_workspace_schema_still_refuses_an_explicit_facet_or_endpoint(member):
    value = {"facet": "planned", "endpoint": "finish"}[member]
    with pytest.raises(ContractError):
        _normalize([_annotation(**{member: value})])


def test_normalized_sources_are_plain_data_so_no_frozen_container_reaches_a_source_document():
    result = _normalize([_annotation()])

    for _kind, source in result.draft_sources():
        assert _plain(source), source


def test_the_original_representer_error_reproduction_is_no_longer_raised():
    # Before #709 this raised yaml.representer.RepresenterError from `_identity` on the frozen annotation.
    assert _normalize([_annotation()]).view_source["body"]["annotations"][-1]["id"] == "note-1"


def test_a_duplicate_annotation_id_is_an_authoring_error_with_a_stable_code():
    with pytest.raises(AuthoringError, match="E_AUTHORING_ANNOTATION_ID"):
        _normalize([_annotation(), _annotation()])


def test_the_normalizer_does_not_mutate_the_frozen_workspace():
    workspace = _contract("authoring-workspace", _with_annotation(_workspace(), [_annotation()]))
    resources = _resources()
    normalize_authoring_workspace(workspace, _contract("presentation-preset", _preset(resources)), resources)

    assert "facet" not in workspace.binding["overrides"]["view"]["annotations"][0]["anchor"]


def _with_annotation(workspace: dict, annotations: list) -> dict:
    workspace["body"]["presentation"]["binding"]["overrides"]["view"]["annotations"] = annotations
    return workspace


def _guided_files(tmp_path: Path, annotation: dict) -> Path:
    root = _root()
    preset_root = tmp_path / "preset"
    preset_root.mkdir()
    resources = {
        "view.yaml": yaml.safe_load((root / "examples/controller-z/views/annotations.yaml").read_text(encoding="utf-8")),
        "theme.yaml": yaml.safe_load((root / "examples/controller-z/themes/executive-light.yaml").read_text(encoding="utf-8")),
        "scheme.yaml": yaml.safe_load((root / "examples/controller-z/schemes/executive-light.yaml").read_text(encoding="utf-8")),
        "layout.yaml": yaml.safe_load((root / "examples/controller-z/layouts/annotations-review.yaml").read_text(encoding="utf-8")),
    }
    # The committed controller-z annotation set (View, Layout Profile, Theme, Scheme) renders annotations; the
    # preset View annotates nothing itself, so the guided annotation is the only one in the Scene.
    resources["view.yaml"]["body"].pop("annotations")
    for name, document in resources.items():
        (preset_root / name).write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    preset = {
        "version": "chrona/presentation-preset/v0.1", "kind": "presentation-preset", "id": "starter",
        "body": {"package": {"version": "1"}, "resources": {
            "view": {"id": resources["view.yaml"]["id"], "kind": "view", "path": "view.yaml"},
            "theme": {"id": resources["theme.yaml"]["id"], "kind": "theme", "path": "theme.yaml"},
            "colorScheme": {"id": resources["scheme.yaml"]["id"], "kind": "color-scheme", "path": "scheme.yaml"},
            "layout": {"id": resources["layout.yaml"]["id"], "kind": "layout-profile", "path": "layout.yaml"},
        }, "compatibleColorSchemes": [{"id": resources["scheme.yaml"]["id"], "kind": "color-scheme", "path": "scheme.yaml"}]},
    }
    (preset_root / "starter.yaml").write_text(yaml.safe_dump(preset, sort_keys=False), encoding="utf-8")
    document = {
        "version": "chrona/authoring-workspace/v0.1", "kind": "authoring-workspace", "id": "workspace",
        "body": {"project": {"id": "project", "tasks": [{"id": "firmware", "title": "Firmware", "planned": {"start": "2026-04-01", "finish": "2026-04-10"}}]},
                 "actuals": [{"taskId": "firmware", "actual": {"start": "2026-04-02", "finish": "2026-04-12"}}],
                 "presentation": {"mode": "guided", "binding": {
                     "preset": {"id": "starter", "version": "1", "path": "preset/starter.yaml"},
                     "overrides": {"view": {"grouping": "none", "annotations": [annotation]}}}}},
    }
    path = tmp_path / "workspace.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path


def test_a_guided_annotation_renders_end_to_end_into_the_scene(tmp_path):
    workspace = _guided_files(tmp_path, _annotation())

    draft = resolve_guided_draft_render(workspace_path=workspace)
    rendered = render_review(RenderRequest(draft.closure, draft.asset_root, ReferenceScheduler(), asset_root=draft.asset_root))

    assert draft.closure.view.view.annotations[-1]["anchor"] == {
        "kind": "object", "id": "firmware", "facet": "planned", "endpoint": "finish"}
    assert b"Watch this" in rendered.artifact.content
    primitives = [primitive for surface in rendered.scene.surfaces for primitive in surface.primitives]
    mine = {primitive.visual_role: primitive for primitive in primitives if primitive.source_ref == "note-1"}
    assert set(mine) == {"annotation-note-box", "annotation-note-text", "annotation-note-leader"}
    assert mine["annotation-note-text"].text.endswith("Watch this")
