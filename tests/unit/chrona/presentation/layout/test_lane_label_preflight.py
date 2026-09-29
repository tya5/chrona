from types import SimpleNamespace

from chrona.presentation.layout.lane_label_preflight import lane_label_row_requirements
from chrona.presentation.layout.lane_projection import LaneProjectionInstance
from chrona.presentation.layout.lane_subtracks import (
    LaneFacetFootprint, LaneItemFootprints, LaneItemSubtrack, LaneSubtrack,
    LaneSubtrackPlan,
)
from chrona.presentation.layout.obstacles import ObstacleRect
from chrona.presentation.layout.surface_quality import ScalePlacement


def _label(member: str, source: str, lane: str = "lane"):
    return SimpleNamespace(placement_id=f"name:{member}", source_ref=source,
                           lane_id=lane, member_id=member, width=10.0, height=4.0,
                           gap=1.0, candidates=("end", "start"))


def test_measured_overlapping_end_intervals_create_finite_stagger_rows():
    first = LaneItemFootprints("a", LaneProjectionInstance("r", "a", "a", "primary"),
                               (LaneFacetFootprint("a-mark", ObstacleRect(10, 2, 20, 8)),))
    second = LaneItemFootprints("b", LaneProjectionInstance("r", "b", "b", "primary"),
                                (LaneFacetFootprint("b-mark", ObstacleRect(15, 2, 25, 8)),))
    plan = LaneSubtrackPlan((LaneSubtrack("lane", 1, 10, 0, 10),), (
        LaneItemSubtrack("a", first.projection_instance_id, "lane", 0, 0),
        LaneItemSubtrack("b", second.projection_instance_id, "lane", 0, 0),
    ))
    scale = ScalePlacement("surface", "completed", None, None, 0, 100, 0, 1)

    requirements = lane_label_row_requirements(
        (SimpleNamespace(**{**vars(_label("a", "a")), "candidates": ("end",)}),
         SimpleNamespace(**{**vars(_label("b", "b")), "candidates": ("end",)})),
        scale, plan, (first, second),
        timeline_bounds=(0, 100), row_padding=2,
    )

    # The finite envelope reserves a measured level and clearance for each
    # label, even when the interval lower bound happens to agree on two levels.
    assert requirements == {"lane": 22.0}


def test_disjoint_measured_intervals_share_one_stagger_row():
    first = LaneItemFootprints("a", LaneProjectionInstance("r", "a", "a", "primary"),
                               (LaneFacetFootprint("a-mark", ObstacleRect(10, 2, 20, 8)),))
    second = LaneItemFootprints("b", LaneProjectionInstance("r", "b", "b", "primary"),
                                (LaneFacetFootprint("b-mark", ObstacleRect(60, 2, 70, 8)),))
    plan = LaneSubtrackPlan((LaneSubtrack("lane", 1, 10, 0, 10),), (
        LaneItemSubtrack("a", first.projection_instance_id, "lane", 0, 0),
        LaneItemSubtrack("b", second.projection_instance_id, "lane", 0, 0),
    ))
    scale = ScalePlacement("surface", "completed", None, None, 0, 100, 0, 1)

    requirements = lane_label_row_requirements(
        (_label("a", "a"), _label("b", "b")), scale, plan, (first, second),
        timeline_bounds=(0, 100), row_padding=2,
    )

    # Disjoint inline intervals share the interval lower bound, but the
    # conservative envelope accounts for later mark/label obstructions.
    assert requirements == {"lane": 22.0}
