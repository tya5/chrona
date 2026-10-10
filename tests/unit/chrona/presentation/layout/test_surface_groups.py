from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_backgrounds import _background_bounds, replace_group_header_band
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


@pytest.mark.parametrize("start,width,expected_start,expected_width", [
    (10, 45, 10, 45), (10, 150, 10, 100), (0, 45, 10, 35),
    (10, 0, 10, 0), (10, 8, 10, 8), (150, 20, 110, 0),
])
def test_text_header_band_uses_completed_interval_clamped_to_table(
    start, width, expected_start, expected_width,
) -> None:
    source = Rect(Decimal(0), Decimal(20), Decimal(300), Decimal(30))
    content = Rect(Decimal(start), Decimal(99), Decimal(width), Decimal(12))
    bounds, slot = _background_bounds(
        semantic_id="groupHeaderBand", extent="text", source_bounds=source,
        table_bounds=(10, 0, 100, 200), timeline_bounds=(110, 0, 200, 200), text_bounds=content,
    )
    assert bounds == Rect(Decimal(expected_start), source.block,
                          Decimal(expected_width), source.block_size)
    assert slot == "table"


@pytest.mark.parametrize("semantic,content", [("groupHeaderBand", None), ("rowBand", _rect(0, 5))])
def test_text_extent_requires_header_content_and_refuses_other_roles(semantic, content) -> None:
    with pytest.raises(LayoutError) as caught:
        _background_bounds(semantic_id=semantic, extent="text", source_bounds=_rect(0, 5),
                           table_bounds=(0, 0, 100, 200), timeline_bounds=(100, 0, 200, 200),
                           text_bounds=content)
    assert caught.value.diagnostic_id == "E_LAYOUT_BACKGROUND_EXTENT"
    assert caught.value.path == "/layoutManifest/reviewSurface/backgroundExtents"


def test_folded_text_band_keeps_completed_inline_interval() -> None:
    group = GroupPlacement("g", _rect(0, 20), _rect(0, 5))
    update = GroupHeaderExtentUpdate(group, _rect(20, 10))
    band = ShapePlacement("group-header-band:g", "g", "Rect",
                          Rect(Decimal(8), Decimal(0), Decimal(42), Decimal(5)))
    (completed,) = replace_group_header_band((band,), update, extent="text")
    assert completed.bounds == Rect(Decimal(8), Decimal(20), Decimal(42), Decimal(10))
