"""Production Scene and SVG acceptance, independent of the example corpus."""
from datetime import date
import xml.etree.ElementTree as ET

import pytest

from tests.support import synthetic_review as sr


def _source():
    return sr.project({
        "before": sr.span("before", date(2026, 1, 1), 2),
        "across": sr.span("across", date(2026, 1, 1), 14),
        "after": sr.span("after", date(2026, 1, 12), 2),
        "early-gate": sr.point("early-gate", date(2026, 1, 2)),
        "gate": sr.point("gate", date(2026, 1, 6)),
        "late-gate": sr.point("late-gate", date(2026, 1, 12)),
    })


def _parts(lanes):
    parts = sr.bundle()
    if lanes:
        parts["view"] = sr.lane_view(parts["view"], packing=("explicit",))
    else:
        body = parts["view"]["body"]
        body["rows"] = {"mode": "automatic"}
        body["visibility"]["labels"]["placement"] = "table"
        body["tableColumns"] = [{"id": "Task", "source": "title", "missing": "em-dash",
            "align": "start", "width": "content", "headerOrientation": "horizontal"}]
    return parts


@pytest.mark.parametrize("lanes", [False, True], ids=["rows", "lanes"])
def test_before_across_after_close_every_production_plot_primitive_and_warn_exact_sources(tmp_path, lanes):
    parts = _parts(lanes)
    parts["view"]["body"]["window"] = {
        "mode": "explicit", "start": "2026-01-05", "end": "2026-01-09"}
    source = _source()
    rendered = sr.render(tmp_path, source, presentation=parts)
    surface = rendered.surface
    x, y, width, height = next(slot.bounds for slot in surface.slots if slot.source == "timeline")
    marks = [p for p in surface.primitives if p.slot_id == "timeline" and p.source_ref in source["objects"]]
    assert marks
    assert {p.source_ref for p in marks} == {"across", "gate"}
    for primitive in marks:
        px, py, pw, ph = primitive.bounds
        assert x <= px <= px + pw <= x + width
        assert y <= py <= py + ph <= y + height
        if primitive.symbol is not None:
            assert all(x <= a <= x + width and y <= b <= y + height
                       for command in primitive.symbol.outline for a, b in command.points)
    across = next(p for p in marks if p.source_ref == "across" and p.purpose == "planned")
    assert across.kind == "Symbol" and across.paint_clip is not None
    assert surface.canvas_bounds[0] == 0 and surface.canvas_bounds[2] == 1600
    assert [float(v) for v in ET.fromstring(rendered.artifact.content).attrib["viewBox"].split()][::2] == [0, 1600]
    outside = [r.payload for r in rendered.warning_records if r.payload["code"] == "W_LAYOUT_OUTSIDE_WINDOW"]
    assert len(outside) == 1
    assert {s["sourceRef"] for s in outside[0]["sourceSubjects"]} == {
        "/objects/before", "/objects/across", "/objects/after", "/objects/early-gate", "/objects/late-gate"}


@pytest.mark.parametrize("lanes", [False, True], ids=["rows", "lanes"])
def test_containing_window_preserves_complete_scene_surface_and_svg(tmp_path, lanes):
    (tmp_path / "derived").mkdir()
    (tmp_path / "explicit").mkdir()
    source, parts = _source(), _parts(lanes)
    derived = sr.render(tmp_path / "derived", source, presentation=parts)
    scale = derived.surface.scale_manifest
    parts["view"]["body"]["window"] = {
        "mode": "explicit", "start": scale.domain_start.isoformat(), "end": scale.domain_end.isoformat()}
    explicit = sr.render(tmp_path / "explicit", source, presentation=parts)
    # Only the authored View provenance differs; compare the whole completed
    # Scene surface, not selected marks, and actual adapter bytes.
    assert explicit.surface == derived.surface
    assert explicit.artifact.content == derived.artifact.content
    assert not any(r.payload["code"] == "W_LAYOUT_OUTSIDE_WINDOW" for r in explicit.warning_records)
