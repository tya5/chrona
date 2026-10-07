"""An empty content-sized summary slot must not acquire a suppressed caption's block."""
from __future__ import annotations

from copy import deepcopy
from datetime import date

from tests.support import synthetic_review as sr


CAPTION = "slot-heading:summary"
ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
          "body": {"asOf": "2026-02-20", "observations": []}}
SLOT = {"id": "summary", "kind": "slot", "source": "summary", "inlineSize": "content",
        "blockSize": "content", "place": {"inline": "start", "block": "start", "safety": "safe"},
        "priority": "preferred", "overflow": "ellipsize-with-source"}


def _with_heading_role(parts):
    body = parts["theme"]["body"]
    body["values"].update({
        "slot-heading-size": {"type": "number", "value": 11},
        "slot-heading-weight": {"type": "fontWeight", "value": 700},
        "slot-heading-spacing": {"type": "number", "value": 0.1},
        "slot-heading-transform": {"type": "textTransform", "value": "uppercase"}})
    body["roles"]["slot-heading"] = {
        **body["roles"]["text"], "fontWeight": "slot-heading-weight", "fontSize": "slot-heading-size",
        "letterSpacing": "slot-heading-spacing", "textTransform": "slot-heading-transform"}


def _render(tmp_path, name, *, panels, headed):
    directory = tmp_path / name
    directory.mkdir()
    parts = sr.bundle("control-room-dark")
    parts["view"]["body"]["figures"] = [{"id": "countdown", "kind": "daysUntil",
                                         "to": {"period": "window", "side": "start"}}]
    node = deepcopy(SLOT)
    if headed:
        node["heading"] = {"text": "Figures"}
        _with_heading_role(parts)
    parts["layout"]["root"]["children"].insert(1, node)
    profile = ({"version": "chrona/summary-profile/v0.1", "kind": "summary-profile", "id": "figures",
                "body": {"panels": panels}} if panels is not None else None)
    source = sr.project({"a": sr.span("a", date(2026, 1, 5), 40),
                         "launch": sr.point("launch", date(2026, 3, 20), owner="b")})
    source["periods"] = {"window": {"title": "Window", "start": {"object": "launch", "endpoint": "at"},
                                    "end": "2026-03-30"}}
    return sr.render(directory, source, presentation=parts, actual=ACTUAL, summary=profile)


def _slot(rendered):
    return next(slot for slot in rendered.surface.slots if slot.slot_id == "summary")


def test_empty_content_sized_summary_does_not_reserve_a_suppressed_heading(tmp_path):
    plain = _render(tmp_path, "empty-plain", panels=None, headed=False)
    headed = _render(tmp_path, "empty-headed", panels=None, headed=True)

    assert _slot(headed).bounds == _slot(plain).bounds
    assert CAPTION not in {item.scene_id for item in headed.surface.primitives}
    assert "I_LAYOUT_SLOT_HEADING_OMITTED:summary:no-content" in headed.surface.diagnostics
    assert headed.artifact.content == plain.artifact.content


def test_nonempty_content_sized_summary_still_reserves_and_draws_its_heading(tmp_path):
    panels = [{"id": "key", "title": "Key figures", "presentation": "figures", "metrics": [
        {"id": "countdown", "source": {"figure": "countdown"}, "label": "DAYS", "format": "count"}]}]
    plain = _render(tmp_path, "filled-plain", panels=panels, headed=False)
    headed = _render(tmp_path, "filled-headed", panels=panels, headed=True)

    caption = next(item for item in headed.surface.primitives if item.scene_id == CAPTION)
    summary_runs = [item for item in headed.surface.primitives if item.scene_id.startswith("summary:")]
    assert summary_runs and all(item.bounds[1] >= caption.bounds[1] + caption.bounds[3] for item in summary_runs)
    assert _slot(headed).bounds[3] > _slot(plain).bounds[3]
    assert b">FIGURES<" in headed.artifact.content


