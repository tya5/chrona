"""Synthetic integration coverage for the #1581 opposite-as-of fallback."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from chrona.presentation.layout import surface_annotations
from tests.support import synthetic_review as sr


AS_OF_VERSION = "chrona/actual-set/v0.3"


def _render(tmp_path, *, as_of: date):
    start = date(2026, 1, 5)
    source = sr.project({
        "anchor": sr.span("anchor", start, 2, title="Early anchor"),
        "later": sr.span("later", start + timedelta(days=150), 5, title="Later milestone"),
    })
    parts = sr.bundle()
    sr.with_balloon_notes(parts)
    sr.add_notes(source, parts["view"], ["anchor"],
                 [sr.candidate("only-candidate", connector="tail")], endpoint="finish")
    actual = {
        "version": AS_OF_VERSION,
        "kind": "actual-set",
        "id": "synthetic-as-of",
        "body": {"asOf": as_of.isoformat(), "observations": []},
    }
    return sr.render(tmp_path, source, presentation=parts, actual=actual,
                     visual_profile="chrona-output/visual/v0.6-svg")


def _primitives(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives}


def test_blocked_anchor_side_uses_other_side_with_exact_candidate_and_one_crossing(tmp_path):
    rendered = _render(tmp_path, as_of=date(2026, 1, 10))
    primitives = _primitives(rendered)
    box = primitives["annotation-box:note-0"]
    leader = primitives["annotation-leader:note-0"]
    as_of = primitives["as-of"]

    assert any(item == "W_LAYOUT_ANNOTATION_AS_OF_OTHER_SIDE:note-0:only-candidate:other-side-of-as-of"
               for item in rendered.scene.diagnostics)
    assert leader.points
    rule_x = as_of.points[0][0]
    assert box.bounds[0] > rule_x
    points = leader.points
    crossings = [
        (left, right) for left, right in zip(points, points[1:])
        if left[1] == right[1] and min(left[0], right[0]) < rule_x < max(left[0], right[0])
    ]
    assert len(crossings) == 1
    assert not any(item.startswith("W_LAYOUT_ANNOTATION_ROUTE_SEARCH_EXHAUSTED:note-0")
                   for item in rendered.scene.diagnostics)
    assert not any(item.startswith("W_LAYOUT_LABEL_OVERFLOW:annotation-text:note-0")
                   for item in rendered.scene.diagnostics)


def test_feasible_anchor_side_keeps_the_original_candidate_placement(tmp_path, monkeypatch):
    def reject_opposite_pass(*_args, **_kwargs):
        pytest.fail("a feasible anchor-side placement must not invoke the opposite-side pass")

    monkeypatch.setattr(surface_annotations, "nearest_free_routed_tail_box", reject_opposite_pass)
    rendered = _render(tmp_path, as_of=date(2026, 5, 1))
    primitives = _primitives(rendered)
    box = primitives["annotation-box:note-0"]
    as_of = primitives["as-of"]

    assert box
    assert box.bounds[0] == pytest.approx(506.4)  # existing nearest anchor-side candidate
    assert box.bounds[0] + box.bounds[2] < as_of.points[0][0]
    assert "W_LAYOUT_ANNOTATION_AS_OF_OTHER_SIDE:note-0:only-candidate:other-side-of-as-of" not in rendered.scene.diagnostics
    assert "W_LAYOUT_ANNOTATION_CANDIDATE_FALLBACK:note-0:only-candidate" not in rendered.scene.diagnostics
    assert not any(item.startswith("W_LAYOUT_LABEL_OVERFLOW:annotation-text:note-0")
                   for item in rendered.scene.diagnostics)
