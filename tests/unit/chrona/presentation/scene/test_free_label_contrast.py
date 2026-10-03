"""#980: free labels (the as-of label, member labels, axis labels, table text, ...) are gated on the ground under them.

A free label keeps the shared role `text` (or a role of its own) and is classified `ground-text` by its purpose: the
required 4.5:1 floor, a blocking error, judged on the canvas, a band, a chip, a texture or pattern (two colours), a
region frame or the as-of cone, exactly as the group header is (#884). Synthetic Scene documents; no `examples/` input.
"""
from __future__ import annotations

import pytest

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.paint_analysis import blend_over, composited_contrast

DARK = "#101820"
NEAR = "#1E2833"  # close to DARK: unreadable
LIGHT = "#F2F2F2"
INK = "#FFC800"
BOX = {"inline": 10.0, "block": 10.0, "inlineSize": 40.0, "blockSize": 12.0}
PATTERN = {"tileInlineSize": 8, "tileBlockSize": 4, "angleDegrees": 45, "densityBasisPoints": 1250,
           "primitives": [{"kind": "rect", "x": 0, "y": 0, "inlineSize": 1, "blockSize": 4}], "origin": [10, 10],
           "regionBounds": dict(BOX), "clipBounds": dict(BOX), "cornerRadius": 0}

# Every label shape the issue names, plus the roles of their own: (purpose, role) of one Text primitive.
FREE_LABELS = [
    ("as-of-label", "text"), ("member-label", "text"), ("axis-label", "text"), ("table-cell", "text"),
    ("table-column-label", "text"), ("group-detail", "text"), ("legend-label", "text"), ("title-text", "text"),
    ("axis-label", "axis-label2"), ("axis-label", "axis-label3"), ("note-index", "note-index"),
    ("annotation-text", "annotation-callout-text"), ("member-label", "member-label-inside-planned"),
]


def _scene(*primitives, canvas=DARK, version="chrona/scene/v0.7"):
    return {"version": version, "kind": "scene", "surfaces": [{
        "id": "review", "canvasPaint": {"fill": canvas, "opacity": 1}, "primitives": list(primitives),
        "decorationDispositions": []}]}


def _label(fill=LIGHT, *, purpose="as-of-label", role="text", identifier="label", order=300, bounds=BOX, **paint):
    return {"id": identifier, "visualRole": role, "purpose": purpose, "kind": "Text", "paintOrder": order,
            "bounds": dict(bounds), "paint": {"fill": fill, "opacity": 1, **paint}}


def _rect(identifier, fill, *, role, purpose, order, stroke=None, pattern=None, opacity=1, bounds=BOX, kind="Rect"):
    paint = {"fill": fill, "opacity": opacity, **({"stroke": stroke, "strokeWidth": 1} if stroke else {})}
    value = {"id": identifier, "visualRole": role, "purpose": purpose, "kind": kind, "paintOrder": order,
             "bounds": dict(bounds), "paint": paint}
    if pattern is not None:
        value["pattern"] = dict(pattern)
    return value


def _cone(*, strength=1.0, order=50):
    outline = [("move", (30.0, 0.0)), ("line", (80.0, 200.0)), ("line", (-20.0, 200.0)), ("line", (30.0, 0.0))]
    return {"id": "as-of-cone", "visualRole": "as-of-cone", "purpose": "as-of-cone", "kind": "Symbol", "paintOrder": order,
            "bounds": {"inline": -20.0, "block": 0.0, "inlineSize": 100.0, "blockSize": 200.0},
            "symbol": {"outline": [{"kind": kind, "points": [list(point)]} for kind, point in outline]},
            "paint": {"fill": INK, "opacity": strength, "gradient": {
                "start": [30.0, 0.0], "end": [30.0, 200.0], "fidelity": "required",
                "stops": [{"offset": 0, "color": INK, "opacity": 1}, {"offset": 1, "color": INK, "opacity": 0}]}}}


