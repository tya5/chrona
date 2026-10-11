from datetime import date
from types import SimpleNamespace

import pytest

from chrona.presentation.renderers import registry, v05_svg, v05_typeset
from chrona.presentation.scene.model import PathCommand, ScenePaint, ScenePrimitive, SceneSurface, SurfaceScaleManifest, TextLayout


def _surface(*primitives, canvas_paint=None, canvas_bounds=(0, 0, 10, 10)):
    scale = SurfaceScaleManifest("s", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 10, 0, 10)
    return SceneSurface("s", (), (), (), scale, primitives,
                        canvas_paint if canvas_paint is not None else ScenePaint("#fff", None, None, (), 1),
                        canvas_bounds=canvas_bounds)


def _error_text(call):
    with pytest.raises(ValueError) as error:
        call()
    return str(error.value)


def test_svg_paint_failure_names_canvas_field_and_expected_value():
    message = _error_text(lambda: v05_svg.render_v05_svg(_surface(canvas_paint=ScenePaint(None, None, None, (), 1))))
    assert message.startswith("E_PRESENTATION_PAINT_INVALID:")
    assert "canvasPaint.fill" in message and "background" in message


def test_svg_primitive_failure_names_identity_and_missing_payload():
    node = ScenePrimitive("broken-label", "Text", "src", "text", "label", "label", (1, 2, 3, 4),
                          paint=ScenePaint("#000", None, None, (), 1))
    message = _error_text(lambda: v05_svg.render_v05_svg(_surface(node)))
    assert message.startswith("E_PRESENTATION_PRIMITIVE_INVALID:")
    assert "broken-label" in message and "text_layout" in message and "baseline" in message


def test_typeset_paint_failure_names_primitive_and_channel():
    node = SimpleNamespace(scene_id="label-7", paint=SimpleNamespace(fill=None))
    message = _error_text(lambda: v05_typeset._color(node, "fill"))
    assert message.startswith("E_PRESENTATION_PAINT_INVALID:")
    assert "label-7" in message and "paint.fill" in message and "color string" in message
    assert "received None" in message


def test_typeset_numeric_spacing_failure_names_actual_value():
    message = _error_text(lambda: v05_typeset._typst_numeric_width(SimpleNamespace(numeric_spacing="narrow")))
    assert message.startswith("E_PRESENTATION_PRIMITIVE_INVALID:")
    assert "numeric_spacing='narrow'" in message and "tabular" in message


def test_typeset_opacity_failure_names_scene_and_invalid_value():
    node = SimpleNamespace(scene_id="fade-3", paint=SimpleNamespace(opacity=1.25))
    message = _error_text(lambda: v05_typeset._opacity(node))
    assert message.startswith("E_PRESENTATION_OPACITY_INVALID:")
    assert "fade-3" in message and "1.25" in message and "[0, 1]" in message


def test_typst_draws_a_rounded_path_as_a_curve_and_names_a_path_without_two_points():
    rounded = ScenePrimitive("curve-4", "Path", "src", "path", "planned", "planned", (1, 1, 3, 3),
                             points=((1, 1), (3, 3)),
                             path_commands=(PathCommand("move", ((1, 1),)), PathCommand("quadratic", ((1, 3), (3, 3)))),
                             paint=ScenePaint(None, "#000", 1, (), 1))
    assert "curve.quad((1pt, 3pt), (3pt, 3pt))" in v05_typeset.render_v05_typst(_surface(rounded))

    short = ScenePrimitive("curve-5", "Path", "src", "path", "planned", "planned", (1, 1, 3, 3),
                           points=((1, 1),), paint=ScenePaint(None, "#000", 1, (), 1))
    message = _error_text(lambda: v05_typeset.render_v05_typst(_surface(short)))
    assert message.startswith("E_PRESENTATION_PRIMITIVE_INVALID:") and "curve-5" in message and "two Path points" in message


def test_tikz_capability_failure_names_primitive_and_requested_scale():
    layout = TextLayout((1, 1, 3, 2), (1, 3), ("abc",), "Test Sans", 400, 2, 1,
                        "sha256:test", 0, "mixed", "proportional", horizontal_scale=0.8)
    node = ScenePrimitive("scaled-title", "Text", "src", "text", "title", "title", (1, 1, 3, 2),
                          text="abc", baseline=(1, 3), text_layout=layout,
                          paint=ScenePaint("#000", None, None, (), 1))
    message = _error_text(lambda: v05_typeset.render_v05_tikz(_surface(node)))
    assert message.startswith("E_VISUAL_CAPABILITY_UNSUPPORTED:")
    assert "scaled-title" in message and "horizontal_scale=0.8" in message


def test_registry_capability_failure_names_target_and_unsupported_capability():
    message = _error_text(lambda: registry.renderer_for(
        {"kind": "png", "capabilities": ["accessibleText"]}, {}))
    assert message.startswith("E_OUTPUT_CAPABILITY_MISSING:")
    assert "png" in message and "accessibleText" in message


def test_registry_identity_failure_names_expected_and_received_engine():
    message = _error_text(lambda: registry.renderer_for(
        {"kind": "typst", "capabilities": []},
        {"typesetter": {"engine": "tectonic", "adapterGrammar": "other"}}))
    assert message.startswith("E_RENDER_TYPESETTER_IDENTITY:")
    assert "chrona-typst/v0.1" in message and "other" in message


def test_registry_font_closure_error_names_required_inputs():
    closure = _error_text(lambda: registry._font_files(None, None))
    assert closure.startswith("E_RENDER_FONT_CLOSURE:") and "fontMetrics" in closure


def test_registry_target_error_names_unsupported_target():
    target = _error_text(lambda: registry.renderer_for({"kind": "eps", "capabilities": []}, {}))
    assert target.startswith("E_PRESENTATION_TARGET:") and "eps" in target and "svg" in target


def test_registry_rasterizer_identity_names_installed_adapter_version():
    message = _error_text(lambda: registry._verify_resvg(
        {"engine": "resvg-py", "version": "wrong", "resvgVersion": "wrong"}))
    assert message.startswith("E_RENDER_RASTERIZER_IDENTITY:")
    assert "descriptor engine/version/resvgVersion" in message and "resvg_py" in message


def test_registry_resvg_import_failure_names_missing_adapter(monkeypatch):
    import builtins

    original_import = builtins.__import__

    def reject_resvg(name, *args, **kwargs):
        if name == "resvg_py":
            raise ImportError("resvg adapter absent")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_resvg)
    message = _error_text(lambda: registry._verify_resvg({}))
    assert message.startswith("E_RENDER_RASTERIZER_UNAVAILABLE:")
    assert "resvg_py" in message and "rasterizer verification" in message


def test_registry_reportlab_unavailable_names_version_probe(monkeypatch):
    monkeypatch.setattr(registry, "version", lambda name: (_ for _ in ()).throw(LookupError(name)))
    message = _error_text(lambda: registry._verify_reportlab({}))
    assert message.startswith("E_RENDER_RASTERIZER_UNAVAILABLE:")
    assert "svglib/reportlab" in message and "inspected" in message


def test_render_input_failure_names_required_completed_surface_field():
    typst = _error_text(lambda: v05_typeset.V05TypstRenderer().render(object()))
    assert typst.startswith("E_PRESENTATION_RENDER_INPUT:") and "SceneSurface" in typst and "canvas paint" in typst
    assert "received object" in typst
    svg_surface = _surface(canvas_bounds=None)
    svg = _error_text(lambda: v05_svg.render_v05_svg(svg_surface))
    assert svg.startswith("E_PRESENTATION_RENDER_INPUT:") and "canvasBounds" in svg
