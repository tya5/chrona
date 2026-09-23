from pathlib import Path
from datetime import date
from importlib.metadata import version

import pytest

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.renderers.registry import renderer_for
from chrona.presentation.scene.model import DropShadow, LinearGradient, ScenePaint, ScenePrimitive, SceneSurface, StrokeFinish, SurfaceScaleManifest
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


def test_svg_derivative_adapters_characterize_one_completed_rich_surface():
    import resvg_py

    paint = ScenePaint("#112233", "#445566", 1, (), 1,
                       LinearGradient((1, 2), (4, 5), ((0, "#112233"), (1, "#778899")), "required"),
                       DropShadow("#000000", 1, 2, 3, 0.4, "required"), StrokeFinish("round", "bevel", "required"))
    scale = SurfaceScaleManifest("s", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 1, 0, 1)
    surface = SceneSurface("s", (), (), (), scale,
                           (ScenePrimitive("p", "Rect", "a", "object", "planned", "planned", (1, 2, 40, 10), paint=paint),),
                           ScenePaint("#ffffff", None, None, (), 1))
    environments = {
        "png": {"rasterizer": {"engine": "resvg-py", "version": resvg_py.__version__, "resvgVersion": resvg_py.__resvg_version__, "dpi": 96}},
        "pdf": {"rasterizer": {"engine": "reportlab", "svglibVersion": version("svglib"), "reportlabVersion": version("reportlab"), "invariant": True}},
    }
    for kind, prefix in (("png", b"\x89PNG\r\n\x1a\n"), ("pdf", b"%PDF-")):
        renderer = renderer_for({"kind": kind, "capabilities": []}, environments[kind])
        first = renderer.render(surface, viewport=(100, 50)).content
        assert first.startswith(prefix) and first == renderer.render(surface, viewport=(100, 50)).content


def test_renderer_adapters_do_not_import_theme_scheme_or_profile_policy():
    paths = ("chrona.presentation.renderers.v05_svg", "chrona.presentation.renderers.v05_typeset", "chrona.presentation.renderers.registry")
    forbidden = ("color_scheme", "theme_tokens", "visual_capabilities", "resolve_scene_paint", "resolve_theme")
    for module_name in paths:
        source = Path(__import__(module_name, fromlist=["*"]).__file__).read_text(encoding="utf-8")
        assert all(fragment not in source for fragment in forbidden)
