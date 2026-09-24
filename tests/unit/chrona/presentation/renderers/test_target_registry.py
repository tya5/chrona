from io import BytesIO
from hashlib import sha256
from importlib.resources import files
from pathlib import Path

import pytest
import yaml
from PIL import Image, ImageChops

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.renderers.registry import renderer_for
from chrona.presentation.scene.visual_capabilities import BASELINE_PROFILE, PNG_PROFILE
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderFailed, RenderRequest, render_review


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
                     context.environment.renderer_environment(), asset_root=draft.asset_root),
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
        renderer_for({"kind": context.target.kind, "capabilities": list(context.target.capabilities)}, context.environment.renderer_environment(), asset_root=draft.asset_root),
        asset_root=draft.asset_root,
    ))
    return rendered.surface


@pytest.mark.parametrize(("kind", "media_type", "prefix"), [("png", "image/png", b"\x89PNG\r\n\x1a\n"), ("pdf", "application/pdf", b"%PDF-")])
def test_export_targets_are_pinned_and_repeatable(kind, media_type, prefix):
    first, second = _render(kind), _render(kind)
    assert (first.target_kind, first.media_type, first.content[:len(prefix)]) == (kind, media_type, prefix)
    assert first.content == second.content


def test_declared_cjk_font_closure_reaches_svg_png_and_pdf_without_host_fonts(tmp_path):
    root = _root()
    example = root / "examples/controller-z-ja"
    cjk_provider = pytest.importorskip(
        "chrona_fonts_noto_cjk", reason="requires the optional local CJK font provider",
    )
    cjk_descriptor = files(cjk_provider).joinpath("font-metrics.yaml")

    def render(kind: str):
        draft = resolve_draft_render(
            project_path=example / "project.yaml", view_path=example / "views/executive.yaml",
            theme_path=example / "themes/executive-light.yaml",
            scheme_path=example / "schemes/executive-light.yaml",
            layout_path=example / "layouts/executive-review.yaml",
            actual_path=example / "actual.yaml", target_kind=kind, locale="ja-JP",
                font_metrics_path=Path(str(cjk_descriptor)),
        )
        context = draft.closure.context
        return render_review(RenderRequest(
            draft.closure, draft.asset_root, ReferenceScheduler(),
            renderer_for({"kind": context.target.kind, "capabilities": list(context.target.capabilities)},
                         context.environment.renderer_environment(), asset_root=draft.asset_root),
            asset_root=draft.asset_root,
        )).artifact.content

    svg, png, pdf = render("svg"), render("png"), render("pdf")
    assert "シリコン立ち上げおよび初期機能確認" in svg.decode("utf-8")
    assert png.startswith(b"\x89PNG\r\n\x1a\n") and pdf.startswith(b"%PDF-")
    assert sha256(png).hexdigest() == sha256(render("png")).hexdigest()


def test_public_render_diagnoses_a_glyph_absent_from_declared_metrics(tmp_path):
    root = _root()
    project = yaml.safe_load((root / "examples/controller-z/project.yaml").read_text(encoding="utf-8"))
    project["project"]["title"] = "Known \U0010ffff"
    project_path = tmp_path / "project-missing-glyph.yaml"
    project_path.write_text(yaml.safe_dump(project, allow_unicode=True, sort_keys=False), encoding="utf-8")
    draft = resolve_draft_render(
        project_path=project_path, view_path=root / "examples/controller-z/views/executive.yaml",
        theme_path=root / "examples/controller-z/themes/executive-light.yaml",
        scheme_path=root / "examples/controller-z/schemes/executive-light.yaml",
        layout_path=root / "conformance/layout-profile-intent-v0.2.yaml",
        actual_path=root / "examples/controller-z/actual.yaml",
    )
    with pytest.raises(RenderFailed, match="E_FONT_GLYPH_UNAVAILABLE") as error:
        render_review(RenderRequest(draft.closure, draft.asset_root, ReferenceScheduler(), asset_root=draft.asset_root))
    assert error.value.source_ref == "/body/environment/fontMetrics"
    assert "U+10FFFF" in error.value.message


