"""Optional v0.7 paint clip records Layout's completed absolute containment."""

import json
from dataclasses import replace

import pytest

from chrona.presentation.layout.relation_terminals import project_marker_outline
from chrona.presentation.layout.surface_quality import MarkerGeometry, PaintClip, PathCommand
from chrona.presentation.scene.model import (
    ContentFamilyCounts, InspectionScene, SceneManifest, ScenePaint, ScenePrimitive,
    SceneIconPath, SceneProvenance, SceneSlot, SceneSurface, SymbolGeometry,
)
from chrona.presentation.scene.serialization import (
    SceneSerializationError, scene_document, serialize_scene, validate_scene_document,
)


def _scene(primitive: ScenePrimitive) -> InspectionScene:
    slot = SceneSlot("timeline", "timeline", None, (0, 0, 100, 100))
    surface = SceneSurface("timeline", (slot,), (), (), None, (primitive,),
                           canvas_bounds=(0, 0, 100, 100))
    manifest = SceneManifest("chrona/scene-manifest/v0.1", "test", (100, 100), (), (),
                             ContentFamilyCounts(0, 0, 0, 0, 0), ())
    return InspectionScene(SceneProvenance("draft", "test", ()), (100, 100), (), (surface,),
                           manifest, ())


def _primitive(**overrides) -> ScenePrimitive:
    values = dict(scene_id="mark", kind="Rect", source_ref="source", source_kind="object",
                  purpose="planned", visual_role="planned", bounds=(10, 20, 30, 40),
                  slot_id="timeline")
    return ScenePrimitive(**(values | overrides))


def _marker(*, angle=None, physical_units=True, stroke_width=None) -> MarkerGeometry:
    outline = (PathCommand("move", ((0, 0),)), PathCommand("line", ((4, 2),)),
               PathCommand("line", ((0, 4),)), PathCommand("line", ((0, 0),)))
    return MarkerGeometry(outline, 4, 4, 0, "fill", angle_degrees=angle,
                          physical_units=physical_units, stroke_width=stroke_width)


def test_paint_clip_is_optional_and_absence_keeps_v06_shape_and_bytes() -> None:
    primitive = _primitive()
    before = scene_document(_scene(primitive))
    assert before["version"] == "chrona/scene/v0.6"
    assert "paintClip" not in before["surfaces"][0]["primitives"][0]
    assert json.loads(serialize_scene(_scene(primitive))) == before


def test_paint_clip_selects_v07_and_serializes_completed_bounds() -> None:
    primitive = _primitive(paint_clip=PaintClip((5, 10, 60, 60)))
    document = scene_document(_scene(primitive))
    assert document["version"] == "chrona/scene/v0.7"
    assert document["surfaces"][0]["primitives"][0]["paintClip"] == {
        "bounds": {"inline": 5, "block": 10, "inlineSize": 60, "blockSize": 60},
    }
    validate_scene_document(document)
    assert json.loads(serialize_scene(_scene(primitive))) == document


@pytest.mark.parametrize("bounds", [(), (0, 0, 0, 2), (0, 0, 2, -1), (0, 0, float("inf"), 2),
                                    (0, 0, True, 2), (1e308, 0, 1e308, 2)])
def test_paint_clip_rejects_malformed_bounds(bounds) -> None:
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        PaintClip(bounds)


@pytest.mark.parametrize("field,value", [
    ("bounds", (0, 20, 30, 40)),
    ("points", ((10, 20), (41, 30))),
    ("path_commands", (PathCommand("move", ((10, 20),)), PathCommand("line", ((41, 30),)))),
    ("symbol", SymbolGeometry((PathCommand("move", ((10, 20),)), PathCommand("line", ((41, 30),))))),
])
def test_typed_scene_rejects_absolute_geometry_outside_clip(field, value) -> None:
    clip = PaintClip((10, 20, 30, 40))
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        _primitive(**{field: value, "paint_clip": clip})


def test_typed_scene_rejects_nonfinite_derived_bounds_endpoint() -> None:
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        _primitive(bounds=(1e308, 20, 1e308, 2), paint_clip=PaintClip((0, 0, 1e308, 50)))


