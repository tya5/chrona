from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.lane_label_preflight import lane_label_row_requirements
from chrona.presentation.layout.lane_preflight import LaneInlineFrame
from chrona.presentation.layout.lane_projection import LaneProjectionInstance
from chrona.presentation.layout.lane_subtracks import (
    LaneFacetFootprint,
    FixedLanePreflight,
    LaneItemFootprints,
    LaneSubtrackPlan,
    LaneSubtrack,
    assign_lane_subtracks,
)
from chrona.presentation.layout.lane_mark_facets import LaneFacetPort
from chrona.presentation.layout.obstacles import ObstacleRect
from chrona.presentation.layout.surface_quality import ScalePlacement
from chrona.presentation.review.lane_membership import Lane, LaneAssignment, LaneMembership


def _membership(*item_ids: str) -> LaneMembership:
    return LaneMembership(
        (Lane("lane-alpha", "group-alpha", tuple(item_ids)),),
        tuple(LaneAssignment(item_id, "lane-alpha", "group-alpha", "single", item_id)
              for item_id in item_ids),
    )


def _unit(item_id: str, facet_id: str, left: float, right: float,
          overlay_with: tuple[str, ...] = ()) -> LaneItemFootprints:
    return LaneItemFootprints(
        item_id,
        LaneProjectionInstance("row-alpha", item_id, item_id, "primary"),
        (LaneFacetFootprint(facet_id, ObstacleRect(left, 0, right, 10), overlay_with),),
    )


def test_candidate_input_identifies_invalid_semantic_port_operand():
    with pytest.raises(ValueError) as caught:
        LaneFacetPort("port-alpha", "label-anchor", (float("nan"), 4))

    assert str(caught.value).startswith("E_LAYOUT_LANE_CANDIDATE_INPUT:")
    assert "LaneFacetPort" in str(caught.value)
    assert "port_id='port-alpha'" in str(caught.value)
    assert "position=(nan, 4)" in str(caught.value)


def test_subtrack_invalid_and_bad_metric_errors_name_actual_lane_inputs():
    with pytest.raises(ValueError) as invalid:
        LaneSubtrack("lane-alpha", 1, 0, 0, 10)
    assert str(invalid.value).startswith("E_LAYOUT_LANE_SUBTRACK_INVALID:")
    assert "lane_id='lane-alpha'" in str(invalid.value)
    assert "pitch=0" in str(invalid.value)

    with pytest.raises(ValueError) as metrics:
        assign_lane_subtracks(_membership("item-alpha"),
                              (_unit("item-alpha", "mark-alpha", 0, 4),),
                              mark_band_size=0)
    assert str(metrics.value).startswith("E_LAYOUT_LANE_SUBTRACK_INPUT:")
    assert "lane metrics" in str(metrics.value)
    assert "mark_band_size=0" in str(metrics.value)


def test_fixed_lane_preflight_error_names_failed_extent():
    with pytest.raises(ValueError) as caught:
        FixedLanePreflight(
            LaneSubtrackPlan((), ()),
            LaneInlineFrame(*(Decimal(1) for _ in range(5))),
            Decimal(-2), None,
            ScalePlacement("scale-alpha", "complete", None, None, 0, 100, 0, 1),
        )
    assert str(caught.value).startswith("E_LAYOUT_LANE_PREFLIGHT_INVALID:")
    assert "natural_block_requirement=Decimal('-2')" in str(caught.value)


