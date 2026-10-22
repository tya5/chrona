"""Finite connector boundary ports are Layout geometry, not Scene offsets."""
from __future__ import annotations

from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.ports import (
    coincident_endpoint_port_ids, connector_boundary_port, connector_boundary_ports,
    connector_egress_candidates,
)
from chrona.presentation.layout.surface_quality import MarkPlacement


def _mark(shape: str) -> MarkPlacement:
    bounds = Rect(Decimal(10), Decimal(20), Decimal(8), Decimal(8))
    return MarkPlacement("planned:item", "item", bounds, (10, 24), (18, 24), mark_shape=shape)


def test_span_start_finish_are_fixed_completed_ports() -> None:
    mark = _mark("span")
    assert connector_boundary_ports(mark, "start", (100, 100)) == (("start", (10, 24)),)
    assert connector_boundary_ports(mark, "finish", (0, 0)) == (("end", (18, 24)),)
    assert connector_boundary_ports(mark, "end", (0, 0)) == (("end", (18, 24)),)


@pytest.mark.parametrize(("endpoint", "start", "finish", "expected"), [
    ("start", None, (18, 24), ()),
    ("finish", (10, 24), None, ()),
    ("end", (10, 24), None, ()),
    ("finish", None, (18, 24), (("end", (18, 24)),)),
    ("start", (10, 24), None, (("start", (10, 24)),)),
])
def test_temporally_unavailable_span_endpoint_has_no_boundary_candidate(
        endpoint, start, finish, expected):
    mark = MarkPlacement("actual:item", "item", Rect(Decimal(10), Decimal(20), Decimal(8), Decimal(8)),
                         start, finish)
    assert connector_boundary_ports(mark, endpoint, (0, 0)) == expected
    candidates = connector_egress_candidates(mark, endpoint, (0, 0), ())
    if not expected:
        assert candidates == ()
    else:
        semantic = expected[0][1]
        assert candidates and all(candidate.semantic_port == semantic for candidate in candidates)


def test_direct_temporal_port_helper_raises_bounded_anchor_diagnostic_when_absent():
    mark = MarkPlacement("actual:item", "item", Rect(Decimal(10), Decimal(20), Decimal(8), Decimal(8)),
                         None, (18, 24))
    with pytest.raises(LayoutError) as caught:
        connector_boundary_port(mark, "start", (0, 0))
    assert caught.value.diagnostic_id == "E_PRESENTATION_ANCHOR_MISSING"
    assert caught.value.path == "/layout/connectorPort"


def test_point_ports_are_finite_deterministic_and_not_center() -> None:
    mark = _mark("point")
    candidates = connector_boundary_ports(mark, "at", (30, 40))
    assert len(candidates) == 4
    assert candidates[0] == ("end", (18, 24))
    assert candidates[1] == ("below", (14, 28))
    assert (14, 24) not in [port for _, port in candidates]
    assert candidates == connector_boundary_ports(mark, "at", (30, 40))


def test_body_port_uses_same_finite_boundary_policy() -> None:
    assert connector_boundary_ports(_mark("span"), "body", (14, 0))[0] == ("above", (14, 20))


@pytest.mark.parametrize("shape", ("span", "point"))
@pytest.mark.parametrize("endpoint", ("start", "finish", "end", "at", "body"))
@pytest.mark.parametrize("entry", ("any", "side", "side-when-free"))
@pytest.mark.parametrize("toward", ((-20, 24), (50, 24)))
@pytest.mark.parametrize("sibling_count", (0, 10, 50))
def test_surface_port_product_is_bounded_independently_of_comparison_siblings(
        shape, endpoint, entry, toward, sibling_count) -> None:
    """#1298: four source exits × (four target exits + one stub) <= 20.

    Overlapping comparison instances alter the exposed outline, not the
    number of candidate ports. Surface source exits never request a stub.
    """
    mark = _mark(shape)
    siblings = tuple(MarkPlacement(
        f"planned:comparison:{index}", "item", mark.bounds,
        mark.start_port, mark.end_port, mark_shape=shape,
    ) for index in range(sibling_count))
    source = connector_egress_candidates(mark, endpoint, toward, siblings)
    target = connector_egress_candidates(
        mark, endpoint, toward, siblings, entry=entry,
        stub_length=4, stub_free=lambda candidate: True,
    )
    assert 1 <= len(source) <= 4
    assert 1 <= len(target) <= 5
    assert len(source) * len(target) <= 20
    assert sum(candidate.stub for candidate in target) <= 1
    assert not any(candidate.stub for candidate in source)
    assert len(source) == len(connector_egress_candidates(mark, endpoint, toward, ()))
    assert len(target) == len(connector_egress_candidates(
        mark, endpoint, toward, (), entry=entry,
        stub_length=4, stub_free=lambda candidate: True,
    ))


