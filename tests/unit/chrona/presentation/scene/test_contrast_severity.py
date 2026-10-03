"""#995: severity classes of the completed-Scene contrast policy.

Marks and text keep blocking floors; a decoration (a stripe, a band, a tint) below its floor, or on a ground
that cannot be read, is a typed warning unless the caller (the Theme's `contrastPolicy`) asks for it to block.
Every Scene here is built by hand, so no corpus input can change what these tests prove.
"""
from __future__ import annotations

import pytest

from chrona.presentation.scene.contrast_policy import (
    DECORATION_WARNING_BLOCKING_CODES, evaluate_scene_contrast)

WHITE = "#FFFFFF"
FAINT = "#F4F4F4"      # 1.099:1 on white, under the 1.10 decoration floor
BOX = {"inline": 10, "block": 10, "inlineSize": 20, "blockSize": 10}


def _scene(*primitives, version="chrona/scene/v0.6"):
    return {"version": version, "kind": "scene", "surfaces": [{
        "id": "review", "canvasPaint": {"fill": WHITE, "opacity": 1}, "primitives": list(primitives),
        "decorationDispositions": [],
    }]}


def _primitive(identifier, role, purpose, fill, *, kind="Rect", order=100, opacity=1, treatment=None, bounds=None,
               stroke=None, pattern=None):
    value = {"id": identifier, "visualRole": role, "purpose": purpose, "kind": kind, "paintOrder": order,
             "bounds": bounds or BOX,
             "paint": {"fill": fill, "opacity": opacity, **({"stroke": stroke, "strokeWidth": 1} if stroke else {})}}
    if treatment is not None:
        value["contrastTreatment"] = treatment
    if pattern is not None:
        value["pattern"] = pattern
    return value


def _band(fill=FAINT, *, opacity=1, order=10):
    return _primitive("band", "row-band", "row-decoration", fill, order=order, opacity=opacity)


def _by_id(findings):
    return {item.primitive_id: item for item in findings}


# --- (a) illegible text and marks still block -------------------------------------------------------------

ILLEGIBLE = {
    "state text": (_primitive("x", "variance-ahead", "table-cell", WHITE, treatment="required"),
                   "E_SCENE_STATE_TEXT_CONTRAST"),
    "deemphasized state text": (_primitive("x", "variance-on-track", "table-cell", WHITE, treatment="deemphasized"),
                                "E_SCENE_STATE_TEXT_CONTRAST"),
    "ground text": (_primitive("x", "text", "group-header", WHITE, kind="Text"), "E_SCENE_STATE_TEXT_CONTRAST"),
    "data mark": (_primitive("x", "planned", "planned", WHITE), "E_SCENE_MARK_CONTRAST"),
    "progress fill": (_primitive("x", "progress-fill", "progress-fill", WHITE), "E_SCENE_MARK_CONTRAST"),
}


@pytest.mark.parametrize("name", list(ILLEGIBLE))
@pytest.mark.parametrize("decoration_severity", ["warning", "error"])
def test_illegible_text_and_marks_are_errors_whatever_the_decoration_severity(name, decoration_severity):
    primitive, code = ILLEGIBLE[name]
    (finding,) = evaluate_scene_contrast(_scene(primitive), decoration_severity=decoration_severity)

    assert (finding.code, finding.severity) == (code, "error")
    assert finding.severity_class == "legibility"
    assert finding.contrast_ratio == pytest.approx(1.0)


def test_illegible_note_text_is_an_error_on_its_box_not_a_warning():
    box = _primitive("note-box", "annotation-note-box", "annotation-box", "#202020", order=10)
    box["sourceRef"] = "n0"
    text = _primitive("note-text", "annotation-note-text", "annotation-text", "#222222", kind="Text",
                      treatment="required")
    text["sourceRef"] = "n0"
    findings = _by_id(evaluate_scene_contrast(_scene(box, text)))

    assert (findings["note-text"].code, findings["note-text"].severity) == ("E_SCENE_STATE_TEXT_CONTRAST", "error")
    assert findings["note-text"].ground_id == "note-box"


def test_a_mark_on_a_translucent_ground_is_judged_on_the_composite_and_blocks_below_its_floor():
    host = _band("#000000", opacity=0.5)  # over the white canvas: #808080
    faint = _primitive("faint", "planned", "planned", "#808080")
    bold = _primitive("bold", "planned", "planned", "#000000")
    findings = _by_id(evaluate_scene_contrast(_scene(host, faint), decoration_severity="warning"))
    assert (findings["faint"].code, findings["faint"].severity, findings["faint"].severity_class) == (
        "E_SCENE_MARK_CONTRAST", "error", "legibility")
    assert (findings["faint"].ground_color, findings["faint"].ground_kind) == ("#808080", "translucent-over-canvas")
    findings = _by_id(evaluate_scene_contrast(_scene(host, bold)))
    assert (findings["bold"].severity, findings["bold"].ground_id) == ("info", "band")