def test_subtrack_host_and_overlay_failures_name_lane_and_facet_operands():
    attached_without_host = LaneMembership(
        (Lane("lane-alpha", "group-alpha", ("child-alpha",)),),
        (LaneAssignment("child-alpha", "lane-alpha", "group-alpha", "attached", "host-missing"),),
    )
    with pytest.raises(ValueError) as host:
        assign_lane_subtracks(
            attached_without_host,
            (_unit("child-alpha", "child-mark", 0, 4),),
            mark_band_size=10,
        )
    assert str(host.value).startswith("E_LAYOUT_LANE_SUBTRACK_INPUT:")
    assert "item_id='child-alpha'" in str(host.value)
    assert "host_id='host-missing'" in str(host.value)

    with pytest.raises(ValueError) as overlay:
        assign_lane_subtracks(
            _membership("item-alpha", "item-beta"),
            (_unit("item-alpha", "facet-alpha", 0, 10, ("facet-beta",)),
             _unit("item-beta", "facet-beta", 0, 10)),
            mark_band_size=10,
        )
    assert str(overlay.value).startswith("E_LAYOUT_LANE_SUBTRACK_OVERLAY_INVALID:")
    assert "facet_id='facet-alpha'" in str(overlay.value)
    assert "target_facet_id='facet-beta'" in str(overlay.value)

    with pytest.raises(ValueError) as collision:
        assign_lane_subtracks(
            _membership("item-alpha"),
            (LaneItemFootprints(
                "item-alpha",
                LaneProjectionInstance("row-alpha", "item-alpha", "item-alpha", "primary"),
                (LaneFacetFootprint("facet-left", ObstacleRect(0, 0, 10, 10)),
                 LaneFacetFootprint("facet-right", ObstacleRect(2, 2, 8, 8))),
            ),),
            mark_band_size=10,
        )
    assert str(collision.value).startswith("E_LAYOUT_LANE_SUBTRACK_OVERLAY_MISSING:")
    assert "facet-left:facet-right" in str(collision.value)


def test_unplaceable_lane_track_reports_candidate_item(monkeypatch):
    import chrona.presentation.layout.lane_subtracks as module

    monkeypatch.setattr(module, "_fits_track", lambda *args, **kwargs: False)
    with pytest.raises(ValueError) as caught:
        assign_lane_subtracks(_membership("item-alpha"),
                              (_unit("item-alpha", "mark-alpha", 0, 4),),
                              mark_band_size=10)
    assert str(caught.value).startswith("E_LAYOUT_LANE_SUBTRACK_UNPLACEABLE:")
    assert "item_id='item-alpha'" in str(caught.value)
    assert "lane_id='lane-alpha'" in str(caught.value)


def test_lane_label_preflight_names_scale_and_label_measurement_inputs():
    plan = LaneSubtrackPlan((), ())
    with pytest.raises(ValueError) as caught:
        lane_label_row_requirements((), SimpleNamespace(scale_id="scale-alpha"), plan, (),
                                    timeline_bounds=(0, 100))
    assert str(caught.value).startswith("E_LAYOUT_LANE_LABEL_PREFLIGHT_INPUT:")
    assert "scale metrics" in str(caught.value)
    assert "scale_id='scale-alpha'" in str(caught.value)


def test_lane_label_preflight_identifies_bad_measured_member():
    item = _unit("member-alpha", "mark-alpha", 0, 4)
    from chrona.presentation.layout.lane_subtracks import LaneItemSubtrack, LaneSubtrackPlan

    plan = LaneSubtrackPlan((LaneSubtrack("lane-alpha", 1, 10, 0, 10),), (
        LaneItemSubtrack("member-alpha", item.projection_instance_id, "lane-alpha", 0, 0),
    ))
    scale = ScalePlacement("scale-alpha", "complete", None, None, 0, 100, 0, 1)
    label = SimpleNamespace(placement_id="label-alpha", member_id="member-alpha",
                            lane_id="lane-alpha", width=-1, height=4, gap=1,
                            candidates=("end",))
    with pytest.raises(ValueError) as caught:
        lane_label_row_requirements((label,), scale, plan, (item,), timeline_bounds=(0, 100))
    assert str(caught.value).startswith("E_LAYOUT_LANE_LABEL_PREFLIGHT_INPUT:")
    assert "placement_id='label-alpha'" in str(caught.value)
    assert "member_id='member-alpha'" in str(caught.value)
    assert "width=-1" in str(caught.value)
