"""`{subject}` in a kind header is the anchored object's title, else its id (#1870 row 3)."""
from __future__ import annotations

from copy import deepcopy
from datetime import date

from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr


def _headers(tmp_path, source):
    kinds = deepcopy(ak.KINDS)
    kinds["risk"]["title"] = "{label} · {subject}"
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    ak.with_kind_theme(parts, kinds=kinds, bar=False, border_side="start", label_fill="text")
    rendered = sr.render(tmp_path, source, presentation=parts)
    return [item.text for item in rendered.surface.primitives if item.scene_id.startswith("annotation-kind-text:")]


def test_a_note_on_a_point_folded_into_a_group_header_shows_the_points_title(tmp_path):
    source = sr.project({
        "task": sr.span("task", date(2026, 1, 5), 30, owner="a", title="Build"),
        "gate": sr.point("gate", date(2026, 2, 12), owner="a", title="Design review"),
    })
    source["annotations"] = {"n0": {"kind": "risk", "text": "Sign-off pending", "anchor": {"object": "gate"}}}
    kinds = deepcopy(ak.KINDS)
    kinds["risk"]["title"] = "{label} · {subject}"
    parts = sr.bundle()
    parts["view"]["body"]["rows"] = {"mode": "automatic", "points": "group-header"}
    parts["view"]["body"]["window"] = {"mode": "explicit", "start": "2026-01-01", "end": "2026-03-01"}
    ak.with_view_notes(parts, source)
    ak.with_kind_theme(parts, kinds=kinds, bar=False, border_side="start", label_fill="text")
    rendered = sr.render(tmp_path, source, presentation=parts)

    texts = [item.text for item in rendered.surface.primitives if item.scene_id.startswith("annotation-kind-text:")]
    assert texts[0] == "RISK · Design review"


def test_an_object_with_a_title_shows_the_title_not_the_id(tmp_path):
    assert _headers(tmp_path, ak.project(("risk",)))[0] == "RISK · Task 0"

