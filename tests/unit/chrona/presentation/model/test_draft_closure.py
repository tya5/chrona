"""Draft ingress freezes explicit authoring files before they enter rendering."""
from pathlib import Path
from hashlib import sha256
import shutil

import pytest
import yaml

from chrona.presentation.model.closure import ClosureError, resolve_draft_render, resolve_guided_draft_render
from chrona.presentation.fonts.system import SystemFontFace, resolve_system_font
from chrona.presentation.contracts import PresentationIngressRejected, ProjectContract, TypesetterIdentity
from chrona.usecases.render_review import RenderRequest, render_review
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.resources import default_preset_resource, default_preset_root


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def _paths(root: Path) -> dict[str, Path]:
    return {
        "project_path": root / "tests/fixtures/controller-z/project.yaml",
        "view_path": root / "tests/fixtures/controller-z/views/executive.yaml",
        "theme_path": root / "tests/fixtures/controller-z/themes/executive-light.yaml",
        "scheme_path": root / "tests/fixtures/controller-z/schemes/executive-light.yaml",
        "layout_path": root / "conformance/layout-profile-intent-v0.2.yaml",
    }


def test_draft_closure_accepts_optional_review_inputs():
    root = _root()
    draft = resolve_draft_render(
        **_paths(root), actual_path=root / "tests/fixtures/controller-z/actual.yaml",
        detail_path=root / "tests/fixtures/controller-z/profiles/review-detail.yaml",
    )
    assert draft.closure.actual_set is not None
    assert draft.closure.detail_profile is not None
    assert draft.closure.context.identity.revision == "draft"
    assert draft.asset_root.name == "resources"


def test_draft_snapshot_project_is_typed_without_fabricating_snapshot_reference(tmp_path):
    root = _root()
    project_path = _paths(root)["project_path"]
    snapshot_path = tmp_path / "snapshot-project.yaml"
    source_bytes = project_path.read_bytes()
    snapshot_path.write_bytes(source_bytes)

    without_snapshot = resolve_draft_render(**_paths(root))
    draft = resolve_draft_render(**_paths(root), snapshot_project_path=snapshot_path)

    (snapshot_project,) = [item for item in draft.closure.resources if item.kind == "snapshot-project"]
    assert isinstance(snapshot_project.contract, ProjectContract)
    assert snapshot_project.id == draft.closure.project.identity.id
    assert snapshot_project.revision == "draft"
    assert snapshot_project.content_identity == "sha256:" + sha256(source_bytes).hexdigest()
    assert snapshot_project.contract.identity.kind == "project"
    assert snapshot_project.contract.identity.content_identity == snapshot_project.content_identity
    assert draft.closure.snapshot_project is snapshot_project.contract
    assert draft.closure.snapshot is None
    assert draft.closure.resource("snapshot-ref") is None
    assert draft.closure.context.snapshot is None
    assert draft.closure.context == without_snapshot.closure.context
    assert without_snapshot.closure.snapshot_project is None
    assert snapshot_path.read_bytes() == source_bytes


def test_draft_snapshot_project_rejects_a_different_project_id(tmp_path):
    root = _root()
    primary = yaml.safe_load(_paths(root)["project_path"].read_bytes())
    primary_id = primary["project"]["id"]
    primary["project"]["id"] = "different-project"
    snapshot_path = tmp_path / "different-project.yaml"
    snapshot_path.write_text(yaml.safe_dump(primary, sort_keys=False), encoding="utf-8")

    with pytest.raises(ClosureError, match="E_CLOSURE_ID") as error:
        resolve_draft_render(**_paths(root), snapshot_project_path=snapshot_path)

    assert error.value.detail == (
        f"the snapshot project id 'different-project' is not the context project id {primary_id!r}")


