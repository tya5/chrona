"""`relationRouting.entry: side-when-free` enters a span start (or the mirrored end) horizontally (#1030).

Synthetic projections only, routed by the real surface composer. A relation's last segment is the entry: horizontal at
the bar's mid height means it arrives from the side, vertical means it drops onto the bar's corner.
"""
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from chrona.presentation.layout.sources import MeasuredSources, SourceInput
from chrona.presentation.layout.model import RelationUnroutableMode
from chrona.presentation.model.projection import ReviewItem, ReviewProjection, ReviewRowProjection
from chrona.presentation.surface_pipeline import compose_review_surface

from tests.unit.chrona.presentation.scene.test_v05_builder import (
    _Font, _manifest, _theme, _title_measurement, build_surface_input, surface_content,
)

D = date


def _item(oid, start, end, track="stacked"):
    return ReviewItem(oid, oid.upper(), "span", {"start": start, "end": end}, None, None, (), item_id=oid,
                      source_kind="primary", track=track)


def _route(items, rows, relation, entry, *, max_bends=4, window=None, distribution="fill", max_detour=2.0, diagnostics=False,
           allow_suppressed=False, search="first-fit"):
    """Return (points, plan marks) of the single relation path for one declared entry policy."""
    all_items = tuple(items)
    window = window or (min(i.planned["start"] for i in all_items), max(i.planned["end"] for i in all_items))
    projection = ReviewProjection(all_items, window, (), (), tuple(rows))
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8),
                                   "timeline.mark.blockSize": Decimal(8)})
    manifest = replace(_manifest("title", "table", "timeline", "timeline-axis"), relation_entry=entry, row_distribution=distribution,
                       relation_max_bends=max_bends, relation_max_detour_ratio=max_detour, relation_search=search,
                       relation_unroutable=RelationUnroutableMode.SUPPRESS)
    value = build_surface_input(projection=projection, surface_content=surface_content(
                              relations=(relation,), relation_overflow_declared=True),
                              layout_manifest=manifest, resolved_theme=_theme(), font_metrics=_Font(),
                              measured_sources=measurement, capabilities={"svg": True})
    surface = compose_review_surface(value)
    paths = [p for p in surface.primitives if p.scene_id.startswith("relation:") and not p.scene_id.startswith("relation-label")]
    assert len(paths) <= 1 if allow_suppressed else len(paths) == 1
    marks = {p.scene_id: p for p in surface.primitives if p.scene_id.startswith("planned:")}
    if diagnostics:
        return paths[0].points if paths else (), marks, (
            *surface.diagnostics, *(info.scene_diagnostic() for info in surface.info_diagnostics))
    return paths[0].points if paths else (), marks


def _rows(*groups):
    return [ReviewRowProjection(g[0].object_id, g[0].title, "", g[0].object_id, tuple(g)) for g in groups]


def _horizontal_last(points):
    return points[-2][1] == points[-1][1]


def _bends(points):
    return sum(1 for a, b, c in zip(points, points[1:], points[2:]) if (a[0] == b[0]) != (b[0] == c[0]))


def _assert_closed_contact_free(points, marks, *, source="a", target="b"):
    """Assert only the declared terminal point may touch its own primary mark."""
    from chrona.presentation.layout.obstacles import (
        ObstacleRect, ObstacleSegment, segment_closed_rect_contact_interval,
    )

    for mark in marks.values():
        x, y, width, height = mark.bounds
        rect = ObstacleRect(x, y, x + width, y + height)
        for index, (start, end) in enumerate(zip(points, points[1:])):
            contact = segment_closed_rect_contact_interval(ObstacleSegment(start, end), rect)
            if contact is None:
                continue
            terminal_source = mark.source_ref == source and index == 0 and contact == (0.0, 0.0)
            terminal_target = (mark.source_ref == target and index == len(points) - 2
                               and contact == (1.0, 1.0))
            assert terminal_source or terminal_target, (mark.source_ref, index, contact, points)


A = _item("a", D(2026, 2, 1), D(2026, 2, 8))
B = _item("b", D(2026, 2, 12), D(2026, 2, 20))
DEP = {"id": "dep", "from": {"object": "a", "endpoint": "end"}, "to": {"object": "b", "endpoint": "start"}}


def test_a_source_on_the_left_with_free_space_enters_the_start_horizontally_at_mid_height():
    points, marks = _route((A, B), _rows((A,), (B,)), DEP, "side-when-free")
    mark = marks["planned:b:b"]
    assert _horizontal_last(points)
    assert points[-1][0] == pytest.approx(mark.bounds[0])
    assert points[-1][1] == pytest.approx(mark.bounds[1] + mark.bounds[3] / 2)


