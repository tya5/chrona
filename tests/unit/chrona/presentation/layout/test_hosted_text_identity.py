from dataclasses import replace

import pytest

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.mark_geometry import SymbolPartPlacement
from chrona.presentation.layout.obstacles import ObstacleRect
from chrona.presentation.layout.surface_lanes import complete_hosted_text_identity
from chrona.presentation.layout.surface_quality import (
    LaneEmissionFacet, LaneEmissionPlacement, MarkPlacement, TextPlacement, SurfacePlacement,
)
from chrona.presentation.model.primitive_identity import completed_symbol_primitive_ids


def _mark_and_number():
    mark = MarkPlacement("planned:gate", "gate", Rect(0, 0, 10, 10),
                         (0, 5), (10, 5), slot_id="timeline", paint_order=100,
                         lane_row_id="lane", lane_member_id="gate")
    number = TextPlacement("note-index:n", "n", "1", Rect(10, 10, 10, 10),
                           "annotation", slot_id="timeline", semantic_id="noteIndex",
                           paint_order=200, host_placement_id=mark.placement_id)
    return mark, number


def _emission(*ids):
    return LaneEmissionPlacement("mark", "planned:gate", "lane", "gate", "planned",
        tuple(LaneEmissionFacet(f"facet:{index}", "mark", "planned:gate", primitive_id,
                                ObstacleRect(0, 0, 10, 10), "mark", index)
              for index, primitive_id in enumerate(ids)))


def test_single_part_host_identity_remains_byte_stable():
    mark, number = _mark_and_number()
    completed = complete_hosted_text_identity((number,), (mark,), (_emission("planned:gate"),))
    assert completed == (number,)


def test_glyph_host_resolves_to_first_painted_emitted_part():
    mark, number = _mark_and_number()
    completed = complete_hosted_text_identity(
        (number,), (mark,), (_emission("planned:gate:part0", "planned:gate:part1"),))
    assert completed[0].host_placement_id == "planned:gate:part0"
    assert completed[0].paint_order > mark.paint_order


def test_missing_emitted_mark_host_is_a_layout_error():
    mark, number = _mark_and_number()
    with pytest.raises(LayoutError, match="E_LAYOUT_HOST_EMISSION_INVALID"):
        complete_hosted_text_identity((number,), (mark,), ())


@pytest.mark.parametrize("shape", ["point", "span"])
@pytest.mark.parametrize("paint_modes", [(), (None,), ("fill", "stroke")])
def test_non_lane_mark_closes_the_actual_emitted_host_without_geometry_changes(shape, paint_modes):
    mark, number = _mark_and_number()
    mark = replace(mark, lane_row_id=None, lane_member_id=None, mark_shape=shape,
                   semantic_id="planned", symbol_parts=tuple(SymbolPartPlacement((), mode) for mode in paint_modes))
    text = replace(number, source_ref="gate", semantic_id="memberLabel", collision_region="plot-label")
    completed = complete_hosted_text_identity((text,), (mark,), ())
    ids = completed_symbol_primitive_ids(mark.placement_id, mark.symbol_parts)
    expected = ids[0] if ids else mark.placement_id
    assert completed == (replace(text, host_placement_id=expected),)
    SurfacePlacement(marks=(mark,), text=completed).assert_valid()
    if expected != mark.placement_id:
        with pytest.raises(ValueError, match="E_LAYOUT_TEXT_HOST_INVALID"):
            SurfacePlacement(marks=(mark,), text=(text,)).assert_valid()


@pytest.mark.parametrize("field,value", [("slot_id", "other"), ("paint_order", 100)])
def test_non_lane_completion_does_not_waive_host_slot_or_paint_order(field, value):
    mark, number = _mark_and_number()
    mark = replace(mark, lane_row_id=None, lane_member_id=None)
    with pytest.raises(LayoutError, match="E_LAYOUT_HOST_EMISSION_INVALID"):
        complete_hosted_text_identity((replace(number, **{field: value}),), (mark,), ())
