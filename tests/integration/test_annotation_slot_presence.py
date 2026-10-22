"""Optional side slots consume allocation only when their resolved content is present (#1597)."""
from __future__ import annotations

from datetime import date
from math import isclose

import pytest

from chrona.presentation.layout import surface_composer
from chrona.presentation.layout.surface_quality import NarrativeReceipt
from chrona.usecases.render_review import RenderFailed
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


def _terminal_list_candidate(candidate_id="memo-list"):
    return sr.candidate(candidate_id, region={"kind": "slot", "source": "annotations"},
                        connector="none", search_kind="row-aligned")


def _literal_note(parts, *, text, candidate):
    body = parts["view"]["body"]
    body["visibility"]["annotations"] = {"mode": "presentation", "marker": "none"}
    body["annotations"] = [{
        "id": "literal-note", "purpose": "note", "text": text,
        "anchor": {"kind": "object", "id": "a", "facet": "planned", "endpoint": "body"},
        "candidates": [candidate],
    }]


def _remove_slot(node, slot_id):
    if "children" not in node:
        return
    node["children"] = [item for item in node["children"] if item.get("id") != slot_id]
    for item in node["children"]:
        _remove_slot(item, slot_id)


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


def test_unnumbered_terminal_list_keeps_body_once_without_fabricated_leader(tmp_path, monkeypatch):
    source = _project()
    parts = _parts(annotation_rail=True)
    text = "An unnumbered note keeps this complete sentence."
    _literal_note(parts, text=text, candidate=_terminal_list_candidate("not-a-rail-id"))
    captured = []
    original = surface_composer.complete_route_annotations

    def capture(plan, context):
        result = original(plan, context)
        captured.append(result)
        return result

    monkeypatch.setattr(surface_composer, "complete_route_annotations", capture)
    rendered = _render(tmp_path, source, parts)

    list_text = [item for item in rendered.surface.primitives
                 if item.scene_id == "annotation-list:literal-note"]
    assert len(list_text) == 1 and list_text[0].text == text
    assert not any(item.scene_id.startswith("annotation-leader:literal-note")
                   for item in rendered.surface.primitives)
    assert captured[-1].narrative_receipts == (
        NarrativeReceipt("annotation", "literal-note", "annotation-list:literal-note", "summary"),)


def test_nonfitting_terminal_list_emits_named_overflow_and_retains_full_body(tmp_path):
    source = _project()
    parts = _parts(annotation_rail=True)
    long_text = "The complete unnumbered note remains present even when the declared list slot is far too small."
    _literal_note(parts, text=long_text, candidate=_terminal_list_candidate("end-of-list"))
    parts["theme"]["body"]["values"]["note-rail-width"]["value"] = 24

    rendered = _render(tmp_path, source, parts)

    list_text = [item for item in rendered.surface.primitives
                 if item.scene_id == "annotation-list:literal-note"]
    assert len(list_text) == 1 and list_text[0].text == long_text
    overflow = [item for item in rendered.surface.fit_warnings
                if item.placement_id == "annotation-list:literal-note"]
    assert len(overflow) == 1 and overflow[0].behaviour == "visible-overflow"


@pytest.mark.parametrize("automatic", [False, True], ids=["explicit", "automatic-policy"])
def test_terminal_list_without_declared_slot_fails_at_placement_source(tmp_path, automatic):
    source = _project()
    parts = _parts()
    _remove_slot(parts["layout"]["root"], "annotations")
    terminal = _terminal_list_candidate("not-a-rail-id")
    if automatic:
        source["annotations"] = {"note-a": {
            "kind": "note", "text": "An auto-expanded note.", "anchor": {"object": "a"}}}
        body = parts["view"]["body"]
        body["visibility"]["annotations"] = {"mode": "presentation", "marker": "numbered"}
        body.pop("annotations", None)
        body["annotationBindings"] = [{
            "kind": "note", "temporalKind": "span", "purpose": "note",
            "facet": "planned", "endpoint": "body"}]
        parts["layout"].setdefault("viewDefaults", {})["annotationPlacement"] = {
            "note": {"candidates": [terminal]}}
        expected_source = "/body/annotationPlacement/note"
    else:
        _literal_note(parts, text="An explicit note.", candidate=terminal)
        expected_source = "/body/annotations/0/candidates"

    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, source, parts)

    assert raised.value.code == "E_LAYOUT_ANNOTATION_FALLBACK_REQUIRED"
    assert raised.value.source_ref == expected_source


def test_blocked_leader_candidates_retain_note_in_safe_terminal_list(tmp_path, monkeypatch):
    from chrona.presentation.layout import surface_annotations

    source = _project()
    parts = _parts(annotation_rail=True)
    body = parts["view"]["body"]
    text = "The note remains in the explicitly declared list."
    _literal_note(parts, text=text, candidate=sr.candidate(
        "blocked-leader", region={"kind": "slot", "source": "annotations"},
        connector="leader", search_kind="row-aligned"))
    body["annotations"][0]["candidates"].append(_terminal_list_candidate("final-list"))

    monkeypatch.setattr(surface_annotations, "route_annotation_candidate", lambda *_args, **_kwargs: None)
    rendered = _render(tmp_path, source, parts)
    primitives = rendered.surface.primitives

    assert any(item.scene_id == "annotation-list:literal-note" and item.text == text
               for item in primitives)
    assert not any(item.scene_id == "annotation-leader:literal-note" for item in primitives)


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


@pytest.mark.parametrize("mode", ["none", "presentation"])
def test_empty_required_annotation_source_is_available_then_omitted(tmp_path, mode):
    parts = _parts(annotation_rail=True)
    sr.find_node(parts["layout"], "annotations")["priority"] = "required"
    parts["view"]["body"]["visibility"]["annotations"] = {"mode": mode, "marker": "none"}

    rendered = _render(tmp_path, _project(), parts)

    assert _slot(rendered, "annotations") is None
    assert _timeline(rendered).bounds[2] > 300


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

