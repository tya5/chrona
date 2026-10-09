"""#583 I583-2: a per-group band tint from a Theme colour scale, rendered end to end.

A Project built in `tests/support/synthetic_review.py` goes through the packaged `control-room-dark`
bundle (groups by `owner` with header presentation; Theme `colorScales.series` is a cyclic palette).
No `examples/` input.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta

import pytest

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr

OWNERS = ("bus", "payload", "ground")
BAND = {"group-decoration", "group-header-band"}


def _project(owners=OWNERS):
    objects = {}
    for index, owner in enumerate(owners):
        for number in range(2):
            key = f"t-{owner}-{number}"
            objects[key] = sr.span(key, date(2026, 1, 5) + timedelta(days=index * 20 + number * 15), 12, owner=owner)
    source = sr.project(objects)
    for owner in owners:
        source["entities"][owner]["title"] = owner.title()
    return source


def _parts(tint=None, *, extent="both", groups=None, mutate=None):
    parts = sr.bundle("control-room-dark")
    if tint is not None:
        parts["view"]["body"]["grouping"]["tint"] = tint
    parts["layout"]["reviewSurface"]["backgroundExtents"]["groupBand"] = extent
    if groups is not None:
        parts["view"]["body"]["backgroundDecoration"]["groups"] = groups
    if mutate is not None:
        mutate(parts)
    return parts


def _render(tmp_path, parts, source=None):
    return sr.render(tmp_path, source or _project(), presentation=parts)


def _bands(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives if item.purpose in BAND}


def _scheme(parts, slot):
    return parts["scheme"]["body"]["categories"][slot]


def test_without_a_tint_every_group_band_shares_the_role_fill(tmp_path):
    bands = _bands(_render(tmp_path, _parts()))
    assert len(bands) == 3 and {item.paint.fill for item in bands.values()} == {"#16213A"}


def test_each_group_band_takes_its_scale_colour_in_display_order(tmp_path):
    parts = _parts({"scale": "series"})
    bands = _bands(_render(tmp_path, parts))
    assert {key: item.paint.fill for key, item in bands.items()} == {
        "group:bus": _scheme(parts, "series-1"), "group:payload": _scheme(parts, "series-2"),
        "group:ground": _scheme(parts, "series-3")}


def test_the_tint_changes_only_the_group_bands_fill(tmp_path):
    (tmp_path / "plain").mkdir()
    (tmp_path / "tinted").mkdir()
    plain = _render(tmp_path / "plain", _parts())
    tinted = _render(tmp_path / "tinted", _parts({"scale": "series"}))
    before, after = list(plain.surface.primitives), list(tinted.surface.primitives)
    assert [item.scene_id for item in before] == [item.scene_id for item in after]
    for old, new in zip(before, after, strict=True):
        if old.purpose in BAND:
            assert (new.bounds, new.paint.opacity, new.paint_order, new.paint.stroke) == (
                old.bounds, old.paint.opacity, old.paint_order, old.paint.stroke)
            assert new.paint.fill != old.paint.fill
        else:
            assert new == old


def test_the_tinted_band_spans_the_table_and_the_timeline(tmp_path):
    rendered = _render(tmp_path, _parts({"scale": "series"}))
    slots = {item.source: item for item in rendered.surface.slots}
    table, timeline = slots["table"].bounds, slots["timeline"].bounds
    for band in _bands(rendered).values():
        assert band.bounds[0] == pytest.approx(table[0])
        assert band.bounds[0] + band.bounds[2] == pytest.approx(timeline[0] + timeline[2])


def test_a_listed_domain_maps_each_group_through_explicit_slots(tmp_path):
    def mutate(parts):
        parts["theme"]["body"]["colorScales"]["fixed"] = {
            "slots": {"bus": "series-3", "payload": "series-1", "ground": "series-2"}}
    parts = _parts({"scale": "fixed", "domain": ["bus", "payload", "ground"]}, mutate=mutate)
    bands = _bands(_render(tmp_path, parts))
    assert bands["group:bus"].paint.fill == _scheme(parts, "series-3")
    assert bands["group:payload"].paint.fill == _scheme(parts, "series-1")


def test_a_group_outside_a_listed_domain_is_an_error_naming_it(tmp_path):
    def mutate(parts):
        parts["theme"]["body"]["colorScales"]["fixed"] = {"slots": {"bus": "series-1", "payload": "series-2"}}
    with pytest.raises(RenderFailed) as failure:
        _render(tmp_path, _parts({"scale": "fixed", "domain": ["bus", "payload"]}, mutate=mutate))
    assert failure.value.code == "E_PRESENTATION_SCALE_VALUE"
    assert failure.value.source_ref == "/body/grouping/tint"
    assert "value='ground'" in failure.value.message


def test_an_unknown_scale_is_a_mapping_error(tmp_path):
    with pytest.raises(RenderFailed) as failure:
        _render(tmp_path, _parts({"scale": "missing"}))
    assert "E_PRESENTATION_SCALE_MAPPING" in str(failure.value)


def test_under_alternate_an_unselected_group_has_no_band_and_so_no_tint(tmp_path):
    parts = _parts({"scale": "series"}, groups="alternate")
    bands = _bands(_render(tmp_path, parts))
    assert set(bands) == {"group:bus", "group:ground"}
    assert bands["group:ground"].paint.fill == _scheme(parts, "series-3")


def test_with_no_group_bands_the_header_band_is_tinted(tmp_path):
    parts = _parts({"scale": "series"}, groups="none")
    bands = _bands(_render(tmp_path, parts))
    assert set(bands) == {"group-header-band:bus", "group-header-band:payload", "group-header-band:ground"}
    assert bands["group-header-band:payload"].paint.fill == _scheme(parts, "series-2")


def test_an_outline_band_takes_the_tint_as_its_stroke_and_stays_unfilled(tmp_path):
    def mutate(parts):
        role = parts["theme"]["body"]["roles"]["group-band"]
        role.update({"backgroundTreatment": "outline", "strokeWidth": "stroke-width"})
        parts["theme"]["body"]["colorBindings"]["group-band.stroke"] = "neutral"
    parts = sr.bundle("control-room-dark")
    probe = _bands(_render(tmp_path, _parts({"scale": "series"}, mutate=mutate)))
    first = probe["group:bus"]
    assert first.paint.stroke == _scheme(parts, "series-1") and first.paint.fill in (None, "none")


def test_a_translucent_band_stays_translucent_under_the_tint(tmp_path):
    def mutate(parts):
        parts["theme"]["body"]["values"]["opacity.group-band"]["value"] = 0.5
        parts["view"]["body"]["backgroundDecoration"]["rows"] = "none"  # a translucent band may not overlap a stripe
    bands = _bands(_render(tmp_path, _parts({"scale": "series"}, mutate=mutate)))
    assert {item.paint.opacity for item in bands.values()} == {0.5}


def test_two_groups_a_reader_cannot_tell_apart_are_warned_about(tmp_path):
    def mutate(parts):  # a scale of its own, so the mark scale's identical diagnostics cannot stand in for it
        parts["theme"]["body"]["colorScales"]["groups"] = {"palette": ["series-1", "series-1", "series-3"]}
    rendered = _render(tmp_path, _parts({"scale": "groups"}, mutate=mutate))
    assert any(item.startswith("W_PRESENTATION_SCALE_NOT_SEPARABLE:groups:bus:payload")
               for item in rendered.scene.diagnostics)
    assert any(item.scale_id == "groups" for item in rendered.scale_collisions)


def _findings(rendered, decoration_severity="warning"):
    return evaluate_scene_contrast(scene_document(rendered.scene), decoration_severity=decoration_severity)


def _with_tint_colour(colour):
    def mutate(parts):
        parts["scheme"]["body"]["categories"]["series-1"] = colour
    return mutate


def test_the_contrast_gate_reads_a_tint_as_the_ground_under_the_marks_it_carries(tmp_path):
    (tmp_path / "plain").mkdir()
    ink = "#EAF0FA"  # a tint as light as the mark: the mark cannot be seen on it
    plain = [item for item in _findings(_render(tmp_path / "plain", _parts())) if item.code == "E_SCENE_MARK_CONTRAST" and item.severity == "error"]
    assert plain == []
    glare = _findings(_render(tmp_path, _parts({"scale": "series"}, mutate=_with_tint_colour(ink))))
    failing = [item for item in glare if item.severity == "error" and item.code == "E_SCENE_MARK_CONTRAST"]
    assert failing and all(item.ground_color.upper() == ink for item in failing)
    assert {item.primitive_id for item in failing} == {"planned:review-lane:[\"generated\",\"bus\",\"t-bus-1\"]:t-bus-1"}


def test_the_contrast_gate_fails_a_tinted_band_the_canvas_swallows(tmp_path):
    canvas = "#0B1220"
    rendered = _render(tmp_path, _parts({"scale": "series"}, mutate=_with_tint_colour(canvas)))
    findings = _findings(rendered, "error")  # a Theme that declares decoration blocking (#995)
    assert [item.primitive_id for item in _findings(rendered)
            if item.visual_role == "group-band" and item.severity == "warning"] == ["group:bus"]
    swallowed = [item for item in findings if item.visual_role == "group-band" and item.severity == "error"]
    assert [item.primitive_id for item in swallowed] == ["group:bus"]
    assert swallowed[0].contrast_ratio < swallowed[0].floor
    assert [item for item in findings if item.visual_role == "group-band" and item.severity == "info"]


def test_a_row_stripe_is_judged_against_the_tint_it_lies_on(tmp_path):
    findings = _findings(_render(tmp_path, _parts({"scale": "series"})))
    stripes = [item for item in findings if item.visual_role == "row-band" and "bus" in item.primitive_id]
    assert stripes and {item.ground_color.upper() for item in stripes} == {"#142642"}


def test_a_tint_on_a_band_grouping_by_object_type_is_rejected_at_the_contract(tmp_path):
    parts = _parts()
    parts["view"]["body"]["grouping"] = {"by": "objectType", "presentation": "header", "tint": {"scale": "series"}}
    with pytest.raises(Exception) as failure:
        _render(tmp_path, parts)
    assert "E_VIEW_GROUP_TINT_UNUSABLE" in str(failure.value)


def test_a_tint_does_not_change_the_row_or_mark_colour_scales(tmp_path):
    parts = _parts({"scale": "series"})
    parts["view"]["body"]["colorEncoding"] = {"scale": "series", "target": "planned", "source": {"field": "owner"},
                                              "domain": "firstAppearance"}
    rendered = _render(tmp_path, parts)
    planned = {item.source_ref: item.paint.fill for item in rendered.surface.primitives if item.purpose == "planned"}
    assert planned["t-bus-0"] == _scheme(parts, "series-1") and planned["t-payload-0"] == _scheme(parts, "series-2")
    assert deepcopy(_bands(rendered))["group:payload"].paint.fill == _scheme(parts, "series-2")
