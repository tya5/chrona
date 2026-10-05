"""Same-target-port relation fan-in keeps every path but paints one target terminal (R6)."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from math import hypot
import xml.etree.ElementTree as ET

import pytest

from chrona.presentation.layout.sources import MeasuredSources, SourceInput
from chrona.presentation.model.projection import ReviewItem, ReviewProjection, ReviewRowProjection
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.scene.model import (
    ContentFamilyCounts, InspectionScene, SceneManifest, SceneProvenance,
)
from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.presentation.scene.serialization import scene_document
from chrona.presentation.scene.v05_builder import build_scene_input, compose_review_surface

from tests.unit.chrona.presentation.scene.test_relation_entry_side import D, _item
from tests.unit.chrona.presentation.scene.test_v05_builder import (
    _Font, _manifest, _theme, _title_measurement, surface_content,
)


def _rows(*items):
    return tuple(ReviewRowProjection(item.object_id, item.title, "", item.object_id, (item,))
                 for item in items)


def _relation(relation_id, source, source_endpoint="end", target="target", target_endpoint="start"):
    return {"id": relation_id,
            "from": {"object": source, "endpoint": source_endpoint},
            "to": {"object": target, "endpoint": target_endpoint}}


def _surface(items, relations, *, target_shape="triangle", target_head=10, target_offset=1):
    items = tuple(items)
    relations = tuple(relations)
    theme = _theme()
    theme["body"]["values"]["fan-source"] = {
        "type": "marker", "value": {"shape": "triangle", "headLength": 8, "headWidth": 8, "attachmentOffset": 1},
    }
    theme["body"]["values"]["fan-target"] = {
        "type": "marker", "value": {"shape": target_shape, "headLength": target_head,
                                       "headWidth": target_head, "attachmentOffset": target_offset},
    }
    theme["body"]["roles"]["relationSourceTerminal"] = {"marker": "fan-source"}
    theme["body"]["roles"]["relationTargetTerminal"] = {"marker": "fan-target"}
    first = min(item.planned.get("start", item.planned.get("at")) for item in items)
    last = max(item.planned.get("end", item.planned.get("at")) for item in items)
    projection = ReviewProjection(items, (first, last), (), (), _rows(*items))
    measured = MeasuredSources(
        {"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
        {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
         "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8),
         "timeline.mark.blockSize": Decimal(8)},
    )
    manifest = replace(_manifest("title", "table", "timeline", "timeline-axis"),
                       relation_entry="side", row_distribution="pack",
                       relation_max_bends=6, relation_max_detour_ratio=6.0)
    value = build_scene_input(
        projection=projection, surface_content=surface_content(relations=relations),
        layout_manifest=manifest, resolved_theme=theme, font_metrics=_Font(),
        measured_sources=measured, capabilities={"svg": True},
    )
    return compose_review_surface(value)


def _paths(surface):
    return tuple(item for item in surface.primitives
                 if item.kind == "Path" and item.source_kind == "relation"
                 and item.scene_id.startswith("relation:"))


def _path_by_source(surface, source_ref):
    return next(path for path in _paths(surface) if path.source_ref == source_ref)


def _mark(surface, object_id):
    return next(item for item in surface.primitives
                if item.scene_id.startswith("planned:") and item.scene_id.endswith(f":{object_id}"))


def _target_port(surface, object_id, endpoint="start"):
    x, y, width, height = _mark(surface, object_id).bounds
    return ((x, y + height / 2) if endpoint == "start" else (x + width, y + height / 2))


def _assert_side_entry(path, port, endpoint="start"):
    before, end = path.points[-2:]
    assert before[1] == pytest.approx(end[1])
    assert end == pytest.approx(port)
    assert (end[0] - before[0] > 0) if endpoint == "start" else (end[0] - before[0] < 0)


def _terminal_center(path):
    marker = path.marker_end
    assert marker is not None and marker.centred
    before, end = path.points[-2:]
    length = hypot(end[0] - before[0], end[1] - before[1])
    direction = ((end[0] - before[0]) / length, (end[1] - before[1]) / length)
    behind = marker.head_length - marker.attachment_offset - marker.head_length / 2
    return (end[0] - direction[0] * behind, end[1] - direction[1] * behind)


def _svg_relation_paths(surface):
    root = ET.fromstring(render_v05_svg(surface))
    return tuple(element for element in root.iter()
                 if element.tag.rsplit("}", 1)[-1] == "path"
                 and element.get("data-scene-id", "").startswith("relation:"))


def _observer_findings(surface):
    viewport = (surface.canvas_bounds[2], surface.canvas_bounds[3])
    paths = _paths(surface)
    manifest = SceneManifest(
        "chrona/scene-manifest/v0.1", "fan-in-test", viewport, (), (),
        ContentFamilyCounts(len(paths), 0, 0, 0, 0),
        (surface.scale_manifest,) if surface.scale_manifest is not None else (),
    )
    scene = InspectionScene(SceneProvenance("draft", "fan-in-test", ()), viewport, (),
                            (surface,), manifest, surface.diagnostics)
    return evaluate_scene_perceptibility(scene_document(scene))


def _arrivals(count):
    starts = (date(2026, 1, 5), date(2026, 1, 12), date(2026, 1, 19))
    sources = tuple(_item(f"source-{index + 1}", day, day.replace(day=day.day + 3))
                    for index, day in enumerate(starts[:count]))
    target = _item("target", date(2026, 2, 10), date(2026, 2, 20))
    relations = tuple(_relation(f"arrival-{index + 1}", item.object_id)
                      for index, item in enumerate(sources))
    return (*sources, target), relations, sources, target


@pytest.mark.parametrize("count", (2, 3))
def test_same_start_port_arrivals_keep_every_path_and_emit_one_svg_target_head(count):
    items, relations, sources, target = _arrivals(count)
    surface = _surface(items, relations)
    paths = _paths(surface)
    assert {path.source_ref for path in paths} == {f"arrival-{index}" for index in range(1, count + 1)}
    assert len(paths) == count
    for index, source in enumerate(sources, 1):
        _assert_side_entry(_path_by_source(surface, f"arrival-{index}"), _target_port(surface, target.object_id))

    owner = _path_by_source(surface, "arrival-1")
    assert owner.marker_end is not None
    assert all(_path_by_source(surface, f"arrival-{index}").marker_end is None
               for index in range(2, count + 1))
    assert all(path.fan_in is not None for path in paths)
    assert {path.fan_in.terminal_owner_id for path in paths} == {owner.scene_id}
    assert len({path.fan_in.target_port_id for path in paths}) == 1
    findings = _observer_findings(surface)
    assert "E_SCENE_RELATION_FAN_IN_INVALID" not in {finding.code for finding in findings}
    assert "E_SCENE_RELATION_NODE_APPROACH_SHARED" not in {finding.code for finding in findings}

    svg_paths = _svg_relation_paths(surface)
    assert {path.get("data-scene-id") for path in svg_paths} == {path.scene_id for path in paths}
    assert sum(path.get("marker-end") is not None for path in svg_paths) == 1


def test_round_target_marker_stays_centered_while_shared_terminal_stroke_remains():
    items, relations, _sources, target = _arrivals(3)
    surface = _surface(items, relations, target_shape="circle", target_head=8, target_offset=0)
    paths = _paths(surface)
    owner = _path_by_source(surface, "arrival-1")
    assert _terminal_center(owner) == pytest.approx(_target_port(surface, target.object_id))
    assert all(path.points[-1][1] == pytest.approx(_target_port(surface, target.object_id)[1]) for path in paths)

    def horizontal_interval(path):
        before, end = path.points[-2:]
        return (min(before[0], end[0]), max(before[0], end[0]))

    owner_start, owner_end = horizontal_interval(owner)
    for path in paths[1:]:
        start, end = horizontal_interval(path)
        assert min(owner_end, end) - max(owner_start, start) > 0
    assert sum(element.get("marker-end") is not None for element in _svg_relation_paths(surface)) == 1


def test_headless_same_port_arrivals_keep_paths_without_inventing_a_target_head():
    items, relations, _sources, _target = _arrivals(2)
    surface = _surface(items, relations, target_shape="none")
    paths = _paths(surface)
    assert len(paths) == 2
    assert all(path.marker_end is None for path in paths)
    assert all(path.fan_in is not None for path in paths)
    findings = _observer_findings(surface)
    assert "E_SCENE_RELATION_FAN_IN_INVALID" not in {finding.code for finding in findings}
    assert "E_SCENE_RELATION_NODE_APPROACH_SHARED" not in {finding.code for finding in findings}
    assert sum(element.get("marker-end") is not None for element in _svg_relation_paths(surface)) == 0


def test_distinct_target_ports_and_distinct_target_instances_keep_separate_heads():
    early = _item("early", date(2026, 1, 5), date(2026, 1, 8))
    late = _item("late", date(2026, 2, 25), date(2026, 2, 28))
    target = _item("target", date(2026, 2, 10), date(2026, 2, 20))
    other = _item("other-target", date(2026, 2, 10), date(2026, 2, 20))
    relations = (_relation("target-start", "early", target="target", target_endpoint="start"),
                 _relation("target-end", "late", target="target", target_endpoint="end"),
                 _relation("other-instance", "early", target="other-target", target_endpoint="start"))
    surface = _surface((early, late, target, other), relations)
    paths = _paths(surface)
    assert len(paths) == 3 and all(path.marker_end is not None for path in paths)
    assert all(path.fan_in is None for path in paths)
    assert sum(element.get("marker-end") is not None for element in _svg_relation_paths(surface)) == 3


def test_departure_from_a_fan_in_node_is_not_joined_to_its_arrival_group():
    items, arrivals, sources, target = _arrivals(2)
    successor = _item("successor", date(2026, 2, 25), date(2026, 3, 5))
    departure = _relation("departure", target.object_id, source_endpoint="end",
                          target="successor", target_endpoint="start")
    surface = _surface((*items, successor), (*arrivals, departure))
    incoming = tuple(_path_by_source(surface, f"arrival-{index}") for index in (1, 2))
    outgoing = _path_by_source(surface, "departure")
    assert all(path.fan_in is not None for path in incoming)
    assert outgoing.fan_in is None
    assert outgoing.marker_start is not None and outgoing.marker_end is not None
    assert all(path.fan_in.terminal_owner_id == incoming[0].scene_id for path in incoming)
