"""A Project annotation on a drawn target is drawn or named in a warning (#1870 row 1)."""
from __future__ import annotations

from datetime import date

from tests.support import synthetic_review as sr

CODE = "W_PRESENTATION_ANNOTATION_NOT_DRAWN"
POLICY = {"note": {"placement": {"side": "end", "alignment": "center"}}}
SPAN_NOTE = {"kind": "note", "temporalKind": "span", "purpose": "note", "facet": "planned", "endpoint": "end"}


def _drop_notes_slot(node):
    if "children" in node:
        node["children"] = [child for child in node["children"] if child.get("id") != "notes"]
        for child in node["children"]:
            _drop_notes_slot(child)


def _render(tmp_path, *, bindings, notes_slot, mode="presentation"):
    parts = sr.bundle("executive-light")
    body = parts["view"]["body"]
    body["annotationBindings"] = bindings
    body["annotationPlacement"] = POLICY
    body["visibility"]["annotations"] = {"mode": mode, "marker": "numbered"} if mode != "none" else "none"
    if not notes_slot:
        _drop_notes_slot(parts["layout"]["root"])
    project = sr.project({"task": sr.span("task", date(2026, 1, 5), 12), "gate": sr.point("gate", date(2026, 1, 9))})
    project["annotations"] = {
        "n1": {"kind": "note", "text": "Task note", "anchor": {"object": "task"}},
        "r1": {"kind": "risk", "text": "Gate risk", "anchor": {"object": "gate"}},
        "x1": {"kind": "note", "text": "Elsewhere", "anchor": {"object": "absent"}},
    }
    rendered = sr.render(tmp_path, project, presentation=parts)
    return [item.payload for item in rendered.warning_records if item.payload.get("code") == CODE]


def test_a_note_matching_no_binding_is_named_with_id_kind_and_target(tmp_path):
    warnings = _render(tmp_path, bindings=[SPAN_NOTE], notes_slot=False)

    assert [item["diagnostic"] for item in warnings] == [
        CODE + ':{"annotation":"r1","kind":"risk","target":"gate","targetShape":"point"}']
    assert warnings[0]["severity"] == "warning"
    assert "risk r1 on gate" in warnings[0]["message"]
    assert "annotationBindings" in warnings[0]["message"]
    assert "no further detail" not in warnings[0]["message"]


def test_no_bindings_at_all_names_every_note_on_a_drawn_target(tmp_path):
    warnings = _render(tmp_path, bindings=[], notes_slot=False)

    assert [item["diagnostic"].split('"annotation":"')[1].split('"')[0] for item in warnings] == ["n1", "r1"]


def test_a_notes_slot_draws_the_left_over_notes_so_nothing_is_reported(tmp_path):
    assert _render(tmp_path, bindings=[SPAN_NOTE], notes_slot=True) == []


def test_hidden_annotations_are_the_authors_choice_and_not_reported(tmp_path):
    assert _render(tmp_path, bindings=[SPAN_NOTE], notes_slot=False, mode="none") == []