def test_a_mark_on_a_host_that_cannot_be_read_is_still_an_unreadable_error():
    host = _band("#000000", opacity=2)  # not a number in [0, 1]
    mark = _primitive("mark", "planned", "planned", "#000000")
    findings = _by_id(evaluate_scene_contrast(_scene(host, mark)))

    assert (findings["mark"].code, findings["mark"].severity) == ("E_SCENE_CONTRAST_GROUND_UNSUPPORTED", "error")


def test_a_malformed_decoration_paint_is_still_an_error_not_a_warning():
    band = _band()
    band["paint"]["opacity"] = 7
    (finding,) = evaluate_scene_contrast(_scene(band))

    assert (finding.code, finding.severity) == ("E_SCENE_CONTRAST_PAINT", "error")


def test_a_missing_treatment_is_still_an_error():
    (finding,) = evaluate_scene_contrast(_scene(_primitive("x", "variance-on-track", "table-cell", WHITE)))

    assert (finding.code, finding.severity) == ("E_SCENE_STATE_TEXT_CONTRAST_TREATMENT", "error")


# --- (b) a decoration-only failure warns ------------------------------------------------------------------


def test_a_decoration_below_its_floor_is_a_typed_warning_and_the_scene_has_no_error():
    legible_mark = _primitive("mark", "planned", "planned", "#000000", order=100)
    legible_text = _primitive("cell", "variance-ahead", "table-cell", "#000000", treatment="required", order=300,
                              bounds={"inline": 50, "block": 12, "inlineSize": 4, "blockSize": 4})
    findings = evaluate_scene_contrast(_scene(_band(), legible_mark, legible_text))
    by_id = _by_id(findings)

    assert not [item for item in findings if item.severity == "error"]
    band = by_id["band"]
    assert (band.code, band.severity, band.floor) == ("W_SCENE_DECORATION_CONTRAST", "warning", 1.10)
    assert band.contrast_ratio < 1.10
    assert (band.severity_class, band.ground_id, band.paint_channel) == ("decoration", "canvas", "fill")
    assert band.as_mapping()["severityClass"] == "decoration"
    assert by_id["mark"].severity == by_id["cell"].severity == "info"


def test_a_legible_decoration_stays_info():
    (finding,) = evaluate_scene_contrast(_scene(_band("#202020")))

    assert (finding.code, finding.severity) == ("E_SCENE_DECORATION_CONTRAST", "info")


@pytest.mark.parametrize("role,purpose", [
    ("calendar-closed", "calendar-closed"), ("period-band", "period-band"), ("group-band", "group-decoration"),
    ("axis-band-decoration", "axis-band"), ("annotation-note-box", "annotation-box"),
    ("annotation-kind-bar", "annotation-kind-bar"), ("group-header-band", "group-header-band")])
def test_every_registry_decoration_role_warns_by_class_not_by_name(role, purpose):
    (finding,) = evaluate_scene_contrast(_scene(_primitive("d", role, purpose, FAINT)))

    assert (finding.code, finding.severity, finding.severity_class) == (
        "W_SCENE_DECORATION_CONTRAST", "warning", "decoration")


def test_a_decoration_on_a_translucent_ground_warns_that_it_cannot_be_judged():
    host = _band("#000000", opacity=0.5)
    closed = _primitive("closed", "calendar-closed", "calendar-closed", FAINT, order=20)
    findings = _by_id(evaluate_scene_contrast(_scene(host, closed)))

    assert (findings["closed"].code, findings["closed"].severity) == (
        "W_SCENE_DECORATION_GROUND_UNSUPPORTED", "warning")
    assert findings["closed"].ground_id == "band" and findings["closed"].severity_class == "decoration"


def test_a_decoration_pattern_whose_ink_equals_its_substrate_warns_on_that_channel_pair():
    tab = _primitive("tab", "group-tab", "group-tab", "#202020", stroke="#202020", order=10, pattern={
        "densityBasisPoints": 5000, "tileInlineSize": 4, "tileBlockSize": 4, "angleDegrees": 45})
    findings = evaluate_scene_contrast(_scene(tab, version="chrona/scene/v0.7"))
    failing = [item for item in findings if item.severity != "info"]

    assert failing and {item.severity for item in failing} == {"warning"}
    assert {item.code for item in failing} == {"W_SCENE_DECORATION_CONTRAST"}
    assert {(item.paint_channel, item.ground_kind) for item in failing} == {("stroke", "pattern-substrate")}
    assert not [item for item in findings if item.severity == "error"]


