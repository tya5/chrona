"""Named presets inherit as-of wording without overriding an authored View (#1563)."""
from __future__ import annotations

from datetime import date

import pytest

from chrona.presentation.contracts.view_defaults import merge_view_defaults
from chrona.resources import builtin_preset_source_root, safe_load, schema_validator
from tests.support import synthetic_review as sr


def _resource(root, filename):
    return safe_load(builtin_preset_source_root(root).joinpath(filename).read_bytes())


@pytest.mark.parametrize(("design", "wording"), [
    ("target-b", "as of"), ("marquee", "AS OF"), ("sunday", "TODAY!"),
    ("titlecard", "現在 NOW"), ("yuya", "as of"),
])
def test_generic_preset_uses_the_design_wording_and_retains_explicit_view_precedence(design, wording):
    view = _resource("presets/bundles/design-default", "view.yaml")
    defaults = _resource(f"designs/{design}", "layout.yaml")["viewDefaults"]
    assert "label" not in view["body"]["markers"][0]
    effective = merge_view_defaults(view, defaults)
    assert effective["body"]["markers"][0]["label"] == wording
    assert not list(schema_validator("view-v0.28.schema.yaml").iter_errors(effective))

    view["body"]["markers"][0]["label"] = "Project voice"
    assert merge_view_defaults(view, defaults)["body"]["markers"][0]["label"] == "Project voice"


def test_a_thin_marker_without_design_defaults_still_needs_a_label():
    view = _resource("presets/bundles/design-default", "view.yaml")
    errors = list(schema_validator("view-v0.28.schema.yaml").iter_errors(merge_view_defaults(view, {})))
    assert any(error.validator == "required" and "label" in error.message
               and list(error.absolute_path) == ["body", "markers", 0] for error in errors)


@pytest.mark.parametrize("explicit", [None, "Project voice"])
def test_synthetic_render_closes_design_wording_before_validation_and_measurement(tmp_path, explicit):
    parts = sr.bundle("executive-light")
    marker = {"kind": "asOf", "source": "actual"}
    if explicit is not None:
        marker["label"] = explicit
    parts["view"]["body"]["markers"] = [marker]
    parts["layout"].setdefault("viewDefaults", {})["markerPresentation"] = {
        "kind": "asOf", "label": "Design voice", "date": {"form": "day-month"},
    }
    source = sr.with_calendar(sr.project({"a": sr.span("a", date(2026, 2, 1), 40)}))
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
              "body": {"asOf": "2026-02-20", "observations": []}}

    rendered = sr.render(tmp_path, source, presentation=parts, actual=actual)

    label = next(item for item in rendered.surface.primitives if item.scene_id == "as-of-label")
    assert label.text == f"{explicit or 'Design voice'} 20 Feb"


@pytest.mark.parametrize("append_date", [False, True])
@pytest.mark.parametrize("filled_chip", [False, True])
def test_existing_date_and_theme_chip_controls_are_independent(tmp_path, append_date, filled_chip):
    parts = sr.bundle("executive-light")
    parts["view"]["body"]["markers"] = [{"kind": "asOf", "source": "actual"}]
    defaults = {"kind": "asOf", "label": "Design voice"}
    if append_date:
        defaults["date"] = {"form": "day-month"}
    parts["layout"].setdefault("viewDefaults", {})["markerPresentation"] = defaults
    roles = parts["theme"]["body"]["roles"]
    roles.pop("as-of-label-chip", None)
    if filled_chip:
        roles["as-of-label-chip"] = {"backgroundTreatment": "fill", "chipPadding": "chip-padding"}
        parts["theme"]["body"]["colorBindings"]["as-of-label-chip.fill"] = "surfaceRaised"
    source = sr.with_calendar(sr.project({"a": sr.span("a", date(2026, 2, 1), 40)}))
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
              "body": {"asOf": "2026-02-20", "observations": []}}

    rendered = sr.render(tmp_path, source, presentation=parts, actual=actual)

    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    label = primitives["as-of-label"]
    assert label.text == "Design voice" + (" 20 Feb" if append_date else "")
    assert ("chip:as-of-label" in primitives) == filled_chip
    if filled_chip:
        chip = primitives["chip:as-of-label"]
        assert chip.paint is not None and chip.paint.fill
        assert chip.paint_order < label.paint_order
        assert chip.bounds[0] < label.bounds[0]
        assert chip.bounds[1] < label.bounds[1]
        assert chip.bounds[2] > label.bounds[2]
        assert chip.bounds[3] > label.bounds[3]


def test_wallboard_keeps_its_bare_word_in_a_theme_painted_chip(tmp_path):
    source = sr.with_calendar(sr.project({"a": sr.span("a", date(2026, 2, 1), 40)}))
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
              "body": {"asOf": "2026-02-20", "observations": []}}

    rendered = sr.render(tmp_path, source, presentation=sr.bundle("wallboard-dark"), actual=actual)

    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    label, chip = primitives["as-of-label"], primitives["chip:as-of-label"]
    assert label.text == "Today"
    assert chip.paint is not None and chip.paint.fill
    assert label.paint is not None and label.paint.fill != chip.paint.fill
    assert chip.paint_order < label.paint_order
