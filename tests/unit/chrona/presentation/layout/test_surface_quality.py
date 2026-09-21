from decimal import Decimal
from datetime import date

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_quality import (
    GroupPlacement,
    MarkPlacement,
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


def test_surface_placement_rejects_overlapping_required_text():
    surface = SurfacePlacement(text=(
        TextPlacement("left", "view:left", "left", _rect(0, 0, 10, 10), "text"),
        TextPlacement("right", "view:right", "right", _rect(9, 0, 10, 10), "text"),
    ))
    with pytest.raises(ValueError, match="E_LAYOUT_TEXT_OVERLAP:left:right"):
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
