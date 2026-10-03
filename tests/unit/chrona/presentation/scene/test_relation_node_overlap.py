"""Two relations at one node never overlap, and a route has no needless bend or sub-stroke segment (#1108, #1109).

Synthetic Projects only, routed by the real surface composer; the published Scene paths are asserted.
"""
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

import pytest

from chrona.presentation.layout.sources import MeasuredSources, SourceInput
from chrona.presentation.model.projection import ReviewProjection
from chrona.presentation.scene.v05_builder import build_scene_input, compose_review_surface

from tests.unit.chrona.presentation.scene.test_relation_entry_side import D, _bends, _item, _manifest, _rows
from tests.unit.chrona.presentation.scene.test_relation_route_invariant import gate, reverses
from tests.unit.chrona.presentation.scene.test_v05_builder import _Font, _theme, _title_measurement, surface_content


def routes(items, rows, relations, entry="side-when-free", *, window, max_bends=4, max_detour=6.0, marks=False):
    projection = ReviewProjection(tuple(items), window, (), (), tuple(rows))
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8),
                                   "timeline.mark.blockSize": Decimal(8)})
    manifest = replace(_manifest("title", "table", "timeline", "timeline-axis"), relation_entry=entry,
                       row_distribution="pack", relation_max_bends=max_bends, relation_max_detour_ratio=max_detour)
    value = build_scene_input(projection=projection, surface_content=surface_content(relations=tuple(relations)),
                              layout_manifest=manifest, resolved_theme=_theme(), font_metrics=_Font(),
                              measured_sources=measurement, capabilities={"svg": True})
    surface = compose_review_surface(value)
    paths = {path.source_ref: path.points for path in surface.primitives
             if path.scene_id.startswith("relation:") and not path.scene_id.startswith("relation-label")}
    if marks:
        return paths, {item.scene_id: item.bounds for item in surface.primitives if item.scene_id.startswith("planned:")}
    return paths


def overlap(first, second) -> float:
    """The collinear overlap length of two segments (0 when they only cross or touch)."""
    (a, b), (c, d) = first, second
    if a[1] == b[1] == c[1] == d[1]:
        return min(max(a[0], b[0]), max(c[0], d[0])) - max(min(a[0], b[0]), min(c[0], d[0]))
    if a[0] == b[0] == c[0] == d[0]:
        return min(max(a[1], b[1]), max(c[1], d[1])) - max(min(a[1], b[1]), min(c[1], d[1]))
    return 0.0


def shortest(points) -> float:
    return min(abs(q[0] - p[0]) + abs(q[1] - p[1]) for p, q in zip(points, points[1:]) if p != q)


def egress_overlaps_arrival(paths, node_in, node_out) -> bool:
    """Whether the first segment of the outgoing path overlaps the last segment of the incoming one."""
    incoming, outgoing = paths[node_in], paths[node_out]
    return overlap((incoming[-2], incoming[-1]), (outgoing[0], outgoing[1])) > 1e-6


FROM = {"id": "f-g", "from": {"object": "f", "endpoint": "end"}, "to": {"object": "g", "endpoint": "start"}}
OUT = {"id": "g-l", "from": {"object": "g", "endpoint": "end"}, "to": {"object": "l", "endpoint": "start"}}


def chain(gap_days: int, *, days: int = 90, entry: str = "side-when-free"):
    f = _item("f", D(2026, 2, 1), D(2026, 2, 6))
    g = gate("g", date(2026, 2, 10))
    start = date(2026, 2, 10) + timedelta(days=gap_days)
    leop = _item("l", start, start + timedelta(days=6))
    window = (date(2026, 1, 20), date(2026, 1, 20) + timedelta(days=days))
    return routes((f, g, leop), _rows((f,), (g,), (leop,)), (FROM, OUT), entry, window=window)