def _only(findings, identifier="label"):
    matching = [item for item in findings if item.primitive_id == identifier]
    assert len(matching) == 1, matching
    return matching[0]


def _judge(*primitives, canvas=DARK, identifier="label"):
    return _only(evaluate_scene_contrast(_scene(*primitives, canvas=canvas)), identifier)


@pytest.mark.parametrize(("purpose", "role"), FREE_LABELS)
def test_a_free_label_too_close_to_a_dark_canvas_is_a_blocking_error(purpose, role):
    finding = _judge(_label(NEAR, purpose=purpose, role=role))
    assert (finding.code, finding.severity, finding.severity_class) == (
        "E_SCENE_STATE_TEXT_CONTRAST", "error", "legibility")
    assert (finding.floor, finding.disposition, finding.paint_channel) == (4.5, "required", "fill")
    assert (finding.ground_id, finding.ground_kind, finding.ground_color) == ("canvas", "canvas", DARK)
    assert (finding.purpose, finding.visual_role) == (purpose, role)
    assert finding.contrast_ratio < 4.5


@pytest.mark.parametrize(("purpose", "role"), FREE_LABELS)
def test_the_same_label_in_a_legible_ink_passes_at_the_required_floor(purpose, role):
    finding = _judge(_label(LIGHT, purpose=purpose, role=role))
    assert (finding.severity, finding.floor) == ("info", 4.5)
    assert finding.contrast_ratio > 10


def test_an_inside_label_is_judged_on_the_mark_it_lies_on():
    bar = _rect("bar", "#3986E6", role="planned", purpose="planned", order=100)
    failing = _judge(bar, _label("#FFFFFF", purpose="member-label", role="member-label-inside-planned"), canvas="#FFFFFF")
    assert (failing.ground_id, failing.severity) == ("bar", "error") and 3.0 < failing.contrast_ratio < 4.5
    passing = _judge(bar, _label("#000000", purpose="member-label", role="member-label-inside-planned"), canvas="#FFFFFF")
    assert (passing.ground_id, passing.severity) == ("bar", "info")


def test_the_floor_is_required_whatever_the_primitive_claims():
    # A mid ink: above the 3.0 deemphasized floor and below 4.5. A free label has no authored treatment.
    mid = "#6B7A8A"
    plain = _judge(_label(mid), canvas="#FFFFFF")
    assert 3.0 < plain.contrast_ratio < 4.5 and plain.severity == "error" and plain.floor == 4.5
    claimed = _label(mid)
    claimed["contrastTreatment"] = "deemphasized"
    assert _judge(claimed, canvas="#FFFFFF").severity == "error"


def test_a_tinted_band_under_the_label_is_the_ground():
    band = _rect("band", NEAR, role="group-band", purpose="group-decoration", order=10)
    finding = _judge(band, _label(LIGHT, purpose="table-cell"), canvas="#FFFFFF")
    assert (finding.ground_id, finding.ground_color, finding.severity) == ("band", NEAR, "info")
    over_light_canvas = _judge(_rect("band", "#F2F2F2", role="row-band", purpose="row-decoration", order=10),
                               _label(LIGHT, purpose="table-cell"), canvas=DARK)
    assert (over_light_canvas.ground_id, over_light_canvas.severity) == ("band", "error")


def test_a_label_on_an_opaque_chip_is_judged_on_the_chip_not_the_canvas():
    chip = _rect("chip", "#F2F2F2", role="as-of-label-chip", purpose="label-chip", order=299)
    # Light ink on a dark canvas passes, but the label lies on its light chip: that is the ground that decides.
    finding = _judge(chip, _label(LIGHT), canvas=DARK)
    assert (finding.ground_id, finding.ground_color, finding.severity) == ("chip", "#F2F2F2", "error")
    dark_chip = _rect("chip", DARK, role="as-of-label-chip", purpose="label-chip", order=299)
    rescued = _judge(dark_chip, _label(LIGHT), canvas="#F2F2F2")
    assert (rescued.ground_id, rescued.severity) == ("chip", "info")


