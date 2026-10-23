"""Relation ink keeps the shared label gap from member names and note indices (#1848 row 02 adoption).

Synthetic Projects only: nothing here reads `examples/`, so a corpus edit cannot change what is proved.
The rule is judged on a completed Scene: every painted relation stroke segment and every arrowhead keeps
`timeline.mark.labelGap` (default a quarter of the label font size, at least one pixel) from every member-name
box and note index, on whichever side of its mark the name or index lies. The three reviewer defects are the
cases: an arrowhead left of a name, a route leaving the start side of a name, an index against a bar end and
its stub.
"""
from __future__ import annotations

from datetime import date

import pytest

from tests.support import label_clearance as clearance
from tests.support import synthetic_review as sr

ENDPOINTS = [("end", "start"), ("start", "start"), ("end", "end"), ("start", "end")]
GAPS = [None, 8.0]


def _project(source_endpoint: str, target_endpoint: str):
    return sr.project(
        {"source": sr.span("source", date(2026, 1, 5), 10, owner="team-a", title="Source work item"),
         "target": sr.span("target", date(2026, 3, 2), 10, owner="team-b", title="Target work item")},
        [{"id": "dep", "type": "dependency", "lag": "0d",
          "from": {"object": "source", "endpoint": source_endpoint},
          "to": {"object": "target", "endpoint": target_endpoint}}])


def _parts(gap: float | None, *, note: bool = False, source: dict | None = None):
    parts = sr.bundle()
    parts["view"] = sr.lane_view(parts["view"], packing=("explicit",))
    parts["layout"].setdefault("relationRouting", {"maxBends": 4, "maxDetourRatio": 2})["search"] = "best"
    if gap is not None:
        theme = parts["theme"]["body"]
        theme["values"]["mark-label-gap"] = {"type": "number", "value": gap}
        theme.setdefault("metrics", {})["timeline.mark.labelGap"] = "mark-label-gap"
    if note:
        sr.with_note_rail(parts, width=300)
        sr.add_notes(source, parts["view"], ("source",), [
            sr.candidate("terminal", region={"kind": "slot", "source": "annotations"},
                         connector="none", search_kind="row-aligned")], words=0, endpoint="end")
    return parts


def _render(tmp_path, endpoints, gap, *, note=False):
    source = _project(*endpoints)
    return sr.render(tmp_path, source, presentation=_parts(gap, note=note, source=source),
                     viewport=(1800, 1100) if note else (1600, 900))


def _facts(rendered):
    primitives = rendered.surface.primitives
    return {
        "names": sorted(item.text for item in primitives if item.purpose == "member-label"),
        "indices": sorted(item.text for item in primitives if item.purpose == "note-index"),
        "stubs": [item.scene_id for item in primitives if ":stub-" in (item.scene_id or "")],
        "routes": [item for item in primitives if item.purpose == "dependency"],
    }


def _describe(items):
    return [(item.ink, item.text, item.gap, item.label_gap) for item in items]


@pytest.mark.parametrize("gap", GAPS)
@pytest.mark.parametrize("endpoints", ENDPOINTS)
def test_arrowheads_and_route_segments_keep_the_label_gap_from_member_names(tmp_path, endpoints, gap):
    """Every endpoint pairing, so the name lies left or right of the mark the ink touches."""
    rendered = _render(tmp_path, endpoints, gap)
    facts = _facts(rendered)
    gaps = clearance.scene_gaps(rendered, label_gap=gap)

    assert facts["names"] == ["Source work item", "Target work item"]
    assert facts["stubs"] == [] and len(facts["routes"]) == 1
    assert not clearance.violations(gaps), _describe(clearance.violations(gaps))


