from datetime import date

from chrona.presentation.layout.lane_item_footprints import compose_lane_item_footprints
from chrona.presentation.layout.obstacles import ObstacleRect
from chrona.presentation.layout.presentation import MarkGeometry
from chrona.presentation.layout.surface_quality import ScalePlacement
from chrona.presentation.model.projection import (
    ReviewItem,
    ReviewLaneRowProjection,
    ReviewProjection,
    ReviewRowProjection,
)
from chrona.presentation.review.lane_membership import (
    Lane,
    LaneAssignment,
    LaneMembership,
)


class _Theme:
    def optional_number(self, _role, name):
        return 2 if name == "strokeWidth" else None

    def variant_symbol(self, _variant):
        return {"shape": "diamond"}


def test_footprints_follow_fixed_lane_member_identity_and_zero_origin_geometry():
    item = ReviewItem(
        "work", "Work", "span",
        {"start": date(2026, 1, 1), "end": date(2026, 1, 5)},
        None, None, ("planned",), group_id="systems", item_id="work-view",
        source_kind="primary",
    )
    row = ReviewRowProjection("row-1", "Work", "systems", "work-view", (item,))
    lane = Lane("lane-fixed", "systems", ("work-view",))
    membership = LaneMembership((lane,), (
        LaneAssignment("work-view", "lane-fixed", "systems", "dates", "first-compatible:lane-fixed"),
    ))
    projection = ReviewProjection(
        (item,), (date(2026, 1, 1), date(2026, 2, 1)), (), (), rows=(row,),
        lane_membership=membership,
        lane_rows=(ReviewLaneRowProjection("lane-fixed", "systems", (item,), ("work-view",)),),
    )
    footprints = compose_lane_item_footprints(
        projection,
        scale=ScalePlacement("timeline", "scale:test", date(2026, 1, 1), date(2026, 2, 1), 0, 100, 0, 2),
        as_of=None,
        theme_tokens=_Theme(),
        mark_band_size=10,
        role_geometries={
            "planned": MarkGeometry(0.4, 0.1, 0, 0),
            "actual": MarkGeometry(0.4, 0.5, 1, 0),
            "missing-actual": MarkGeometry(0.4, 0.5, 2, 0),
        },
        slot_id="lane-slot", icon_assets={},
    )

    assert tuple((value.item_id, value.projection_instance_id.item_id) for value in footprints) == (
        ("work-view", "work-view"),
    )
    assert len(footprints[0].facets) == 1
    footprint = footprints[0].facets[0].footprint
    assert isinstance(footprint, ObstacleRect)
    assert footprint.top == 0
    assert footprint.bottom == 6
