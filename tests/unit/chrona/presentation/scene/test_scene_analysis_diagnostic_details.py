from datetime import date
from types import SimpleNamespace

import pytest

from chrona.presentation.scene import capabilities, paint_analysis, pattern_geometry, perceptibility, serialization
from chrona.presentation.scene.model import (
    ContentFamilyCounts, InspectionScene, SceneManifest, ScenePaint, ScenePrimitive,
    SceneProvenance, SceneSlot, SceneSurface,
)


def _scene(*primitives, canvas_bounds=(0, 0, 20, 12)):
    slot = SceneSlot("canvas", "canvas", None, (0, 0, 20, 12))
    surface = SceneSurface("surface", (slot,), (), (), None, tuple(primitives),
                           canvas_paint=ScenePaint("#ffffff", None, None, (), 1),
                           canvas_bounds=canvas_bounds)
    manifest = SceneManifest("chrona/scene-manifest/v0.1", "test", (20, 12), (), (),
                             ContentFamilyCounts(0, 0, 0, 0, 0), ())
    return InspectionScene(SceneProvenance("draft", "test", ()), (20, 12), (), (surface,), manifest, ())


def _message(call, exception=ValueError):
    with pytest.raises(exception) as error:
        call()
    return str(error.value)


def test_pattern_kind_number_extra_field_and_geometry_errors_name_operands():
    choice = _message(lambda: pattern_geometry.pattern_geometry({"kind": "dots"}))
    assert choice.startswith("E_THEME_TOKEN_TYPE:") and "pattern.kind='dots'" in choice and "outline" in choice

    numeric = _message(lambda: pattern_geometry.pattern_geometry(
        {"kind": "diagonal-hatch", "tileInlineSize": "wide", "tileBlockSize": 8,
         "angle": 0, "strokeWidth": 1}))
    assert "pattern.tileInlineSize='wide'" in numeric and "finite number" in numeric

    extra = _message(lambda: pattern_geometry.pattern_geometry({"kind": "outline", "strokeWidth": 2}))
    assert "pattern.kind='outline'" in extra and "strokeWidth" in extra

    geometry = _message(lambda: pattern_geometry.pattern_geometry(
        {"kind": "diagonal-hatch", "tileInlineSize": -4, "tileBlockSize": 8,
         "angle": 360, "strokeWidth": 1}))
    assert "tileInlineSize=-4.0" in geometry and "angle=360.0" in geometry and "[0, 360)" in geometry


def test_paint_analysis_errors_name_color_opacity_gradient_and_sample_point():
    flat = _message(lambda: paint_analysis.composited_contrast(fill="red", opacity=2, ground="#FFFFFF"))
    assert flat.startswith("E_SCENE_PAINT_ANALYSIS_INPUT:") and "fill='red'" in flat and "opacity=2" in flat

    malformed = _message(lambda: paint_analysis.sample_linear_gradient({}, (1, 2)))
    assert "gradient must provide finite start/end" in malformed and "KeyError" in malformed

    out_of_order = _message(lambda: paint_analysis.sample_linear_gradient(
        {"start": (0, 0), "end": (10, 0), "stops": [
            {"offset": 0, "color": "#000000"}, {"offset": .7, "color": "#FFFFFF"},
            {"offset": .6, "color": "#FFFFFF"}, {"offset": 1, "color": "#FFFFFF"}]}, (4, 0)))
    assert "strict order" in out_of_order and "sample point=(4, 0)" in out_of_order and "stop_count=4" in out_of_order

    bad_sample = _message(lambda: paint_analysis.blend_over(ink="#000000", opacity=-.2, ground="paper"))
    assert "ink='#000000'" in bad_sample and "ground='paper'" in bad_sample and "opacity=-0.2" in bad_sample


def test_capability_ceiling_error_names_identifier_and_expected_admission():
    ceiling = _message(lambda: capabilities.admitted_capability_ids("decoration.row-band"))
    assert ceiling.startswith("E_VISUAL_CAPABILITY_CEILING:") and "decoration.row-band" in ceiling
    assert "deferred" in ceiling and "admitted capability" in ceiling


def test_capability_substitution_error_names_identifier_and_missing_owner():
    substitution = _message(lambda: capabilities.validate_substitution_request("paint.linear-gradient"))
    assert substitution.startswith("E_VISUAL_CAPABILITY_SUBSTITUTION:")
    assert "paint.linear-gradient" in substitution and "no substitution owner" in substitution