@pytest.mark.parametrize(
    ("document", "code", "source_ref"),
    [
        ({"version": "timeline/v0.7", "project": {"id": "controller-z", "title": 7}},
         "E_PROJECT_SCHEMA", "/project/title"),
        ({"version": "timeline/v0.6", "project": {"id": "controller-z"}, "objects": {}},
         "E_RESOURCE_VERSION_UNSUPPORTED", "/version"),
    ],
)
def test_draft_snapshot_project_uses_normal_project_validation(tmp_path, document, code, source_ref):
    root = _root()
    primary = yaml.safe_load(_paths(root)["project_path"].read_bytes())
    document["project"]["id"] = primary["project"]["id"]
    snapshot_path = tmp_path / "invalid-snapshot-project.yaml"
    snapshot_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    with pytest.raises(ClosureError) as error:
        resolve_draft_render(**_paths(root), snapshot_project_path=snapshot_path)

    assert (error.value.diagnostic_id, error.value.source_ref) == (code, source_ref)


def test_draft_closure_aggregates_every_schema_finding_in_the_known_resource_set(tmp_path):
    invalid_view = tmp_path / "view.yaml"
    invalid_view.write_text("version: chrona/view/v0.26\nkind: view\nid: bad\nbody: {}\n", encoding="utf-8")
    with pytest.raises(PresentationIngressRejected) as error:
        resolve_draft_render(**(_paths(_root()) | {"view_path": invalid_view}))
    assert {item.pointer for item in error.value.diagnostics} >= {"/body"}
    assert {item.resource_kind for item in error.value.diagnostics} == {"view"}


def test_draft_closure_reports_unsupported_view_version_at_version_pointer(tmp_path):
    root = _root()
    view = yaml.safe_load((root / "tests/fixtures/controller-z/views/executive.yaml").read_text(encoding="utf-8"))
    view["version"] = "chrona/view/v0.22"
    stale_view = tmp_path / "stale-view.yaml"
    stale_view.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")

    with pytest.raises(ClosureError) as error:
        resolve_draft_render(**(_paths(root) | {"view_path": stale_view}))

    assert (error.value.diagnostic_id, error.value.source_ref) == (
        "E_RESOURCE_VERSION_UNSUPPORTED", "/version")
    assert "chrona/view/v0.22" in error.value.detail
    assert "chrona/view/v0.26" in error.value.detail


def test_draft_preset_resolves_the_same_typed_resources_as_explicit_inputs():
    root = _root() / "tests/fixtures/controller-z"
    preset = root / "executive-light.preset.yaml"
    draft = resolve_draft_render(project_path=root / "project.yaml", preset_path=preset, preset_root=root)
    explicit = resolve_draft_render(
        project_path=root / "project.yaml", view_path=root / "views/executive.yaml",
        theme_path=root / "themes/executive-light.yaml", scheme_path=root / "schemes/executive-light.yaml",
        layout_path=root / "layouts/executive-review.yaml",
    )
    assert tuple((item.kind, item.content_identity) for item in draft.closure.resources) == tuple(
        (item.kind, item.content_identity) for item in explicit.closure.resources)


def test_bundled_default_preset_resolves_a_non_halcyon_project_with_or_without_actuals():
    root = _root()
    values = {
        "project_path": root / "tests/fixtures/controller-z/project.yaml",
        "preset_path": Path(str(default_preset_resource())),
        "preset_root": Path(str(default_preset_root())),
    }
    without_actual = resolve_draft_render(**values)
    with_actual = resolve_draft_render(**values, actual_path=root / "tests/fixtures/controller-z/actual.yaml")
    # #383/#429: the bundled default's own top-level id stays chrona-default-draft
    # (D1: no rename); its View is the readable Editorial-derived default.
    assert without_actual.closure.resource("view").id == with_actual.closure.resource("view").id == "chrona-preset-editorial-readable-default"
    assert without_actual.closure.actual_set is None
    assert with_actual.closure.actual_set is not None
    assert without_actual.auto_block is with_actual.auto_block is True
    assert without_actual.closure.context.environment.viewport_block == 900


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


