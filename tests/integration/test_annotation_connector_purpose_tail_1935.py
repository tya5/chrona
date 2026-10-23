"""A routed tail on a purpose without a leader style is named, not dropped (#1935)."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from tests.support import synthetic_review as sr

CODE = "W_LAYOUT_ANNOTATION_CONNECTOR_UNSUPPORTED_FOR_PURPOSE"
AS_OF = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "synthetic-as-of",
         "body": {"asOf": date(2026, 1, 10).isoformat(), "observations": []}}


def _render(tmp_path, purpose):
    start = date(2026, 1, 5)
    source = sr.project({
        "anchor": sr.span("anchor", start, 2, title="Early anchor"),
        "later": sr.span("later", start + timedelta(days=150), 5, title="Later milestone"),
    })
    parts = sr.bundle()
    sr.with_balloon_notes(parts)
    parts["theme"]["body"]["roles"]["annotation-highlight-box"]["annotationContainer"] = "balloon-container"
    sr.add_notes(source, parts["view"], ["anchor"], [sr.candidate("only", connector="tail")], endpoint="finish")
    parts["view"]["body"]["annotations"][0]["purpose"] = purpose
    return sr.render(tmp_path, source, presentation=parts, actual=AS_OF,
                     visual_profile="chrona-output/visual/v0.6-svg")


@pytest.mark.parametrize("purpose,named", [("note", False), ("highlight", True)])
def test_routed_tail_is_drawn_for_a_leader_style_and_named_for_a_highlight(tmp_path, purpose, named):
    rendered = _render(tmp_path, purpose)
    ids = {item.scene_id for item in rendered.surface.primitives}
    # The as-of rule forces the opposite-side routed-tail pass for this fixture.
    assert "W_LAYOUT_ANNOTATION_AS_OF_OTHER_SIDE:note-0:only:other-side-of-as-of" in rendered.scene.diagnostics
    assert "annotation-box:note-0" in ids and "annotation-text:note-0" in ids
    warned = [item for item in rendered.scene.diagnostics if item.startswith(CODE)]
    if named:
        assert warned == [f"{CODE}:note-0:highlight:tail"]
    else:
        assert warned == []
        assert "annotation-leader:note-0" in ids
