"""Draft ingress freezes explicit authoring files before they enter rendering."""
from pathlib import Path

import pytest
import yaml

from chrona.presentation.model.closure import ClosureError, resolve_draft_render, resolve_guided_draft_render


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def _paths(root: Path) -> dict[str, Path]:
    return {
        "project_path": root / "examples/controller-z/project.yaml",
        "view_path": root / "examples/controller-z/views/executive.yaml",
        "theme_path": root / "examples/controller-z/themes/executive-light.yaml",
        "scheme_path": root / "examples/controller-z/schemes/executive-light.yaml",
        "layout_path": root / "conformance/layout-profile-intent-v0.2.yaml",
    }


def test_draft_closure_accepts_optional_review_inputs():
    root = _root()
    draft = resolve_draft_render(
        **_paths(root), actual_path=root / "examples/controller-z/actual.yaml",
        detail_path=root / "examples/controller-z/profiles/review-detail.yaml",
    )
    assert draft.closure.actual_set is not None
    assert draft.closure.detail_profile is not None
    assert draft.closure.context.identity.revision == "draft"
    assert draft.asset_root.name == "resources"


def test_draft_closure_reports_the_invalid_resource_schema_pointer(tmp_path):
    invalid_view = tmp_path / "view.yaml"
    invalid_view.write_text("version: chrona/view/v0.8\nkind: view\nid: bad\nbody: {}\n", encoding="utf-8")
    with pytest.raises(ClosureError) as error:
        resolve_draft_render(**(_paths(_root()) | {"view_path": invalid_view}))
    assert error.value.diagnostic_id == "E_VIEW_SCHEMA"
    assert error.value.source_ref.startswith("/body")


def test_guided_draft_closure_normalizes_in_memory_and_records_non_scene_provenance(tmp_path):
    root = _root()
    preset_root = tmp_path / "preset"
    preset_root.mkdir()
    resources = {
        "view.yaml": yaml.safe_load((root / "examples/aster-ssd/views/01-overview.yaml").read_text()),
        "theme.yaml": yaml.safe_load((root / "examples/aster-ssd/themes/executive-light.yaml").read_text()),
        "scheme.yaml": yaml.safe_load((root / "examples/aster-ssd/schemes/executive-light.yaml").read_text()),
        "layout.yaml": yaml.safe_load((root / "conformance/layout-profile-intent-v0.2.yaml").read_text()),
    }
    resources["view.yaml"]["body"]["selection"] = {"include": {"types": ["task"]}}
    for name, value in resources.items():
        (preset_root / name).write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
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
    workspace = {
        "version": "chrona/authoring-workspace/v0.1", "kind": "authoring-workspace", "id": "workspace",
        "body": {"project": {"id": "project", "tasks": [{"id": "task", "title": "Task", "planned": {"start": "2026-04-01", "finish": "2026-04-10"}}]},
        "actuals": [{"taskId": "task", "actual": {"start": "2026-04-02", "finish": "2026-04-12"}}],
        "presentation": {"mode": "guided", "binding": {"preset": {"id": "starter", "version": "1", "path": "preset/starter.yaml"}}}},
    }
    workspace_path = tmp_path / "workspace.yaml"
    workspace_path.write_text(yaml.safe_dump(workspace, sort_keys=False), encoding="utf-8")

    draft = resolve_guided_draft_render(workspace_path=workspace_path)

    assert draft.closure.project.scheduler_input["project"]["id"] == "project"
    assert draft.closure.actual_set is not None
    assert draft.closure.guided_provenance is not None
    assert draft.closure.guided_provenance.normalizer_version == "chrona/authoring-normalizer/v0.1"