def test_scene_serialization_errors_name_version_schema_path_and_closed_reference():
    version = _message(lambda: serialization.validate_scene_document({"version": "chrona/scene/v0.99"}),
                       serialization.SceneSerializationError)
    assert version.startswith("E_SCENE_SERIALIZATION:") and "document.version" in version and "v0.99" in version

    schema = _message(lambda: serialization.validate_scene_document(
        {"version": "chrona/scene/v0.6", "kind": "wrong"}), serialization.SceneSerializationError)
    assert "scene-v0.6.schema.yaml" in schema and "schema error(s)" in schema and "first at /" in schema

    document = serialization.scene_document(_scene())
    document["surfaces"][0]["primitives"] = [{
        "id": "rect-1", "kind": "Rect", "sourceRef": "box", "sourceKind": "object",
        "purpose": "planned", "visualRole": "planned", "bounds": {"inline": 1, "block": 1,
        "inlineSize": 2, "blockSize": 2}, "paint": {"fill": "#000000", "opacity": 1}, "slotId": "missing-slot",
    }]
    references = _message(lambda: serialization.validate_scene_document(document),
                          serialization.SceneSerializationError)
    assert "cross-references" in references and "slots, rows, columns, primitives" in references


def test_scene_serialization_encoding_finite_canvas_lane_and_icon_failures_are_actionable(monkeypatch):
    monkeypatch.setattr(serialization.json, "dumps", lambda *args, **kwargs: (_ for _ in ()).throw(TypeError("opaque")))
    encoded = _message(lambda: serialization.serialize_scene(_scene()), serialization.SceneSerializationError)
    assert "canonical JSON encoding" in encoded and "TypeError" in encoded
    monkeypatch.undo()

    document = serialization.scene_document(_scene())
    document["surfaces"][0]["canvasBounds"]["inline"] = float("nan")
    finite = _message(lambda: serialization.validate_scene_document(document), serialization.SceneSerializationError)
    assert "non-finite numeric Scene fact" in finite and "completed bounds" in finite

    with pytest.raises(serialization.SceneSerializationError, match="canvasBounds") as canvas:
        serialization.scene_document(_scene(canvas_bounds=None))
    assert "surface 'surface'" in str(canvas.value)

    obstacle = SimpleNamespace(primitive_id="mark-3", geometry=object())
    lane = _message(lambda: serialization._lane_obstacle(obstacle), serialization.SceneSerializationError)
    assert "mark-3" in lane and "object" in lane and "rectangle or stroked segment" in lane

    icon = SimpleNamespace(scene_id="icon-9", icon_kind=None, icon_asset_identity="sha256:test", icon_viewport=None)
    icon_message = _message(lambda: serialization._icon(icon), serialization.SceneSerializationError)
    assert "icon-9" in icon_message and "icon_kind" in icon_message and "icon_viewport" in icon_message


def test_scene_perceptibility_document_helper_names_actual_field_and_shape():
    message = _message(lambda: perceptibility._string(None, "surfaces[2].id"),
                       perceptibility.ScenePerceptibilityError)
    assert message.startswith("E_SCENE_PERCEPTIBILITY_DOCUMENT:")
    assert "expected string at surfaces[2].id" in message


def test_owner_detail_helpers_are_required_by_code_only_mutations(monkeypatch):
    monkeypatch.setattr(pattern_geometry, "_token_error", lambda detail: ValueError("E_THEME_TOKEN_TYPE"))
    with pytest.raises(AssertionError):
        assert "pattern.kind='dots'" in _message(lambda: pattern_geometry.pattern_geometry({"kind": "dots"}))

    monkeypatch.setattr(paint_analysis, "_analysis_error", lambda detail: ValueError("E_SCENE_PAINT_ANALYSIS_INPUT"))
    with pytest.raises(AssertionError):
        assert "fill='red'" in _message(lambda: paint_analysis.composited_contrast(fill="red", opacity=2, ground="#FFFFFF"))

    monkeypatch.setattr(capabilities, "_capability_error", lambda code, detail: ValueError(code))
    with pytest.raises(AssertionError):
        assert "deferred" in _message(lambda: capabilities.admitted_capability_ids("decoration.row-band"))

    monkeypatch.setattr(serialization, "_scene_error", lambda detail: serialization.SceneSerializationError("E_SCENE_SERIALIZATION"))
    with pytest.raises(AssertionError):
        assert "document.version" in _message(
            lambda: serialization.validate_scene_document({"version": "chrona/scene/v0.99"}),
            serialization.SceneSerializationError)

    monkeypatch.setattr(perceptibility, "_require", lambda condition, detail: (
        None if condition else (_ for _ in ()).throw(perceptibility.ScenePerceptibilityError("E_SCENE_PERCEPTIBILITY_DOCUMENT"))))
    with pytest.raises(AssertionError):
        assert "surfaces[2].id" in _message(
            lambda: perceptibility._string(None, "surfaces[2].id"), perceptibility.ScenePerceptibilityError)
