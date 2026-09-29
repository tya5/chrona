from dataclasses import replace
from datetime import date
from decimal import Decimal

from chrona.presentation.layout.lane_item_footprints import compose_lane_item_footprints
from chrona.presentation.layout.lane_subtracks import assign_lane_subtracks
from chrona.presentation.layout.obstacles import ObstacleRect
from chrona.presentation.layout.presentation import MarkGeometry
from chrona.presentation.layout.surface_quality import ScalePlacement
from chrona.presentation.model.projection import (
    ObservationState,
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
    def __init__(self, stroke_width=2):
        self.stroke_width = stroke_width

    def optional_number(self, _role, name):
        return self.stroke_width if name == "strokeWidth" else None

    def variant_symbol(self, _variant):
        return {"shape": "diamond"}

    def progress_track(self, _role):
        return (Decimal("0.1"), Decimal(0))


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


def test_theme_stroke_geometry_changes_footprint_without_changing_lane_membership():
    item = ReviewItem(
        "work", "Work", "span",
        {"start": date(2026, 1, 1), "end": date(2026, 1, 5)},
        None, None, ("planned",), group_id="systems", item_id="work-view",
        source_kind="primary",
    )
    membership = LaneMembership((Lane("lane-fixed", "systems", ("work-view",)),), (
        LaneAssignment("work-view", "lane-fixed", "systems", "dates", "first-compatible:lane-fixed"),
    ))
    projection = ReviewProjection(
        (item,), (date(2026, 1, 1), date(2026, 2, 1)), (), (),
        rows=(ReviewRowProjection("row-1", "Work", "systems", "work-view", (item,)),),
        lane_membership=membership,
        lane_rows=(ReviewLaneRowProjection("lane-fixed", "systems", (item,), ("work-view",)),),
    )
    common = dict(
        projection=projection,
        scale=ScalePlacement("timeline", "scale:test", date(2026, 1, 1), date(2026, 2, 1), 0, 100, 0, 2),
        as_of=None,
        mark_band_size=10,
        role_geometries={
            "planned": MarkGeometry(0.4, 0.1, 0, 0),
            "actual": MarkGeometry(0.4, 0.5, 1, 0),
            "missing-actual": MarkGeometry(0.4, 0.5, 2, 0),
        },
        slot_id="lane-slot",
        icon_assets={},
    )

    thin_theme = compose_lane_item_footprints(theme_tokens=_Theme(stroke_width=2), **common)
    thick_theme = compose_lane_item_footprints(theme_tokens=_Theme(stroke_width=8), **common)

    assert tuple(value.item_id for value in thin_theme) == tuple(value.item_id for value in thick_theme) == (
        "work-view",
    )
    assert tuple(value.projection_instance_id for value in thin_theme) == tuple(
        value.projection_instance_id for value in thick_theme
    )
    thin_footprint = thin_theme[0].facets[0].footprint
    thick_footprint = thick_theme[0].facets[0].footprint
    assert thin_footprint != thick_footprint
    assert thick_footprint.left < thin_footprint.left
    assert thick_footprint.right > thin_footprint.right


def test_catalog_glyph_stroke_fit_reaches_lane_projection_and_footprint():
    item = ReviewItem(
        "gate", "Gate", "point", {"at": date(2026, 1, 5)}, None, None, ("planned",),
        group_id="systems", item_id="gate-view", source_kind="primary",
    )
    membership = LaneMembership((Lane("lane-fixed", "systems", ("gate-view",)),), (
        LaneAssignment("gate-view", "lane-fixed", "systems", "single", "gate-view"),
    ))
    projection = ReviewProjection(
        (item,), (date(2026, 1, 1), date(2026, 2, 1)), (), (),
        rows=(ReviewRowProjection("row-1", "Gate", "systems", "gate-view", (item,)),),
        lane_membership=membership,
        lane_rows=(ReviewLaneRowProjection("lane-fixed", "systems", (item,), ("gate-view",)),),
    )

    class CatalogTheme(_Theme):
        def variant_symbol(self, _variant):
            return {"shape": "catalog-glyph", "ref": "starter:gate",
                    "viewport": {"inlineSize": 10, "blockSize": 10},
                    "parts": [{"paint": "stroke", "data": "M 0 0 L 10 10",
                               "strokeWidth": 1.5, "lineCap": "round", "lineJoin": "bevel"}]}

    footprints = compose_lane_item_footprints(
        projection,
        scale=ScalePlacement("timeline", "scale:test", date(2026, 1, 1), date(2026, 2, 1), 0, 100, 0, 2),
        as_of=None,
        theme_tokens=CatalogTheme(),
        mark_band_size=10,
        role_geometries={
            "planned": MarkGeometry(0.5, 0.1, 0, 0),
            "actual": MarkGeometry(0.4, 0.5, 1, 0),
            "missing-actual": MarkGeometry(0.4, 0.5, 2, 0),
        },
        slot_id="lane-slot", icon_assets={},
    )

    glyph_footprint = footprints[0].facets[0].footprint
    # A 10x10 viewport fitted into a 5x5 mark scales the authored 1.5-unit
    # stroke to .75 before it becomes the exact segment footprint.
    assert glyph_footprint.stroke_width == 0.75


def test_combined_plan_actual_and_missing_facets_have_exact_overlays():
    base = ReviewItem(
        "work", "Work", "span",
        {"start": date(2026, 1, 1), "end": date(2026, 1, 5)},
        None, None, ("planned",), group_id="systems", item_id="work",
        source_kind="combined",
    )
    lane = Lane("lane-fixed", "systems", ("work",))
    membership = LaneMembership((lane,), (
        LaneAssignment("work", "lane-fixed", "systems", "single", "work"),
    ))
    for item, as_of, observed_purpose in (
        (replace(base, actual={"start": date(2026, 1, 2), "finish": date(2026, 1, 4)},
                 roles=("planned", "actual"), observation_state=ObservationState.RECORDED), None, "actual"),
        (replace(base, roles=("planned", "missing-actual"),
                 observation_state=ObservationState.DUE_UNOBSERVED), date(2026, 1, 5), "missing-actual"),
    ):
        row = ReviewRowProjection("work", "Work", "systems", "work", (item,))
        projection = ReviewProjection(
            (item,), (date(2026, 1, 1), date(2026, 2, 1)), (), (), rows=(row,),
            lane_membership=membership,
            lane_rows=(ReviewLaneRowProjection("lane-fixed", "systems", (item,), ("work",)),),
        )
        units = compose_lane_item_footprints(
            projection,
            scale=ScalePlacement("timeline", "scale:test", date(2026, 1, 1), date(2026, 2, 1), 0, 100, 0, 2),
            as_of=as_of, theme_tokens=_Theme(), mark_band_size=10,
            role_geometries={
                "planned": MarkGeometry(0.8, 0.1, 0, 0),
                "actual": MarkGeometry(0.4, 0.3, 1, 0),
                "missing-actual": MarkGeometry(0.4, 0.3, 2, 0),
            },
            slot_id="lane-slot", icon_assets={},
        )

        assert len(units) == 1
        assert len(units[0].facets) == 2
        planned, observed = units[0].facets
        assert ":planned:" in planned.facet_id
        assert f":{observed_purpose}:" in observed.facet_id
        assert observed.facet_id in planned.overlay_with
        assert planned.facet_id in observed.overlay_with
        assert assign_lane_subtracks(membership, units, mark_band_size=10).lanes[0].subtrack_count == 1
        if observed_purpose == "missing-actual":
            omitted = compose_lane_item_footprints(
                replace(projection, comparison_facets=("planned",)),
                scale=ScalePlacement("timeline", "scale:test", date(2026, 1, 1), date(2026, 2, 1), 0, 100, 0, 2),
                as_of=as_of, theme_tokens=_Theme(), mark_band_size=10,
                role_geometries={
                    "planned": MarkGeometry(0.8, 0.1, 0, 0),
                    "actual": MarkGeometry(0.4, 0.3, 1, 0),
                    "missing-actual": MarkGeometry(0.4, 0.3, 2, 0),
                },
                slot_id="lane-slot", icon_assets={},
            )
            assert len(omitted[0].facets) == 1
            assert ":planned:" in omitted[0].facets[0].facet_id


def test_actual_progress_overlays_only_its_own_combined_planned_facet():
    item = ReviewItem(
        "work", "Work", "span",
        {"start": date(2026, 1, 1), "end": date(2026, 1, 5)},
        {"start": date(2026, 1, 2), "finish": date(2026, 1, 4), "progress": 0.5},
        None, ("planned", "actual"), group_id="systems", item_id="work",
        source_kind="combined", observation_state=ObservationState.RECORDED,
    )
    other = replace(item, object_id="other", item_id="other", title="Other")
    membership = LaneMembership((Lane("lane-fixed", "systems", ("work", "other")),), (
        LaneAssignment("work", "lane-fixed", "systems", "explicit", "shared"),
        LaneAssignment("other", "lane-fixed", "systems", "explicit", "shared"),
    ))
    projection = ReviewProjection(
        (item, other), (date(2026, 1, 1), date(2026, 2, 1)), (), (),
        rows=(ReviewRowProjection("work", "Work", "systems", "work", (item,)),
              ReviewRowProjection("other", "Other", "systems", "other", (other,))),
        lane_membership=membership,
        lane_rows=(ReviewLaneRowProjection("lane-fixed", "systems", (item, other),
                                          ("work", "other")),),
    )
    units = compose_lane_item_footprints(
        projection,
        scale=ScalePlacement("timeline", "scale:test", date(2026, 1, 1), date(2026, 2, 1), 0, 100, 0, 2),
        as_of=None, theme_tokens=_Theme(), mark_band_size=10,
        role_geometries={
            "planned": MarkGeometry(0.8, 0.1, 0, 0),
            "actual": MarkGeometry(0.4, 0.3, 1, 0),
            "missing-actual": MarkGeometry(0.4, 0.3, 2, 0),
        },
        slot_id="lane-slot", icon_assets={}, progress_fill_source="actual",
    )
    planned = next(facet for facet in units[0].facets if ":planned:" in facet.facet_id)
    progress = next(facet for facet in units[0].facets if ":progress:" in facet.facet_id)
    other_planned = next(facet for facet in units[1].facets if ":planned:" in facet.facet_id)
    assert progress.facet_id in planned.overlay_with
    assert planned.facet_id in progress.overlay_with
    assert progress.facet_id not in other_planned.overlay_with
    assert other_planned.facet_id not in progress.overlay_with
    assert assign_lane_subtracks(membership, units, mark_band_size=10).lanes[0].subtrack_count == 2
