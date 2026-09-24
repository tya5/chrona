"""Draft ingress freezes explicit authoring files before they enter rendering."""
from pathlib import Path

import pytest
import yaml

from chrona.presentation.model.closure import ClosureError, resolve_draft_render, resolve_guided_draft_render
from chrona.presentation.contracts import TypesetterIdentity


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
    invalid_view.write_text("version: chrona/view/v0.13\nkind: view\nid: bad\nbody: {}\n", encoding="utf-8")
    with pytest.raises(ClosureError) as error:
        resolve_draft_render(**(_paths(_root()) | {"view_path": invalid_view}))
    assert error.value.diagnostic_id == "E_VIEW_SCHEMA"
    assert error.value.source_ref.startswith("/body")


def test_draft_typeset_closure_uses_an_explicit_descriptor_without_host_discovery():
    draft = resolve_draft_render(
        **_paths(_root()), target_kind="typst",
        typesetter=TypesetterIdentity("typst", "0.13.1", "chrona-typst/v0.1"),
    )
    assert draft.closure.context.environment.typesetter == TypesetterIdentity("typst", "0.13.1", "chrona-typst/v0.1")


def test_draft_typeset_closure_requires_an_explicit_descriptor():
    with pytest.raises(ClosureError, match="E_RENDER_TYPESETTER_DESCRIPTOR"):
        resolve_draft_render(**_paths(_root()), target_kind="tikz")


def test_draft_closure_closes_only_explicit_catalogs_and_resolves_set_aliases(tmp_path):
    catalog = tmp_path / "icons.yaml"
    catalog.write_text(yaml.safe_dump({
        "version": "chrona/icon-catalog/v0.3", "kind": "icon-catalog", "id": "acme-icons",
        "body": {
            "set": "acme", "aliases": ["acme-ui"],
            "provenance": {"sourceKind": "iconify-json", "sourcePrefix": "acme",
                           "sourceContentIdentity": "sha256:" + "a" * 64,
                           "license": {"spdx": "MIT", "notice": "MIT"}},
            "entryAliases": {"warning": "risk"},
            "icons": {"risk": {"kind": "vector", "viewport": {"inlineSize": 24, "blockSize": 24},
                               "alternative": "Risk", "paths": [{"paint": "fill", "data": "M 0 0 L 24 24"}]}}
        },
    }, sort_keys=False), encoding="utf-8")

    draft = resolve_draft_render(**_paths(_root()), icon_catalog_paths=(catalog,))

    assert len(draft.closure.context.icon_catalogs) == 1
    assert draft.closure.icon_catalogs[0].aliases == ("acme-ui",)
    assert draft.closure.icon_catalogs[0].entry_aliases["warning"] == "risk"
    with pytest.raises(ClosureError, match="E_ICON_SET_UNKNOWN"):
        draft.closure.icon_asset("other:risk")
    with pytest.raises(ClosureError) as error:
        draft.closure.icon_asset("acme-ui:rsk")
    assert error.value.diagnostic_id == "E_ICON_NAME_UNKNOWN"
    assert error.value.detail == "reference=acme-ui:rsk; catalog=acme; candidates=risk"


def test_draft_closure_never_probes_a_host_typesetter():
    source = Path(__import__("chrona.presentation.model.closure", fromlist=["*"]).__file__).read_text(encoding="utf-8")
    assert "subprocess" not in source
    assert '"--version"' not in source


