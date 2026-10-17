"""The PDF registry consumes closed glow engine/font evidence, never discovers it."""
from importlib.metadata import version
from io import BytesIO
from types import SimpleNamespace

import pytest
from pypdf import PdfReader
from pypdf.generic import ContentStream

from chrona.presentation.model.font_metrics import FontFile
from chrona.presentation.renderers import registry
from chrona.presentation.scene.model import Glow, ScenePaint, ScenePrimitive, StrokeFinish
from tests.unit.chrona.presentation.renderers.test_pdf_scene_paints import _surface


def _descriptor():
    return {"engine": "reportlab", "svglibVersion": version("svglib"),
            "reportlabVersion": version("reportlab"), "invariant": True}


def _glowing_surface():
    return _surface(ScenePrimitive(
        "lamp", "Rect", "lamp", "object", "planned", "planned", (30, 30, 20, 20),
        paint=ScenePaint("#FF0000", None, None, (), 1,
                         glow=Glow("#FFCC00", 3, 0.8, "required", (21, 21, 38, 38)))))


@pytest.mark.parametrize("glow", [None, {}, "resvg-py", {"dpi": 72}, {"dpi": True}])
def test_glowing_pdf_requires_valid_pinned_halo_evidence(glow):
    descriptor = {**_descriptor(), "glowRasterizer": glow}
    with pytest.raises(ValueError, match="E_RENDER_RASTERIZER_IDENTITY"):
        registry.ReportLabPdfRenderer(descriptor, None, None, font_files=()).render(_glowing_surface())


def test_glow_rejects_engine_version_mismatch_before_lowering():
    descriptor = {**_descriptor(), "glowRasterizer": {
        "engine": "resvg-py", "version": "not-installed", "resvgVersion": "not-installed", "dpi": 96}}
    with pytest.raises(ValueError, match="E_RENDER_RASTERIZER_IDENTITY"):
        registry.ReportLabPdfRenderer(descriptor, None, None, font_files=()).render(_glowing_surface())


def test_glow_engine_unavailable_keeps_the_existing_typed_failure(monkeypatch):
    def unavailable(_descriptor):
        raise ValueError("E_RENDER_RASTERIZER_UNAVAILABLE: resvg_py unavailable")
    monkeypatch.setattr(registry, "_verify_resvg", unavailable)
    descriptor = {**_descriptor(), "glowRasterizer": {"dpi": 96}}
    with pytest.raises(ValueError, match="E_RENDER_RASTERIZER_UNAVAILABLE"):
        registry.ReportLabPdfRenderer(descriptor, None, None, font_files=()).render(_glowing_surface())


def test_no_glow_pdf_does_not_require_or_verify_resvg(monkeypatch):
    def forbidden(_descriptor):
        pytest.fail("a vector-only PDF must not verify or import the halo engine")
    monkeypatch.setattr(registry, "_verify_pdf_glow_rasterizer", forbidden)
    surface = _surface(ScenePrimitive("box", "Rect", "box", "object", "planned", "planned",
                                      (10, 10, 20, 20), paint=ScenePaint("#224466", None, None, (), 1)))
    renderer = registry.ReportLabPdfRenderer(_descriptor(), None, None, font_files=())
    artifact = renderer.render(surface)
    assert artifact.content.startswith(b"%PDF-")
    assert "resvg" not in artifact.adapter_identity


def test_glow_forces_exact_primary_face_alias_even_without_fallback_runs(tmp_path):
    layout = SimpleNamespace(family="Face", weight=400, asset_identity="sha256:exact", runs=())
    surface = SimpleNamespace(primitives=(SimpleNamespace(kind="Text", scene_id="title", text_layout=layout),))
    svg = b'<svg><text data-scene-id="title" font-family="Face" font-weight="400">A</text></svg>'
    files = (FontFile(tmp_path / "face.ttf", "sha256:exact", "Face", 400),)
    assert registry._pdf_private_svg(surface, svg, files) == (svg, None)
    private, aliases = registry._pdf_private_svg(surface, svg, files, force_asset_aliases=True)
    assert registry._svg_font_characters(private) == {(aliases[("sha256:exact", "face", 400)], 400): frozenset({65})}
    with pytest.raises(ValueError, match="E_RENDER_FONT_CLOSURE"):
        registry._pdf_private_svg(surface, svg, (), force_asset_aliases=True)