def test_overlapping_comparison_sibling_exposes_temporal_endpoint_without_moving_it() -> None:
    current = MarkPlacement("planned:item", "item", Rect(Decimal(10), Decimal(20), Decimal(20), Decimal(8)),
                            (10, 24), (30, 24))
    scenario = MarkPlacement("planned:scenario:item", "item",
                             Rect(Decimal(5), Decimal(20), Decimal(30), Decimal(8)), (5, 24), (35, 24))
    unrelated = MarkPlacement("planned:other", "other",
                              Rect(Decimal(30), Decimal(20), Decimal(15), Decimal(8)), (30, 24), (45, 24))
    candidates = connector_egress_candidates(current, "end", (50, 40), (scenario, unrelated))
    assert len(candidates) == 3
    assert candidates[0].semantic_port == (30, 24)
    assert candidates[0].exposed_port == (35, 24)
    assert candidates[0].host_ids == ("planned:item", "planned:scenario:item")
    assert {candidate.side for candidate in candidates} == {"end", "above", "below"}
    assert all(candidate.semantic_port == (30, 24) for candidate in candidates)


def test_span_start_candidates_mirror_the_finish_and_keep_the_temporal_port() -> None:
    mark = _mark("span")
    candidates = connector_egress_candidates(mark, "start", (-20, 24), ())
    assert {candidate.side for candidate in candidates} == {"start", "above", "below"}
    assert all(candidate.semantic_port == (10, 24) for candidate in candidates)
    assert next(candidate for candidate in candidates if candidate.side == "start").exposed_port == (10, 24)


@pytest.mark.parametrize(("endpoint", "side", "semantic", "exposed", "blocker"), (
    ("start", "above", (10, 24), (10, 20), (9.5, 21.5, 10.5, 22.5)),
    ("start", "below", (10, 24), (10, 28), (9.5, 25.5, 10.5, 26.5)),
    ("end", "above", (18, 24), (18, 20), (17.5, 21.5, 18.5, 22.5)),
    ("end", "below", (18, 24), (18, 28), (17.5, 25.5, 18.5, 26.5)),
))
def test_span_above_and_below_corridors_are_checked_against_shared_obstacle_index(
        endpoint, side, semantic, exposed, blocker) -> None:
    mark = _mark("span")
    candidates = connector_egress_candidates(mark, endpoint, (50, 40), ())
    candidate = next(item for item in candidates if item.side == side)
    assert candidate.semantic_port == semantic
    assert candidate.exposed_port == exposed

    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle(mark.placement_id, "mark", "timeline",
                              ObstacleRect(10, 20, 18, 28)))
    index.add(SurfaceObstacle("blocking-label", "label", "timeline", ObstacleRect(*blocker)))
    assert index.egress_collisions(ObstacleSegment(candidate.semantic_port, candidate.exposed_port),
                                   host_ids=(mark.placement_id,),
                                   classes=("mark", "label")) == (
        index.select(classes=("label",))[0],)


def test_coincident_port_aliases_are_exact_and_host_scoped() -> None:
    index = SurfaceObstacleIndex()
    for placement_id, x in (("port:planned:item:end", 18),
                            ("port:planned:scenario:item:start", 18),
                            ("port:planned:other:end", 18),
                            ("port:planned:item:above", 14)):
        index.add(SurfaceObstacle(placement_id, "port", "timeline",
                                  ObstacleRect(x - 0.01, 24 - 0.01, x + 0.01, 24 + 0.01)))
    assert coincident_endpoint_port_ids(index, (18, 24),
                                         ("planned:item", "planned:scenario:item")) == (
        "port:planned:item:end", "port:planned:scenario:item:start")


