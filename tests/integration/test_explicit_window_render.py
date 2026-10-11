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


@pytest.mark.parametrize("lanes", [False, True], ids=["rows", "lanes"])
def test_all_objects_outside_keep_rows_without_fabricated_marks(tmp_path, lanes):
    parts = _parts(lanes)
    parts["view"]["body"]["window"] = {"mode": "explicit", "start": "2027-01-01", "end": "2027-01-09"}
    source = _source()
    rendered = sr.render(tmp_path, source, presentation=parts)
    assert len(rendered.surface.rows) == len(source["objects"])
    assert not any(p.slot_id == "timeline" and p.source_ref in source["objects"]
                   for p in rendered.surface.primitives)
    if lanes:
        assert len(rendered.surface.lane_members) == len(source["objects"])
        assert all(not member.primary_mark_ids and member.window_absences
                   for member in rendered.surface.lane_members)


@pytest.mark.parametrize("lanes", [False, True], ids=["rows", "lanes"])
@pytest.mark.parametrize("open_actual", [False, True], ids=["closed", "open"])
def test_actual_and_progress_project_completed_cut_contours(tmp_path, lanes, open_actual):
    parts = _parts(lanes)
    parts["view"]["body"]["window"] = {"mode": "explicit", "start": "2026-01-05", "end": "2026-01-09"}
    parts["view"]["body"]["progressFill"] = {"source": "actual"}
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed", "body": {
        "asOf": "2026-01-08", "observations": [{"id": "a", "sequence": 1, "projectObjectId": "across",
            "actual": {"start": "2026-01-01", "progress": 0.9,
                       **({"openUntil": "asOf"} if open_actual else {"finish": "2026-01-08"})}}]}}
    rendered = sr.render(tmp_path, _source(), presentation=parts, actual=actual)
    marks = [p for p in rendered.surface.primitives if p.source_ref == "across"
             and p.purpose in {"actual", "progress-fill"}]
    assert {p.purpose for p in marks} == {"actual", "progress-fill"}
    assert all(p.kind == "Symbol" and p.paint_clip is not None for p in marks)
    x, y, w, h = next(slot.bounds for slot in rendered.surface.slots if slot.source == "timeline")
    assert all(x <= a <= x + w and y <= b <= y + h
               for p in marks for command in p.symbol.outline for a, b in command.points)


@pytest.mark.parametrize("lanes", [False, True], ids=["rows", "lanes"])
def test_relations_use_only_original_visible_endpoints(tmp_path, lanes):
    parts = _parts(lanes)
    parts["view"]["body"]["window"] = {"mode": "explicit", "start": "2026-01-05", "end": "2026-01-09"}
    source = sr.project({"before": sr.span("before", date(2026, 1, 1), 2),
                         "a": sr.span("a", date(2026, 1, 5), 1),
                         "b": sr.span("b", date(2026, 1, 7), 1)}, [
        {"id": "outside", "type": "dependency", "lag": "0d", "from": {"object": "before", "endpoint": "end"},
         "to": {"object": "a", "endpoint": "start"}},
        {"id": "inside", "type": "dependency", "lag": "0d", "from": {"object": "a", "endpoint": "end"},
         "to": {"object": "b", "endpoint": "start"}}])
    rendered = sr.render(tmp_path, source, presentation=parts)
    relations = [p for p in rendered.surface.primitives if p.source_ref in {"inside", "outside"}]
    assert {p.source_ref for p in relations} == {"inside"}
    assert all(p.paint_clip is not None for p in relations)
    x, y, w, h = next(slot.bounds for slot in rendered.surface.slots if slot.source == "timeline")
    for p in relations:
        # Paths carry completed points/commands, not a rectangular host bound.
        coordinates = (*p.points, *(point for command in p.path_commands for point in command.points))
        if p.symbol is not None:
            coordinates += tuple(point for command in p.symbol.outline for point in command.points)
        assert coordinates
        assert all(x <= a <= x + w and y <= b <= y + h for a, b in coordinates)
    assert any(r.payload["code"] == "W_LAYOUT_RELATION_SUPPRESSED" for r in rendered.warning_records)