def _system_resolver(root: Path):
    faces = {
        400: root / "src/chrona/resources/fonts/noto-sans-regular-v1.ttf",
        700: root / "src/chrona/resources/fonts/noto-sans-bold-v1.ttf",
    }

    def runner(command, **_kwargs):
        weight = 700 if "weight=200" in command[-1] else 400
        return type("Result", (), {"stdout": f"{faces[weight]}\nNoto Sans\n80\n0\n"})()

    return lambda family, weight: resolve_system_font(family, weight, runner=runner)


def test_system_font_opt_in_reuses_packaged_exact_face_without_host_discovery():
    root = _root()
    def unexpected_host(_family, _weight):
        raise AssertionError("packaged face should take precedence")
    draft = resolve_draft_render(**_paths(root), system_fonts=True, system_font_resolver=unexpected_host)

    assert draft.font_resolution is not None
    assert draft.font_resolution.faces == ()
    assert tuple(item.family for item in draft.font_resolution.font_files) == ("Noto Sans",)


def test_system_font_opt_in_closes_multiple_theme_faces_before_layout(tmp_path):
    root = _root()
    theme = yaml.safe_load((root / "tests/fixtures/controller-z/themes/executive-light.yaml").read_text(encoding="utf-8"))
    theme["body"]["values"]["editorial"]["value"] = "Fixture Sans"
    theme["body"]["values"]["heading-weight"] = {"type": "fontWeight", "value": 700}
    theme["body"]["roles"]["heading"]["fontWeight"] = "heading-weight"
    theme["body"]["values"]["packaged-family"] = {"type": "fontFamily", "value": "Noto Sans"}
    theme["body"]["roles"]["heading"]["fontFamily"] = "packaged-family"
    theme_path = tmp_path / "multiple-faces.yaml"
    theme_path.write_text(yaml.safe_dump(theme, sort_keys=False), encoding="utf-8")

    path = root / "src/chrona/resources/fonts/noto-sans-regular-v1.ttf"
    def host(family, weight):
        assert (family, weight) == ("Fixture Sans", 400)
        return SystemFontFace(family, weight, path, family, weight,
                              "sha256:" + sha256(path.read_bytes()).hexdigest())
    draft = resolve_draft_render(**(_paths(root) | {"theme_path": theme_path,
                                                    "actual_path": root / "tests/fixtures/controller-z/actual.yaml"}), system_fonts=True,
                                 system_font_resolver=host)
    assert draft.font_resolution is not None
    assert tuple((face.family, face.weight) for face in draft.font_resolution.faces) == (("Fixture Sans", 400),)
    assert draft.font_resolution.metrics.select("Noto Sans", 700).content_identity != (
        draft.font_resolution.metrics.select("Fixture Sans", 400).content_identity)
    rendered = render_review(RenderRequest(
        draft.closure, draft.asset_root, ReferenceScheduler(), asset_root=draft.asset_root,
        draft_font_resolution=draft.font_resolution,
    ))
    identities = {(primitive.text_layout.weight, primitive.text_layout.asset_identity)
                  for surface in rendered.scene.surfaces for primitive in surface.primitives
                  if primitive.text_layout is not None}
    assert (400, draft.font_resolution.metrics.select("Fixture Sans", 400).content_identity) in identities
    assert (700, draft.font_resolution.metrics.select("Noto Sans", 700).content_identity) in identities


def test_system_font_opt_in_is_accepted_for_every_target():
    # #1281: installed fonts are a normal source; the draft-only SVG/PNG limit was never required.
    root = _root()
    draft = resolve_draft_render(**_paths(root), target_kind="pdf", system_fonts=True,
                                 system_font_resolver=_system_resolver(root))

    assert draft.closure.context.target.kind == "pdf" and draft.font_resolution is not None


