from decimal import Decimal
from datetime import date

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.path_geometry import open_span_path
from chrona.presentation.layout.surface_composer import progress_fill_bounds, relation_label_content
from chrona.presentation.model.surface_content import RelationPresentationFact
from chrona.presentation.layout.surface_quality import (
    AxisIntervalOutcome,
    AxisTierOutcome,
    CollisionDomain,
    GroupPlacement,
    IconPlacement,
    MarkPlacement,
    PlacementDecision,
    PrimitivePlacement,
    RelationPlacement,
    RowPlacement,
    ScalePlacement,
    ShapePlacement,
    SlotPlacement,
    SurfacePlacement,
    TextPlacement,
    intersects,
)


def _rect(inline, block, inline_size, block_size):
    return Rect(Decimal(inline), Decimal(block), Decimal(inline_size), Decimal(block_size))


def test_intersects_treats_touching_rectangles_as_non_overlapping():
    assert not intersects(_rect(0, 0, 10, 10), _rect(10, 0, 10, 10))
    assert intersects(_rect(0, 0, 10, 10), _rect(9, 0, 10, 10))


def test_relation_label_content_preserves_signed_calendar_provenance_and_omits_zero_lag():
    positive = RelationPresentationFact("r", "a", "start", "b", "start",
                                        {"value": "2wd", "calendar": "range"}, "range",
                                        "dependency", ("endpointPair", "lag"))
    zero = RelationPresentationFact("z", "a", "end", "b", "start", "0d", None,
                                    "dependency", ("lag",))
    assert relation_label_content(positive) == "start->start +2wd [range]"
    assert relation_label_content(zero) == ""


def test_surface_placement_rejects_overlapping_required_text():
    surface = SurfacePlacement(text=(
        TextPlacement("left", "view:left", "left", _rect(0, 0, 10, 10), "text"),
        TextPlacement("right", "view:right", "right", _rect(9, 0, 10, 10), "text"),
    ))
    with pytest.raises(ValueError, match="E_LAYOUT_TEXT_OVERLAP:left:right"):
        surface.assert_valid()


def test_surface_placement_rejects_cross_region_text_in_the_same_physical_domain():
    domain = CollisionDomain("timeline", "overlay")
    surface = SurfacePlacement(text=(
        TextPlacement("as-of", "actual-set", "As of", _rect(0, 0, 10, 10), "text",
                      collision_region="timeline-as-of", collision_domain=domain),
        TextPlacement("label", "task:a", "Task A", _rect(9, 0, 10, 10), "text",
                      collision_region="plot-label", collision_domain=domain),
    ))
    with pytest.raises(ValueError, match="E_LAYOUT_TEXT_OVERLAP:as-of:label"):
        surface.assert_valid()


def test_surface_placement_allows_overlapping_text_in_distinct_axis_lanes():
    surface = SurfacePlacement(text=(
        TextPlacement("coarse", "timeline-axis", "Q1", _rect(0, 0, 10, 10), "axis",
                      collision_domain=CollisionDomain("timeline-axis", "coarse-band")),
        TextPlacement("fine", "timeline-axis", "Jan", _rect(0, 0, 10, 10), "axis",
                      collision_domain=CollisionDomain("timeline-axis", "fine-label")),
    ))
    surface.assert_valid()


def test_surface_placement_allows_explicit_relation_suppression_only_with_diagnostic():
    SurfacePlacement(relations=(RelationPlacement("r", "a:end", "b:start", suppressed=True, diagnostic="W_LAYOUT_RELATION_SUPPRESSED"),)).assert_valid()
    with pytest.raises(ValueError, match="E_LAYOUT_RELATION_SUPPRESSION_INVALID:r"):
        SurfacePlacement(relations=(RelationPlacement("r", "a:end", "b:start", suppressed=True),)).assert_valid()


def test_surface_placement_validates_completed_mark_and_shape_geometry():
    bounds = _rect(1, 2, 3, 4)
    SurfacePlacement(
        marks=(MarkPlacement("mark:a", "a", bounds, (1.0, 4.0), (4.0, 4.0)),),
        shapes=(ShapePlacement("path:a", "a", "Path", bounds, ((1.0, 2.0), (4.0, 6.0))),),
    ).assert_valid()
    with pytest.raises(ValueError, match="E_LAYOUT_MARK_PLACEMENT_INVALID:mark:bad"):
        SurfacePlacement(marks=(MarkPlacement("mark:bad", "a", _rect(0, 0, 0, 1), (0, 0), (0, 0)),)).assert_valid()
    with pytest.raises(ValueError, match="E_LAYOUT_SHAPE_PLACEMENT_INVALID:path:bad"):
        SurfacePlacement(shapes=(ShapePlacement("path:bad", "a", "Path", bounds, ((1.0, 2.0),)),)).assert_valid()


