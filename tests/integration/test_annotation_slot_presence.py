"""Optional side slots consume allocation only when their resolved content is present (#1597)."""
from __future__ import annotations

from datetime import date
from math import isclose

from tests.support import synthetic_review as sr


def _parts(*, annotation_rail: bool = False, side_legend: bool = False):
    parts = sr.bundle("executive-light")
    root = parts["layout"]["root"]
    review = next(item for item in root["children"] if item["id"] == "review")
    if annotation_rail:
        slot = next(item for item in root["children"] if item["id"] == "annotations")
        root["children"].remove(slot)
        slot.update(inlineSize={"fixed": {"token": "note-rail-width"}}, blockSize="fill",
                    place={"inline": "stretch", "block": "stretch", "safety": "strict"})
        parts["layout"]["requiredThemeTokens"] = sorted(
            {*parts["layout"]["requiredThemeTokens"], "note-rail-width"})
        parts["theme"]["body"]["values"]["note-rail-width"] = {"type": "number", "value": 300}
        review["children"].append(slot)
    if side_legend:
        footer = next(item for item in root["children"] if item["id"] == "footer")
        slot = next(item for item in footer["children"] if item["id"] == "legend")
        footer["children"].remove(slot)
        slot.update(inlineSize="content", blockSize="fill",
                    place={"inline": "stretch", "block": "stretch", "safety": "strict"})
        review["children"].append(slot)
    return parts


def _rail_candidate():
    return sr.candidate("rail", region={"kind": "slot", "source": "annotations"},
                        connector="leader", search_kind="row-aligned")


def _render(tmp_path, source, parts, *, detail=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    return sr.render(tmp_path, source, presentation=parts, detail=detail)


def _slot(rendered, source):
    return next((item for item in rendered.surface.slots if item.source == source), None)


def _timeline(rendered):
    return _slot(rendered, "timeline")


def _project():
    return sr.project({"a": sr.span("a", date(2026, 2, 2), 30, title="Task")})


def test_resolved_view_note_keeps_the_rail_and_empty_selection_releases_it(tmp_path):
    source = _project()
    parts = _parts(annotation_rail=True)
    sr.add_notes(source, parts["view"], ["a"], [_rail_candidate()], words=0)
    present = _render(tmp_path / "present", source, parts)

    absent_parts = _parts(annotation_rail=True)
    absent_parts["view"]["body"]["visibility"]["annotations"] = {
        "mode": "presentation", "marker": "none"}
    absent = _render(tmp_path / "absent", _project(), absent_parts)

    present_rail, absent_rail = _slot(present, "annotations"), _slot(absent, "annotations")
    assert present_rail is not None and present_rail.bounds[2] == 300
    assert absent_rail is None
    assert _timeline(absent).bounds[2] > _timeline(present).bounds[2]
    assert isclose(_timeline(absent).bounds[0] + _timeline(absent).bounds[2],
                   present_rail.bounds[0] + present_rail.bounds[2])


def test_literal_view_note_keeps_the_rail_without_a_project_note(tmp_path):
    source = _project()
    parts = _parts(annotation_rail=True)
    parts["view"]["body"]["visibility"]["annotations"] = {"mode": "presentation", "marker": "none"}
    parts["view"]["body"]["annotations"] = [{
        "id": "literal-note", "purpose": "note", "text": "A View-local note.",
        "anchor": {"kind": "object", "id": "a", "facet": "planned", "endpoint": "body"},
        "candidates": [_rail_candidate()],
    }]

    rendered = _render(tmp_path, source, parts)

    assert "annotations" not in source
    assert _slot(rendered, "annotations") is not None
    assert any(item.scene_id == "annotation-text:literal-note" for item in rendered.surface.primitives)


def test_project_note_filtered_out_of_resolved_view_releases_the_rail(tmp_path):
    source = _project()
    source["annotations"] = {"unmatched": {"kind": "note", "text": "Not selected.",
                                             "anchor": {"object": "a"}}}
    parts = _parts(annotation_rail=True)
    body = parts["view"]["body"]
    body["visibility"]["annotations"] = {"mode": "presentation", "marker": "none"}
    body["annotations"] = []
    body["annotationBindings"] = [{"kind": "risk", "temporalKind": "span", "purpose": "note",
                                    "facet": "planned", "endpoint": "body"}]
    body["annotationPlacement"] = {"note": {"placement": {"side": "end", "alignment": "center"}}}

    rendered = _render(tmp_path, source, parts)

    assert _slot(rendered, "annotations") is None
    assert _timeline(rendered).bounds[2] > 300


def test_hidden_view_note_does_not_reserve_a_rail(tmp_path):
    source = _project()
    parts = _parts(annotation_rail=True)
    sr.add_notes(source, parts["view"], ["a"], [_rail_candidate()], words=0)
    parts["view"]["body"]["visibility"]["annotations"] = {"mode": "none", "marker": "none"}

    rendered = _render(tmp_path, source, parts)

    assert _slot(rendered, "annotations") is None
    assert not any(item.purpose == "annotation" for item in rendered.surface.primitives)


def test_empty_and_nonempty_side_legend_only_allocate_when_entries_exist(tmp_path):
    parts = _parts(side_legend=True)
    empty = _render(tmp_path / "empty", _project(), parts)

    populated = _render(tmp_path / "populated", _project(), _parts(side_legend=True),
                        detail={"version": "chrona/review-detail-profile/v0.1", "id": "key",
                                "body": {"legend": [{"role": "planned", "label": "Planned"}]}})

    assert _slot(empty, "legend") is None
    assert _slot(populated, "legend") is not None
    assert any(item.scene_id == "legend:planned" for item in populated.surface.primitives)
    assert _timeline(empty).bounds[2] > _timeline(populated).bounds[2]

