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
    context = draft.closure.context
    return render_review(RenderRequest(
        draft.closure, draft.asset_root, ReferenceScheduler(),
        renderer_for({"kind": context.target.kind, "capabilities": list(context.target.capabilities)},
                     {"rasterizer": context.environment.rasterizer} if context.environment.rasterizer else {}),
        asset_root=draft.asset_root,
    )).artifact


def _completed_surface():
    root = _root()
    draft = resolve_draft_render(
        project_path=root / "examples/controller-z/project.yaml", view_path=root / "examples/controller-z/views/executive.yaml",
        theme_path=root / "examples/controller-z/themes/executive-light.yaml", scheme_path=root / "examples/controller-z/schemes/executive-light.yaml",
        layout_path=root / "conformance/layout-profile-intent-v0.2.yaml", actual_path=root / "examples/controller-z/actual.yaml",
    )
    context = draft.closure.context
    rendered = render_review(RenderRequest(
        draft.closure, draft.asset_root, ReferenceScheduler(),
        renderer_for({"kind": context.target.kind, "capabilities": list(context.target.capabilities)}, context.environment.renderer_environment()),
        asset_root=draft.asset_root,
    ))
    return rendered.surface


@pytest.mark.parametrize(("kind", "media_type", "prefix"), [("png", "image/png", b"\x89PNG\r\n\x1a\n"), ("pdf", "application/pdf", b"%PDF-")])
def test_export_targets_are_pinned_and_repeatable(kind, media_type, prefix):
    first, second = _render(kind), _render(kind)
    assert (first.target_kind, first.media_type, first.content[:len(prefix)]) == (kind, media_type, prefix)
    assert first.content == second.content


def test_raster_target_rejects_semantic_capability_requirement():
    with pytest.raises(ValueError, match="E_OUTPUT_CAPABILITY_MISSING"):
        renderer_for({"kind": "png", "capabilities": ["accessibleText"]}, {"rasterizer": {"engine": "cairosvg", "version": "2.9.1", "cairoVersion": "1.18.4", "dpi": 96}})


def test_rasterizer_identity_mismatch_is_rejected():
    with pytest.raises(ValueError, match="E_RENDER_RASTERIZER_IDENTITY"):
        renderer_for({"kind": "png", "capabilities": []}, {"rasterizer": {"engine": "resvg-py", "version": "wrong", "resvgVersion": "wrong", "dpi": 96}}).render(None, viewport=(1, 1))


def test_pdf_rasterizer_identity_mismatch_is_rejected():
    with pytest.raises(ValueError, match="E_RENDER_RASTERIZER_IDENTITY"):
        renderer_for({"kind": "pdf", "capabilities": []}, {"rasterizer": {"engine": "reportlab", "svglibVersion": "wrong", "reportlabVersion": "wrong", "invariant": True}}).render(None, viewport=(1, 1))


@pytest.mark.parametrize(("kind", "media_type", "signature", "identity"), [
    ("typst", "application/x-typst", b"// chrona-typst/v0.1", "chrona-typst/v0.1"),
    ("tikz", "application/x-tex", b"% chrona-tikz/v0.1", "chrona-tikz/v0.1"),
])
def test_typeset_sources_preserve_completed_placement_order(kind, media_type, signature, identity):
    surface = _completed_surface()
    descriptor = ({"engine": "typst", "version": "0.13.1", "adapterGrammar": identity}
                  if kind == "typst" else {"engine": "tectonic", "version": "0.15.0", "adapterGrammar": identity})
    renderer = renderer_for({"kind": kind, "capabilities": []}, {"typesetter": descriptor})
    first = renderer.render(surface, viewport=(1600, 900))
    second = renderer.render(surface, viewport=(1600, 900))
    source = first.content.decode("utf-8")
    assert (first.target_kind, first.media_type, first.content[:len(signature)], first.adapter_identity) == (kind, media_type, signature, identity)
    assert first.content == second.content
    identifiers = [f"scene-id: {node.scene_id}" for node in surface.primitives]
    assert [source.index(identifier) for identifier in identifiers] == sorted(source.index(identifier) for identifier in identifiers)
    assert "font-asset:" in source and "baseline:" in source


def test_typeset_target_rejects_svg_semantic_requirement():
    with pytest.raises(ValueError, match="E_OUTPUT_CAPABILITY_MISSING"):
        renderer_for({"kind": "typst", "capabilities": ["accessibleText"]}, {"typesetter": {"engine": "typst", "version": "0.13.1", "adapterGrammar": "chrona-typst/v0.1"}})


def test_typeset_identity_mismatch_is_rejected():
    with pytest.raises(ValueError, match="E_RENDER_TYPESETTER_IDENTITY"):
        renderer_for({"kind": "tikz", "capabilities": []}, {"typesetter": {"engine": "typst", "version": "0.13.1", "adapterGrammar": "chrona-tikz/v0.1"}})


def test_typeset_adapters_are_completed_scene_only():
    source = Path(__import__("chrona.presentation.renderers.v05_typeset", fromlist=["*"]).__file__).read_text(encoding="utf-8")
    forbidden = ("chrona.presentation.layout", "chrona.presentation.contracts", "chrona.scheduling", "font_metrics", "route_", "resolve_draft")
    assert all(fragment not in source for fragment in forbidden)
