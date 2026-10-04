"""Completed relation paths retain opaque node identity and diagnose shared terminal segments (#1109 R2)."""

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
import json

import pytest

from chrona.presentation.layout.sources import MeasuredSources, SourceInput
from chrona.presentation.model.projection import ReviewProjection, ReviewRowProjection
from chrona.presentation.scene.v05_builder import build_scene_input, compose_review_surface

from tests.unit.chrona.presentation.scene.test_relation_entry_side import D, _item, _manifest, _rows
from tests.unit.chrona.presentation.scene.test_relation_route_invariant import gate
from tests.unit.chrona.presentation.scene.test_v05_builder import _Font, _theme, _title_measurement, surface_content


def _compose(items, rows, relations, *, window, max_bends=4):
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
    paths = tuple(
        primitive for primitive in surface.primitives
        if primitive.kind == "Path" and primitive.source_kind == "relation"
        and primitive.from_instance_id is not None
    )
    marks = {
        primitive.scene_id.removeprefix("planned:"): primitive
        for primitive in surface.primitives
        if primitive.scene_id.startswith("planned:")
    }
    return paths, marks, surface.diagnostics


def _overlap(first, second) -> float:
    (a, b), (c, d) = first, second
    if a[1] == b[1] == c[1] == d[1]:
        return max(0.0, min(max(a[0], b[0]), max(c[0], d[0])) - max(min(a[0], b[0]), min(c[0], d[0])))
    if a[0] == b[0] == c[0] == d[0]:
        return max(0.0, min(max(a[1], b[1]), max(c[1], d[1])) - max(min(a[1], b[1]), min(c[1], d[1])))
    return 0.0


def _terminal_segment_residuals(paths):
    """Independent all-endpoint oracle: shared instance plus positive-length terminal overlap."""
    incidents = {}
    for path in paths:
        incidents.setdefault(path.from_instance_id, []).append((path.scene_id, (path.points[0], path.points[1])))
        incidents.setdefault(path.to_instance_id, []).append((path.scene_id, (path.points[-2], path.points[-1])))
    residuals = set()
    for node_id, segments in incidents.items():
        for index, (first_id, first) in enumerate(segments):
            for second_id, second in segments[index + 1:]:
                if first_id != second_id and _overlap(first, second) > 1e-9:
                    residuals.add((node_id, tuple(sorted((first_id, second_id)))))
    return residuals


def _diagnosed_pairs(diagnostics):
    prefix = "I_LAYOUT_RELATION_NODE_APPROACH_SHARED:"
    result = []
    for diagnostic in diagnostics:
        if not diagnostic.startswith(prefix):
            continue
        record = json.loads(diagnostic.removeprefix(prefix))
        assert isinstance(record, dict)
        assert isinstance(record.get("nodeInstanceId"), str) and record["nodeInstanceId"]
        relation_ids = record.get("relationIds")
        assert isinstance(relation_ids, list) and len(relation_ids) == 2
        assert relation_ids == sorted(relation_ids) and all(isinstance(item, str) and item for item in relation_ids)
        assert isinstance(record.get("reason"), str) and record["reason"]
        result.append((record["nodeInstanceId"], tuple(relation_ids)))
    return result


def _assert_exact_residual_diagnostics(paths, diagnostics):
    expected = _terminal_segment_residuals(paths)
    observed = _diagnosed_pairs(diagnostics)
    assert len(observed) == len(set(observed)), "each residual node/pair must be diagnosed exactly once"
    assert set(observed) == expected
    return expected


INCOMING = {"id": "f-g", "from": {"object": "f", "endpoint": "end"},
            "to": {"object": "g", "endpoint": "end"}}
OUTGOING = {"id": "g-l", "from": {"object": "g", "endpoint": "end"},
            "to": {"object": "l", "endpoint": "start"}}