def test_svg_accepts_metrics_only_but_png_names_missing_declared_font_bytes(tmp_path):
    root = _root()
    descriptor = yaml.safe_load(files("chrona.resources").joinpath("fonts", "default-font-metrics.yaml").read_text())
    descriptor["assets"][0]["font"]["locator"]["address"] = "fonts/absent-regular.ttf"
    descriptor_path = tmp_path / "metrics-only.yaml"
    descriptor_path.write_text(yaml.safe_dump(descriptor, sort_keys=False), encoding="utf-8")

    def draft(kind: str):
        return resolve_draft_render(
            project_path=root / "examples/controller-z/project.yaml", view_path=root / "examples/controller-z/views/executive.yaml",
            theme_path=root / "examples/controller-z/themes/executive-light.yaml", scheme_path=root / "examples/controller-z/schemes/executive-light.yaml",
            layout_path=root / "conformance/layout-profile-intent-v0.2.yaml", actual_path=root / "examples/controller-z/actual.yaml",
            target_kind=kind, font_metrics_path=descriptor_path,
        )

    svg = draft("svg")
    assert render_review(RenderRequest(svg.closure, svg.asset_root, ReferenceScheduler(), asset_root=svg.asset_root)).artifact.target_kind == "svg"
    png = draft("png")
    with pytest.raises(RenderFailed, match="E_FONT_METRICS_UNAVAILABLE") as error:
        render_review(RenderRequest(png.closure, png.asset_root, ReferenceScheduler(), asset_root=png.asset_root))
    assert "fonts/absent-regular.ttf" in error.value.message


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


def test_public_png_profile_preserves_optional_rich_treatment_in_pixels(tmp_path):
    root = _root()
    theme = yaml.safe_load((root / "examples/controller-z/themes/elevated-light.yaml").read_text(encoding="utf-8"))
    theme["body"]["values"]["elevated.fidelity"]["value"] = "decorative-optional"
    theme_path = tmp_path / "optional-elevated.yaml"
    theme_path.write_text(yaml.safe_dump(theme, sort_keys=False))

    def render(profile: str) -> bytes:
        draft = resolve_draft_render(
            project_path=root / "examples/controller-z/project.yaml", view_path=root / "examples/controller-z/views/executive.yaml",
            theme_path=theme_path, scheme_path=root / "examples/controller-z/schemes/executive-light.yaml",
            layout_path=root / "conformance/layout-profile-intent-v0.2.yaml", actual_path=root / "examples/controller-z/actual.yaml",
            target_kind="png", visual_profile=profile,
        )
        context = draft.closure.context
        return render_review(RenderRequest(
            draft.closure, draft.asset_root, ReferenceScheduler(),
            renderer_for({"kind": context.target.kind, "capabilities": list(context.target.capabilities)},
                         context.environment.renderer_environment(), asset_root=draft.asset_root), asset_root=draft.asset_root,
        )).artifact.content

    baseline, rich = render(BASELINE_PROFILE), render(PNG_PROFILE)
    assert baseline.startswith(b"\x89PNG\r\n\x1a\n") and rich.startswith(b"\x89PNG\r\n\x1a\n")
    baseline_pixels = Image.open(BytesIO(baseline)).convert("RGB")
    rich_pixels = Image.open(BytesIO(rich)).convert("RGB")
    assert baseline_pixels.size == rich_pixels.size
    assert ImageChops.difference(baseline_pixels, rich_pixels).getbbox() is not None


def test_renderer_adapters_do_not_import_theme_scheme_or_profile_policy():
    paths = ("chrona.presentation.renderers.v05_svg", "chrona.presentation.renderers.v05_typeset", "chrona.presentation.renderers.registry")
    forbidden = ("color_scheme", "theme_tokens", "visual_capabilities", "resolve_scene_paint", "resolve_theme")
    for module_name in paths:
        source = Path(__import__(module_name, fromlist=["*"]).__file__).read_text(encoding="utf-8")
        assert all(fragment not in source for fragment in forbidden)
