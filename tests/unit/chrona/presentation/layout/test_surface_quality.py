from decimal import Decimal

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_quality import (
    RelationPlacement,
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
