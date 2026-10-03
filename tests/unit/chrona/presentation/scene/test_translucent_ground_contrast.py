"""#1013: a label or mark on a translucent chip or panel is judged on the host composited over its own ground.

The host (a label chip, a region frame, a panel) is blended over every ground beneath it (the canvas, a band, an
opaque gradient, a texture or catalogue pattern in two colours, the as-of cone), and the worst ratio decides, as for
patterns and cones. What cannot be read stays a blocking `E_SCENE_CONTRAST_GROUND_UNSUPPORTED`. Synthetic Scene
documents; no `examples/` input.
"""
from __future__ import annotations

import pytest

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.paint_analysis import blend_over, composited_contrast

DARK = "#101820"
NEAR = "#1E2833"
LIGHT = "#F2F2F2"
INK = "#FFC800"
BOX = {"inline": 10.0, "block": 10.0, "inlineSize": 40.0, "blockSize": 12.0}
AT = {"inline": 20.0, "block": 100.0, "inlineSize": 20.0, "blockSize": 10.0}  # inside the cone below
PATTERN = {"tileInlineSize": 8, "tileBlockSize": 4, "angleDegrees": 45, "densityBasisPoints": 1250,
           "primitives": [{"kind": "rect", "x": 0, "y": 0, "inlineSize": 1, "blockSize": 4}], "origin": [10, 10],
           "regionBounds": dict(BOX), "clipBounds": dict(BOX), "cornerRadius": 0}


def _scene(*primitives, canvas=DARK, canvas_opacity=1):
    return {"version": "chrona/scene/v0.7", "kind": "scene", "surfaces": [{
        "id": "review", "canvasPaint": {"fill": canvas, "opacity": canvas_opacity}, "primitives": list(primitives),
        "decorationDispositions": []}]}


def _label(fill, *, bounds=BOX, order=300, purpose="as-of-label", role="text", identifier="label"):
    return {"id": identifier, "visualRole": role, "purpose": purpose, "kind": "Text", "paintOrder": order,
            "bounds": dict(bounds), "paint": {"fill": fill, "opacity": 1}}


def _mark(fill, *, bounds=BOX, order=300):
    return {"id": "label", "visualRole": "planned", "purpose": "planned", "kind": "Rect", "paintOrder": order,
            "bounds": dict(bounds), "paint": {"fill": fill, "opacity": 1}}


def _rect(identifier, fill, *, order, opacity=1, role="as-of-label-chip", purpose="label-chip", stroke=None,
          pattern=None, gradient=None, bounds=BOX):
    paint = {"fill": fill, "opacity": opacity, **({"stroke": stroke, "strokeWidth": 1} if stroke else {})}
    if gradient is not None:
        paint["gradient"] = gradient
    value = {"id": identifier, "visualRole": role, "purpose": purpose, "kind": "Rect", "paintOrder": order,
             "bounds": dict(bounds), "paint": paint}
    if pattern is not None:
        value["pattern"] = dict(pattern)
    return value


def _cone(*, order):
    outline = [("move", (30.0, 0.0)), ("line", (80.0, 200.0)), ("line", (-20.0, 200.0)), ("line", (30.0, 0.0))]
    return {"id": "as-of-cone", "visualRole": "as-of-cone", "purpose": "as-of-cone", "kind": "Symbol",
            "paintOrder": order, "bounds": {"inline": -20.0, "block": 0.0, "inlineSize": 100.0, "blockSize": 200.0},
            "symbol": {"outline": [{"kind": kind, "points": [list(point)]} for kind, point in outline]},
            "paint": {"fill": INK, "opacity": 1.0, "gradient": {
                "start": [30.0, 0.0], "end": [30.0, 200.0], "fidelity": "required",
                "stops": [{"offset": 0, "color": INK, "opacity": 1}, {"offset": 1, "color": INK, "opacity": 0}]}}}


def _judge(*primitives, **scene):
    findings = [item for item in evaluate_scene_contrast(_scene(*primitives, **scene)) if item.primitive_id == "label"]
    assert len(findings) == 1, findings
    return findings[0]


def _ratio(ink, ground):
    return composited_contrast(fill=ink, opacity=1.0, ground=ground)


# --- the composite over a light and a dark canvas ----------------------------------------------------------

