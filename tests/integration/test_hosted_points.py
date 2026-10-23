"""Synthetic public-render evidence for physical point hosting (#1373 row 3)."""
from __future__ import annotations

from datetime import date
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree

import pytest

from chrona.presentation.model.info_diagnostics import RelationResolutionInfo
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr


@pytest.mark.parametrize("corruption", ["glyph-shift", "missing-mark", "frame-shift"])
def test_final_host_frame_gate_rejects_geometry_or_partition_drift(tmp_path, monkeypatch, corruption):
    from chrona.presentation.layout import surface_completion
    from chrona.presentation.layout.point_host_geometry import translate_point_block
    original = surface_completion.validate_point_host_frames

    def corrupt(preflight, marks, icons, shapes, tracks, theme, *, paint_capabilities):
        if corruption == "glyph-shift":
            marks = tuple(translate_point_block(mark, 1.0) if mark.physical_host is not None else mark
                          for mark in marks)
        elif corruption == "missing-mark":
            marks = tuple(mark for mark in marks if mark.physical_host is None)
        else:
            allocation = preflight.point_host_allocation
            frames = tuple(replace(frame, block_offset=frame.block_offset + 1.0)
                           if frame.semantic_instance != frame.allocation_instance else frame
                           for frame in allocation.frames)
            preflight = replace(preflight, point_host_allocation=replace(allocation, frames=frames))
        return original(preflight, marks, icons, shapes, tracks, theme,
                        paint_capabilities=paint_capabilities)

    monkeypatch.setattr(surface_completion, "validate_point_host_frames", corrupt)
    objects = {"host": sr.span("host", date(2026, 1, 1), 20),
               "gate": {**sr.point("gate", date(2026, 1, 10)), "parent": "host"}}
    with pytest.raises(RenderFailed) as failure:
        _render(tmp_path, objects)
    assert failure.value.code == "E_PRESENTATION_PLACEMENT_REQUIRED"


def test_typeset_adapters_serialize_completed_hosted_geometry(tmp_path):
    from chrona.presentation.renderers.v05_typeset import V05TikzRenderer, V05TypstRenderer
    objects = {"host": sr.span("host", date(2026, 1, 1), 20),
               "gate": {**sr.point("gate", date(2026, 1, 10)), "parent": "host"}}
    off = _render(tmp_path / "off", objects, parts=_parts(host=False))
    on = _render(tmp_path / "on", objects)
    for renderer in (V05TikzRenderer(), V05TypstRenderer()):
        before = renderer.render(off.surface).content
        after = renderer.render(on.surface).content
        assert after and after != before


def test_dependency_can_enter_span_endpoint_covered_by_its_hosted_point(tmp_path):
    objects = {"earlier": sr.span("earlier", date(2025, 12, 20), 5),
               "host": sr.span("host", date(2026, 1, 1), 20),
               "gate": {**sr.point("gate", date(2026, 1, 1)), "parent": "host"}}
    relations = [{"id": "enter-host", "type": "dependency", "lag": "0d",
                  "from": {"object": "earlier", "endpoint": "end"},
                  "to": {"object": "host", "endpoint": "start"}}]
    rendered = _render(tmp_path, objects, relations=relations)
    # The legal completions are paired stubs and, once the names keep their label gap from the relation ink
    # (#1848), the fixed overlap route that a name abutting the lead used to prevent: either way a connected
    # fragment enters the glyph, so select the fragment with the head rather than assuming which one it is.
    fragments = [item for item in rendered.surface.primitives
                 if item.purpose == "dependency" and item.source_ref == "relation:id:enter-host"]
    receipt, = [item for item in rendered.info_diagnostics
                if isinstance(item, RelationResolutionInfo)
                and (set(item.fragment_ids or ()) == {fragment.scene_id for fragment in fragments}
                     or item.relation_id in {fragment.scene_id for fragment in fragments})]
    assert receipt.stage.value in {"stub", "overlap"}
    assert len(fragments) == (2 if receipt.stage.value == "stub" else 1)
    route, = [item for item in fragments if item.marker_end is not None]
    gate = _mark(rendered, "planned", "gate")
    x, y = route.points[-1]
    left, top, width, height = gate.bounds
    assert left <= x <= left + width and top <= y <= top + height
    assert any(node.get("data-scene-id") == route.scene_id and node.get("d")
               for node in ElementTree.fromstring(rendered.artifact.content).iter())


