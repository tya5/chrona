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
