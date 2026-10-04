"""Completed relation paths keep distinct approaches at a shared node (#1109)."""

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
import json

import pytest

from chrona.presentation.layout.sources import MeasuredSources, SourceInput
from chrona.presentation.model.projection import ReviewProjection
from chrona.presentation.scene.model import ScenePrimitive
from chrona.presentation.scene.v05_builder import build_scene_input, compose_review_surface

from tests.unit.chrona.presentation.scene.test_relation_entry_side import D, _item, _manifest, _rows
from tests.unit.chrona.presentation.scene.test_relation_route_invariant import gate
from tests.unit.chrona.presentation.scene.test_v05_builder import _Font, _theme, _title_measurement, surface_content


def _compose(items, rows, relations, *, window, max_bends=4, include_diagnostics=False):
    projection = ReviewProjection(tuple(items), window, (), (), tuple(rows))
    measurement = MeasuredSources(
        {"title": _title_measurement()},
        {"title": SourceInput(("Plan",))},
        {
            "text.body.size": Decimal(14),
            "text.body.lineHeight": Decimal("1.4"),
            "timeline.row.minBlockSize": Decimal(40),
            "timeline.row.paddingBlock": Decimal(8),
            "timeline.mark.blockSize": Decimal(8),
        },
    )
    manifest = replace(
        _manifest("title", "table", "timeline", "timeline-axis"),
        relation_entry="side-when-free",
        row_distribution="pack",
        relation_max_bends=max_bends,
        relation_max_detour_ratio=6.0,
    )
    value = build_scene_input(
        projection=projection,
        surface_content=surface_content(relations=tuple(relations)),
        layout_manifest=manifest,
        resolved_theme=_theme(),
        font_metrics=_Font(),
        measured_sources=measurement,
        capabilities={"svg": True},
    )
    surface = compose_review_surface(value)
    paths = {
        primitive.source_ref: primitive
        for primitive in surface.primitives
        if primitive.kind == "Path" and primitive.source_ref in {relation["id"] for relation in relations}
    }
    marks = {
        primitive.scene_id.removeprefix("planned:"): primitive
        for primitive in surface.primitives
        if primitive.scene_id.startswith("planned:")
    }
    return (paths, marks, surface.diagnostics) if include_diagnostics else (paths, marks)


def _gate_chain(relations, *, gap=2, days=120):
    incoming_source = _item("f", D(2026, 2, 1), D(2026, 2, 6))
    node = gate("g", date(2026, 2, 10))
    successor_start = date(2026, 2, 10) + timedelta(days=gap)
    successor = _item("l", successor_start, successor_start + timedelta(days=6))
    window = (date(2026, 1, 20), date(2026, 1, 20) + timedelta(days=days))
    return _compose(
        (incoming_source, node, successor),
        _rows((incoming_source,), (node,), (successor,)),
        relations,
        window=window,
    )


def _overlap(first, second) -> float:
    (a, b), (c, d) = first, second
    if a[1] == b[1] == c[1] == d[1]:
        return max(0.0, min(max(a[0], b[0]), max(c[0], d[0])) - max(min(a[0], b[0]), min(c[0], d[0])))
    if a[0] == b[0] == c[0] == d[0]:
        return max(0.0, min(max(a[1], b[1]), max(c[1], d[1])) - max(min(a[1], b[1]), min(c[1], d[1])))
    return 0.0


def _approach_overlap(incoming: ScenePrimitive, outgoing: ScenePrimitive) -> float:
    return _overlap(
        (incoming.points[-2], incoming.points[-1]),
        (outgoing.points[0], outgoing.points[1]),
    )


def _residual_pairs(paths):
    return tuple(
        (outgoing, incoming)
        for outgoing in paths.values()
        for incoming in paths.values()
        if outgoing is not incoming
        and outgoing.from_instance_id == incoming.to_instance_id
        and _approach_overlap(incoming, outgoing) > 1e-9
    )


def _bends(points) -> int:
    return sum(1 for a, b, c in zip(points, points[1:], points[2:]) if (a[0] == b[0]) != (b[0] == c[0]))


