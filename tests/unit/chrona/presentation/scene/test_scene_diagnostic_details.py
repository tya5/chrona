"""Scene model failures identify the invalid completed field without dumping payloads."""
import pytest

from chrona.presentation.layout.surface_quality import TextFit
from chrona.presentation.scene.model import (
    BOX_FOLLOWS_TEXT, DecorationDisposition, ImageFill, PatternGeometry, PatternStroke,
    RadialGradient, RadialGradientStop, SceneLaneMember, SceneLaneObstacle,
    SceneLaneRectObstacle, SceneLaneSegmentObstacle, ScenePaint, ScenePrimitive,
    SceneRow, SceneSurface, SymbolGeometry, TextLayout,
)


def error_detail(call, *expected):
    with pytest.raises(ValueError) as caught:
        call()
    message = str(caught.value)
    assert message.startswith("E_PRESENTATION_PRIMITIVE_INVALID:") or message.startswith("E_PRESENTATION_TEXT_LAYOUT_INVALID:")
    for item in expected:
        assert item in message
    return message


def primitive(scene_id="p-1", **changes):
    values = {"scene_id": scene_id, "kind": "Rect", "source_ref": "/objects/task-1", "source_kind": "task",
              "purpose": "planned", "visual_role": "planned", "bounds": (1, 2, 30, 12)}
    values.update(changes)
    return ScenePrimitive(**values)


def surface(*primitives, **changes):
    values = {"surface_id": "surface-main", "slots": (), "rows": (), "groups": (),
              "scale_manifest": None, "primitives": tuple(primitives)}
    values.update(changes)
    return SceneSurface(**values)


def test_simple_geometry_fields_name_bad_values():
    error_detail(lambda: ImageFill("asset-1", (20, 30), b"bytes-not-echoed", ()), "ImageFill.tiles/viewport", "viewport", "20, 30")
    error_detail(lambda: PatternStroke((0, 0), (1, 0), -2), "PatternStroke.width", "-2", "positive")
    error_detail(lambda: PatternGeometry(0, 4, 30), "PatternGeometry.tile_inline_size", "0", "positive tile sizes")
    error_detail(lambda: SymbolGeometry(()), "SymbolGeometry.outline", "non-empty tuple")


@pytest.mark.parametrize("kwargs,expected", [
    ({"numeric_spacing": "wide", "orientation": "vertical", "rotation_degrees": 0},
     ("TextLayout.numeric_spacing/orientation/rotation_degrees", "wide", "vertical")),
    ({"horizontal_scale": 1.5}, ("TextLayout.horizontal_scale", "1.5", "[0.5, 1]")),
    ({"fit": TextFit("text-follows-box", line_inline_sizes=(10,))},
     ("TextLayout.fit.line_inline_sizes", "lineCount=2")),
])
def test_text_layout_failures_name_text_fields(kwargs, expected):
    values = dict(bounds=(0, 0, 20, 10), baseline=(0, 8), lines=("a", "b"), family="sans", weight=400,
                  font_size=10, line_height=12, asset_identity="font-1")
    values.update(kwargs)
    error_detail(lambda: TextLayout(**values), *expected)


def test_radial_gradient_failure_reports_bounded_geometry_and_stops():
    long_color = "#" + "a" * 1000
    message = error_detail(lambda: RadialGradient((0, 0), (4, -1), (), "required"),
                           "radial geometry", "radii=(4, -1)", "stopCount=0")
    assert len(message) < 400
    message = error_detail(lambda: RadialGradient((0, 0), (2, 2),
                                                  (RadialGradientStop(0, long_color, 0),
                                                   RadialGradientStop(1, "#fff", 1)), "required"),
                           "radial stops", "colors=tuple")
    assert len(message) < 500
    assert long_color not in message


