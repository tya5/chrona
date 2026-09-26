import pytest

from chrona.presentation.layout.image_slice_geometry import image_slice_tiles


def test_symmetric_insets_produce_nine_tiles_with_matching_source_and_dest_area() -> None:
    tiles = image_slice_tiles((0.0, 0.0, 100.0, 60.0), viewport=(40, 40), slice_insets=(10, 10, 10, 10))
    assert len(tiles) == 9
    source_area = sum(width * height for (_, _, width, height), _ in tiles)
    dest_area = sum(width * height for _, (_, _, width, height) in tiles)
    assert source_area == pytest.approx(40 * 40)
    assert dest_area == pytest.approx(100 * 60)


def test_asymmetric_insets_keep_each_corner_tile_at_its_source_size() -> None:
    tiles = image_slice_tiles((5.0, 5.0, 120.0, 80.0), viewport=(30, 20), slice_insets=(4, 6, 8, 2))
    corner = next(destination for source, destination in tiles if source == (0.0, 0.0, 2.0, 4.0))
    assert corner == (5.0, 5.0, 2.0, 4.0)  # top-left corner tile keeps its own pixel size


def test_zero_inset_on_one_axis_collapses_that_axis_to_one_full_bleed_stretch() -> None:
    # A vertical three-slice (only top/bottom rods fixed, no horizontal border).
    tiles = image_slice_tiles((0.0, 0.0, 50.0, 90.0), viewport=(20, 30), slice_insets=(6, 0, 6, 0))
    assert len(tiles) == 3
    assert all(source[0] == 0.0 and source[2] == 20.0 for source, _ in tiles)  # full width every row


def test_box_smaller_than_the_declared_border_scales_it_down_without_inverting() -> None:
    tiles = image_slice_tiles((0.0, 0.0, 8.0, 8.0), viewport=(20, 20), slice_insets=(9, 9, 9, 9))
    for _, (dx, dy, dw, dh) in tiles:
        assert dw > 0 and dh > 0
        assert dx >= 0.0 and dy >= 0.0 and dx + dw <= 8.0 + 1e-9 and dy + dh <= 8.0 + 1e-9


@pytest.mark.parametrize("box,viewport,insets", [
    ((0.0, 0.0, 0.0, 10.0), (10, 10), (1, 1, 1, 1)),
    ((0.0, 0.0, 10.0, 10.0), (0, 10), (1, 1, 1, 1)),
    ((0.0, 0.0, 10.0, 10.0), (10, 10), (1, -1, 1, 1)),
])
def test_invalid_geometry_is_rejected(box, viewport, insets) -> None:
    with pytest.raises(ValueError):
        image_slice_tiles(box, viewport=viewport, slice_insets=insets)