def test_any_can_choose_the_same_minimal_bend_side_route_without_entry_preference():
    any_points, marks = _route((A, B), _rows((A,), (B,)), DEP, "any", search="best")
    side_points, _ = _route((A, B), _rows((A,), (B,)), DEP, "side-when-free", search="best")
    assert _horizontal_last(any_points)
    assert _bends(any_points) == 2
    assert any_points == side_points
    _assert_closed_contact_free(any_points, marks)


def test_a_source_on_the_right_of_a_finish_endpoint_enters_the_end_horizontally_mirrored():
    late = _item("a", D(2026, 2, 14), D(2026, 2, 26))
    early = _item("b", D(2026, 2, 1), D(2026, 2, 10))
    relation = {"id": "ff", "from": {"object": "a", "endpoint": "end"}, "to": {"object": "b", "endpoint": "end"}}
    points, marks = _route((late, early), _rows((late,), (early,)), relation, "side-when-free",
                           window=(D(2026, 1, 25), D(2026, 3, 10)))
    assert _horizontal_last(points)
    mark = marks["planned:b:b"]
    assert points[-1][0] == pytest.approx(mark.bounds[0] + mark.bounds[2])
    assert points[-2][0] > points[-1][0]
    _assert_closed_contact_free(points, marks)


def test_a_source_not_on_the_approach_side_keeps_the_order():
    # The source ends after the target starts: it is not left of the start edge.
    right = _item("a", D(2026, 2, 10), D(2026, 2, 24))
    target = _item("b", D(2026, 2, 12), D(2026, 2, 20))
    window = (D(2026, 1, 25), D(2026, 3, 10))
    first, marks = _route((right, target), _rows((right,), (target,)), DEP, "any", window=window)
    second, _ = _route((right, target), _rows((right,), (target,)), DEP, "side-when-free", window=window)
    assert first == second
    _assert_closed_contact_free(first, marks)


def test_a_blocked_corridor_keeps_the_order():
    # Another mark of the target's own row sits in the stub space right before the start.
    shared_b, blocker = _item("b", D(2026, 2, 12), D(2026, 2, 20), "shared"), _item("c", D(2026, 2, 10), D(2026, 2, 12), "shared")
    rows = _rows((A,), (shared_b, blocker))
    first, _, first_diagnostics = _route((A, shared_b, blocker), rows, DEP, "any", diagnostics=True,
                                         allow_suppressed=True)
    second, _, second_diagnostics = _route((A, shared_b, blocker), rows, DEP, "side-when-free",
                                           diagnostics=True, allow_suppressed=True)
    assert first == second == ()
    assert any(item.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for item in first_diagnostics)
    assert any(item.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for item in second_diagnostics)


def test_no_room_between_the_start_and_the_timeline_edge_keeps_the_order():
    # The target starts at the first day of the window: a stub would leave the timeline.
    edge = _item("b", D(2026, 2, 1), D(2026, 2, 6))
    source = _item("a", D(2026, 1, 20), D(2026, 1, 25))
    window = (D(2026, 2, 1), D(2026, 2, 6))
    first, _, first_diagnostics = _route((source, edge), _rows((source,), (edge,)), DEP, "any", window=window,
                                        diagnostics=True, allow_suppressed=True)
    second, _, diagnostics = _route((source, edge), _rows((source,), (edge,)), DEP, "side-when-free", window=window,
                                    diagnostics=True, allow_suppressed=True)
    assert first == second == ()  # Layout suppress does not invoke legacy visible overflow.
    assert any(item.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for item in first_diagnostics)
    assert any(item.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for item in diagnostics)


def test_a_narrow_gap_requires_extra_bends_for_the_declared_stub_and_obeys_max_bends():
    # One day between the source end and the target start on a long window: the stub is wider than the gap, so the
    # declared stub must come round its tip; an unconstrained horizontal last leg may be shorter than the stub.
    near = _item("b", D(2026, 2, 9), D(2026, 2, 20))
    window = (D(2026, 1, 1), D(2027, 2, 1))
    drop, drop_marks = _route((A, near), _rows((A,), (near,)), DEP, "any", window=window, search="best")
    side, side_marks = _route((A, near), _rows((A,), (near,)), DEP, "side-when-free", window=window, search="best")
    assert _horizontal_last(side) and _horizontal_last(drop)
    assert _bends(side) <= 4 and _bends(drop) <= 4
    assert abs(side[-1][0] - side[-2][0]) >= 11  # head 10 + clearance 1
    assert abs(drop[-1][0] - drop[-2][0]) >= 11
    assert _bends(side) == 4 and _bends(drop) == 4
    _assert_closed_contact_free(side, side_marks)
    _assert_closed_contact_free(drop, drop_marks)
    limited, _, limited_diagnostics = _route((A, near), _rows((A,), (near,)), DEP, "side-when-free",
                                              max_bends=3, window=window, search="best", diagnostics=True,
                                              allow_suppressed=True)
    assert limited == ()
    assert any(item.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for item in limited_diagnostics)