def _parts(*, host: bool = True, rows: str = "lanes"):
    parts = sr.bundle("executive-light")
    body = parts["view"]["body"]
    body["rows"] = ({"mode": rows, "packing": ["explicit"], "laneTable": {"label": "lane"}}
                    if rows == "lanes" else {"mode": rows})
    body["grouping"] = {"by": "none", "missing": "ungrouped"}
    body["visibility"]["labels"] = {
        "placement": "plot", "content": ["title"], "side": "end", "overflow": "suppress"}
    body["visibility"]["relations"] = {"mode": "semantic", "overflow": "suppress"}
    if host:
        marks = parts["layout"]["reviewSurface"].setdefault("marks", {})
        marks.setdefault("points", {})["host"] = "span-when-inside"
    return parts


def _render(tmp_path, objects, *, parts=None, relations=(), actual=None):
    Path(tmp_path).mkdir(parents=True, exist_ok=True)
    return sr.render(tmp_path, sr.project(objects, relations), presentation=parts or _parts(), actual=actual)


def _mark(rendered, purpose, source_ref, source_kind=None):
    return next(item for item in rendered.surface.primitives
                if item.purpose == purpose and item.source_ref == source_ref
                and (source_kind is None or item.source_kind == source_kind))


def _centre(bounds, axis):
    start, size = (bounds[1], bounds[3]) if axis == "block" else (bounds[0], bounds[2])
    return start + size / 2


def test_hosting_is_default_off_and_preserves_the_point_when_omitted(tmp_path):
    objects = {"host": sr.span("host", date(2026, 1, 1), 20),
               "gate": {**sr.point("gate", date(2026, 1, 10)), "parent": "host"}}
    off = _render(tmp_path / "off", objects, parts=_parts(host=False))
    on = _render(tmp_path / "on", objects)
    off_mark, on_mark = _mark(off, "planned", "gate"), _mark(on, "planned", "gate")
    host = _mark(on, "planned", "host")
    assert _centre(off_mark.bounds, "block") != pytest.approx(_centre(host.bounds, "block"))
    assert _centre(on_mark.bounds, "block") == pytest.approx(_centre(host.bounds, "block"))
    assert _centre(on_mark.bounds, "inline") == pytest.approx(_centre(off_mark.bounds, "inline"))
    assert off_mark.scene_id == on_mark.scene_id


def test_cross_row_parent_host_keeps_lane_identity_and_renders_label_and_dependency(tmp_path):
    objects = {
        "host": sr.span("host", date(2026, 1, 1), 20, owner="a", title="Host span"),
        "gate": {**sr.point("gate", date(2026, 1, 1), owner="b", title="Review gate"), "parent": "host"},
        "later": sr.span("later", date(2026, 1, 24), 5, owner="b"),
    }
    relations = [{"id": "gate-to-later", "type": "dependency", "lag": "0d",
                  "from": {"object": "gate", "endpoint": "at"},
                  "to": {"object": "later", "endpoint": "start"}}]
    parts = _parts()
    parts["view"]["body"]["visibility"]["labels"]["side"] = "start"
    rendered = _render(tmp_path, objects, parts=parts, relations=relations)
    gate, host = _mark(rendered, "planned", "gate"), _mark(rendered, "planned", "host")
    assert _centre(gate.bounds, "block") == pytest.approx(_centre(host.bounds, "block"))
    assert gate.lane_row_id != host.lane_row_id  # semantic membership stays with the child
    label = _mark(rendered, "member-label", "gate")
    assert "Review gate" in label.text
    host_row = next(row for row in rendered.surface.rows if row.row_id == host.lane_row_id)
    assert label.lane_row_id == gate.lane_row_id
    assert host_row.bounds[1] <= label.bounds[1]
    assert label.bounds[1] + label.bounds[3] <= host_row.bounds[1] + host_row.bounds[3]
    svg_text = "".join(ElementTree.fromstring(rendered.artifact.content).itertext())
    assert "Review gate" in svg_text
    dependency, = [item for item in rendered.surface.primitives
                   if item.purpose == "dependency" and item.source_kind == "relation"]
    assert len(dependency.points) >= 2
    svg_routes = [item for item in ElementTree.fromstring(rendered.artifact.content).iter()
                  if item.tag.endswith("path") and item.get("data-purpose") == "dependency"]
    assert any(item.get("d") for item in svg_routes)