def _gate_chain(relations, *, gap=2):
    incoming_source = _item("f", D(2026, 2, 1), D(2026, 2, 6))
    node = gate("g", date(2026, 2, 10))
    successor_start = date(2026, 2, 10) + timedelta(days=gap)
    successor = _item("l", successor_start, successor_start + timedelta(days=6))
    return _compose(
        (incoming_source, node, successor),
        _rows((incoming_source,), (node,), (successor,)),
        relations,
        window=(D(2026, 1, 20), D(2026, 5, 20)),
    )


@pytest.mark.parametrize("relations", [(INCOMING, OUTGOING), (OUTGOING, INCOMING)])
def test_gate_departure_avoids_incoming_final_segment_in_both_declaration_orders(relations):
    paths, _, diagnostics = _gate_chain(relations)
    incoming = next(path for path in paths if path.source_ref == "f-g")
    outgoing = next(path for path in paths if path.source_ref == "g-l")

    assert incoming.to_instance_id == outgoing.from_instance_id == "g:g"
    assert _overlap((incoming.points[-2], incoming.points[-1]),
                    (outgoing.points[0], outgoing.points[1])) == 0.0
    assert _assert_exact_residual_diagnostics(paths, diagnostics) == set()
    assert tuple(path.source_ref for path in paths) == tuple(relation["id"] for relation in relations)


def test_departure_avoids_shared_approach_when_successor_precedes_gate():
    # Reusing the public 0977b5ea `_gate_chain` fixture shape on the R1 public
    # baseline, gap -20 routed f→g into g's right side and g→l back along the
    # same terminal corridor (12.4 units). This geometry assertion does not rely
    # on endpoint metadata, so it fails on the old router independently of IDs.
    paths, _, diagnostics = _gate_chain((INCOMING, OUTGOING), gap=-20)
    incoming = next(path for path in paths if path.source_ref == "f-g")
    outgoing = next(path for path in paths if path.source_ref == "g-l")
    overlap = _overlap((incoming.points[-2], incoming.points[-1]),
                       (outgoing.points[0], outgoing.points[1]))

    assert incoming.to_instance_id == outgoing.from_instance_id == "g:g"
    assert overlap == 0.0
    assert _assert_exact_residual_diagnostics(paths, diagnostics) == set()


def test_relation_scene_paths_keep_their_resolved_fixed_endpoints():
    paths, marks, diagnostics = _gate_chain((INCOMING, OUTGOING))
    incoming = next(path for path in paths if path.source_ref == "f-g")
    outgoing = next(path for path in paths if path.source_ref == "g-l")

    assert incoming.from_instance_id == "f:f"
    assert incoming.to_instance_id == "g:g"
    assert outgoing.from_instance_id == "g:g"
    assert outgoing.to_instance_id == "l:l"
    assert incoming.points[0] == pytest.approx((marks["f:f"].bounds[0] + marks["f:f"].bounds[2],
                                                marks["f:f"].bounds[1] + marks["f:f"].bounds[3] / 2))
    assert outgoing.points[-1] == pytest.approx((marks["l:l"].bounds[0],
                                                  marks["l:l"].bounds[1] + marks["l:l"].bounds[3] / 2))
    _assert_exact_residual_diagnostics(paths, diagnostics)


def test_mirrored_span_end_approach_keeps_shared_endpoint_and_avoids_reuse():
    source = _item("f", D(2026, 2, 15), D(2026, 2, 20))
    node = _item("g", D(2026, 2, 1), D(2026, 2, 10))
    successor = _item("l", D(2026, 2, 10), D(2026, 2, 16))
    incoming = {"id": "f-g", "from": {"object": "f", "endpoint": "start"},
                "to": {"object": "g", "endpoint": "end"}}
    outgoing = {"id": "g-l", "from": {"object": "g", "endpoint": "end"},
                "to": {"object": "l", "endpoint": "start"}}
    paths, marks, diagnostics = _compose(
        (source, node, successor), _rows((source,), (node,), (successor,)),
        (outgoing, incoming), window=(D(2026, 1, 20), D(2026, 5, 20)),
    )
    arrival = next(path for path in paths if path.source_ref == "f-g")
    departure = next(path for path in paths if path.source_ref == "g-l")
    node_right = marks["g:g"].bounds[0] + marks["g:g"].bounds[2]
    node_middle = marks["g:g"].bounds[1] + marks["g:g"].bounds[3] / 2

    assert arrival.to_instance_id == departure.from_instance_id == "g:g"
    assert arrival.points[-1] == departure.points[0] == pytest.approx((node_right, node_middle))
    assert _overlap((arrival.points[-2], arrival.points[-1]),
                    (departure.points[0], departure.points[1])) == 0.0
    _assert_exact_residual_diagnostics(paths, diagnostics)


