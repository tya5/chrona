from dataclasses import replace
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.lane_projection import LaneProjectionInstance
from chrona.presentation.layout.lane_subtracks import LaneFacetFootprint, LaneItemFootprints
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.obstacles import ObstacleRect
from chrona.presentation.layout.point_host_allocation import partition_hosted_facets
from chrona.presentation.layout.point_hosting import PointHostOccurrence, PointHostPlan, PointHostRelation


def _fixture():
    host = LaneProjectionInstance("host-source", "a", "a", "primary")
    child = LaneProjectionInstance("child-source", "p", "p", "primary")
    a = PointHostOccurrence(host, "host-row", "a", None, SimpleNamespace(instance_id="a"))
    p = PointHostOccurrence(child, "child-row", "p", None, SimpleNamespace(instance_id="p"))
    plan = PointHostPlan((a, p), (PointHostRelation(p, a, "planned"),))
    host_facet = LaneFacetFootprint("bar", ObstacleRect(0, 2, 100, 6),
                                   mark_id="planned:a", mark_block_center=4, is_mark_geometry=True)
    point = LaneFacetFootprint("gate", ObstacleRect(46, 10, 54, 18),
                              mark_id="planned:p", mark_block_center=14, is_mark_geometry=True)
    return plan, (LaneItemFootprints("a", host, (host_facet,)),
                  LaneItemFootprints("p", child, (point,)))


def test_partition_moves_facet_once_and_keeps_immutable_semantic_inventory():
    plan, units = _fixture()
    result = partition_hosted_facets(units, plan)
    assert result.semantic_units is units
    assert result.semantic_units[1].facets[0].footprint.top == 10
    assert result.physical_units[1].facets == ()
    assert result.hosted_only_instances == frozenset((units[1].projection_instance_id,))
    bar, gate = result.physical_units[0].facets
    assert gate.footprint == ObstacleRect(46, 0, 54, 8)
    assert gate.overlay_with == ("bar",) and bar.overlay_with == ("gate",)
    assert {frame.facet_id for frame in result.frames} == {"bar", "gate"}
    assert result.frames[1].semantic_instance == units[1].projection_instance_id
    assert result.frames[1].allocation_instance == units[0].projection_instance_id
    assert result.frames[1].block_offset == -10


def test_unhosted_actual_retains_its_original_allocation():
    plan, units = _fixture()
    actual = replace(units[1].facets[0], facet_id="observed", mark_id="actual:p")
    units = (units[0], replace(units[1], facets=(*units[1].facets, actual)))
    result = partition_hosted_facets(units, plan)
    assert result.physical_units[1].facets == (actual,)
    assert result.hosted_only_instances == frozenset()


def test_bound_icon_moves_but_does_not_gain_blanket_host_overlap_authority():
    plan, units = _fixture()
    icon = replace(units[1].facets[0], facet_id="icon", is_mark_geometry=False)
    units = (units[0], replace(units[1], facets=(*units[1].facets, icon)))
    with pytest.raises(LayoutError, match="E_LAYOUT_POINT_HOST_OVERLAP"):
        partition_hosted_facets(units, plan)


def test_conflicting_hosted_points_fail_instead_of_being_moved_to_another_track():
    plan, units = _fixture()
    other = LaneProjectionInstance("other-source", "q", "q", "primary")
    q = PointHostOccurrence(other, "other-row", "q", None, SimpleNamespace(instance_id="q"))
    point = replace(units[1].facets[0], facet_id="other-gate", mark_id="planned:q")
    plan = replace(plan, occurrences=(*plan.occurrences, q),
                   relations=(*plan.relations, PointHostRelation(q, plan.occurrences[0], "planned")))
    with pytest.raises(LayoutError, match="E_LAYOUT_POINT_HOST_OVERLAP"):
        partition_hosted_facets((*units, LaneItemFootprints("q", other, (point,))), plan)


def test_no_host_plan_preserves_unrelated_overlay_authority():
    _, units = _fixture()
    result = partition_hosted_facets(units, PointHostPlan())
    assert result.physical_units == units
    assert all(frame.block_offset == 0 for frame in result.frames)
