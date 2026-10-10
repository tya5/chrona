from types import SimpleNamespace

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_lanes import build_lane_emissions
from chrona.presentation.layout.surface_quality import ShapePlacement


def _rect(x: str, y: str, width: str, height: str) -> Rect:
    from decimal import Decimal

    return Rect(Decimal(x), Decimal(y), Decimal(width), Decimal(height))


def _chip(*, parts=(), collision_bounds=None, placement_id="chip:label:member"):
    return ShapePlacement(
        placement_id, "view:label", "Rect", _rect("10", "20", "30", "12"),
        slot_id="timeline", semantic_id="memberLabelChip", lane_row_id="row:1",
        lane_member_id="member:1", symbol_parts=parts, collision_bounds=collision_bounds,
    )


def _emissions(*shapes):
    projection = SimpleNamespace(lane_membership=object())
    return build_lane_emissions(projection, (), [], [], list(shapes), (), None)


def test_catalog_chip_emits_one_typed_facet_per_symbol_part_with_whole_chip_footprint():
    parts = (object(), object(), object())
    visible = _rect("8", "18", "34", "16")
    emission, = _emissions(_chip(parts=parts, collision_bounds=visible))

    assert (emission.placement_type, emission.placement_id, emission.row_id,
            emission.member_id) == ("shape", "chip:label:member", "row:1", "member:1")
    assert tuple((facet.primitive_id, facet.part_index) for facet in emission.facets) == (
        ("chip:label:member", 0),
        ("chip:label:member:part1", 1),
        ("chip:label:member:part2", 2),
    )
    assert all(facet.placement_id == "chip:label:member" for facet in emission.facets)
    assert all(facet.obstacle.left == 8 and facet.obstacle.top == 18
               and facet.obstacle.right == 42 and facet.obstacle.bottom == 34
               for facet in emission.facets)


def test_rectangle_chip_and_unrelated_symbol_shapes_keep_single_default_facet():
    chip, other = _emissions(
        _chip(),
        ShapePlacement("decoration:one", "view:decoration", "Symbol",
                       _rect("2", "3", "4", "5"), slot_id="timeline",
                       semantic_id="memberLabelChip", lane_row_id="row:1",
                       lane_member_id="member:1", symbol_parts=(object(), object())),
    )

    assert len(chip.facets) == 1
    assert (chip.facets[0].primitive_id, chip.facets[0].part_index) == (
        "chip:label:member", None)
    assert len(other.facets) == 1
    assert (other.facets[0].primitive_id, other.facets[0].part_index) == (
        "decoration:one", None)
    assert (chip.facets[0].obstacle.left, chip.facets[0].obstacle.top,
            chip.facets[0].obstacle.right, chip.facets[0].obstacle.bottom) == (10, 20, 40, 32)