def test_a_label_on_a_chip_whose_paint_cannot_be_read_cannot_be_judged_and_is_an_error():
    # A translucent chip is composited over what lies beneath it (#1013, test_translucent_ground_contrast.py);
    # one whose opacity is not a number in [0, 1] stays unreadable and fails closed.
    chip = _rect("chip", DARK, role="as-of-label-chip", purpose="label-chip", order=299, opacity=1.5)
    finding = _judge(chip, _label(LIGHT))
    assert (finding.code, finding.severity, finding.ground_id) == ("E_SCENE_CONTRAST_GROUND_UNSUPPORTED", "error", "chip")


def test_a_region_frame_fill_is_the_ground_of_the_label_in_it():
    frame = _rect("frame", LIGHT, role="region-frame", purpose="region-frame", order=5, bounds={
        "inline": 0.0, "block": 0.0, "inlineSize": 200.0, "blockSize": 100.0})
    finding = _judge(frame, _label(LIGHT, purpose="axis-label"), canvas=DARK)
    assert (finding.ground_id, finding.ground_color, finding.severity) == ("frame", LIGHT, "error")


def test_a_pattern_is_two_grounds_for_a_label_and_the_worse_decides():
    band = _rect("band", "#FFFFFF", role="group-band", purpose="group-decoration", order=10,
                 stroke=NEAR, pattern=PATTERN)
    # Light ink on a white substrate would fail, and on a near-dark ink passes: the worse is the substrate.
    on_substrate = _judge(band, _label("#EDEDED", purpose="axis-label"), canvas=DARK)
    assert (on_substrate.severity, on_substrate.ground_kind, on_substrate.ground_color) == (
        "error", "pattern-host-substrate", "#FFFFFF")
    # Dark ink on a light substrate passes there, but equals the hatch ink: the ink decides.
    on_ink = _judge(_rect("band", "#FFFFFF", role="group-band", purpose="group-decoration", order=10,
                          stroke=NEAR, pattern=PATTERN), _label(NEAR, purpose="axis-label"), canvas="#FFFFFF")
    assert (on_ink.severity, on_ink.ground_kind, on_ink.ground_color) == ("error", "pattern-host-ink", NEAR)
    legible = _judge(_rect("band", "#FFFFFF", role="group-band", purpose="group-decoration", order=10,
                           stroke="#D0D0D0", pattern=PATTERN), _label("#101820", purpose="axis-label"), canvas="#FFFFFF")
    assert legible.severity == "info"


def test_a_canvas_texture_is_two_grounds_for_a_label():
    texture = _rect("texture", DARK, role="canvas-texture", purpose="canvas-texture", order=1, stroke="#E8E8E8", bounds={
        "inline": 0.0, "block": 0.0, "inlineSize": 400.0, "blockSize": 300.0})
    finding = _judge(texture, _label("#F0F0F0", purpose="as-of-label"), canvas=DARK)
    assert (finding.severity, finding.ground_kind, finding.ground_color) == ("error", "texture-ink", "#E8E8E8")


