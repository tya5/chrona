from pathlib import Path

import pytest

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.renderers.registry import renderer_for
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def _render(kind: str):
    root = _root()
    draft = resolve_draft_render(
        project_path=root / "examples/controller-z/project.yaml", view_path=root / "examples/controller-z/views/executive.yaml",
        theme_path=root / "examples/controller-z/themes/executive-light.yaml", scheme_path=root / "examples/controller-z/schemes/executive-light.yaml",
        layout_path=root / "conformance/layout-profile-intent-v0.2.yaml", actual_path=root / "examples/controller-z/actual.yaml", target_kind=kind,
    )
    return render_review(RenderRequest(draft.closure, draft.asset_root, ReferenceScheduler(), renderer_for(draft.closure.context.body["target"], draft.closure.context.body["environment"]), asset_root=draft.asset_root)).artifact


@pytest.mark.parametrize(("kind", "media_type", "prefix"), [("png", "image/png", b"\x89PNG\r\n\x1a\n"), ("pdf", "application/pdf", b"%PDF-")])
def test_cairo_targets_are_pinned_and_repeatable(kind, media_type, prefix):
    first, second = _render(kind), _render(kind)
    assert (first.target_kind, first.media_type, first.content[:len(prefix)]) == (kind, media_type, prefix)
    assert first.content == second.content


def test_raster_target_rejects_semantic_capability_requirement():
    with pytest.raises(ValueError, match="E_OUTPUT_CAPABILITY_MISSING"):
        renderer_for({"kind": "png", "capabilities": ["accessibleText"]}, {"rasterizer": {"engine": "cairosvg", "version": "2.9.1", "cairoVersion": "1.18.4", "dpi": 96}})


def test_rasterizer_identity_mismatch_is_rejected():
    with pytest.raises(ValueError, match="E_RENDER_RASTERIZER_IDENTITY"):
        renderer_for({"kind": "png", "capabilities": []}, {"rasterizer": {"engine": "cairosvg", "version": "wrong", "cairoVersion": "wrong", "dpi": 96}}).render(None, viewport=(1, 1), tokens=None)


def test_pdf_rasterizer_identity_mismatch_is_rejected():
    with pytest.raises(ValueError, match="E_RENDER_RASTERIZER_IDENTITY"):
        renderer_for({"kind": "pdf", "capabilities": []}, {"rasterizer": {"engine": "reportlab", "svglibVersion": "wrong", "reportlabVersion": "wrong", "invariant": True}}).render(None, viewport=(1, 1), tokens=None)