def test_multiple_arrivals_then_departure_restore_public_order_and_diagnose_all_residuals():
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
        (first, second, node, successor), _rows((first,), (second,), (node,), (successor,)), declared,
        window=(D(2026, 1, 20), D(2026, 5, 20)),
    )

    assert tuple(path.source_ref for path in paths) == tuple(item["id"] for item in declared)
    assert {path.source_ref for path in paths} == {"a-g", "b-g", "g-l"}
    assert all(path.to_instance_id == "g:g" for path in paths if path.source_ref in {"a-g", "b-g"})
    assert next(path for path in paths if path.source_ref == "g-l").from_instance_id == "g:g"
    residuals = _assert_exact_residual_diagnostics(paths, diagnostics)
    # Do not assume all arrivals are mutually disjoint: any actual same-direction residual must be reported too.
    assert all(node_id == "g:g" for node_id, _ in residuals)


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
def test_cycle_keeps_declared_scene_order_and_exactly_diagnoses_every_residual(relations):
    first = _item("a", D(2026, 2, 10), D(2026, 2, 20))
    second = _item("b", D(2026, 2, 10), D(2026, 2, 20))
    paths, _, diagnostics = _compose(
        (first, second), _rows((first,), (second,)), relations,
        window=(D(2026, 1, 20), D(2026, 5, 20)), max_bends=0,
    )

    assert tuple(path.source_ref for path in paths) == tuple(item["id"] for item in relations)
    assert len(paths) == 2
    residuals = _assert_exact_residual_diagnostics(paths, diagnostics)
    assert residuals, "cyclic residual fixture must exercise diagnosed overlap rather than vacuous success"


def test_repeated_opaque_instances_are_not_conflated_by_object_identity():
    source = _item("f", D(2026, 2, 1), D(2026, 2, 6))
    node_one = replace(gate("g", date(2026, 2, 10)), item_id="gate:one,opaque")
    node_two = replace(gate("g", date(2026, 2, 10)), item_id="gate:two,opaque")
    target = _item("l", D(2026, 2, 12), D(2026, 2, 18))
    rows = (
        *_rows((source,)),
        ReviewRowProjection("node-row-one", "Gate one", "", "g", (node_one,)),
        ReviewRowProjection("node-row-two", "Gate two", "", "g", (node_two,)),
        *_rows((target,)),
    )
    relations = (
        {"id": "f-g", "from": {"object": "f", "endpoint": "end"},
         "to": {"object": "g", "endpoint": "end"}},
        {"id": "g-l", "from": {"object": "g", "endpoint": "end"},
         "to": {"object": "l", "endpoint": "start"}},
    )
    paths, _, diagnostics = _compose(
        (source, node_one, node_two, target), rows, relations,
        window=(D(2026, 1, 20), D(2026, 5, 20)),
    )

    assert len(paths) == 4  # both relations are projected to both opaque gate instances
    incoming_nodes = {path.to_instance_id for path in paths if path.source_ref == "f-g"}
    outgoing_nodes = {path.from_instance_id for path in paths if path.source_ref == "g-l"}
    assert incoming_nodes == outgoing_nodes == {
        "node-row-one:gate:one,opaque", "node-row-two:gate:two,opaque",
    }
    assert _assert_exact_residual_diagnostics(paths, diagnostics) == _terminal_segment_residuals(paths)