def test_scene_primitive_failures_name_primitive_semantics_and_operands():
    error_detail(lambda: primitive("stroke-1", kind="Text", stroke_clip=object()),
                 "primitive 'stroke-1'", "stroke_clip", "kind='Text'")
    error_detail(lambda: primitive("table-cell-1", purpose="table-cell"),
                 "primitive 'table-cell-1'", "incompatible completed fields", "table_row_id=None", "table_column_id=None")
    error_detail(lambda: primitive("paint-order-1", paint_order=-3),
                 "primitive 'paint-order-1'", "paint_order", "-3", "non-negative")
    error_detail(lambda: primitive("end-treatment-1", end_treatment="sideways"),
                 "primitive 'end-treatment-1'", "end_treatment", "sideways", "closed")
    error_detail(lambda: primitive("fit-mode-1", viewer_fit="unrecognized"),
                 "primitive 'fit-mode-1'", "viewer_fit", "unrecognized", "known fit mode")
    error_detail(lambda: primitive("contrast-1", kind="Text", purpose="annotation-note-text",
                                   visual_role="annotation-note-text", contrast_treatment="deemphasized"),
                 "primitive 'contrast-1'", "visual_role/contrast_treatment", "annotation-note-text", "deemphasized")
    error_detail(lambda: primitive("open-1", kind="Path", end_treatment="open"),
                 "primitive 'open-1'", "end_treatment/kind/symbol/purpose", "kind='Path'", "purpose='planned'")


def test_scene_row_and_lane_fact_errors_name_numeric_bounds_and_identity():
    error_detail(lambda: SceneRow("task-1", "group-1", (0, 10, 20, 30), row_id="row-1",
                                  lane_mark_band_block=45),
                 "SceneRow 'row-1'", "lane_mark_band_block", "bounds", "45")
    error_detail(lambda: SceneLaneMember("row-1", "member-1", ("p-1", "p-1"), ("p-2",)),
                 "SceneLaneMember.row_id/member_id/emitted_primitive_ids/primary_mark_ids", "row-1", "member-1")
    error_detail(lambda: SceneLaneRectObstacle(0, 0, 0, 4), "SceneLaneRectObstacle.left/top/right/bottom", "right > left")
    error_detail(lambda: SceneLaneSegmentObstacle((0, 0), (0, 0), -1),
                 "SceneLaneSegmentObstacle.start/end/stroke_width", "distinct endpoints")
    error_detail(lambda: SceneLaneObstacle("facet-1", "p-1", "row-1", "member-1", "leader", object()),
                 "SceneLaneObstacle.facet_id/primitive_id/row_id/member_id/obstacle_class/geometry", "leader", "facet-1")


def test_surface_referential_failures_name_surface_and_related_primitives():
    first = primitive("duplicate")
    second = primitive("duplicate", kind="Path")
    error_detail(lambda: surface(first, second), "SceneSurface('surface-main').primitives.scene_id", "duplicate")

    host = primitive("host", paint_order=3)
    text = primitive("label", kind="Text", purpose="title", visual_role="title",
                     host_placement_id="host", paint_order=2)
    error_detail(lambda: surface(host, text), "primitive 'label'", "host_placement_id", "host_order=3")

    clipped = primitive("clip-1", clip_source_id="missing-source", paint_order=4)
    error_detail(lambda: surface(clipped), "primitive 'clip-1'", "clip_source_id", "missing-source", "source_kind=None")

    lane_tagged = primitive("lane-tagged", lane_row_id="row-absent", lane_member_id="member-1")
    error_detail(lambda: surface(lane_tagged), "primitive 'lane-tagged'", "lane_row_id", "row-absent", "lane_mark_band_block")


def test_surface_lane_manifest_and_decoration_errors_name_contract_fields():
    error_detail(lambda: surface(lane_mode="unknown"), "SceneSurface('surface-main').lane_mode", "unknown", "None or 'lanes'")
    error_detail(lambda: surface(decoration_dispositions=(DecorationDisposition("planned", "removed"),)),
                 "DecorationDisposition(planned).disposition", "removed", "absent")

    # A lane-mode surface cannot omit its member/obstacle inventory or valid clearance.
    error_detail(lambda: surface(lane_mode="lanes", lane_clearance=-2),
                 "SceneSurface('surface-main').lane_members/lane_obstacles/lane_clearance/rows", "-2", "non-empty typed lane facts")

    box = primitive("fit-box", viewer_fit=BOX_FOLLOWS_TEXT)
    error_detail(lambda: surface(box), "SceneSurface('surface-main').viewer_fit", "fit-box", "text_box_ids")

    gradient = RadialGradient((5, 5), (4, 4),
                              (RadialGradientStop(0, "#222", 0), RadialGradientStop(1, "#222", 1)),
                              "required")
    canvas = ScenePaint(fill="#222", stroke=None, stroke_width=None, dash=(), opacity=1,
                        radial_gradient=gradient)
    error_detail(lambda: surface(canvas_paint=canvas), "SceneSurface('surface-main').canvas_paint/canvas_bounds",
                 "no radial-gradient canvas paint")
