from decimal import Decimal

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_backgrounds import replace_group_header_band
from chrona.presentation.layout.surface_groups import GroupHeaderExtentUpdate, replace_group_header_extent
from chrona.presentation.layout.surface_quality import GroupPlacement, ShapePlacement


def _rect(block: int, size: int) -> Rect:
    return Rect(Decimal(0), Decimal(block), Decimal(100), Decimal(size))


def test_folded_header_update_preserves_selected_group_and_band_identity() -> None:
    first = GroupPlacement("shared", _rect(0, 20), _rect(0, 5))
    selected = GroupPlacement("shared", _rect(20, 20), _rect(20, 5))
    update = GroupHeaderExtentUpdate(selected, _rect(20, 10))

    groups = replace_group_header_extent((first, selected), update)
    assert groups[0] is first
    assert groups[1].header_bounds == _rect(20, 10)

    bands = (
        ShapePlacement("group-header-band:shared", "shared", "Rect", _rect(0, 5)),
        ShapePlacement("group-header-band:shared", "shared", "Rect", _rect(20, 5)),
    )
    assert tuple(shape.bounds for shape in replace_group_header_band(bands, update)) == (
        _rect(20, 10), _rect(20, 10),
    )