def test_automatic_rows_parent_host_label_uses_host_row_band(tmp_path):
    objects = {"host": sr.span("host", date(2026, 1, 1), 20, title="Host span"),
               "gate": {**sr.point("gate", date(2026, 1, 1), title="Review gate"), "parent": "host"}}
    parts = _parts(rows="automatic")
    parts["view"]["body"]["visibility"]["labels"]["side"] = "start"
    rendered = _render(tmp_path, objects, parts=parts)
    gate, host = _mark(rendered, "planned", "gate"), _mark(rendered, "planned", "host")
    label = _mark(rendered, "member-label", "gate")
    assert _centre(gate.bounds, "block") == pytest.approx(_centre(host.bounds, "block"))
    host_row = next(row for row in rendered.surface.rows if row.row_id == "host")
    assert host_row.bounds[1] <= label.bounds[1]
    assert label.bounds[1] + label.bounds[3] <= host_row.bounds[1] + host_row.bounds[3]
    assert "Review gate" in "".join(ElementTree.fromstring(rendered.artifact.content).itertext())


def test_declared_attachment_precedes_direct_parent(tmp_path):
    objects = {
        "parent": sr.span("parent", date(2026, 1, 1), 20),
        "attached": sr.span("attached", date(2026, 1, 5), 10, owner="b"),
        "gate": {**sr.point("gate", date(2026, 1, 10)), "parent": "parent", "attachesTo": "attached"},
    }
    rendered = _render(tmp_path, objects)
    gate = _mark(rendered, "planned", "gate")
    assert _centre(gate.bounds, "block") == pytest.approx(_centre(_mark(rendered, "planned", "attached").bounds, "block"))
    assert _centre(gate.bounds, "block") != pytest.approx(_centre(_mark(rendered, "planned", "parent").bounds, "block"))


@pytest.mark.parametrize("offset", [0, 20], ids=["inclusive-start", "inclusive-end"])
def test_original_span_interval_includes_both_point_endpoints(tmp_path, offset):
    start = date(2026, 1, 1)
    objects = {"host": sr.span("host", start, 20),
               "gate": {**sr.point("gate", start.fromordinal(start.toordinal() + offset)), "parent": "host"}}
    rendered = _render(tmp_path, objects)
    gate, host = _mark(rendered, "planned", "gate"), _mark(rendered, "planned", "host")
    assert _centre(gate.bounds, "block") == pytest.approx(_centre(host.bounds, "block"))
    days_from_domain = (start.fromordinal(start.toordinal() + offset) - rendered.surface.scale_manifest.domain_start).days
    assert _centre(gate.bounds, "inline") == pytest.approx(
        rendered.surface.scale_manifest.origin + days_from_domain * rendered.surface.scale_manifest.unit_ratio)


@pytest.mark.parametrize("point_day", [date(2025, 12, 31), date(2026, 1, 22)], ids=["before", "after"])
def test_parent_outside_original_interval_leaves_point_in_its_own_row(tmp_path, point_day):
    objects = {"host": sr.span("host", date(2026, 1, 1), 20),
               "gate": {**sr.point("gate", point_day), "parent": "host"}}
    rendered = _render(tmp_path, objects)
    gate, host = _mark(rendered, "planned", "gate"), _mark(rendered, "planned", "host")
    assert _centre(gate.bounds, "block") != pytest.approx(_centre(host.bounds, "block"))


def test_point_without_any_attachment_or_parent_stays_in_its_own_row(tmp_path):
    objects = {"host": sr.span("host", date(2026, 1, 1), 20),
               "gate": sr.point("gate", date(2026, 1, 10))}
    rendered = _render(tmp_path, objects)
    assert _centre(_mark(rendered, "planned", "gate").bounds, "block") != pytest.approx(
        _centre(_mark(rendered, "planned", "host").bounds, "block"))