def test_document_validation_rejects_outside_geometry_and_nonpositive_clip() -> None:
    document = scene_document(_scene(_primitive(points=((10, 20), (40, 30)),
                                                paint_clip=PaintClip((10, 20, 30, 40)))))
    document["surfaces"][0]["primitives"][0]["points"][1] = [41, 30]
    with pytest.raises(SceneSerializationError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        validate_scene_document(document)
    document["surfaces"][0]["primitives"][0]["points"] = [[20, 30]]
    document["surfaces"][0]["primitives"][0]["paintClip"]["bounds"]["inlineSize"] = 0
    with pytest.raises(SceneSerializationError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        validate_scene_document(document)


def test_v06_schema_remains_strict_for_paint_clip() -> None:
    document = scene_document(_scene(_primitive()))
    document["surfaces"][0]["primitives"][0]["paintClip"] = {
        "bounds": {"inline": 5, "block": 10, "inlineSize": 60, "blockSize": 60},
    }
    with pytest.raises(SceneSerializationError):
        validate_scene_document(document)


def test_marker_projection_uses_source_endpoints_and_completed_tangent() -> None:
    marker = _marker()
    start = project_marker_outline(marker, side="start", points=((20, 50), (30, 50)),
                                   path_commands=(), stroke_width=1)
    end = project_marker_outline(marker, side="end", points=((20, 50), (30, 50)),
                                 path_commands=(), stroke_width=1)
    assert start[0].points[0] == (16, 48)
    assert end[0].points[0] == (26, 48)

    curved = (PathCommand("move", ((20, 50),)),
              PathCommand("quadratic", ((20, 60), (30, 60))))
    actual_curve = project_marker_outline(marker, side="start", points=((20, 50), (30, 60)),
                                          path_commands=curved, stroke_width=1)
    assert actual_curve[0].points[0] == (22, 46)  # vertical start tangent, not endpoint chord


def test_stroke_relative_terminal_is_checked_after_paint_binding_and_by_raw_scene():
    intermediate = _primitive(kind="Path", bounds=(10, 20, 30, 40), points=((20, 40), (30, 40)),
                              marker_start=_marker(physical_units=False), paint_clip=PaintClip((10, 20, 30, 40)))
    complete = replace(intermediate, paint=ScenePaint(None, "#000000", 1, (), 1))
    validate_scene_document(scene_document(_scene(complete)))
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        replace(intermediate, paint=ScenePaint(None, "#000000", 5, (), 1))
    document = scene_document(_scene(complete))
    document["surfaces"][0]["primitives"][0]["paint"]["strokeWidth"] = 5
    with pytest.raises(SceneSerializationError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        validate_scene_document(document)


def test_marker_projection_matches_explicit_angle_and_legacy_stroke_units() -> None:
    explicit = project_marker_outline(_marker(angle=90), side="start", points=((20, 50), (30, 50)),
                                      path_commands=(), stroke_width=3)
    assert explicit[0].points[0] == (22, 46)
    legacy = project_marker_outline(_marker(physical_units=False), side="start", points=((20, 50), (30, 50)),
                                    path_commands=(), stroke_width=2)
    assert legacy[0].points[0] == (12, 46)
    with pytest.raises(ValueError, match="strokeWidth-unit marker"):
        project_marker_outline(_marker(physical_units=False), side="start", points=((20, 50), (30, 50)),
                               path_commands=(), stroke_width=None)
    negative_offset = MarkerGeometry(_marker().outline, 4, 4, -2, "fill", physical_units=True)
    beyond_offset = MarkerGeometry(_marker().outline, 4, 4, 6, "fill", physical_units=True)
    assert project_marker_outline(negative_offset, side="start", points=((20, 50), (30, 50)),
                                  path_commands=(), stroke_width=None)[0].points[0] == (14, 48)
    assert project_marker_outline(beyond_offset, side="start", points=((20, 50), (30, 50)),
                                  path_commands=(), stroke_width=None)[0].points[0] == (22, 48)
    with pytest.raises(ValueError, match="completed start or end"):
        project_marker_outline(_marker(), side="middle", points=((20, 50), (30, 50)),
                               path_commands=(), stroke_width=1)
    with pytest.raises(ValueError, match="nonzero endpoint tangent"):
        project_marker_outline(_marker(), side="start", points=((20, 50), (20, 50)),
                               path_commands=(), stroke_width=1)


def test_marker_end_uses_quadratic_end_tangent_not_start_tangent() -> None:
    commands = (PathCommand("move", ((20, 50),)),
                PathCommand("quadratic", ((20, 60), (30, 60))))
    projected = project_marker_outline(_marker(), side="end", points=(),
                                       path_commands=commands, stroke_width=1)
    assert projected[0].points[0] == (26, 58)


def test_markers_apply_only_at_entire_path_start_and_end() -> None:
    commands = (PathCommand("move", ((20, 50),)), PathCommand("line", ((30, 50),)),
                PathCommand("move", ((40, 60),)), PathCommand("line", ((40, 70),)))
    start = project_marker_outline(_marker(), side="start", points=(),
                                   path_commands=commands, stroke_width=1)
    end = project_marker_outline(_marker(), side="end", points=(),
                                 path_commands=commands, stroke_width=1)
    assert len(start) == len(end) == len(_marker().outline)
    assert start[0].points[0] == (16, 48)
    assert end[0].points[0] == (42, 66)


@pytest.mark.parametrize("clip", [None, {}, {"bounds": {}},
    {"bounds": {"inline": 0, "block": 0, "inlineSize": float("inf"), "blockSize": 100}},
    {"inline": 0, "block": 0, "inlineSize": 100, "blockSize": 100},
])
def test_malformed_serialized_clip_has_stable_primitive_error(clip) -> None:
    document = scene_document(_scene(_primitive(paint_clip=PaintClip((0, 0, 100, 100)))))
    document["surfaces"][0]["primitives"][0]["paintClip"] = clip
    with pytest.raises(SceneSerializationError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        validate_scene_document(document)


def test_typed_and_serialized_paint_clip_check_absolute_marker_outline() -> None:
    marker = _marker()
    paint = ScenePaint(None, "#000000", 1, (), 1)
    base = dict(kind="Path", purpose="dependency-connector", bounds=(20, 50, 10, 0),
                points=((20, 50), (30, 50)), paint=paint, marker_start=marker,
                paint_clip=PaintClip((15, 47, 20, 10)))
    primitive = _primitive(**base)
    document = scene_document(_scene(primitive))
    validate_scene_document(document)

    with pytest.raises(ValueError, match="marker_start"):
        _primitive(**(base | {"paint_clip": PaintClip((17, 47, 20, 10))}))
    document["surfaces"][0]["primitives"][0]["paintClip"]["bounds"]["inline"] = 17
    with pytest.raises(SceneSerializationError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        validate_scene_document(document)


def test_paint_clip_contains_completed_absolute_vector_icon_paths() -> None:
    path = SceneIconPath((
        ("move", ((2, 2),)), ("line", ((8, 2),)), ("line", ((8, 8),)),
    ), "#000000", None, None)
    base = dict(kind="Icon", purpose="icon-mark", bounds=(0, 0, 10, 10),
                icon_kind="vector", icon_asset_identity="sha256:" + "a" * 64,
                icon_viewport=(10, 10), icon_paths=(path,),
                paint_clip=PaintClip((0, 0, 10, 10)))
    primitive = _primitive(**base)
    document = scene_document(_scene(primitive))
    validate_scene_document(document)

    outside = SceneIconPath((
        ("move", ((2, 2),)), ("line", ((11, 2),)),
    ), "#000000", None, None)
    with pytest.raises(ValueError, match=r"icon_paths\[0\]"):
        _primitive(**(base | {"icon_paths": (outside,)}))
    document["surfaces"][0]["primitives"][0]["icon"]["paths"][0]["commands"][1]["points"] = [[11, 2]]
    with pytest.raises(SceneSerializationError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        validate_scene_document(document)