INCOMING = {"id": "f-g", "from": {"object": "f", "endpoint": "end"},
            "to": {"object": "g", "endpoint": "end"}}
OUTGOING = {"id": "g-l", "from": {"object": "g", "endpoint": "end"},
            "to": {"object": "l", "endpoint": "start"}}


@pytest.mark.parametrize("relations", [(INCOMING, OUTGOING), (OUTGOING, INCOMING)])
def test_gate_departure_does_not_reuse_incoming_final_segment_in_either_declaration_order(relations):
    paths, _ = _gate_chain(relations)
    incoming, outgoing = paths["f-g"], paths["g-l"]

    assert incoming.to_instance_id == outgoing.from_instance_id == "g:g"
    assert incoming.points[-1] == outgoing.points[0]
    assert _approach_overlap(incoming, outgoing) == 0.0


def test_relation_scene_paths_keep_their_resolved_fixed_endpoints():
    paths, marks = _gate_chain((INCOMING, OUTGOING))
    incoming, outgoing = paths["f-g"], paths["g-l"]

    assert incoming.from_instance_id == "f:f"
    assert incoming.to_instance_id == "g:g"
    assert outgoing.from_instance_id == "g:g"
    assert outgoing.to_instance_id == "l:l"
    assert incoming.points[0] == pytest.approx((marks["f:f"].bounds[0] + marks["f:f"].bounds[2],
                                                marks["f:f"].bounds[1] + marks["f:f"].bounds[3] / 2))
    assert outgoing.points[-1] == pytest.approx((marks["l:l"].bounds[0],
                                                 marks["l:l"].bounds[1] + marks["l:l"].bounds[3] / 2))


def test_mirrored_span_end_approach_keeps_the_shared_endpoint_and_avoids_reuse():
    source = _item("f", D(2026, 2, 15), D(2026, 2, 20))
    node = _item("g", D(2026, 2, 1), D(2026, 2, 10))
    successor = _item("l", D(2026, 2, 10), D(2026, 2, 16))
    incoming = {"id": "f-g", "from": {"object": "f", "endpoint": "start"},
                "to": {"object": "g", "endpoint": "end"}}
    outgoing = {"id": "g-l", "from": {"object": "g", "endpoint": "end"},
                "to": {"object": "l", "endpoint": "start"}}
    paths, marks = _compose(
        (source, node, successor), _rows((source,), (node,), (successor,)),
        (outgoing, incoming), window=(D(2026, 1, 20), D(2026, 5, 20)),
    )

    arrival, departure = paths["f-g"], paths["g-l"]
    node_right = marks["g:g"].bounds[0] + marks["g:g"].bounds[2]
    node_middle = marks["g:g"].bounds[1] + marks["g:g"].bounds[3] / 2
    assert arrival.to_instance_id == departure.from_instance_id == "g:g"
    assert arrival.points[-1] == departure.points[0] == pytest.approx((node_right, node_middle))
    assert _approach_overlap(arrival, departure) == 0.0


@pytest.mark.parametrize("relations", [
    (
        {"id": "a-b", "from": {"object": "a", "endpoint": "start"},
         "to": {"object": "b", "endpoint": "start"}},
        {"id": "b-a", "from": {"object": "b", "endpoint": "start"},
         "to": {"object": "a", "endpoint": "start"}},
    ),
    (
        {"id": "b-a", "from": {"object": "b", "endpoint": "start"},
         "to": {"object": "a", "endpoint": "start"}},
        {"id": "a-b", "from": {"object": "a", "endpoint": "start"},
         "to": {"object": "b", "endpoint": "start"}},
    ),
])
def test_cycle_keeps_declared_scene_order_and_diagnoses_every_residual_overlap(relations):
    first = _item("a", D(2026, 2, 10), D(2026, 2, 20))
    second = _item("b", D(2026, 2, 10), D(2026, 2, 20))
    paths, _, diagnostics = _compose(
        (first, second), _rows((first,), (second,)), relations,
        window=(D(2026, 1, 20), D(2026, 5, 20)), max_bends=0, include_diagnostics=True,
    )

    assert tuple(paths) == tuple(relation["id"] for relation in relations)
    assert len(paths) == 2  # neither cyclic relation is suppressed
    residual = _residual_pairs(paths)
    assert len(residual) == 2
    prefix = "I_LAYOUT_RELATION_NODE_APPROACH_SHARED:"
    expected = {}
    for outgoing, incoming in residual:
        expected.setdefault(outgoing.scene_id, set()).add(incoming.scene_id)
    observed = {}
    for diagnostic in diagnostics:
        if not diagnostic.startswith(prefix):
            continue
        outgoing_id, incoming_json = diagnostic.removeprefix(prefix).split(";incoming=", 1)
        incoming_ids = json.loads(incoming_json)
        assert isinstance(incoming_ids, list) and all(isinstance(item, str) for item in incoming_ids)
        observed[outgoing_id] = set(incoming_ids)
    assert observed == expected
    for outgoing, incoming in residual:
        assert outgoing.from_instance_id == incoming.to_instance_id


