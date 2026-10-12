"""Count completed producer occurrences, not indexes, kind bars or Scene ID patterns (#1346)."""
from copy import deepcopy
from datetime import date

import pytest

from tests.integration.test_annotation_list_status import _fixture
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr


def _capture(monkeypatch):
    from chrona.presentation import surface_pipeline as pipeline
    project = pipeline.project_review_surface
    completed = []
    def observe(value):
        value.completion.placement.assert_valid()
        completed.append(value.completion.placement)
        return project(value)
    monkeypatch.setattr(pipeline, "project_review_surface", observe)
    return completed


def test_index_kind_and_subject_fragments_add_no_narrative_occurrences(tmp_path, monkeypatch):
    captured = _capture(monkeypatch)
    source = ak.project()
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    ak.with_kind_theme(parts)
    rendered = sr.render(tmp_path, source, presentation=parts)
    receipts = captured[0].narrative_receipts
    assert len(receipts) == 2
    assert {(r.kind, r.source_id, r.form) for r in receipts} == {
        ("annotation", "view-n0", "body"), ("annotation", "view-n1", "body")}
    assert len(rendered.surface.primitives) > len(receipts)
    assert any(p.scene_id.startswith("annotation-kind-text:") for p in rendered.surface.primitives)


def test_two_explicit_references_to_one_project_note_are_two_completed_occurrences(tmp_path, monkeypatch):
    captured = _capture(monkeypatch)
    source = ak.project(kinds=("risk",))
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    duplicate = deepcopy(parts["view"]["body"]["annotations"][0])
    duplicate["id"] = "second-occurrence"
    parts["view"]["body"]["annotations"].append(duplicate)
    sr.render(tmp_path, source, presentation=parts)
    receipts = captured[0].narrative_receipts
    assert len(receipts) == 2
    assert {r.identity for r in receipts} == {
        ("annotation", "view-n0", 0), ("annotation", "second-occurrence", 0)}


def test_unconsumed_notes_are_counted_by_their_note_producer(tmp_path, monkeypatch):
    captured = _capture(monkeypatch)
    source = sr.project({"a": sr.span("a", date(2026, 2, 2), 20)})
    source["annotations"] = {key: {"kind": "note", "text": "Unconsumed narrative.", "anchor": {"object": "a"}}
                             for key in ("", "two")}
    sr.render(tmp_path, source, presentation=sr.bundle())
    receipts = captured[0].narrative_receipts
    assert {(r.kind, r.source_id, r.form, r.occurrence_index) for r in receipts} == {
        ("note", "", "body", 0), ("note", "two", "body", 1)}


@pytest.mark.parametrize("numbered", [True, False])
def test_completed_rail_summary_counts_once_while_suppressed_body_does_not(tmp_path, monkeypatch, numbered):
    from chrona.presentation.layout import surface_annotations
    captured = _capture(monkeypatch)
    source, parts = _fixture()
    sr.with_note_rail(parts, width=300)
    parts["view"]["body"]["visibility"]["annotations"]["marker"] = "numbered" if numbered else "none"
    parts["view"]["body"]["visibility"].setdefault("fallback", {})["annotations"] = ["end", "suppress"]
    annotation = parts["view"]["body"]["annotations"][2]
    annotation.pop("candidates")
    annotation["placement"] = {"side": "end", "alignment": "center"}
    original = surface_annotations.project_annotation_box
    def suppress(annotation, *args, **kwargs):
        return None if annotation.annotation_id == "note-2" else original(annotation, *args, **kwargs)
    monkeypatch.setattr(surface_annotations, "project_annotation_box", suppress)
    rendered = sr.render(tmp_path, source, presentation=parts, viewport=(2400, 1400))
    receipts = captured[0].narrative_receipts
    expected = {("note-0", "body"), ("note-1", "body"), ("note-3", "body")}
    if numbered:
        expected.add(("note-2", "summary"))
    assert len(receipts) == len(expected)
    assert {(r.source_id, r.form) for r in receipts} == expected
    assert "W_LAYOUT_ANNOTATION_SUPPRESSED:annotation:note-2" in rendered.surface.diagnostics


def test_no_narrative_has_no_receipts_even_though_titles_and_labels_are_drawn(tmp_path, monkeypatch):
    captured = _capture(monkeypatch)
    sr.render(tmp_path, sr.project({"a": sr.span("a", date(2026, 2, 2), 20)}))
    assert captured[0].text and captured[0].narrative_receipts == ()
