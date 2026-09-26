from io import BytesIO
from dataclasses import replace
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
import platform
import shutil

import pytest
import yaml
from PIL import Image, ImageChops

from chrona.presentation.model.closure import ClosureError, resolve_draft_render
from chrona.presentation.fonts.system import resolve_system_font
from chrona.presentation.scene.serialization import serialize_scene
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


def _fixture_system_resolver(root: Path):
    face = root / "src/chrona/resources/fonts/noto-sans-regular-v1.ttf"

    def runner(_command, **_kwargs):
        return type("Result", (), {"stdout": f"{face}\nNoto Sans\n80\n0\n"})()

    return lambda family, weight: resolve_system_font(family, weight, runner=runner)


def test_draft_system_font_png_receives_the_measured_file_without_scene_path_provenance():
    root = _root()
    draft = resolve_draft_render(
        project_path=root / "examples/controller-z/project.yaml", view_path=root / "examples/controller-z/views/executive.yaml",
        theme_path=root / "examples/controller-z/themes/executive-light.yaml", scheme_path=root / "examples/controller-z/schemes/executive-light.yaml",
        layout_path=root / "conformance/layout-profile-intent-v0.2.yaml", actual_path=root / "examples/controller-z/actual.yaml",
        target_kind="png", system_fonts=True, system_font_resolver=_fixture_system_resolver(root),
    )
    context = draft.closure.context
    rendered = render_review(RenderRequest(
        draft.closure, draft.asset_root, ReferenceScheduler(),
        renderer_for({"kind": context.target.kind, "capabilities": list(context.target.capabilities)},
                     context.environment.renderer_environment(), asset_root=draft.asset_root,
                     font_files=draft.font_resolution.font_files),
        asset_root=draft.asset_root, draft_font_resolution=draft.font_resolution,
    ))

    assert rendered.artifact.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert all(str(face.path).encode() not in serialize_scene(rendered.scene)
               for face in draft.font_resolution.faces)


def test_real_hiragino_collection_paints_png_from_selected_face_on_macos(tmp_path):
    if platform.system() != "Darwin" or not shutil.which("fc-match"):
        pytest.skip("Hiragino collection and fontconfig are macOS host evidence")
    root = _root()
    theme = yaml.safe_load((root / "examples/controller-z/themes/executive-light.yaml").read_text())
    theme["body"]["values"]["editorial"]["value"] = "Hiragino Sans"
    theme_path = tmp_path / "hiragino.yaml"
    theme_path.write_text(yaml.safe_dump(theme, sort_keys=False), encoding="utf-8")
    draft = resolve_draft_render(
        project_path=root / "examples/controller-z/project.yaml",
        view_path=root / "examples/controller-z/views/executive.yaml", theme_path=theme_path,
        scheme_path=root / "examples/controller-z/schemes/executive-light.yaml",
        layout_path=root / "conformance/layout-profile-intent-v0.2.yaml",
        actual_path=root / "examples/controller-z/actual.yaml", target_kind="png", system_fonts=True,
    )
    assert draft.font_resolution is not None
    assert draft.font_resolution.faces[0].path.suffix == ".ttc"
    rendered = render_review(RenderRequest(
        draft.closure, draft.asset_root, ReferenceScheduler(), asset_root=draft.asset_root,
        draft_font_resolution=draft.font_resolution,
    ))
    bitmap = Image.open(BytesIO(rendered.artifact.content)).convert("RGB")
    title = next(item for item in rendered.scene.surfaces[0].primitives if item.scene_id == "title")
    x, y, width, height = title.bounds
    painted_title = bitmap.crop((int(x), int(y), int(x + width), int(y + height)))
    assert painted_title.getbbox() is not None
    assert len(painted_title.getcolors(maxcolors=1_000_000) or ()) > 1
    assert all(item.path.suffix == ".ttc" for item in draft.font_resolution.font_files)
    assert title.text_layout is not None
    assert title.text_layout.asset_identity == draft.font_resolution.faces[0].content_identity
    assert rendered.artifact.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_hiragino_unsupported_tabular_mode_is_rejected_before_layout_on_macos(tmp_path):
    if platform.system() != "Darwin" or not shutil.which("fc-match"):
        pytest.skip("Hiragino collection and fontconfig are macOS host evidence")
    root = _root()
    theme = yaml.safe_load((root / "examples/controller-z/themes/executive-light.yaml").read_text())
    theme["body"]["values"]["editorial"]["value"] = "Hiragino Sans"
    theme["body"]["values"]["numeric-spacing"]["value"] = "tabular"
    theme_path = tmp_path / "hiragino-tabular.yaml"
    theme_path.write_text(yaml.safe_dump(theme, sort_keys=False), encoding="utf-8")
    with pytest.raises(ClosureError, match="E_FONT_METRICS_UNAVAILABLE") as error:
        resolve_draft_render(**{
            "project_path": root / "examples/controller-z/project.yaml",
            "view_path": root / "examples/controller-z/views/executive.yaml", "theme_path": theme_path,
            "scheme_path": root / "examples/controller-z/schemes/executive-light.yaml",
            "layout_path": root / "conformance/layout-profile-intent-v0.2.yaml",
            "system_fonts": True,
        })
    assert "tabular digit advances" in (error.value.detail or "")


def test_system_font_resolution_is_rejected_if_a_caller_attempts_immutable_rendering():
    root = _root()
    draft = resolve_draft_render(
        project_path=root / "examples/controller-z/project.yaml", view_path=root / "examples/controller-z/views/executive.yaml",
        theme_path=root / "examples/controller-z/themes/executive-light.yaml", scheme_path=root / "examples/controller-z/schemes/executive-light.yaml",
        layout_path=root / "conformance/layout-profile-intent-v0.2.yaml", actual_path=root / "examples/controller-z/actual.yaml",
        system_fonts=True, system_font_resolver=_fixture_system_resolver(root),
    )
    immutable_context = replace(draft.closure.context, identity=replace(draft.closure.context.identity, revision="immutable"))
    immutable = replace(draft.closure, context=immutable_context)

    with pytest.raises(RenderFailed, match="E_FONT_SYSTEM_IMMUTABLE"):
        render_review(RenderRequest(immutable, draft.asset_root, ReferenceScheduler(),
                                    draft_font_resolution=draft.font_resolution, asset_root=draft.asset_root))


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
        renderer_for({"kind": "png", "capabilities": []}, {"rasterizer": {"engine": "resvg-py", "version": "wrong", "resvgVersion": "wrong", "dpi": 96}}).render(None)


def test_pdf_rasterizer_identity_mismatch_is_rejected():
    with pytest.raises(ValueError, match="E_RENDER_RASTERIZER_IDENTITY"):
        renderer_for({"kind": "pdf", "capabilities": []}, {"rasterizer": {"engine": "reportlab", "svglibVersion": "wrong", "reportlabVersion": "wrong", "invariant": True}}).render(None)


@pytest.mark.parametrize(("kind", "descriptor"), [
    ("typst", {"engine": "typst", "version": "0.13.1", "adapterGrammar": "chrona-typst/v0.1"}),
    ("tikz", {"engine": "tectonic", "version": "0.15.0", "adapterGrammar": "chrona-tikz/v0.1"}),
])
def test_typeset_rejects_completed_geometry_it_cannot_serialize(kind, descriptor):
    renderer = renderer_for({"kind": kind, "capabilities": []}, {"typesetter": descriptor})
    with pytest.raises(ValueError, match="E_VISUAL_CAPABILITY_UNSUPPORTED"):
        renderer.render(_completed_surface())


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