# --- #1913: ports of a compound point glyph come from its painted outline -------------------------

def _inset_compound_mark(*, stroke: float = 1.0, bounds=(100.0, 50.0, 20.0, 20.0)) -> MarkPlacement:
    """A two-part glyph (filled diamond plus ring) painted inside the middle of its viewport."""
    from chrona.presentation.layout.mark_geometry import SymbolPartPlacement, symbol_parts
    x, y, w, h = bounds
    glyph = {"shape": "glyph", "viewport": {"inlineSize": 10, "blockSize": 10}, "parts": [
        {"paint": "fill", "data": "M 5 2 L 8 5 L 5 8 L 2 5 Z"},
        {"paint": "stroke", "data": "M 3 3 L 7 3 L 7 7 L 3 7 Z", "strokeWidth": 0.5,
         "lineCap": "butt", "lineJoin": "miter"}]}
    parts = symbol_parts(glyph, bounds)
    # The completed fill edge as Layout adds it (complete_point_outline).
    parts = (*parts, SymbolPartPlacement(parts[0].commands, paint_mode="stroke", stroke_width=stroke))
    return MarkPlacement("planned:glyph", "glyph", Rect(*(Decimal(str(v)) for v in bounds)),
                         (x, y + h / 2), (x + w, y + h / 2), mark_shape="point", symbol_parts=parts)


def test_inset_compound_glyph_ports_touch_the_painted_outline_not_the_viewport() -> None:
    mark = _inset_compound_mark()
    # Fill diamond spans x in [104, 116] (scale 2), centre (110, 60); the outline stroke adds 0.5.
    ports = dict(connector_boundary_ports(mark, "at", (300, 60), painted=True))
    assert ports["end"] == pytest.approx((116.5, 60.0))
    assert ports["start"] == pytest.approx((103.5, 60.0))
    assert ports["above"] == pytest.approx((110.0, 53.5))
    assert ports["below"] == pytest.approx((110.0, 66.5))
    # The viewport edge is 3.5 units beyond the paint.
    assert ports["end"][0] < 120.0 - 3.0
    candidate = connector_egress_candidates(mark, "at", (300, 60), (), painted=True)[0]
    assert candidate.side == "end"
    # The leader starts on the paint and crosses the inset inside its own host to the unchanged exposed port.
    assert candidate.semantic_port == pytest.approx((116.5, 60.0))
    assert candidate.exposed_port == (120.0, 60.0)
    assert candidate.corridor == (candidate.semantic_port, candidate.exposed_port)
    assert candidate.host_ids == ("planned:glyph",)
    assert connector_boundary_port(mark, "at", (300, 60), painted=True) == pytest.approx((116.5, 60.0))


def test_relation_ports_keep_the_viewport_tips_of_a_compound_glyph() -> None:
    """Only annotation leaders opt in; relation routing is unchanged by #1913."""
    mark = _inset_compound_mark()
    assert dict(connector_boundary_ports(mark, "at", (300, 60)))["end"] == (120.0, 60.0)
    assert connector_egress_candidates(mark, "at", (300, 60), ())[0].exposed_port == (120.0, 60.0)


def test_compound_glyph_without_stroke_part_ends_exactly_on_the_fill_edge() -> None:
    mark = _inset_compound_mark()
    mark = MarkPlacement(mark.placement_id, mark.source_ref, mark.bounds, mark.start_port, mark.end_port,
                         mark_shape="point", symbol_parts=mark.symbol_parts[:2])
    assert dict(connector_boundary_ports(mark, "at", (300, 60), painted=True))["end"] == pytest.approx((116.0, 60.0))


