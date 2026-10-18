"""Relation corridors keep off the plot's own inline edges (#1683)."""
from __future__ import annotations

from chrona.presentation.layout.surface_routes import ROUTE_EDGE_CLEARANCE, inset_route_bounds


def test_the_route_region_is_inset_from_both_inline_edges():
    left, top, right, bottom = inset_route_bounds((552.0, 100.0, 1572.0, 800.0), [700.0, 900.0])
    assert (left, right) == (552.0 + ROUTE_EDGE_CLEARANCE, 1572.0 - ROUTE_EDGE_CLEARANCE)
    assert (top, bottom) == (100.0, 800.0)


def test_a_port_beyond_the_inset_keeps_the_region_open_to_it():
    left, _, right, _ = inset_route_bounds((552.0, 0.0, 1572.0, 10.0), [553.0, 1571.0])
    assert left == 553.0 and right == 1571.0


def test_ports_outside_the_region_do_not_widen_it():
    left, _, right, _ = inset_route_bounds((552.0, 0.0, 1572.0, 10.0), [100.0, 2000.0])
    assert left == 552.0 + ROUTE_EDGE_CLEARANCE and right == 1572.0 - ROUTE_EDGE_CLEARANCE