def test_a_translucent_chip_over_a_light_canvas_is_judged_on_the_composite_not_on_its_own_colour():
    chip = _rect("chip", DARK, order=299, opacity=0.3)
    composite = blend_over(ink=DARK, opacity=0.3, ground=LIGHT)
    finding = _judge(chip, _label(LIGHT), canvas=LIGHT)
    assert (finding.ground_id, finding.ground_color, finding.ground_kind) == (
        "chip", composite, "translucent-over-canvas")
    assert finding.contrast_ratio == pytest.approx(_ratio(LIGHT, composite))
    # The chip's own colour would pass (light on dark); the composite is a pale grey, so the label fails.
    assert _ratio(LIGHT, DARK) > 4.5 > finding.contrast_ratio
    assert (finding.code, finding.severity, finding.severity_class) == (
        "E_SCENE_STATE_TEXT_CONTRAST", "error", "legibility")


def test_a_translucent_dark_chip_over_a_light_canvas_rescues_a_light_label_when_dark_enough():
    chip = _rect("chip", DARK, order=299, opacity=0.9)
    finding = _judge(chip, _label(LIGHT), canvas=LIGHT)
    assert (finding.severity, finding.ground_color) == ("info", blend_over(ink=DARK, opacity=0.9, ground=LIGHT))


def test_a_translucent_light_chip_over_a_dark_canvas_is_judged_on_the_composite():
    chip = _rect("chip", LIGHT, order=299, opacity=0.5)
    composite = blend_over(ink=LIGHT, opacity=0.5, ground=DARK)
    failing = _judge(chip, _label(LIGHT), canvas=DARK)
    passing = _judge(chip, _label(DARK), canvas=DARK)
    assert (failing.ground_color, failing.severity) == (composite, "error")
    assert (passing.ground_color, passing.severity) == (composite, "info")


def test_a_fully_transparent_chip_is_its_ground_and_an_opaque_one_is_unchanged():
    clear = _judge(_rect("chip", LIGHT, order=299, opacity=0), _label(LIGHT), canvas=DARK)
    assert (clear.ground_color, clear.severity) == (DARK, "info")
    opaque = _judge(_rect("chip", LIGHT, order=299), _label(LIGHT), canvas=DARK)
    assert (opaque.ground_kind, opaque.ground_color, opaque.severity) == ("flat", LIGHT, "error")


# --- over what lies beneath --------------------------------------------------------------------------------

def test_over_a_band_tint_the_chip_is_composited_over_the_band():
    band = _rect("band", NEAR, order=10, role="group-band", purpose="group-decoration")
    chip = _rect("chip", LIGHT, order=299, opacity=0.4)
    finding = _judge(band, chip, _label(LIGHT), canvas="#FFFFFF")
    assert (finding.ground_id, finding.ground_kind, finding.ground_color) == (
        "chip", "translucent-over-flat", blend_over(ink=LIGHT, opacity=0.4, ground=NEAR))
    assert finding.severity == "error"


def test_over_an_opaque_gradient_the_chip_is_composited_over_the_sample():
    gradient = {"start": [10.0, 0.0], "end": [50.0, 0.0], "stops": [
        {"offset": 0, "color": "#000000"}, {"offset": 1, "color": "#FFFFFF"}]}
    host = _rect("host", "#000000", order=10, role="region-frame", purpose="region-frame", gradient=gradient)
    chip = _rect("chip", DARK, order=299, opacity=0.5)
    finding = _judge(host, chip, _label(LIGHT), canvas=DARK)
    sample = "#808080"  # the gradient at the label's centre (x 30 of 10..50)
    assert finding.ground_color == blend_over(ink=DARK, opacity=0.5, ground=sample)
    assert finding.ground_kind == "translucent-over-gradient-sample"


def test_a_translucent_region_frame_is_the_ground_of_the_label_in_it():
    frame = _rect("frame", LIGHT, order=5, opacity=0.6, role="region-frame", purpose="region-frame",
                  bounds={"inline": 0.0, "block": 0.0, "inlineSize": 200.0, "blockSize": 100.0})
    finding = _judge(frame, _label(LIGHT, purpose="axis-label"), canvas=DARK)
    assert (finding.ground_id, finding.severity) == ("frame", "error")
    assert finding.ground_color == blend_over(ink=LIGHT, opacity=0.6, ground=DARK)


