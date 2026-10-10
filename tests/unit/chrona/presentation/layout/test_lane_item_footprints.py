from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from chrona.presentation.layout.lane_item_footprints import compose_lane_item_footprints
from chrona.presentation.layout.lane_subtracks import assign_lane_subtracks
from chrona.presentation.layout.obstacles import ObstacleRect
from chrona.presentation.layout.presentation import MarkGeometry
from chrona.presentation.layout.surface_quality import ScalePlacement, VisualRequest
from chrona.presentation.layout.surface_mark_visibility import build_item_mark_visibility_index
from chrona.presentation.model.projection import (
    ObservationState,
    ReviewItem,
    ReviewLaneRowProjection,
    ReviewProjection,
    ReviewRowProjection,
    WindowMode,
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


def _window_footprint_fixture(*, point=False, mode=WindowMode.EXPLICIT, all_outside=False):
    start, end = date(2026, 1, 3), date(2026, 1, 6)
    days = (1, 6) if all_outside else (1, 4, 6)
    items = tuple(ReviewItem(
        f"object-{day}", f"Item {day}", "point" if point else "span",
        {"at": date(2026, 1, day)} if point else {
            "start": date(2026, 1, day), "end": date(2026, 1, day + 1)},
        None, None, ("planned",), item_id=f"item-{day}", source_kind="primary",
    ) for day in days)
    members = tuple(item.item_id for item in items)
    membership = LaneMembership((Lane("lane", "group", members),), tuple(
        LaneAssignment(member, "lane", "group", "dates", "fixed") for member in members))
    projection = ReviewProjection(
        items, (start, end), (), (), rows=tuple(
            ReviewRowProjection(f"row-{item.item_id}", item.title, "group", item.item_id, (item,))
            for item in items), lane_membership=membership,
        lane_rows=(ReviewLaneRowProjection("lane", "group", items, members),), window_mode=mode,
    )
    index = build_item_mark_visibility_index(projection, as_of=None)
    kwargs = dict(
        projection=projection, scale=ScalePlacement("timeline", "scale", start, end, 0, 30, 0, 10),
        as_of=None, theme_tokens=_Theme(), mark_band_size=10,
        role_geometries={role: MarkGeometry(0.4, 0.1, 0, 0)
                         for role in ("planned", "actual", "missing-actual")},
        slot_id="timeline", icon_assets={}, mark_visibility_index=index,
    )
    return projection, index, kwargs


def test_clipped_lane_preflight_carries_cut_contour_original_progress_and_bounded_paint(monkeypatch):
    projection, _, kwargs = _window_footprint_fixture()
    across = replace(projection.items[1], planned={
        "start": date(2026, 1, 1), "end": date(2026, 1, 9)}, planned_progress=.6)
    items = (projection.items[0], across, projection.items[2])
    projection = replace(projection, items=items,
        rows=tuple(replace(row, items=(item,)) for row, item in zip(projection.rows, items)),
        lane_rows=(replace(projection.lane_rows[0], items=items),))
    index = build_item_mark_visibility_index(projection, as_of=None)
    kwargs.update(projection=projection, mark_visibility_index=index, progress_fill_source="planned")
    from chrona.presentation.layout import lane_item_footprints as owner
    original = owner._with_mark_visuals
    captured = []
    def checked(item, instance, mark, facets, icons, progress, theme):
        result = original(item, instance, mark, facets, icons, progress, theme)
        captured.append((mark, tuple(progress), result))
        return result
    monkeypatch.setattr(owner, "_with_mark_visuals", checked)
    footprints = compose_lane_item_footprints(**kwargs)
    assert len(captured) == 1
    host, progress, facets = captured[0]
    assert host.start_port is host.end_port is None
    assert host.paint_clip is not None and host.path_commands
    assert all(facet.primitive_type == "Symbol" for facet in facets)
    assert facets[0].completed_geometry == tuple((command.kind, command.points)
                                                for command in host.path_commands)
    assert len(progress) == 1 and progress[0].kind == "Symbol"
    # Original Jan1..9 width80, height4, .1 block-relative inset:
    # original left -20 + inset.4 + remaining79.2*.6 = 27.92, not a
    # fraction of the shortened Jan3..6 host.
    right = max(x for command in progress[0].path_commands for x, _ in command.points)
    assert right == pytest.approx(27.92)
    for facet in footprints[1].facets:
        assert 0 <= facet.footprint.left <= facet.footprint.right <= 30
    assert footprints[0].facets == footprints[2].facets == ()
    assert across.planned == {"start": date(2026, 1, 1), "end": date(2026, 1, 9)}


def test_containing_explicit_lane_preflight_preserves_derived_footprints():
    projection, _, kwargs = _window_footprint_fixture()
    projection = replace(projection, window=(date(2026, 1, 1), date(2026, 1, 9)))
    scale = replace(kwargs["scale"], domain_start=projection.window[0], domain_end=projection.window[1],
                    range_end=80)
    def compose(mode):
        selected = replace(projection, window_mode=mode)
        return compose_lane_item_footprints(**{**kwargs, "projection": selected, "scale": scale,
            "mark_visibility_index": build_item_mark_visibility_index(selected, as_of=None)})
    assert compose(WindowMode.EXPLICIT) == compose(WindowMode.SELECTED_PLANNED)


@pytest.mark.parametrize("point", (False, True))
def test_window_omissions_keep_lane_members_but_never_measure_outside_marks(point, monkeypatch):
    projection, index, kwargs = _window_footprint_fixture(point=point)
    from chrona.presentation.layout import lane_item_footprints as owner
    original = owner.compose_item_marks
    measured = []
    def checked(**inputs):
        measured.extend((inputs["item"].item_id, facet.facet) for facet in inputs["selection"].facets)
        return original(**inputs)
    monkeypatch.setattr(owner, "compose_item_marks", checked)
    footprints = compose_lane_item_footprints(**kwargs)
    assert measured == [("item-4", "planned")]
    assert tuple(unit.item_id for unit in footprints) == ("item-1", "item-4", "item-6")
    assert footprints[0].facets == footprints[2].facets == ()
    assert footprints[1].facets
    plan = assign_lane_subtracks(projection.lane_membership, footprints, mark_band_size=10,
                                mark_visibility_index=index)
    assert tuple(item.item_id for item in plan.items) == ("item-1", "item-4", "item-6")
    assert plan.lanes[0].subtrack_count == 1
    with pytest.raises(ValueError, match="E_LAYOUT_LANE_SUBTRACK_INPUT"):
        assign_lane_subtracks(projection.lane_membership, footprints, mark_band_size=10)


def test_fully_omitted_lane_keeps_ordinary_track_without_fake_obstacle():
    projection, index, kwargs = _window_footprint_fixture(all_outside=True)
    footprints = compose_lane_item_footprints(**kwargs)
    assert all(unit.facets == () for unit in footprints)
    plan = assign_lane_subtracks(projection.lane_membership, footprints, mark_band_size=10,
                                mark_visibility_index=index)
    assert len(plan.items) == 2
    assert plan.lanes[0].subtrack_count == 1
    assert plan.lanes[0].block_extent == 10


def test_valid_visual_selector_for_omitted_host_is_unpainted():
    _, _, kwargs = _window_footprint_fixture(all_outside=True)
    kwargs["visual_requests"] = (VisualRequest(
        "mark", (("object", "object-1"), ("facet", "planned")), ref="icon:user"),)
    # There is intentionally no icon asset: an omitted host never measures or paints it.
    assert all(not unit.facets for unit in compose_lane_item_footprints(**kwargs))
    kwargs["visual_requests"] = (VisualRequest(
        "mark", (("object", "unknown"), ("facet", "planned")), ref="icon:user"),)
    with pytest.raises(ValueError, match="E_LAYOUT_VISUAL_TARGET"):
        compose_lane_item_footprints(**kwargs)


def test_window_account_does_not_excuse_missing_in_window_footprint_or_add_outside_ink():
    projection, index, kwargs = _window_footprint_fixture()
    footprints = compose_lane_item_footprints(**kwargs)
    missing = (footprints[0], replace(footprints[1], facets=()), footprints[2])
    outside_ink = (replace(footprints[0], facets=footprints[1].facets), *footprints[1:])
    for invalid in (missing, outside_ink):
        with pytest.raises(ValueError, match="E_LAYOUT_LANE_SUBTRACK_INPUT"):
            assign_lane_subtracks(projection.lane_membership, invalid, mark_band_size=10,
                                 mark_visibility_index=index)


def test_derived_window_footprints_and_tracks_retain_existing_identity():
    projection, index, kwargs = _window_footprint_fixture(mode=WindowMode.SELECTED_PLANNED)
    footprints = compose_lane_item_footprints(**kwargs)
    assert all(unit.facets for unit in footprints)
    with_index = assign_lane_subtracks(projection.lane_membership, footprints, mark_band_size=10,
                                      mark_visibility_index=index)
    assert with_index == assign_lane_subtracks(projection.lane_membership, footprints, mark_band_size=10)


def test_omission_proof_cannot_be_borrowed_by_another_member_or_projection():
    projection, index, kwargs = _window_footprint_fixture()
    footprints = compose_lane_item_footprints(**kwargs)
    borrowed = (replace(footprints[0], item_id="item-4"), *footprints[1:])
    with pytest.raises(ValueError, match="visibility occurrence mismatch"):
        assign_lane_subtracks(projection.lane_membership, borrowed, mark_band_size=10,
                             mark_visibility_index=index)
    unrelated = replace(projection.lane_membership)
    with pytest.raises(ValueError, match="visibility membership mismatch"):
        assign_lane_subtracks(unrelated, footprints, mark_band_size=10, mark_visibility_index=index)


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
