"""Real Layout/Scene/SVG count headings on independent synthetic membership (#1346)."""
from datetime import date

import pytest

from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr


def _parts():
    parts = sr.bundle("control-room-dark")
    parts["view"]["body"]["heading"] = {
        "title": "{project}: {figure:items} WORK PACKAGES",
        "subtitle": "in {figure:groups} sections",
    }
    parts["view"]["body"]["figures"] = [
        {"id": "items", "kind": "count", "source": "selected"},
        {"id": "groups", "kind": "count", "source": "groups"},
    ]
    parts["layout"]["viewDefaults"] = {"figureFormats": {
        "items": {"form": "digits", "minimumDigits": 2},
        "groups": {"form": "english-words"},
    }}
    return parts


def test_heading_binds_actual_membership_before_source_measurement(tmp_path, monkeypatch):
    from chrona.presentation.layout import surface_render_plan as planner
    original = planner.measure_sources
    measured_text = []

    def measure(inputs, *args, **kwargs):
        measured_text.extend(line for item in inputs.values() for line in item.lines)
        return original(inputs, *args, **kwargs)

    monkeypatch.setattr(planner, "measure_sources", measure)
    source = sr.project({"a": sr.span("a", date(2026, 2, 2), 20, owner="one"),
                         "b": sr.span("b", date(2026, 3, 2), 20, owner="one"),
                         "c": sr.span("c", date(2026, 4, 2), 20, owner="two")})
    rendered = sr.render(tmp_path, source, presentation=_parts())
    texts = {p.scene_id: p.text for p in rendered.surface.primitives if p.scene_id in {"title", "subtitle"}}
    assert texts == {"title": "Synthetic: 03 WORK PACKAGES", "subtitle": "in two sections"}
    assert any("Synthetic: 03 WORK PACKAGES" in text for text in measured_text)
    svg = rendered.artifact.content.decode()
    assert "Synthetic: 03 WORK PACKAGES" in svg and "in two sections" in svg


def test_explicit_empty_formats_replace_layout_defaults_in_real_output(tmp_path):
    parts = _parts()
    parts["view"]["body"]["figureFormats"] = {}
    rendered = sr.render(tmp_path, sr.project({"a": sr.span("a", date(2026, 2, 2), 20)}), presentation=parts)
    texts = {p.scene_id: p.text for p in rendered.surface.primitives if p.scene_id in {"title", "subtitle"}}
    assert texts == {"title": "Synthetic: 1 WORK PACKAGES", "subtitle": "in 1 sections"}


def test_count_range_failure_is_reported_at_its_heading_read(tmp_path):
    parts = _parts()
    parts["view"]["body"]["figureFormats"] = {"items": {"form": "kanji"}}
    with pytest.raises(RenderFailed) as caught:
        sr.render(tmp_path, sr.bunched_project(groups=1, per_group=100), presentation=parts)
    assert caught.value.code == "E_VIEW_FIGURE_FORMAT_RANGE"
    assert caught.value.source_ref == "/body/heading/title"
    assert "value=100" in caught.value.message and "range=0..99" in caught.value.message
