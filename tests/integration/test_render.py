"""Current render-product integration evidence.

The former minimal schedule-SVG adapter is intentionally absent: this proves
authoring inputs enter the same review pipeline as immutable evidence renders.
"""
from pathlib import Path

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def _draft_request() -> RenderRequest:
    root = _root()
    draft = resolve_draft_render(
        project_path=root / "examples/controller-z/project.yaml",
        view_path=root / "examples/controller-z/views/executive.yaml",
        theme_path=root / "examples/controller-z/themes/executive-light.yaml",
        scheme_path=root / "examples/controller-z/schemes/executive-light.yaml",
        layout_path=root / "conformance/layout-profile-intent-v0.2.yaml",
        actual_path=root / "examples/controller-z/actual.yaml",
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