def test_unselected_parent_is_not_a_physical_host(tmp_path):
    objects = {"host": sr.span("host", date(2026, 1, 1), 20),
               "gate": {**sr.point("gate", date(2026, 1, 10)), "parent": "host"}}
    parts = _parts()
    parts["view"]["body"]["selection"] = {"include": {"ids": ["gate"]}}
    rendered = _render(tmp_path, objects, parts=parts)
    assert not any(item.purpose == "planned" and item.source_ref == "host" for item in rendered.surface.primitives)
    assert _mark(rendered, "planned", "gate")


def test_actual_point_uses_its_own_source_facet_and_unhosted_actual_stays_put(tmp_path):
    objects = {"host": sr.span("host", date(2026, 1, 1), 20),
               "gate": {**sr.point("gate", date(2026, 1, 10)), "parent": "host"}}
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
              "body": {"asOf": "2026-01-25", "observations": [
        {"id": "gate-observed", "sequence": 1, "projectObjectId": "gate", "actual": {"at": "2026-01-25"}}]}}
    rendered = _render(tmp_path, objects, actual=actual)
    host, planned = _mark(rendered, "planned", "host"), _mark(rendered, "planned", "gate")
    observed = _mark(rendered, "actual", "gate")
    assert _centre(planned.bounds, "block") == pytest.approx(_centre(host.bounds, "block"))
    assert _centre(observed.bounds, "block") != pytest.approx(_centre(host.bounds, "block"))


def test_two_non_lane_hosted_points_at_same_date_fail_fixed_overlap(tmp_path):
    objects = {
        "host": sr.span("host", date(2026, 1, 1), 20),
        "gate-a": {**sr.point("gate-a", date(2026, 1, 10)), "parent": "host"},
        "gate-b": {**sr.point("gate-b", date(2026, 1, 10)), "parent": "host"},
    }
    parts = _parts(rows="automatic")

    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path / "hosted", objects, parts=parts)

    assert raised.value.code == "E_LAYOUT_POINT_HOST_OVERLAP"


def test_two_same_date_points_without_hosting_policy_keep_existing_rendering(tmp_path):
    objects = {
        "host": sr.span("host", date(2026, 1, 1), 20),
        "gate-a": {**sr.point("gate-a", date(2026, 1, 10)), "parent": "host"},
        "gate-b": {**sr.point("gate-b", date(2026, 1, 10)), "parent": "host"},
    }
    rendered = _render(tmp_path, objects, parts=_parts(host=False, rows="automatic"))

    assert len([item for item in rendered.surface.primitives if item.purpose == "planned"
                and item.source_ref in {"gate-a", "gate-b"}]) == 2


def test_annotation_leader_anchors_to_completed_cross_row_hosted_point(tmp_path):
    source = sr.project({
        "host": sr.span("host", date(2026, 1, 1), 20, owner="a", title="Host span"),
        "gate": {**sr.point("gate", date(2026, 1, 1), owner="b", title="Review gate"), "parent": "host"},
    })
    parts = _parts()
    sr.add_notes(source, parts["view"], ("gate",),
        (sr.candidate("plot-near", connector="leader", max_positions=512),), words=0, endpoint="at")
    rendered = sr.render(tmp_path, source, presentation=parts)

    gate = _mark(rendered, "planned", "gate")
    annotation = next(item for item in rendered.surface.primitives
                      if item.scene_id == "annotation-text:note-0")
    leader = next(item for item in rendered.surface.primitives
                  if item.scene_id == "annotation-leader:note-0")
    assert annotation.text
    assert len(leader.points) >= 2
    gx, gy, gw, gh = gate.bounds
    assert any(gx - 1e-6 <= x <= gx + gw + 1e-6 and gy - 1e-6 <= y <= gy + gh + 1e-6
               for x, y in (leader.points[0], leader.points[-1]))
    svg = ElementTree.fromstring(rendered.artifact.content)
    svg_ids = {item.get("data-scene-id") for item in svg.iter()}
    assert "annotation-text:note-0" in svg_ids and "annotation-leader:note-0" in svg_ids
    svg_leader = next(item for item in svg.iter() if item.get("data-scene-id") == "annotation-leader:note-0")
    assert svg_leader.get("d")