@pytest.mark.parametrize("decoration_severity,code,severity", [
    ("warning", "W_SCENE_DECORATION_GROUND_UNSUPPORTED", "warning"),
    ("error", "E_SCENE_CONTRAST_GROUND_UNSUPPORTED", "error")])
def test_a_decoration_pattern_on_a_translucent_host_follows_the_severity(decoration_severity, code, severity):
    host = _band("#000000", opacity=0.5)
    tab = _primitive("tab", "group-tab", "group-tab", "#202020", stroke="#808080", order=20, pattern={
        "densityBasisPoints": 5000, "tileInlineSize": 4, "tileBlockSize": 4, "angleDegrees": 45})
    findings = _by_id(evaluate_scene_contrast(_scene(host, tab, version="chrona/scene/v0.7"),
                                              decoration_severity=decoration_severity))

    assert (findings["tab"].code, findings["tab"].severity) == (code, severity)
    assert findings["tab"].severity_class == "decoration" and findings["tab"].ground_id == "band"


def test_a_mark_on_a_faint_decoration_is_still_judged_on_that_decoration():
    band = _band(FAINT)
    pale = _primitive("mark", "planned", "planned", "#F8F8F8", order=100)
    findings = _by_id(evaluate_scene_contrast(_scene(band, pale)))

    assert findings["band"].severity == "warning"
    assert (findings["mark"].code, findings["mark"].severity, findings["mark"].ground_id) == (
        "E_SCENE_MARK_CONTRAST", "error", "band")


def test_text_on_a_faint_group_band_is_still_judged_on_the_band():
    band = _primitive("group:a", "group-band", "group-decoration", FAINT, order=10)
    header = _primitive("group-header:a", "text", "group-header", "#F6F6F6", kind="Text", order=300)
    findings = _by_id(evaluate_scene_contrast(_scene(band, header)))

    assert findings["group:a"].severity == "warning"
    assert (findings["group-header:a"].severity, findings["group-header:a"].ground_id) == ("error", "group:a")


# --- (c) the knob restores blocking -----------------------------------------------------------------------


def test_the_blocking_mode_restores_the_error_codes_of_a_decoration():
    (finding,) = evaluate_scene_contrast(_scene(_band()), decoration_severity="error")

    assert (finding.code, finding.severity, finding.severity_class) == (
        "E_SCENE_DECORATION_CONTRAST", "error", "decoration")


def test_the_blocking_mode_restores_the_unreadable_ground_error():
    host = _band("#000000", opacity=0.5)
    closed = _primitive("closed", "calendar-closed", "calendar-closed", FAINT, order=20)
    findings = _by_id(evaluate_scene_contrast(_scene(host, closed), decoration_severity="error"))

    assert (findings["closed"].code, findings["closed"].severity) == ("E_SCENE_CONTRAST_GROUND_UNSUPPORTED", "error")


def test_the_blocking_mode_restores_every_pattern_pair_error():
    tab = _primitive("tab", "group-tab", "group-tab", "#202020", stroke="#202020", order=10, pattern={
        "densityBasisPoints": 5000, "tileInlineSize": 4, "tileBlockSize": 4, "angleDegrees": 45})
    findings = evaluate_scene_contrast(_scene(tab, version="chrona/scene/v0.7"), decoration_severity="error")

    assert [item for item in findings if item.severity == "error"]
    assert not [item for item in findings if item.severity == "warning"]


def test_the_default_is_warning_and_an_unknown_severity_is_refused():
    explicit = evaluate_scene_contrast(_scene(_band()), decoration_severity="warning")
    assert explicit == evaluate_scene_contrast(_scene(_band()))
    with pytest.raises(ValueError):
        evaluate_scene_contrast(_scene(_band()), decoration_severity="info")


def test_every_decoration_warning_names_the_blocking_code_it_stands_for():
    assert DECORATION_WARNING_BLOCKING_CODES == {
        "W_SCENE_DECORATION_CONTRAST": "E_SCENE_DECORATION_CONTRAST",
        "W_SCENE_DECORATION_GROUND_UNSUPPORTED": "E_SCENE_CONTRAST_GROUND_UNSUPPORTED"}