def test_guided_draft_closure_normalizes_in_memory_and_records_non_scene_provenance(tmp_path):
    root = _root()
    preset_root = tmp_path / "preset"
    preset_root.mkdir()
    resources = {
        "view.yaml": yaml.safe_load((root / "examples/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8")),
        "theme.yaml": yaml.safe_load((root / "examples/aster-ssd/themes/executive-light.yaml").read_text(encoding="utf-8")),
        "scheme.yaml": yaml.safe_load((root / "examples/aster-ssd/schemes/executive-light.yaml").read_text(encoding="utf-8")),
        "layout.yaml": yaml.safe_load((root / "conformance/layout-profile-intent-v0.2.yaml").read_text(encoding="utf-8")),
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

    draft = resolve_guided_draft_render(
        workspace_path=workspace_path, target_kind="tikz",
        typesetter=TypesetterIdentity("tectonic", "0.15.0", "chrona-tikz/v0.1"),
    )

    assert draft.closure.project.scheduler_input["project"]["id"] == "project"
    assert draft.closure.actual_set is not None
    assert draft.closure.guided_provenance is not None
    assert draft.closure.guided_provenance.normalizer_version == "chrona/authoring-normalizer/v0.1"
    assert draft.closure.context.environment.typesetter == TypesetterIdentity("tectonic", "0.15.0", "chrona-tikz/v0.1")


def test_guided_draft_closure_uses_only_preset_declared_icon_catalogs(tmp_path):
    root = _root()
    preset_root = tmp_path / "preset"
    preset_root.mkdir()
    resources = {
        "view.yaml": yaml.safe_load((root / "examples/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8")),
        "theme.yaml": yaml.safe_load((root / "examples/aster-ssd/themes/executive-light.yaml").read_text(encoding="utf-8")),
        "scheme.yaml": yaml.safe_load((root / "examples/aster-ssd/schemes/executive-light.yaml").read_text(encoding="utf-8")),
        "layout.yaml": yaml.safe_load((root / "conformance/layout-profile-intent-v0.2.yaml").read_text(encoding="utf-8")),
        "icons.yaml": {"version": "chrona/icon-catalog/v0.3", "kind": "icon-catalog", "id": "preset-icons",
                       "body": {"set": "preset", "aliases": [], "entryAliases": {},
                                "provenance": {"sourceKind": "iconify-json", "sourcePrefix": "preset",
                                               "sourceContentIdentity": "sha256:" + "b" * 64,
                                               "license": {"spdx": "MIT", "notice": "MIT"}},
                                "icons": {"check": {"kind": "vector", "viewport": {"inlineSize": 24, "blockSize": 24},
                                                    "alternative": "Check", "paths": [{"paint": "fill", "data": "M 0 0 L 24 24"}]}}}},
    }
    resources["view.yaml"]["body"]["selection"] = {"include": {"types": ["task"]}}
    for name, value in resources.items():
        (preset_root / name).write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    preset = {"version": "chrona/presentation-preset/v0.1", "kind": "presentation-preset", "id": "starter",
              "body": {"package": {"version": "1"}, "resources": {
                  "view": {"id": resources["view.yaml"]["id"], "kind": "view", "path": "view.yaml"},
                  "theme": {"id": resources["theme.yaml"]["id"], "kind": "theme", "path": "theme.yaml"},
                  "colorScheme": {"id": resources["scheme.yaml"]["id"], "kind": "color-scheme", "path": "scheme.yaml"},
                  "layout": {"id": resources["layout.yaml"]["id"], "kind": "layout-profile", "path": "layout.yaml"},
                  "iconCatalogs": [{"id": "preset-icons", "kind": "icon-catalog", "path": "icons.yaml"}],
              }, "compatibleColorSchemes": [{"id": resources["scheme.yaml"]["id"], "kind": "color-scheme", "path": "scheme.yaml"}]}}
    (preset_root / "starter.yaml").write_text(yaml.safe_dump(preset, sort_keys=False), encoding="utf-8")
    workspace = {"version": "chrona/authoring-workspace/v0.1", "kind": "authoring-workspace", "id": "workspace",
                 "body": {"project": {"id": "project", "tasks": [{"id": "task", "title": "Task", "planned": {"start": "2026-04-01", "finish": "2026-04-10"}}]},
                          "presentation": {"mode": "guided", "binding": {"preset": {"id": "starter", "version": "1", "path": "preset/starter.yaml"}}}}}
    workspace_path = tmp_path / "workspace.yaml"
    workspace_path.write_text(yaml.safe_dump(workspace, sort_keys=False), encoding="utf-8")

    draft = resolve_guided_draft_render(workspace_path=workspace_path)

    assert draft.closure.icon_catalogs[0].set_name == "preset"
    assert draft.closure.icon_catalogs[0].entry_names == ("check",)
