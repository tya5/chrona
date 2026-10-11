"""Axis secondary labels (#493): the View declaration, schema, and the gates over the drawn text.

A synthetic Project is rendered through a packaged preset bundle, so a corpus edit cannot change what these tests
prove. The committed slides that show a secondary are evidence, not a gate.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest

from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.presentation.scene.serialization import scene_document
from chrona.resources import schema_validator
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr

WINDOW = {"mode": "explicit", "start": "2026-01-01", "end": "2026-07-01"}


def _source() -> dict:
    return sr.project({"a": sr.span("a", date(2026, 1, 5), 40), "b": sr.span("b", date(2026, 2, 10), 30, owner="b")})


def _month_labels(view: dict) -> dict:
    return next(tier for tier in view["body"]["axis"]["tiers"] if tier["role"] == "labels" and tier["unit"] == "month")


def _parts(*, placement="inline", secondary_size=9, **overrides) -> dict:
    parts = sr.bundle("executive-light")
    parts["view"]["body"]["window"] = dict(WINDOW)
    # Secondary declarations exercise a fixed month tier, not preset defaults.
    parts["view"]["body"]["axis"]["tiers"] = [
        {"unit": "quarter", "every": 1, "role": "band", "typographyRole": "axisQuarter"},
        {"unit": "quarter", "every": 1, "role": "grid-major"},
        {"unit": "quarter", "every": 1, "role": "labels", "typographyRole": "axisQuarter",
         "label": {"form": "year-quarter", "align": "center", "overflow": "visible-overflow",
                   "orientation": "horizontal"}},
        {"unit": "month", "every": 1, "role": "band", "typographyRole": "axisMonth"},
        {"unit": "month", "every": 1, "role": "labels", "typographyRole": "axisMonth",
         "label": {"form": "short-month", "align": "start", "overflow": "thin-with-record",
                   "orientation": "horizontal"}},
        {"unit": "month", "every": 1, "role": "grid-minor"},
    ]
    label = _month_labels(parts["view"])["label"]
    label["nameTable"] = "en-US"
    label["secondary"] = {"form": "numeric-month", "nameTable": "en-US", "typographyRole": "axisSecondary",
                          "placement": placement, **overrides}
    body = parts["theme"]["body"]
    body["values"]["size.secondary"] = {"type": "number", "value": secondary_size}
    month = {key: value for key, value in body["roles"]["axisMonth"].items()
             if key not in {"laneBlockSize", "labelInset"}}
    body["roles"]["axisSecondary"] = {**month, "fontSize": "size.secondary"}
    return parts


def _render(tmp_path, parts):
    return sr.render(tmp_path, _source(), presentation=parts)


def _texts(rendered, prefix):
    return {item.scene_id: item for item in rendered.surface.primitives if item.scene_id.startswith(prefix)}


def test_a_declared_secondary_is_drawn_with_its_own_name_table_and_size(tmp_path):
    rendered = _render(tmp_path, _parts())

    primaries, secondaries = _texts(rendered, "axis-label:"), _texts(rendered, "axis-label-secondary:")
    month = {key: value for key, value in primaries.items() if value.text in {"Jan", "Feb", "Mar", "Apr", "May", "Jun"}}
    assert [value.text for value in month.values()] == ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    assert [value.text for value in secondaries.values()] == ["01", "02", "03", "04", "05", "06"]
    first = next(iter(secondaries.values()))
    assert first.text_layout.font_size == 9 < next(iter(month.values())).text_layout.font_size
    assert first.visual_role == next(iter(month.values())).visual_role


def test_the_scene_gates_cover_the_secondary_text_and_find_no_error_in_a_fitting_one(tmp_path):
    document = scene_document(_render(tmp_path, _parts()).scene)

    findings = evaluate_scene_perceptibility(document)
    assert [item for item in findings if item.severity == "error"] == []
    assert any(item.code == "I_SCENE_PAINT_CONTRAST" and any(i.startswith("axis-label-secondary:") for i in item.primitive_ids)
               for item in findings)


def test_the_text_intersection_gate_reports_a_secondary_that_overlaps_its_primary(tmp_path):
    document = deepcopy(scene_document(_render(tmp_path, _parts()).scene))
    primitives = document["surfaces"][0]["primitives"]
    primary = next(item for item in primitives if item["id"].startswith("axis-label:") and item.get("text") == "Jan")
    secondary = next(item for item in primitives if item["id"].startswith("axis-label-secondary:"))
    secondary["bounds"] = dict(primary["bounds"])

    codes = {(item.code, item.primitive_ids) for item in evaluate_scene_perceptibility(document)}
    assert ("E_SCENE_TEXT_INTERSECTION", tuple(sorted((primary["id"], secondary["id"])))) in codes


def test_the_secondary_text_is_hosted_by_the_same_axis_band_as_its_primary(tmp_path):
    rendered = _render(tmp_path, _parts())

    hosts = {item.scene_id: item.host_placement_id for item in rendered.surface.primitives
             if item.scene_id.startswith("axis-label")}
    primary_hosts = {value for key, value in hosts.items() if key.startswith("axis-label:") and value}
    secondary_hosts = {value for key, value in hosts.items() if key.startswith("axis-label-secondary:")}
    assert secondary_hosts and secondary_hosts <= primary_hosts


def test_a_view_without_a_secondary_draws_none_and_needs_no_secondary_role(tmp_path):
    parts = _parts()
    del _month_labels(parts["view"])["label"]["secondary"]
    del parts["theme"]["body"]["roles"]["axisSecondary"]

    assert not _texts(_render(tmp_path, parts), "axis-label-secondary:")


def test_a_theme_without_the_named_secondary_role_fails_the_render(tmp_path):
    parts = _parts()
    del parts["theme"]["body"]["roles"]["axisSecondary"]

    with pytest.raises(Exception) as caught:
        _render(tmp_path, parts)
    assert "axisSecondary" in str(caught.value) or isinstance(caught.value, RenderFailed)


# --- the declaration ------------------------------------------------------------------------------------


def _tier(unit="month", **label) -> dict:
    forms = {"month": "short-month", "week": "iso-week", "quarter": "year-quarter", "year": "year",
             "half": "half-year", "day": "localized-date"}
    body = {"form": forms[unit], "align": "center", "overflow": "thin-with-record", "orientation": "horizontal"}
    body.update(label)
    return {"unit": unit, "every": 1, "role": "labels", "label": body}


def _view(*tiers) -> dict:
    view = sr.bundle("executive-light")["view"]
    view["body"]["axis"] = {"tiers": list(tiers)}
    return view


def _errors(view: dict) -> list[str]:
    validator = schema_validator("view-v0.28.schema.yaml")
    return sorted(error.message for error in validator.iter_errors(view))


SECONDARY = {"form": "short-month", "typographyRole": "axisSecondary", "placement": "stacked"}


def test_the_schema_accepts_a_secondary_on_a_fixed_unit_horizontal_tier():
    assert _errors(_view(_tier(secondary=SECONDARY))) == []
    assert _errors(_view(_tier(secondary={**SECONDARY, "nameTable": "ja-JP", "placement": "inline"}))) == []


@pytest.mark.parametrize("unit, form", [("quarter", "year-quarter"), ("week", "iso-week"), ("year", "year"),
                                        ("half", "half-year"), ("day", "localized-date")])
def test_every_fixed_unit_accepts_a_secondary_of_its_own_forms(unit, form):
    assert _errors(_view(_tier(unit, secondary={**SECONDARY, "form": form}))) == []


@pytest.mark.parametrize("secondary", [
    {"typographyRole": "axisSecondary", "placement": "stacked"},
    {"form": "short-month", "placement": "stacked"},
    {"form": "short-month", "typographyRole": "axisSecondary"},
    {**SECONDARY, "placement": "corner"},
    {**SECONDARY, "nameTable": "fr-FR"},
    {**SECONDARY, "typographyRole": ""},
    {**SECONDARY, "extra": 1},
])
def test_the_schema_rejects_an_incomplete_or_unknown_secondary(secondary):
    assert _errors(_view(_tier(secondary=secondary)))


def test_the_schema_rejects_a_form_that_does_not_belong_to_the_tiers_unit():
    assert _errors(_view(_tier("week", secondary={**SECONDARY, "form": "short-month"})))
    assert _errors(_view(_tier("month", secondary={**SECONDARY, "form": "iso-week"})))


@pytest.mark.parametrize("orientation", ["rotate-cw", "rotate-ccw"])
def test_the_schema_rejects_a_secondary_on_rotated_text(orientation):
    assert _errors(_view(_tier(orientation=orientation, secondary=SECONDARY)))


def test_the_schema_rejects_a_secondary_on_an_automatic_unit_tier():
    tier = {"unit": "auto", "every": 1, "role": "labels", "label": {
        "forms": {"month": "short-month"}, "align": "center", "overflow": "thin-with-record",
        "orientation": "horizontal", "secondary": SECONDARY}}
    assert _errors(_view(tier))


@pytest.mark.parametrize("label, locale, expected", [
    ({"nameTable": "ja-JP"}, "en-US", "ja-JP"),
    ({}, "ja-JP", "ja-JP"),
    ({"nameTable": "en-US"}, "ja-JP", "en-US"),
])
def test_a_secondary_without_a_name_table_takes_the_one_the_primary_resolves(label, locale, expected):
    from chrona.presentation.review.v05_content import _axis_tier

    tier = _tier(secondary=SECONDARY, **label)
    intent = _axis_tier(tier, locale=locale).label
    assert (intent.name_table_id, intent.secondary.name_table_id) == (expected, expected)
    explicit = _axis_tier(_tier(secondary={**SECONDARY, "nameTable": "ja-JP"}, **label), locale=locale).label
    assert explicit.secondary.name_table_id == "ja-JP"