def test_glowing_pdf_contains_only_halo_image_with_soft_mask_and_keeps_vector_source():
    import resvg_py

    descriptor = {**_descriptor(), "glowRasterizer": {
        "engine": "resvg-py", "version": resvg_py.__version__,
        "resvgVersion": resvg_py.__resvg_version__, "dpi": 96}}
    artifact = registry.ReportLabPdfRenderer(descriptor, None, None, font_files=()).render(_glowing_surface())
    reader = PdfReader(BytesIO(artifact.content))
    page = reader.pages[0]
    images = [reference.get_object() for reference in page["/Resources"]["/XObject"].values()
              if reference.get_object().get("/Subtype") == "/Image"]
    assert len(images) == 1
    assert "/SMask" in images[0]
    assert (images[0]["/Width"], images[0]["/Height"]) == (38, 38)
    assert any(operator == b"re" and tuple(operands) == (30, 30, 20, 20)
               for operands, operator in ContentStream(page.get_contents(), reader).operations)
    assert "pdf-resvg-completed-glow-v2" in artifact.adapter_identity
    assert "pdf-native-raster-face-alias-v1" in artifact.adapter_identity
    assert f"resvg-py-{resvg_py.__version__}-resvg-{resvg_py.__resvg_version__}-dpi96" in artifact.adapter_identity


@pytest.mark.parametrize("cap,cap_number", [("butt", 0), ("round", 1), ("square", 2)])
@pytest.mark.parametrize("join,join_number", [("miter", 0), ("round", 1), ("bevel", 2)])
def test_pdf_admitted_stroke_finishes_remain_native(cap, cap_number, join, join_number):
    node = ScenePrimitive("line", "Path", "line", "relation", "dependency", "dependency", (10, 10, 60, 40),
                          points=((10, 10), (70, 10), (70, 50)),
                          paint=ScenePaint(None, "#224466", 3, (), 1,
                                           stroke_finish=StrokeFinish(cap, join, "required")))
    artifact = registry.ReportLabPdfRenderer(_descriptor(), None, None, font_files=()).render(_surface(node))
    reader = PdfReader(BytesIO(artifact.content))
    operations = ContentStream(reader.pages[0].get_contents(), reader).operations
    assert any(operator == b"J" and tuple(operands) == (cap_number,) for operands, operator in operations)
    assert any(operator == b"j" and tuple(operands) == (join_number,) for operands, operator in operations)
    assert not reader.pages[0]["/Resources"].get("/XObject")


def test_glow_halo_preserves_vector_relation_and_completed_terminal():
    import resvg_py
    from chrona.presentation.layout.relation_terminals import marker_geometry

    node = ScenePrimitive("route", "Path", "route", "relation", "dependency", "dependency", (10, 10, 60, 40),
                          points=((10, 10), (70, 10), (70, 50)),
                          marker_end=marker_geometry({"shape": "triangle", "headLength": 8, "headWidth": 6},
                                                     stroke_width=3),
                          paint=ScenePaint(None, "#224466", 3, (), 1,
                                           glow=Glow("#FFD24A", 3, 0.8, "required", (0, 0, 90, 70))))
    descriptor = {**_descriptor(), "glowRasterizer": {
        "engine": "resvg-py", "version": resvg_py.__version__,
        "resvgVersion": resvg_py.__resvg_version__, "dpi": 96}}
    artifact = registry.ReportLabPdfRenderer(descriptor, None, None, font_files=()).render(_surface(node))
    reader = PdfReader(BytesIO(artifact.content))
    operations = ContentStream(reader.pages[0].get_contents(), reader).operations
    assert any(operator == b"l" and tuple(operands) == (70, 50) for operands, operator in operations)
    # The terminal is a filled vector contour, not absorbed into the halo image.
    assert any(operator in {b"f", b"f*"} for _, operator in operations)
    images = [reference.get_object() for reference in reader.pages[0]["/Resources"]["/XObject"].values()
              if reference.get_object().get("/Subtype") == "/Image"]
    assert len(images) == 1 and "/SMask" in images[0]
