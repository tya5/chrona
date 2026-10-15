from datetime import date
from decimal import Decimal as D
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.lane_label_preflight import lane_label_row_requirements
from chrona.presentation.layout.lane_projection import LaneProjectionInstance
from chrona.presentation.layout.lane_subtracks import (
    LaneFacetFootprint, LaneItemFootprints, LaneItemSubtrack, LaneSubtrack, LaneSubtrackPlan,
)
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import ObstacleRect
from chrona.presentation.layout.surface_member_labels import (
    SurfaceMemberLabelContext, build_member_label_requests,
)
from chrona.presentation.layout.surface_quality import (
    MarkPlacement, PhysicalMarkHost, ScalePlacement, SlotPlacement,
)
from chrona.presentation.layout.presentation import TrackPlacement
from chrona.presentation.model.projection import ReviewItem


def _preflight_fixture(*, label_lane="child"):
    footprints = (
        LaneItemFootprints("gate", LaneProjectionInstance("row-g", "gate", "gate", "primary"),
            (LaneFacetFootprint("gate-mark", ObstacleRect(10, 0, 12, 4)),)),
        LaneItemFootprints("host", LaneProjectionInstance("row-h", "host", "host", "primary"),
            (LaneFacetFootprint("host-mark", ObstacleRect(20, 0, 40, 4)),)),
    )
    subtracks = LaneSubtrackPlan(
        (LaneSubtrack("child", 1, 10, 0, 10), LaneSubtrack("host", 1, 10, 0, 10)),
        (LaneItemSubtrack("gate", footprints[0].projection_instance_id, "child", 0, 0),
         LaneItemSubtrack("host", footprints[1].projection_instance_id, "host", 0, 0)),
    )
    label = SimpleNamespace(placement_id="member-label:gate", source_ref="gate", lane_id=label_lane,
        member_id="gate", width=10.0, height=4.0, gap=1.0, candidates=("end", "start"))
    scale = ScalePlacement("surface", "completed", date(2026, 1, 1), date(2026, 2, 1), 0, 100, 0, 1)
    return label, scale, subtracks, footprints


def test_lane_label_demand_follows_physical_row_but_keeps_semantic_lane_validation():
    label, scale, subtracks, footprints = _preflight_fixture()

    semantic = lane_label_row_requirements((label,), scale, subtracks, footprints,
        timeline_bounds=(0, 100), row_padding=1)
    hosted = lane_label_row_requirements((label,), scale, subtracks, footprints,
        timeline_bounds=(0, 100), row_padding=1,
        physical_label_rows={label.placement_id: "host"})

    assert semantic == {"child": 16.0, "host": 11.0}
    assert hosted == {"child": 11.0, "host": 16.0}


def test_physical_label_row_must_be_present_in_preflight_rows():
    label, scale, subtracks, footprints = _preflight_fixture()
    with pytest.raises(ValueError, match="physical label row"):
        lane_label_row_requirements((label,), scale, subtracks, footprints,
            timeline_bounds=(0, 100), physical_label_rows={label.placement_id: "missing"})


def test_physical_mapping_does_not_override_semantic_lane_member_validation():
    label, scale, subtracks, footprints = _preflight_fixture(label_lane="host")
    with pytest.raises(ValueError, match="measured lane label"):
        lane_label_row_requirements((label,), scale, subtracks, footprints,
            timeline_bounds=(0, 100), physical_label_rows={label.placement_id: "host"})


def _label_request_context():
    item = ReviewItem("gate", "Review gate", "point", {"at": date(2026, 1, 10)},
        None, None, (), source_kind="primary", item_id="gate")
    row = SimpleNamespace(row_id="child-row", items=(item,), member_item_ids=("member-gate",), key_row=False)
    mark = MarkPlacement("planned:child-row:gate", "gate", Rect(D(10), D(20), D(8), D(8)),
        (14.0, 24.0), (14.0, 24.0), mark_shape="point",
        lane_row_id="child-row", lane_member_id="member-gate", lane_source_kind="primary",
        physical_host=PhysicalMarkHost("planned:host-row:host", "host-row"))
    host = MarkPlacement("planned:host-row:host", "host", Rect(D(0), D(40), D(50), D(10)),
        (0.0, 45.0), (50.0, 45.0), mark_shape="span")
    labels = SimpleNamespace(enabled=True, content=("title",), side="end", overflow="suppress")
    content = SimpleNamespace(attached_labels=(), as_of=None, label_fallback=("end",),
                              label_text_role=None, as_of_placement=None)
    measured_label = SimpleNamespace(placement_id="member-label:child-row:gate", content="Review gate",
        wrap="forbid", candidates=("end",))
    request = SimpleNamespace(
        presentation_contract=SimpleNamespace(labels=labels), surface_content=content,
        fixed_lane_preflight=SimpleNamespace(measured_labels=(measured_label,)), mark_visibility_index=None,
        theme_tokens=SimpleNamespace(), capacity_short_sources=(),
    )
    projection = SimpleNamespace(window_mode=None, lane_membership=object(), rows=(object(),), folded_points=())
    track = TrackPlacement("child-row:gate", 20.0, 20.0, 10.0)
    context = SurfaceMemberLabelContext(
        request=request, projection=projection,
        layout_manifest=SimpleNamespace(row_distribution="pack", member_names={}),
        by_source={"timeline": SlotPlacement("timeline", "timeline", Rect(D(0), D(0), D(100), D(100)))},
        text_slot=lambda _placement: "", review_rows=(row,),
        rows=(SimpleNamespace(row_id="child-row", bounds=Rect(D(0), D(20), D(100), D(10))),
              SimpleNamespace(row_id="host-row", bounds=Rect(D(0), D(40), D(100), D(10)))),
        tracks=(track,), groups=(), scale=ScalePlacement(
            "surface", "scale", date(2026, 1, 1), date(2026, 2, 1), 0, 100, 0, 1),
        marks=(mark, host), timeline_bounds=(0, 0, 100, 100), as_of_label=None,
    )
    return context


def test_member_label_bounds_follow_host_band_while_semantic_row_stays_with_child():
    result = build_member_label_requests(_label_request_context())
    label, = result.pre_route

    assert label.bounds.y == 40
    assert label.lane_row_id == "child-row"
    assert label.lane_member_id == "member-gate"
    assert label.lane_source_kind == "primary"
    assert label.source_ref == "gate"