def test_a_label_in_the_cone_is_judged_on_the_ink_composited_at_the_strength_the_gradient_has_there():
    at = {"inline": 20.0, "block": 100.0, "inlineSize": 20.0, "blockSize": 10.0}
    # Dark ink on a light canvas passes; the warm cone makes the ground darker and the same label fails.
    label = _label("#3A2E00", purpose="as-of-label", bounds=at)
    outside = _judge(label, canvas="#FFFFFF")
    inside = _judge(_cone(), label, canvas="#FFFFFF")
    top = blend_over(ink=INK, opacity=1 - 100 / 200, ground="#FFFFFF")
    bottom = blend_over(ink=INK, opacity=1 - 110 / 200, ground="#FFFFFF")
    assert inside.ground_kind == "cone-blend" and inside.ground_id == "as-of-cone"
    assert inside.contrast_ratio == pytest.approx(min(
        composited_contrast(fill="#3A2E00", opacity=1.0, ground=top),
        composited_contrast(fill="#3A2E00", opacity=1.0, ground=bottom)))
    assert inside.contrast_ratio < outside.contrast_ratio
    # An ink that passes on the bare canvas and fails once the cone has tinted the ground under it.
    marginal = _label("#6E6E6E", purpose="as-of-label", bounds=at)
    assert _judge(marginal, canvas="#FFFFFF").severity == "info"
    tinted = _judge(_cone(), marginal, canvas="#FFFFFF")
    assert tinted.severity == "error" and tinted.ground_kind == "cone-blend"


def test_a_label_straddling_the_cone_edge_also_lies_on_the_unblended_host():
    # Half-width at y 105 is 0.25 * 105 = 26.25, so the right edge is at x 56.25 and this label crosses it.
    at = {"inline": 50.0, "block": 100.0, "inlineSize": 20.0, "blockSize": 10.0}
    finding = _judge(_cone(), _label("#101820", purpose="as-of-label", bounds=at), canvas="#FFFFFF")
    blended = blend_over(ink=INK, opacity=1 - 100 / 200, ground="#FFFFFF")
    assert finding.contrast_ratio == pytest.approx(min(
        composited_contrast(fill="#101820", opacity=1.0, ground=blended),
        composited_contrast(fill="#101820", opacity=1.0, ground="#FFFFFF")))


def test_a_label_the_cone_does_not_reach_keeps_its_own_ground():
    far = {"inline": 300.0, "block": 100.0, "inlineSize": 20.0, "blockSize": 10.0}
    finding = _judge(_cone(), _label("#3A2E00", purpose="as-of-label", bounds=far), canvas="#FFFFFF")
    assert finding.ground_kind == "canvas"


def test_text_translucent_ink_is_composited_over_its_ground():
    solid = _judge(_label("#FFFFFF"), canvas=DARK)
    faint = _judge(_label("#FFFFFF", **{}), canvas=DARK)
    translucent = _label("#FFFFFF")
    translucent["paint"]["opacity"] = 0.25
    assert _judge(translucent, canvas=DARK).contrast_ratio < solid.contrast_ratio == faint.contrast_ratio
    assert _judge(translucent, canvas=DARK).severity == "error"


def test_only_a_text_primitive_with_a_registered_purpose_is_a_free_label():
    not_text = dict(_label(NEAR), kind="Rect")
    assert not [item for item in evaluate_scene_contrast(_scene(not_text)) if item.primitive_id == "label"]
    unknown = _label(NEAR, purpose="no-such-purpose")
    assert not [item for item in evaluate_scene_contrast(_scene(unknown)) if item.primitive_id == "label"]
    # A purpose borrowed by a role of its own is not resolved across purposes.
    assert not [item for item in evaluate_scene_contrast(_scene(_label(NEAR, purpose="member-label", role="axis-label2")))
                if item.primitive_id == "label"]


def test_a_free_label_failure_is_never_softened_by_the_decoration_severity():
    scene = _scene(_label(NEAR))
    for severity in ("warning", "error"):
        finding = _only(evaluate_scene_contrast(scene, decoration_severity=severity))
        assert (finding.severity, finding.code) == ("error", "E_SCENE_STATE_TEXT_CONTRAST")


def test_an_illegible_label_on_a_decoration_ground_is_judged_on_that_decoration_even_when_the_decoration_only_warns():
    # The faint decoration warns; the label on it still blocks.
    band = _rect("band", NEAR, role="group-band", purpose="group-decoration", order=10)
    findings = evaluate_scene_contrast(_scene(band, _label(NEAR)))
    assert _only(findings, "band").severity in {"info", "warning"}
    assert _only(findings).severity == "error"
