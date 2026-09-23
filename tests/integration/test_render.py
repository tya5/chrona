"""Current render-product integration evidence.

The former minimal schedule-SVG adapter is intentionally absent: this proves
authoring inputs enter the same review pipeline as immutable evidence renders.
"""
from pathlib import Path

import yaml

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def _draft_request(*, project_path: Path | None = None, view_path: Path | None = None,
                   actual_path: Path | None = None, icon_catalog_paths: tuple[Path, ...] = (),
                   visual_profile: str = "chrona-output/visual/v0.5-baseline") -> RenderRequest:
    root = _root()
    draft = resolve_draft_render(
        project_path=project_path or root / "examples/controller-z/project.yaml",
        view_path=view_path or root / "examples/controller-z/views/executive.yaml",
        theme_path=root / "examples/controller-z/themes/executive-light.yaml",
        scheme_path=root / "examples/controller-z/schemes/executive-light.yaml",
        layout_path=root / "conformance/layout-profile-intent-v0.2.yaml",
        actual_path=actual_path or root / "examples/controller-z/actual.yaml",
        icon_catalog_paths=icon_catalog_paths,
        visual_profile=visual_profile,
    )
    return RenderRequest(
        closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
        scheduler=ReferenceScheduler(), renderer=V05SvgRenderer(),
    )


def test_draft_render_materializes_the_review_surface():
    svg = render_review(_draft_request()).artifact.content.decode()
    assert '<svg ' in svg
    assert 'data-source-ref="firmware"' in svg
    assert 'data-presentation-adapter="legacy-v0.1"' not in svg


def test_draft_render_is_deterministic():
    assert render_review(_draft_request()).artifact.content == render_review(_draft_request()).artifact.content


def test_draft_visual_ref_reaches_layout_and_scene_icon(tmp_path):
    root = _root()
    view = yaml.safe_load((root / "examples/controller-z/views/executive.yaml").read_text(encoding="utf-8"))
    view["body"]["visuals"] = [{"target": {"kind": "title"}, "ref": "chrona:risk", "decorative": False}]
    path = tmp_path / "visual-view.yaml"; path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")

    svg = render_review(_draft_request(view_path=path, icon_catalog_paths=(root / "examples/controller-z/icons.yaml",),
                                       visual_profile="chrona-output/visual/v0.7-svg")).artifact.content.decode()

    assert 'data-asset-identity=' in svg
    assert 'aria-label="Delivery risk"' in svg


def test_actual_progress_fill_uses_actual_set_progress_and_omits_absent_host(tmp_path):
    root = _root()
    actual_view = yaml.safe_load((root / "examples/controller-z/views/executive.yaml").read_text(encoding="utf-8"))
    actual_view["body"]["progressFill"] = {"source": "actual"}
    view_path = tmp_path / "actual-view.yaml"
    view_path.write_text(yaml.safe_dump(actual_view, sort_keys=False), encoding="utf-8")

    svg = render_review(_draft_request(view_path=view_path)).artifact.content.decode()
    assert 'data-scene-id="progress-fill:actual:firmware:firmware"' in svg
    assert 'data-purpose="progress-fill"' in svg

    actual = yaml.safe_load((root / "examples/controller-z/actual.yaml").read_text(encoding="utf-8"))
    actual["body"]["observations"][0]["actual"] = {"progress": 0.5}
    missing_host_path = tmp_path / "missing-host.yaml"
    missing_host_path.write_text(yaml.safe_dump(actual, sort_keys=False), encoding="utf-8")
    without_host = render_review(_draft_request(view_path=view_path, actual_path=missing_host_path)).artifact.content.decode()
    assert 'data-scene-id="progress-fill:actual:firmware:firmware"' not in without_host


def test_progress_fill_omits_absent_and_zero_planned_progress(tmp_path):
    root = _root()
    project = yaml.safe_load((root / "examples/controller-z/project.yaml").read_text(encoding="utf-8"))
    for item in project["objects"].values():
        item.pop("plannedProgress", None)
    project_path = tmp_path / "without-progress.yaml"
    project_path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
    view = yaml.safe_load((root / "examples/controller-z/views/executive.yaml").read_text(encoding="utf-8"))
    view["body"]["progressFill"] = {"source": "planned"}
    view_path = tmp_path / "planned-view.yaml"
    view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")

    svg = render_review(_draft_request(project_path=project_path, view_path=view_path)).artifact.content.decode()
    assert 'data-purpose="progress-fill"' not in svg

    project["objects"]["firmware"]["plannedProgress"] = 0
    project_path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
    zero = render_review(_draft_request(project_path=project_path, view_path=view_path)).artifact.content.decode()
    assert 'data-scene-id="progress-fill:planned:firmware:firmware"' not in zero
