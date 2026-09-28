import pytest

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.obstacles import ObstacleRect
from chrona.presentation.layout.surface_composer import _complete_hosted_text_identity
from chrona.presentation.layout.surface_quality import (
    LaneEmissionFacet, LaneEmissionPlacement, MarkPlacement, TextPlacement,
)


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
    completed = _complete_hosted_text_identity((number,), (mark,), (_emission("planned:gate"),))
    assert completed == (number,)


def test_glyph_host_resolves_to_first_painted_emitted_part():
    mark, number = _mark_and_number()
    completed = _complete_hosted_text_identity(
        (number,), (mark,), (_emission("planned:gate:part:0", "planned:gate:part:1"),))
    assert completed[0].host_placement_id == "planned:gate:part:0"
    assert completed[0].paint_order > mark.paint_order


def test_missing_emitted_mark_host_is_a_layout_error():
    mark, number = _mark_and_number()
    with pytest.raises(LayoutError, match="E_LAYOUT_HOST_EMISSION_INVALID"):
        _complete_hosted_text_identity((number,), (mark,), ())