@pytest.mark.parametrize("gap", GAPS)
def test_an_arrowhead_left_of_a_name_keeps_the_gap(tmp_path, gap):
    """Defect 1: the head entering a bar from the left touched the name placed to the left of that bar."""
    rendered = _render(tmp_path, ("end", "start"), gap)
    name = next(item for item in rendered.surface.primitives if item.text == "Target work item")
    bar = next(item for item in rendered.surface.primitives
               if item.purpose == "planned" and item.source_ref == "target")
    assert name.bounds[0] + name.bounds[2] <= bar.bounds[0], "the name must lie left of its bar"
    head = next(item for item in clearance.scene_gaps(rendered, label_gap=gap)
                if item.ink == "arrowhead-end" and item.text == "Target work item")
    assert head.gap >= head.label_gap - 1e-6, head


@pytest.mark.parametrize("gap", GAPS)
def test_a_route_leaving_beside_the_start_of_a_name_keeps_the_gap(tmp_path, gap):
    """Defect 2: the stroke leaving a bar end passed against the first letter of the name right of that bar."""
    rendered = _render(tmp_path, ("end", "start"), gap)
    name = next(item for item in rendered.surface.primitives if item.text == "Source work item")
    bar = next(item for item in rendered.surface.primitives
               if item.purpose == "planned" and item.source_ref == "source")
    assert name.bounds[0] >= bar.bounds[0] + bar.bounds[2], "the name must lie right of its bar"
    stroke = next(item for item in clearance.scene_gaps(rendered, label_gap=gap)
                  if item.ink == "segment" and item.text == "Source work item")
    assert stroke.gap >= stroke.label_gap - 1e-6, stroke


NOTE_CASES = [(("start", "start"), 8.0), (("start", "end"), 8.0), (("end", "start"), 8.0), (("end", "start"), None),
              (("end", "end"), 8.0), (("end", "end"), None)]


@pytest.mark.parametrize(("endpoints", "gap"), NOTE_CASES)
def test_note_index_beside_a_bar_end_keeps_the_label_gap_from_strokes_and_arrowheads(tmp_path, endpoints, gap):
    """Defect 3: an index anchored at a bar end sat against the stub and head leaving it."""
    rendered = _render(tmp_path, endpoints, gap, note=True)
    facts = _facts(rendered)
    gaps = clearance.scene_gaps(rendered, label_gap=gap)

    assert facts["names"] == ["Source work item", "Target work item"]
    assert facts["stubs"] == [] and len(facts["routes"]) == 1
    assert facts["indices"] == ["1"], "the gap must neither drop nor add an optional index"
    assert not clearance.violations(gaps), _describe(clearance.violations(gaps))


@pytest.mark.parametrize("gap", [None, 8.0, 14.0])
@pytest.mark.parametrize(("lanes", "names"), [(False, 8), (True, 6)])
def test_a_dense_chain_keeps_every_name_and_connected_route_and_the_gap(tmp_path, lanes, names, gap):
    """Rows packed so that some ink cannot keep the gap without moving a neighbour's name: nothing is lost.

    The counts are those of the unchanged layout: the gap is a preference and never costs a name, turns a
    connected route into a stub, or drops a relation.
    """
    parts = _parts(gap)
    parts["view"] = sr.lane_view(sr.bundle()["view"]) if lanes else sr.bundle()["view"]
    rendered = sr.render(tmp_path, sr.chain_project(groups=2, per_group=4), presentation=parts)
    facts = _facts(rendered)

    assert len(facts["names"]) == names
    assert facts["stubs"] == [] and len(facts["routes"]) == 6
    assert not clearance.violations(clearance.scene_gaps(rendered, label_gap=gap))


def test_the_measurement_reports_a_touching_stroke_as_zero_and_a_clear_one_exactly():
    rect = (10.0, 10.0, 20.0, 20.0)
    assert clearance.segment_rect_distance((0.0, 15.0), (10.0, 15.0), rect) == 0.0
    assert clearance.segment_rect_distance((0.0, 15.0), (30.0, 15.0), rect) == 0.0
    assert clearance.segment_rect_distance((5.0, 0.0), (5.0, 30.0), rect) == 5.0
    assert clearance.segment_rect_distance((0.0, 0.0), (7.0, 10.0), rect) == pytest.approx(3.0)
