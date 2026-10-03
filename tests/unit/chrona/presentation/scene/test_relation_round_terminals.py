"""Round terminals (`circle`, `open-circle`, `dot`) are centred on the endpoint and the line touches them (#1044).

Synthetic projections routed by the real surface composer. For a span the endpoint is the start or end edge at the
mark's vertical centre. The SVG marker's centre is derived from the completed Scene facts: a source circle lies
behind the first route point (its reference is the path start, `attachmentOffset` 0) and a target circle ahead of the
last route point (reference at the path end, `attachmentOffset` = diameter).
"""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from math import hypot

import pytest

from chrona.presentation.layout.sources import MeasuredSources, SourceInput
from chrona.presentation.model.projection import ReviewItem, ReviewProjection, ReviewRowProjection
from chrona.presentation.scene.v05_builder import build_scene_input, compose_review_surface

from tests.unit.chrona.presentation.scene.test_v05_builder import (
    _Font, _manifest, _theme, _title_measurement, surface_content,
)

D = date


def _item(oid, start, end, track="stacked"):
    return ReviewItem(oid, oid.upper(), "span", {"start": start, "end": end}, None, None, (), item_id=oid,
                      source_kind="primary", track=track)


def _compose(items, rows, relation, source_shape, target_shape, *, head=6, entry="any", radius=None):
    theme = _theme()
    for name, shape in (("src", source_shape), ("dst", target_shape)):
        theme["body"]["values"][name] = {"type": "marker", "value": {"shape": shape, "headLength": head,
                                                                     "headWidth": head, "attachmentOffset": 0}}
    theme["body"]["roles"]["relationSourceTerminal"] = {"marker": "src"}
    theme["body"]["roles"]["relationTargetTerminal"] = {"marker": "dst"}
    projection = ReviewProjection(tuple(items), (min(i.planned["start"] for i in items), max(i.planned["end"] for i in items)),
                                  (), (), tuple(rows))
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8),
                                   "timeline.mark.blockSize": Decimal(8),
                                   **({"timeline.relation.cornerRadius": Decimal(radius)} if radius else {})})
    manifest = replace(_manifest("title", "table", "timeline", "timeline-axis"), relation_entry=entry)
    value = build_scene_input(projection=projection, surface_content=surface_content(relations=(relation,)),
                              layout_manifest=manifest, resolved_theme=theme, font_metrics=_Font(),
                              measured_sources=measurement, capabilities={"svg": True})
    surface = compose_review_surface(value)
    paths = [p for p in surface.primitives if p.scene_id.startswith("relation:") and not p.scene_id.startswith("relation-label")]
    assert len(paths) == 1
    marks = {p.scene_id: p for p in surface.primitives if p.scene_id.startswith("planned:")}
    return paths[0], marks


def _rows(*groups):
    return [ReviewRowProjection(g[0].object_id, g[0].title, "", g[0].object_id, tuple(g)) for g in groups]


def _unit(a, b):
    length = hypot(b[0] - a[0], b[1] - a[1])
    return ((b[0] - a[0]) / length, (b[1] - a[1]) / length)


def _centre(path, role):
    """The marker centre implied by the completed facts (reference point and offset), in Scene coordinates."""
    if role == "source":
        direction, point, marker = _unit(path.points[0], path.points[1]), path.points[0], path.marker_start
        # reference at marker x = head_length - attachment_offset; the centre is half a head from the marker's x=0
        behind = marker.head_length - marker.attachment_offset - marker.head_length / 2
    else:
        direction, point, marker = _unit(path.points[-2], path.points[-1]), path.points[-1], path.marker_end
        behind = marker.head_length - marker.attachment_offset - marker.head_length / 2
    return (point[0] - direction[0] * behind, point[1] - direction[1] * behind)


A = _item("a", D(2026, 2, 1), D(2026, 2, 8))
B = _item("b", D(2026, 2, 12), D(2026, 2, 20))
DEP = {"id": "dep", "from": {"object": "a", "endpoint": "end"}, "to": {"object": "b", "endpoint": "start"}}
SHAPES = ["circle", "open-circle", "dot"]


def _end_port(mark):
    x, y, w, h = mark.bounds
    return (x + w, y + h / 2)


def _start_port(mark):
    x, y, w, h = mark.bounds
    return (x, y + h / 2)


@pytest.mark.parametrize("shape", SHAPES)
def test_round_terminals_are_centred_on_the_span_edges_at_mid_height_and_touch_the_line(shape):
    path, marks = _compose((A, B), _rows((A,), (B,)), DEP, shape, shape)
    source_centre, target_centre = _centre(path, "source"), _centre(path, "target")
    assert source_centre == pytest.approx(_end_port(marks["planned:a:a"]))
    assert target_centre == pytest.approx(_start_port(marks["planned:b:b"]))
    radius = path.marker_start.head_length / 2
    assert hypot(path.points[0][0] - source_centre[0], path.points[0][1] - source_centre[1]) == pytest.approx(radius)
    assert hypot(path.points[-1][0] - target_centre[0], path.points[-1][1] - target_centre[1]) == pytest.approx(radius)


SA, SB = _item("a", D(2026, 2, 1), D(2026, 2, 8), "shared"), _item("b", D(2026, 2, 12), D(2026, 2, 20), "shared")
SA, SB = _item("a", D(2026, 2, 1), D(2026, 2, 8), "shared"), _item("b", D(2026, 2, 12), D(2026, 2, 20), "shared")
UA, UB = _item("a", D(2026, 2, 1), D(2026, 2, 8)), _item("b", D(2026, 2, 10), D(2026, 2, 20))
EXITS = {  # exit name: (items, row layout)
    "horizontal": ((SA, SB), lambda: _rows((SA, SB))),     # one shared row: the end port at mid height is nearest
    "downward": ((A, B), lambda: _rows((A,), (B,))),       # the target row is below the source
    "upward": ((UA, UB), lambda: _rows((UB,), (UA,))),     # the target row is above the source
}


def _mark(marks, oid):
    return next(mark for key, mark in marks.items() if key.endswith(":" + oid))


@pytest.mark.parametrize("exit_name", sorted(EXITS))
def test_the_centre_rule_holds_whichever_side_the_route_leaves_from(exit_name):
    items, rows = EXITS[exit_name]
    path, marks = _compose(items, rows(), DEP, "circle", "dot")
    direction = _unit(path.points[0], path.points[1])
    assert ("horizontal" if direction[1] == 0 else "downward" if direction[1] > 0 else "upward") == exit_name
    assert _centre(path, "source") == pytest.approx(_end_port(_mark(marks, "a")))
    assert _centre(path, "target") == pytest.approx(_start_port(_mark(marks, "b")))
    radius = path.marker_start.head_length / 2
    first, last = path.points[0], path.points[-1]
    assert hypot(first[0] - _end_port(_mark(marks, "a"))[0], first[1] - _end_port(_mark(marks, "a"))[1]) == pytest.approx(radius)
    assert hypot(last[0] - _start_port(_mark(marks, "b"))[0], last[1] - _start_port(_mark(marks, "b"))[1]) == pytest.approx(radius)


def test_a_triangular_head_keeps_its_tip_at_the_port_and_the_route_is_untrimmed():
    path, marks = _compose((A, B), _rows((A,), (B,)), DEP, "triangle", "triangle")
    assert path.points[0] == pytest.approx(_end_port(marks["planned:a:a"]))
    assert path.points[-1] == pytest.approx(_start_port(marks["planned:b:b"]))
    assert path.marker_end.attachment_offset == 0.0 and not path.marker_end.centred
