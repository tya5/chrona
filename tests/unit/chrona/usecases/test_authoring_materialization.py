"""Stage-three materialization preserves the reviewed guided surface."""
from pathlib import Path

import pytest
import yaml

from chrona.presentation.model.closure import resolve_draft_render, resolve_guided_draft_render
from chrona.usecases.authoring_materialization import _render_bytes, materialize_presentation_preset


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def _workspace(tmp_path: Path) -> Path:
    root = _root()
    preset_root = tmp_path / "preset"
    preset_root.mkdir()
    resources = {
        "view.yaml": yaml.safe_load((root / "examples/aster-ssd/views/01-overview.yaml").read_text()),
        "theme.yaml": yaml.safe_load((root / "examples/aster-ssd/themes/executive-light.yaml").read_text()),
        "scheme.yaml": yaml.safe_load((root / "examples/aster-ssd/schemes/executive-light.yaml").read_text()),
        "layout.yaml": yaml.safe_load((root / "conformance/layout-profile-intent-v0.2.yaml").read_text()),
    }
    resources["view.yaml"]["body"]["selection"] = {"include": {"types": ["span"]}}
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
        "body": {"project": {"id": "project", "tasks": [{"id": "task", "title": "Task", "planned": {"start": "2026-04-01", "finish": "2026-04-10"}}]},
        "actuals": [{"taskId": "task", "actual": {"start": "2026-04-02", "finish": "2026-04-12"}}],
        "presentation": {"mode": "guided", "binding": {"preset": {"id": "starter", "version": "1", "path": "preset/starter.yaml"}}}},
    }
    path = tmp_path / "workspace.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path


def _explicit_bytes(root: Path) -> bytes:
    draft = resolve_draft_render(
        project_path=root / "presentation/project.yaml", view_path=root / "presentation/view.yaml",
        theme_path=root / "presentation/theme.yaml", scheme_path=root / "presentation/scheme.yaml",
        layout_path=root / "presentation/layout.yaml", actual_path=root / "presentation/actual.yaml",
    )
    return _render_bytes(draft)


def test_materialization_ejects_to_a_closed_explicit_bundle_with_identical_bytes(tmp_path):
    workspace = _workspace(tmp_path)
    guided_bytes = _render_bytes(resolve_guided_draft_render(workspace_path=workspace))

    result = materialize_presentation_preset(workspace)

    assert result["body"]["presentation"]["mode"] == "explicit"
    assert "binding" not in result["body"]["presentation"]
    assert (tmp_path / "presentation/receipt.yaml").is_file()
    assert _explicit_bytes(tmp_path) == guided_bytes


def test_materialization_rejection_does_not_switch_workspace_or_publish_bundle(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path)
    original = workspace.read_bytes()
    calls = iter((b"guided", b"explicit"))
    monkeypatch.setattr("chrona.usecases.authoring_materialization._render_bytes", lambda _draft: next(calls))

    with pytest.raises(ValueError, match="E_AUTHORING_MATERIALIZE_OUTPUT_PROOF"):
        materialize_presentation_preset(workspace)

    assert workspace.read_bytes() == original
    assert not (tmp_path / "presentation").exists()


def test_materialization_rejects_existing_destination_without_switching_workspace(tmp_path):
    workspace = _workspace(tmp_path)
    original = workspace.read_bytes()
    (tmp_path / "presentation").mkdir()

    with pytest.raises(ValueError, match="E_AUTHORING_MATERIALIZE_COLLISION"):
        materialize_presentation_preset(workspace)

    assert workspace.read_bytes() == original
