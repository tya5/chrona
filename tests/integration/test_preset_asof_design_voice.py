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