def test_guided_draft_closure_normalizes_in_memory_and_records_non_scene_provenance(tmp_path):
    root = _root()
    preset_root = tmp_path / "preset"
    preset_root.mkdir()
    resources = {
        "view.yaml": yaml.safe_load((root / "tests/fixtures/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8")),
        "theme.yaml": yaml.safe_load((root / "tests/fixtures/aster-ssd/themes/executive-light.yaml").read_text(encoding="utf-8")),
        "scheme.yaml": yaml.safe_load((root / "tests/fixtures/aster-ssd/schemes/executive-light.yaml").read_text(encoding="utf-8")),
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

    resources["view.yaml"]["version"] = "chrona/view/v0.22"
    (preset_root / "view.yaml").write_text(yaml.safe_dump(resources["view.yaml"], sort_keys=False), encoding="utf-8")
    with pytest.raises(ClosureError) as error:
        resolve_guided_draft_render(
            workspace_path=workspace_path, target_kind="tikz",
            typesetter=TypesetterIdentity("tectonic", "0.15.0", "chrona-tikz/v0.1"),
        )
    assert (error.value.diagnostic_id, error.value.source_ref) == (
        "E_RESOURCE_VERSION_UNSUPPORTED", "/version")


def test_guided_draft_closure_uses_only_preset_declared_icon_catalogs(tmp_path):
    root = _root()
    preset_root = tmp_path / "preset"
    preset_root.mkdir()
    resources = {
        "view.yaml": yaml.safe_load((root / "tests/fixtures/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8")),
        "theme.yaml": yaml.safe_load((root / "tests/fixtures/aster-ssd/themes/executive-light.yaml").read_text(encoding="utf-8")),
        "scheme.yaml": yaml.safe_load((root / "tests/fixtures/aster-ssd/schemes/executive-light.yaml").read_text(encoding="utf-8")),
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
    assert draft.auto_block is True


@pytest.fixture
def preset_with(tmp_path):
    """Write a Controller Z preset variant outside the example; resources resolve from the example root."""
    root = _root() / "tests/fixtures/controller-z"

    def make(**body: object) -> Path:
        preset = yaml.safe_load((root / "executive-light.preset.yaml").read_text(encoding="utf-8"))
        for key, value in body.items():
            (preset["body"]["resources"] if key in {"detailProfile", "summaryProfile"} else preset["body"])[key] = value
        path = tmp_path / "variant.preset.yaml"
        path.write_text(yaml.safe_dump(preset, sort_keys=False), encoding="utf-8")
        return path
    return make


def test_preset_detail_profile_applies_unless_an_explicit_detail_is_given(preset_with):
    root = _root() / "tests/fixtures/controller-z"
    preset = preset_with(detailProfile={"id": "controller-z-review-detail", "kind": "review-detail-profile",
                                        "path": "profiles/review-detail.yaml"})
    draft = resolve_draft_render(project_path=root / "project.yaml", actual_path=root / "actual.yaml", preset_path=preset, preset_root=root)
    assert draft.closure.detail_profile is not None
    plain = resolve_draft_render(project_path=root / "project.yaml", actual_path=root / "actual.yaml",
                                 preset_path=root / "executive-light.preset.yaml")
    assert plain.closure.detail_profile is None
    explicit_theme = resolve_draft_render(project_path=root / "project.yaml", actual_path=root / "actual.yaml",
                                          preset_path=preset, preset_root=root,
                                          theme_path=root / "themes/executive-light.yaml")
    assert explicit_theme.closure.detail_profile is None  # the legend belongs to the preset's own Theme


def test_preset_summary_profile_applies_unless_an_explicit_summary_is_given(preset_with, tmp_path):
    root = _root() / "tests/fixtures/controller-z"
    preset_root = tmp_path / "preset-root"
    for relative in ("views/executive.yaml", "themes/executive-light.yaml",
                     "schemes/executive-light.yaml", "layouts/executive-review.yaml"):
        target = preset_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / relative, target)
    valid_summary = _root() / "src/chrona/resources/designs/titlecard/summary.yaml"
    summary_target = preset_root / "profiles/summary.yaml"
    summary_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(valid_summary, summary_target)
    summary_document = yaml.safe_load(summary_target.read_text(encoding="utf-8"))
    summary_document["id"] = "controller-z-summary"
    summary_target.write_text(yaml.safe_dump(summary_document, sort_keys=False, allow_unicode=True),
                              encoding="utf-8")
    preset = preset_with(summaryProfile={"id": "controller-z-summary", "kind": "summary-profile",
                                         "path": "profiles/summary.yaml"})

    preset_summary = resolve_draft_render(project_path=root / "project.yaml", preset_path=preset,
                                          preset_root=preset_root)
    without_summary = resolve_draft_render(project_path=root / "project.yaml",
                                          preset_path=root / "executive-light.preset.yaml")
    assert preset_summary.closure.summary_profile is not None
    assert preset_summary.closure.summary_profile.identity.id == "controller-z-summary"
    assert without_summary.closure.summary_profile is None

    explicit = dict(summary_document)
    explicit["id"] = "explicit-summary-override"
    explicit_path = tmp_path / "explicit-summary.yaml"
    explicit_path.write_text(yaml.safe_dump(explicit, sort_keys=False), encoding="utf-8")
    overridden = resolve_draft_render(project_path=root / "project.yaml", preset_path=preset,
                                      preset_root=preset_root, summary_path=explicit_path)

    assert overridden.closure.summary_profile is not None
    assert overridden.closure.summary_profile.identity.id == "explicit-summary-override"


def test_preset_preferred_visual_profile_applies_unless_a_flag_is_given(preset_with):
    root = _root() / "tests/fixtures/controller-z"
    preset = preset_with(visualProfile={"preferred": "chrona-output/visual/v0.7-svg"})
    preferred = resolve_draft_render(project_path=root / "project.yaml", preset_path=preset, preset_root=root)
    assert preferred.closure.context.target.visual_profile == "chrona-output/visual/v0.7-svg"
    explicit = resolve_draft_render(project_path=root / "project.yaml", preset_path=preset, preset_root=root,
                                    visual_profile="chrona-output/visual/v0.5-baseline")
    assert explicit.closure.context.target.visual_profile == "chrona-output/visual/v0.5-baseline"
    default = resolve_draft_render(project_path=root / "project.yaml", preset_path=root / "executive-light.preset.yaml")
    assert default.closure.context.target.visual_profile == "chrona-output/visual/v0.5-baseline"
    png = resolve_draft_render(project_path=root / "project.yaml", preset_path=preset, preset_root=root, target_kind="png")
    assert png.closure.context.target.visual_profile == "chrona-output/visual/v0.7-png"
    assert png.preset_visual_profile_fallback.preferred_profile == "chrona-output/visual/v0.7-svg"
    assert png.preset_visual_profile_fallback.selected_profile == "chrona-output/visual/v0.7-png"
    pdf = resolve_draft_render(project_path=root / "project.yaml", preset_path=preset,
                              preset_root=root, target_kind="pdf")
    assert pdf.closure.context.target.visual_profile == "chrona-output/visual/v0.7-pdf"
    assert pdf.preset_visual_profile_fallback.selected_profile == "chrona-output/visual/v0.7-pdf"
    baseline_pdf = resolve_draft_render(project_path=root / "project.yaml", preset_path=preset,
                                       preset_root=root, target_kind="pdf",
                                       visual_profile="chrona-output/visual/v0.5-baseline")
    assert baseline_pdf.closure.context.target.visual_profile == "chrona-output/visual/v0.5-baseline"
    assert baseline_pdf.preset_visual_profile_fallback is None
    assert preferred.preset_visual_profile_fallback is None
    assert explicit.preset_visual_profile_fallback is None


def test_pdf_draft_pins_glow_rasterizer_only_for_the_glow_profile():
    from chrona.presentation.model.closure import _draft_rasterizer, _draft_resvg_rasterizer

    baseline = _draft_rasterizer("pdf", "chrona-output/visual/v0.5-baseline")
    glow = _draft_rasterizer("pdf", "chrona-output/visual/v0.7-pdf")
    assert "glowRasterizer" not in baseline
    assert glow == {**baseline, "glowRasterizer": _draft_resvg_rasterizer()}
    assert glow["glowRasterizer"]["dpi"] == 96
    assert _draft_rasterizer("png", "chrona-output/visual/v0.7-png") == _draft_resvg_rasterizer()