def _render_consumed_note(tmp_path, name, *, headed):
    directory = tmp_path / name
    directory.mkdir()
    parts = sr.bundle("executive-light")
    sr.with_note_rail(parts)
    if headed:
        _with_heading_role(parts)
    notes_slot = sr.find_node(parts["layout"], "notes")
    notes_slot["blockSize"] = "content"
    if headed:
        notes_slot["heading"] = {"text": "Notes"}
    source = sr.project({"a": sr.span("a", date(2026, 2, 2), 30)})
    sr.add_notes(source, parts["view"], ["a"],
                 [sr.candidate("rail", region={"kind": "slot", "source": "annotations"},
                               connector="leader", search_kind="row-aligned")], words=0)
    return sr.render(directory, source, presentation=parts)


def test_consumed_project_note_does_not_reserve_a_heading_in_empty_notes_slot(tmp_path):
    plain = _render_consumed_note(tmp_path, "notes-plain", headed=False)
    headed = _render_consumed_note(tmp_path, "notes-headed", headed=True)
    plain_slot = next(slot for slot in plain.surface.slots if slot.slot_id == "notes")
    headed_slot = next(slot for slot in headed.surface.slots if slot.slot_id == "notes")

    assert headed_slot.bounds == plain_slot.bounds
    assert "slot-heading:notes" not in {item.scene_id for item in headed.surface.primitives}
    assert "I_LAYOUT_SLOT_HEADING_OMITTED:notes:no-content" in headed.surface.diagnostics
    assert headed.scene.manifest.content_family_counts.annotations == 1
    assert headed.scene.manifest.content_family_counts.notes == 0
    assert headed.artifact.content == plain.artifact.content


def _render_empty_legend(tmp_path, name, *, headed):
    directory = tmp_path / name
    directory.mkdir()
    parts = sr.bundle("executive-light")
    legend_slot = sr.find_node(parts["layout"], "legend")
    legend_slot["blockSize"] = "content"
    if headed:
        legend_slot["heading"] = {"text": "Key"}
        _with_heading_role(parts)
    source = sr.project({"a": sr.span("a", date(2026, 2, 2), 30)})
    return sr.render(directory, source, presentation=parts)


def test_empty_legend_placeholder_does_not_reserve_a_suppressed_heading(tmp_path):
    plain = _render_empty_legend(tmp_path, "legend-plain", headed=False)
    headed = _render_empty_legend(tmp_path, "legend-headed", headed=True)
    plain_slot = next(slot for slot in plain.surface.slots if slot.slot_id == "legend")
    headed_slot = next(slot for slot in headed.surface.slots if slot.slot_id == "legend")

    assert headed_slot.bounds == plain_slot.bounds
    assert "slot-heading:legend" not in {item.scene_id for item in headed.surface.primitives}
    assert "I_LAYOUT_SLOT_HEADING_OMITTED:legend:no-content" in headed.surface.diagnostics
    assert headed.scene.manifest.content_family_counts.legend_entries == 0
    assert headed.artifact.content == plain.artifact.content


def test_empty_timeline_axis_does_not_reserve_a_heading(tmp_path):
    def render(name, headed):
        directory = tmp_path / name
        directory.mkdir()
        parts = sr.bundle("executive-light")
        parts["view"]["body"].pop("axis")
        axis = sr.find_node(parts["layout"], "timeline-axis")
        if headed:
            axis["heading"] = {"text": "Calendar"}
        source = sr.project({"a": sr.span("a", date(2026, 2, 2), 30)})
        return sr.render(directory, source, presentation=parts)

    plain = render("axis-plain", headed=False)
    headed = render("axis-headed", headed=True)
    plain_slot = next(slot for slot in plain.surface.slots if slot.slot_id == "timeline-axis")
    headed_slot = next(slot for slot in headed.surface.slots if slot.slot_id == "timeline-axis")

    assert headed_slot.bounds == plain_slot.bounds
    assert "slot-heading:timeline-axis" not in {item.scene_id for item in headed.surface.primitives}
    assert "I_LAYOUT_SLOT_HEADING_OMITTED:timeline-axis:no-content" in headed.surface.diagnostics
    assert headed.artifact.content == plain.artifact.content