def test_diamond_and_ordinary_point_ports_stay_on_viewport_tips() -> None:
    from chrona.presentation.layout.mark_geometry import symbol_parts
    plain = _mark("point")
    diamond = MarkPlacement("planned:d", "item", plain.bounds, (10, 24), (18, 24), mark_shape="point",
                            symbol_parts=symbol_parts({"shape": "diamond"}, (10.0, 20.0, 8.0, 8.0)))
    for mark in (plain, diamond):
        for painted in (False, True):
            assert dict(connector_boundary_ports(mark, "at", (30, 40), painted=painted)) == {
                "end": (18, 24), "start": (10, 24), "above": (14, 20), "below": (14, 28)}
            first = connector_egress_candidates(mark, "at", (30, 40), (), painted=painted)[0]
            assert first.semantic_port == first.exposed_port == (18, 24)


def test_compound_glyph_keeps_nonhost_clearance_and_registered_port_authority() -> None:
    mark = _inset_compound_mark()
    ink_port = (116.5, 60.0)
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("mark:other", "mark", "timeline", ObstacleRect(121, 55, 130, 65)))
    index.add(SurfaceObstacle("port:planned:glyph:end", "port", "timeline",
                              ObstacleRect(ink_port[0] - .01, ink_port[1] - .01, ink_port[0] + .01, ink_port[1] + .01)))
    first = connector_egress_candidates(mark, "at", (300, 60), (), painted=True)[0]
    assert coincident_endpoint_port_ids(index, first.semantic_port, ("planned:glyph",)) == ("port:planned:glyph:end",)
    # The unrelated mark still blocks the route beyond the exposed port.
    assert index.collisions(ObstacleSegment(first.exposed_port, (200, 60)), classes=("mark",))


# --- #1924: an axis in a slit between fill slices still takes the painted port -------------------

def _slit_glyph_mark(*, slit: float = 0.6, stroke: float = 1.0) -> MarkPlacement:
    """Two horizontal fill slices (like the yuya glyph) separated by a thin slit across the axis."""
    from chrona.presentation.layout.mark_geometry import SymbolPartPlacement, symbol_parts
    bounds = (100.0, 50.0, 20.0, 20.0)  # horizontal axis y=60
    half = slit / 2
    parts = symbol_parts({"shape": "glyph", "viewport": {"inlineSize": 20, "blockSize": 20}, "parts": [
        {"paint": "fill", "data": f"M 4 2 L 16 2 L 16 {10 - half} L 4 {10 - half} Z"},
        {"paint": "fill", "data": f"M 5 {10 + half} L 17 {10 + half} L 17 18 L 5 18 Z"}]}, bounds)
    for_outline = tuple(SymbolPartPlacement(part.commands, paint_mode="stroke", stroke_width=stroke) for part in parts)
    return MarkPlacement("planned:slit", "glyph", Rect(*(Decimal(str(v)) for v in bounds)),
                         (100.0, 60.0), (120.0, 60.0), mark_shape="point", symbol_parts=(*parts, *for_outline))


def test_axis_in_a_slit_between_fill_slices_takes_the_painted_port() -> None:
    mark = _slit_glyph_mark()
    ports = dict(connector_boundary_ports(mark, "at", (300, 60), painted=True))
    # Widest bounding slice edge is 117 (+0.5 stroke); narrowest start is 104 (-0.5).
    assert ports["end"] == pytest.approx((117.5, 60.0))
    assert ports["start"] == pytest.approx((103.5, 60.0))
    candidate = connector_egress_candidates(mark, "at", (300, 60), (), painted=True)[0]
    assert candidate.semantic_port == pytest.approx((117.5, 60.0))
    assert candidate.exposed_port == (120.0, 60.0)
    # Not the viewport tip, and the leader endpoint lies on the painted outline (within 0.1).
    assert abs(candidate.semantic_port[0] - 117.5) < 0.1
    # Relations keep the viewport tips.
    assert dict(connector_boundary_ports(mark, "at", (300, 60)))["end"] == (120.0, 60.0)


def test_wide_gap_between_painted_parts_is_not_bridged() -> None:
    from chrona.presentation.layout.ports import painted_cardinal_ports
    assert "end" not in painted_cardinal_ports(_slit_glyph_mark(slit=6.0))