def test_stacked_translucent_hosts_are_composited_in_paint_order():
    lower = _rect("lower", LIGHT, order=100, opacity=0.5)
    upper = _rect("upper", DARK, order=200, opacity=0.5)
    finding = _judge(lower, upper, _label(LIGHT), canvas=DARK)
    expected = blend_over(ink=DARK, opacity=0.5, ground=blend_over(ink=LIGHT, opacity=0.5, ground=DARK))
    assert (finding.ground_id, finding.ground_color) == ("upper", expected)
    assert finding.ground_kind == "translucent-over-translucent-over-canvas"


def test_over_a_canvas_texture_the_chip_is_composited_over_substrate_and_ink_and_the_worse_decides():
    bounds = {"inline": 0.0, "block": 0.0, "inlineSize": 400.0, "blockSize": 300.0}
    texture = _rect("texture", DARK, order=1, role="canvas-texture", purpose="canvas-texture", stroke="#E8E8E8",
                    bounds=bounds)
    chip = _rect("chip", DARK, order=299, opacity=0.5)
    finding = _judge(texture, chip, _label("#F0F0F0"), canvas=DARK)
    over_substrate = blend_over(ink=DARK, opacity=0.5, ground=DARK)
    over_ink = blend_over(ink=DARK, opacity=0.5, ground="#E8E8E8")
    assert _ratio("#F0F0F0", over_substrate) > 4.5 > _ratio("#F0F0F0", over_ink)
    assert (finding.severity, finding.ground_color, finding.ground_kind) == (
        "error", over_ink, "translucent-over-texture-ink")


def test_over_a_catalogue_pattern_the_chip_is_composited_over_substrate_and_ink():
    pattern = _rect("band", "#FFFFFF", order=10, role="group-band", purpose="group-decoration", stroke=NEAR,
                    pattern=PATTERN)
    chip = _rect("chip", LIGHT, order=299, opacity=0.5)
    finding = _judge(pattern, chip, _label("#303030"), canvas="#FFFFFF")
    over_substrate = blend_over(ink=LIGHT, opacity=0.5, ground="#FFFFFF")
    over_ink = blend_over(ink=LIGHT, opacity=0.5, ground=NEAR)
    assert _ratio("#303030", over_substrate) > 4.5 > _ratio("#303030", over_ink)
    assert finding.contrast_ratio == pytest.approx(_ratio("#303030", over_ink))
    assert finding.ground_kind == "translucent-over-pattern-host-ink" and finding.severity == "error"


def test_a_translucent_patterned_chip_is_ground_in_two_colours_over_its_canvas():
    chip = _rect("chip", "#FFFFFF", order=299, opacity=0.6, stroke=NEAR, pattern=PATTERN)
    finding = _judge(chip, _label("#EDEDED"), canvas=DARK)
    substrate = blend_over(ink="#FFFFFF", opacity=0.6, ground=DARK)
    ink = blend_over(ink=NEAR, opacity=0.6, ground=DARK)
    assert finding.contrast_ratio == pytest.approx(min(_ratio("#EDEDED", substrate), _ratio("#EDEDED", ink)))
    assert finding.ground_kind.startswith("translucent-pattern-host-") and finding.ground_kind.endswith("-over-canvas")


def test_a_cone_painted_before_the_chip_tints_the_ground_the_chip_lies_over():
    chip = _rect("chip", LIGHT, order=200, opacity=0.5, bounds=AT)
    finding = _judge(_cone(order=50), chip, _label("#3A2E00", bounds=AT), canvas="#FFFFFF")
    ends = [blend_over(ink=LIGHT, opacity=0.5, ground=blend_over(ink=INK, opacity=1 - block / 200, ground="#FFFFFF"))
            for block in (100, 110)]
    assert finding.contrast_ratio == pytest.approx(min(_ratio("#3A2E00", ground) for ground in ends))
    assert finding.ground_kind == "translucent-over-cone-blend" and finding.ground_id == "chip"