@pytest.mark.parametrize("entry", ["any", "side-when-free", "side"])
@pytest.mark.parametrize("days", [60, 90, 120, 200])
def test_a_relation_never_leaves_a_gate_along_the_incoming_relations_last_segment_1109(days, entry):
    # The successor may start slightly before, at or after the gate; the outgoing path must not reuse the side the
    # incoming relation arrives on.
    for gap in (-1, 0, 1, 2):
        paths = chain(gap, days=days, entry=entry)
        assert not egress_overlaps_arrival(paths, "f-g", "g-l"), (days, gap, paths["f-g"][-2:], paths["g-l"][:2])
        assert not reverses(paths["g-l"])


def test_no_route_has_a_segment_shorter_than_the_stroke_width_1108():
    # A gate dropping to a bar whose port differs from the drop by a sliver: the route drops straight from the port.
    for days, gap in ((120, 1), (200, 2), (300, 3)):
        g = gate("a", date(2026, 2, 8))
        first = date(2026, 2, 8) + timedelta(days=gap)
        b = _item("b", first, first + timedelta(days=6))
        relation = {"id": "a-b", "from": {"object": "a", "endpoint": "end"}, "to": {"object": "b", "endpoint": "start"}}
        path = routes((g, b), _rows((g,), (b,)), (relation,), "any",
                      window=(date(2026, 1, 20), date(2026, 1, 20) + timedelta(days=days)))["a-b"]
        assert shortest(path) >= 1.0, path  # the theme's dependency stroke width is 1
        assert path[0][0] == path[1][0], "the first segment leaves the gate vertically, straight from the port"


def inside(points, bounds, inset=0.5) -> float:
    """The length of the route that runs through the interior of a mark's box (inset by half a stroke)."""
    left, top, width, height = bounds
    x0, x1, y0, y1 = left + inset, left + width - inset, top + inset, top + height - inset
    total = 0.0
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        if ay == by and y0 < ay < y1:
            total += max(0.0, min(max(ax, bx), x1) - max(min(ax, bx), x0))
        if ax == bx and x0 < ax < x1:
            total += max(0.0, min(max(ay, by), y1) - max(min(ay, by), y0))
    return total


@pytest.mark.parametrize("entry", ["any", "side-when-free", "side"])
@pytest.mark.parametrize("target_start", [D(2026, 2, 12), D(2026, 2, 20)])
def test_a_relation_from_a_bars_start_never_runs_through_its_own_bar_1114(entry, target_start):
    # A start-to-start relation leaves the bar's start; the exemption of the endpoint's own mark covers only the
    # outward stub, so the route does not cross the bar interior to reach the other side.
    source, target = _item("a", D(2026, 2, 3), D(2026, 2, 10)), _item("b", target_start, target_start + timedelta(days=6))
    relation = {"id": "ss", "from": {"object": "a", "endpoint": "start"}, "to": {"object": "b", "endpoint": "start"}}
    paths, marks = routes((source, target), _rows((source,), (target,)), (relation,), entry,
                          window=(D(2026, 1, 25), D(2026, 3, 5)), marks=True)
    for key, bounds in marks.items():
        assert inside(paths["ss"], bounds) == 0.0, (key, paths["ss"])


@pytest.mark.parametrize("entry", ["any", "side-when-free", "side"])
def test_a_relation_into_a_bars_end_never_runs_through_that_bar_1114(entry):
    source, target = _item("a", D(2026, 2, 12), D(2026, 2, 18)), _item("b", D(2026, 2, 3), D(2026, 2, 10))
    relation = {"id": "ff", "from": {"object": "a", "endpoint": "end"}, "to": {"object": "b", "endpoint": "end"}}
    paths, marks = routes((source, target), _rows((source,), (target,)), (relation,), entry,
                          window=(D(2026, 1, 25), D(2026, 3, 5)), marks=True)
    for key, bounds in marks.items():
        assert inside(paths["ff"], bounds) == 0.0, (key, paths["ff"])