def test_multiple_arrivals_are_routed_before_departure_and_keep_declared_scene_order():
    first = _item("a", D(2026, 2, 1), D(2026, 2, 5))
    second = _item("b", D(2026, 2, 3), D(2026, 2, 7))
    node = gate("g", date(2026, 2, 10))
    successor = _item("l", D(2026, 2, 12), D(2026, 2, 18))
    arrivals = (
        {"id": "a-g", "from": {"object": "a", "endpoint": "end"},
         "to": {"object": "g", "endpoint": "end"}},
        {"id": "b-g", "from": {"object": "b", "endpoint": "end"},
         "to": {"object": "g", "endpoint": "end"}},
    )
    departure = {"id": "g-l", "from": {"object": "g", "endpoint": "end"},
                 "to": {"object": "l", "endpoint": "start"}}
    declared = (departure, arrivals[1], arrivals[0])
    paths, _, diagnostics = _compose(
        (first, second, node, successor),
        _rows((first,), (second,), (node,), (successor,)), declared,
        window=(D(2026, 1, 20), D(2026, 5, 20)), include_diagnostics=True,
    )

    assert tuple(paths) == tuple(relation["id"] for relation in declared)
    incoming = (paths["a-g"], paths["b-g"])
    outgoing = paths["g-l"]
    assert all(path.to_instance_id == "g:g" for path in incoming)
    assert outgoing.from_instance_id == "g:g"
    assert all(_approach_overlap(path, outgoing) == 0.0 for path in incoming)
    assert not any(item.startswith("I_LAYOUT_RELATION_NODE_APPROACH_SHARED:") for item in diagnostics)


def test_composed_s_jog_fixture_has_minimal_bends_for_fixed_side_entry():
    source = _item("f", D(2026, 2, 1), D(2026, 2, 10))
    blocker = _item("x", D(2026, 1, 25), D(2026, 3, 1))
    target = _item("l", D(2026, 2, 12), D(2026, 2, 20))
    relation = {"id": "f-l", "from": {"object": "f", "endpoint": "end"},
                "to": {"object": "l", "endpoint": "start"}}
    paths, marks = _compose(
        (source, blocker, target), _rows((source,), (blocker,), (target,)), (relation,),
        window=(D(2026, 1, 20), D(2026, 4, 20)),
    )
    path = paths["f-l"]
    source_right = marks["f:f"].bounds[0] + marks["f:f"].bounds[2]
    source_middle = marks["f:f"].bounds[1] + marks["f:f"].bounds[3] / 2
    target_left = marks["l:l"].bounds[0]
    target_middle = marks["l:l"].bounds[1] + marks["l:l"].bounds[3] / 2

    assert path.from_instance_id == "f:f" and path.to_instance_id == "l:l"
    assert path.points[0] == pytest.approx((source_right, source_middle))
    assert path.points[-1] == pytest.approx((target_left, target_middle))
    # The intervening span blocks the direct crossing. Fixed vertical departure
    # and horizontal side entry require the three-bend route around it.
    assert _bends(path.points) == 3, path.points