def test_a_cone_painted_after_the_chip_tints_the_composite():
    chip = _rect("chip", LIGHT, order=200, opacity=0.5, bounds=AT)
    finding = _judge(chip, _cone(order=250), _label("#3A2E00", bounds=AT), canvas="#FFFFFF")
    composite = blend_over(ink=LIGHT, opacity=0.5, ground="#FFFFFF")
    ends = [blend_over(ink=INK, opacity=1 - block / 200, ground=composite) for block in (100, 110)]
    assert finding.contrast_ratio == pytest.approx(min(_ratio("#3A2E00", ground) for ground in ends))
    assert (finding.ground_kind, finding.ground_id) == ("cone-blend", "as-of-cone")


def test_a_mark_on_a_translucent_chip_is_judged_on_the_composite_and_blocks_below_the_mark_floor():
    chip = _rect("chip", DARK, order=299, opacity=0.5)
    composite = blend_over(ink=DARK, opacity=0.5, ground=LIGHT)
    finding = _judge(chip, _mark(composite), canvas=LIGHT)
    assert (finding.code, finding.severity, finding.severity_class, finding.floor) == (
        "E_SCENE_MARK_CONTRAST", "error", "legibility", 3.0)
    assert finding.ground_color == composite


# --- what stays fail-closed ----------------------------------------------------------------------------------

@pytest.mark.parametrize("severity", ["warning", "error"])
def test_text_on_a_host_that_cannot_be_read_blocks_whatever_the_decoration_severity(severity):
    for chip in (_rect("chip", DARK, order=299, opacity=1.5),          # not a number in [0, 1]
                 _rect("chip", "red", order=299, opacity=0.5),         # not #RRGGBB
                 _rect("chip", DARK, order=299, opacity=0.5, gradient={"start": [0, 0], "end": [1, 1], "stops": []})):
        finding = next(item for item in evaluate_scene_contrast(_scene(chip, _label(LIGHT)), decoration_severity=severity)
                       if item.primitive_id == "label")
        assert (finding.code, finding.severity, finding.severity_class, finding.ground_id) == (
            "E_SCENE_CONTRAST_GROUND_UNSUPPORTED", "error", "legibility", "chip")


def test_a_translucent_chip_over_an_unreadable_ground_is_unreadable():
    beneath = _rect("beneath", DARK, order=10, opacity=7)
    chip = _rect("chip", DARK, order=299, opacity=0.5)
    finding = _judge(beneath, chip, _label(LIGHT))
    assert (finding.code, finding.severity, finding.ground_id) == ("E_SCENE_CONTRAST_GROUND_UNSUPPORTED", "error", "chip")


def test_a_translucent_canvas_is_still_no_ground():
    plain = _judge(_label(LIGHT), canvas_opacity=0.5)
    over_chip = _judge(_rect("chip", DARK, order=299, opacity=0.5), _label(LIGHT), canvas_opacity=0.5)
    assert plain.code == over_chip.code == "E_SCENE_CONTRAST_PAINT" and plain.severity == over_chip.severity == "error"


def test_a_decoration_on_a_translucent_host_keeps_its_warning_and_is_not_composited():
    host = _rect("host", DARK, order=10, opacity=0.5, role="row-band", purpose="row-decoration")
    closed = _rect("closed", "#F4F4F4", order=20, role="calendar-closed", purpose="calendar-closed")
    findings = {item.primitive_id: item for item in evaluate_scene_contrast(_scene(host, closed, canvas="#FFFFFF"))}
    assert (findings["closed"].code, findings["closed"].severity, findings["closed"].severity_class) == (
        "W_SCENE_DECORATION_GROUND_UNSUPPORTED", "warning", "decoration")
    blocking = {item.primitive_id: item for item in evaluate_scene_contrast(
        _scene(host, closed, canvas="#FFFFFF"), decoration_severity="error")}
    assert (blocking["closed"].code, blocking["closed"].severity) == ("E_SCENE_CONTRAST_GROUND_UNSUPPORTED", "error")


def test_note_prose_on_a_translucent_box_is_still_unsupported():
    box = {**_rect("box", "#000000", order=10, opacity=0.5, role="annotation-note-box", purpose="annotation-box"),
           "sourceRef": "note:1"}
    text = {**_label("#FFFFFF", purpose="annotation-text", role="annotation-note-text", order=100),
            "sourceRef": "note:1", "contrastTreatment": "required"}
    finding = _judge(box, text, canvas="#FFFFFF")
    assert (finding.code, finding.severity, finding.ground_id) == ("E_SCENE_CONTRAST_GROUND_UNSUPPORTED", "error", "box")
