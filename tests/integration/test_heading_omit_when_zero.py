"""Conditional heading copy is resolved before Layout measures it (#1608)."""
from datetime import date
from copy import deepcopy

import pytest

from chrona.presentation.model.closure import ClosureError
from tests.integration.test_heading_counts import _parts
from tests.integration.test_placed_note_count_closure import _capture, _late
from tests.integration.test_slot_heading import _render
from tests.support import synthetic_review as sr


def _subtitle_role(parts):
    body = parts["theme"]["body"]
    body["roles"]["subtitle"] = deepcopy(body["roles"]["heading"])
    body["colorBindings"]["subtitle.fill"] = "text"
    body["roles"]["kicker"] = deepcopy(body["roles"]["heading"])
    body["colorBindings"]["kicker.fill"] = "text"


@pytest.mark.parametrize("grouped", [False, True])
@pytest.mark.parametrize("split", [False, True])
@pytest.mark.parametrize("member", ["title", "subtitle", "kicker"])
def test_count_part_is_drawn_at_one_omitted_at_zero_before_measurement(tmp_path, monkeypatch, grouped, split, member):
    from chrona.presentation.layout import surface_render_plan as planner
    parts = _parts()
    _subtitle_role(parts)
    parts["view"]["body"]["heading"] = {
        "title": "Plan", member: [{"text": "in {figure:groups} panels", "omitWhenZero": "groups"}]}
    if not grouped:
        parts["view"]["body"]["grouping"] = {"by": "none", "missing": "ungrouped"}
    if split:
        title = parts["layout"]["root"]["children"][0]
        parts["layout"]["root"]["children"][0:1] = [
            dict(title, id=f"heading-{part}", source=f"heading.{part}") for part in dict.fromkeys(("title", member))]
    observed = []
    original = planner.measure_sources
    def measure(inputs, *args, **kwargs):
        observed.extend(line for value in inputs.values() for line in value.lines)
        return original(inputs, *args, **kwargs)
    monkeypatch.setattr(planner, "measure_sources", measure)
    source = sr.project({"a": sr.span("a", date(2026, 2, 2), 5, owner="one")})
    rendered = sr.render(tmp_path, source, presentation=parts)
    subtitles = [p.text for p in rendered.surface.primitives if p.scene_id == member]
    assert subtitles == (["in one panels"] if grouped else [])
    assert ("in one panels" in observed) == grouped
    assert not any("zero panels" in line for line in observed)
    assert not any("HEADING_PART_OMITTED" in item for item in rendered.surface.diagnostics)


def test_zero_omission_preserves_literal_concatenation_and_other_parts(tmp_path):
    parts = _parts()
    parts["view"]["body"]["grouping"] = {"by": "none", "missing": "ungrouped"}
    parts["view"]["body"]["heading"] = {"title": [
        {"text": "{project}"}, {"text": " · in {figure:groups} panels", "omitWhenZero": "groups"},
        {"text": " / {{literal}}"}]}
    rendered = sr.render(tmp_path, sr.project({"a": sr.span("a", date(2026, 2, 2), 5)}), presentation=parts)
    assert next(p.text for p in rendered.surface.primitives if p.scene_id == "title") == "Synthetic / {literal}"


@pytest.mark.parametrize("remaining", ["subtitle", "kicker"])
def test_omitted_title_does_not_rename_or_remove_other_heading_members(tmp_path, remaining):
    parts = _parts()
    _subtitle_role(parts)
    parts["view"]["body"]["grouping"] = {"by": "none", "missing": "ungrouped"}
    parts["view"]["body"]["heading"] = {
        "title": [{"text": "Absent", "omitWhenZero": "groups"}], remaining: "Remaining"}
    rendered = sr.render(tmp_path, sr.project({"a": sr.span("a", date(2026, 2, 2), 5)}), presentation=parts)
    texts = {p.scene_id: p.text for p in rendered.surface.primitives if p.kind == "Text"}
    assert "title" not in texts
    assert texts[remaining] == "Remaining"


@pytest.mark.parametrize("figure,code", [
    ("unknown", "E_VIEW_FIGURE_UNKNOWN"), ("days", "E_VIEW_FIGURE_INVALID"),
    ("local", "E_FIGURE_SCOPE_UNAVAILABLE")])
def test_guard_reference_uses_existing_typed_figure_diagnostic(tmp_path, figure, code):
    parts = _parts()
    parts["view"]["body"]["figures"].extend([
        {"id": "days", "kind": "daysUntil", "to": "asOf"},
        {"id": "local", "kind": "count", "source": "selected", "scope": "group"}])
    parts["view"]["body"]["heading"] = {"subtitle": [{"text": "Visible", "omitWhenZero": figure}]}
    with pytest.raises(ClosureError) as caught:
        sr.render(tmp_path, sr.project({"a": sr.span("a", date(2026, 2, 2), 5)}), presentation=parts)
    assert caught.value.diagnostic_id == code
    assert caught.value.source_ref == "/body/heading/subtitle/0/omitWhenZero"


@pytest.mark.parametrize("notes", [False, True])
def test_guard_without_placeholder_participates_in_deferred_count_closure(tmp_path, monkeypatch, notes):
    completed = _capture(monkeypatch)
    def configure(parts):
        _late(parts)
        _subtitle_role(parts)
        parts["view"]["body"]["heading"] = {"title": "Plan", "subtitle": [
            {"text": "Notes are present", "omitWhenZero": "notes"}]}
    rendered = _render(tmp_path, configure=configure, notes=notes)
    assert [p.text for p in rendered.surface.primitives if p.scene_id == "subtitle"] == (
        ["Notes are present"] if notes else [])
    assert completed[0].trials[-1].outcome == "accepted"
    assert dict(completed[0].projection.figures)["notes"] == (3 if notes else 0)