def test_surface_placement_closes_clip_hosts_and_mark_end_treatment():
    bounds = _rect(1, 2, 20, 4)
    host = MarkPlacement("actual:a", "a", bounds, (1, 4), (21, 4), slot_id="timeline", mark_shape="open-span",
                         path_commands=open_span_path(inline=1, block=2, inline_size=20, block_size=4, radius=1), end_treatment="open")
    SurfacePlacement(marks=(host,), shapes=(ShapePlacement("progress:a", "a", "Rect", bounds,
                                                           slot_id="timeline", clip_host_id="actual:a"),)).assert_valid()
    with pytest.raises(ValueError, match="E_LAYOUT_CLIP_HOST_INVALID:progress:a"):
        SurfacePlacement(shapes=(ShapePlacement("progress:a", "a", "Rect", bounds,
                                                slot_id="timeline", clip_host_id="actual:a"),)).assert_valid()
    with pytest.raises(ValueError, match="E_LAYOUT_MARK_END_TREATMENT_INVALID:actual:a"):
        SurfacePlacement(marks=(MarkPlacement("actual:a", "a", bounds, (1, 4), (21, 4), end_treatment="unknown"),)).assert_valid()
    with pytest.raises(ValueError, match="E_LAYOUT_MARK_OPEN_OUTLINE_INVALID:actual:a"):
        SurfacePlacement(marks=(MarkPlacement("actual:a", "a", bounds, (1, 4), (21, 4), end_treatment="open"),)).assert_valid()


def test_surface_placement_rejects_icon_without_a_declared_slot_owner():
    bounds = _rect(1, 2, 3, 4)
    icon = IconPlacement("visual:title:leading", "title", "/body/visuals/0", "risk", "svg", "sha256:x",
                         (24, 24), (), "Risk", True, bounds)
    surface = SurfacePlacement(slots=(SlotPlacement("title", "title", bounds),), icons=(icon,))
    with pytest.raises(ValueError, match="E_LAYOUT_SLOT_OWNERSHIP_INVALID:icon:visual:title:leading"):
        surface.assert_valid()


def test_progress_fill_bounds_are_layout_owned_and_fractional():
    host = _rect(10, 20, 80, 12)
    assert progress_fill_bounds(host, 0) is None
    assert progress_fill_bounds(host, 0.5) == _rect(10, 20, 40, 12)
    assert progress_fill_bounds(host, 1) == host
    with pytest.raises(ValueError, match="E_PRESENTATION_PROGRESS_INVALID"):
        progress_fill_bounds(host, 1.1)


def test_surface_placement_carries_the_completed_surface_projection_closure():
    bounds = _rect(1, 2, 3, 4)
    text = TextPlacement("text:a", "a", "A", bounds, "text", baseline=(1.0, 3.0), lines=("A",), font_size=12.0)
    SurfacePlacement(
        slots=(SlotPlacement("timeline", "timeline", bounds, scale_id="primary"),),
        rows=(RowPlacement("row:a", "a", "g", bounds),),
        groups=(GroupPlacement("g", bounds),),
        scale=ScalePlacement("table-timeline", "primary", date(2026, 1, 1), date(2026, 1, 2), 1.0, 4.0, 1.0, 3.0),
        primitives=(PrimitivePlacement("text:a", "a", "Text", bounds, text=text),),
    ).assert_valid()
    with pytest.raises(ValueError, match="E_LAYOUT_PRIMITIVE_PLACEMENT_INVALID:text:bad"):
        SurfacePlacement(primitives=(PrimitivePlacement("text:bad", "a", "Text", bounds),)).assert_valid()


def test_surface_placement_validates_inspectable_late_decisions():
    SurfacePlacement(decisions=(
        PlacementDecision("label:a", "a", ("above", "suppress"), "above", "placed"),
        PlacementDecision("label:b", "b", ("below", "suppress"), "suppress", "suppressed"),
    )).assert_valid()
    with pytest.raises(ValueError, match="E_LAYOUT_DECISION_INVALID:label:a"):
        SurfacePlacement(decisions=(PlacementDecision("label:a", "a", ("above", "above"), "above", "placed"),)).assert_valid()


def test_surface_placement_closes_axis_outcomes_for_later_failure_policy():
    interval = AxisIntervalOutcome("axis-label:0:0", date(2026, 1, 1), date(2026, 2, 1),
                                   date(2026, 1, 1), date(2026, 2, 1), "Jan", True, "placed")
    SurfacePlacement(axis_tier_outcomes=(
        AxisTierOutcome(0, "/view/body/axis/tiers/0", "labels", ("month", "quarter"), "month", 1,
                        "short-month", (interval,)),
    )).assert_valid()
    with pytest.raises(ValueError, match="E_LAYOUT_AXIS_OUTCOME_INVALID:0"):
        SurfacePlacement(axis_tier_outcomes=(
            AxisTierOutcome(0, "/view/body/axis/tiers/0", "labels", ("month",), "month", 1,
                            None, (interval,)),
        )).assert_valid()
