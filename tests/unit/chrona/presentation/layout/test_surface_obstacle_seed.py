from dataclasses import replace
from decimal import Decimal

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment
from chrona.presentation.layout.surface_obstacle_seed import seed_surface_obstacles
from chrona.presentation.layout.surface_quality import CollisionDomain, MarkPlacement, ShapePlacement, TextPlacement


def test_seed_preserves_existing_mark_text_rule_inventory_and_segment_identities():
    box = Rect(Decimal(10), Decimal(20), Decimal(30), Decimal(40))
    mark = MarkPlacement("planned:x", "x", box, (10, 40), (40, 40), semantic_id="planned")
    text = TextPlacement("column:x", "x", "X", box, "text",
                         collision_domain=CollisionDomain("table", "content"))
    as_of = ShapePlacement("as-of", "actual-set", "Path", box, ((0, 0), (0, 10)))
    deadline = ShapePlacement("deadline-tick:x", "x", "Path", box,
                              ((10, 10), (10, 10), (15, 10)), semantic_id="deadlineMark")
    background = ShapePlacement("background", "x", "Rect", box, semantic_id="rowBand")
    result = seed_surface_obstacles(
        marks=(mark, replace(mark, placement_id="zero", bounds=replace(box, inline_size=Decimal(0)))),
        text=(text, replace(text, placement_id="optional", required=False),
              replace(text, placement_id="suppressed", overflow="suppressed")),
        shapes=(as_of, deadline, background))
    found = {item.placement_id: item for item in result.all()}
    assert set(found) == {"planned:x", "column:x", "as-of", "deadline-tick:x:segment:1"}
    assert found["planned:x"].geometry == ObstacleRect(10, 20, 40, 60)
    assert found["column:x"].region_id == "table" and found["column:x"].obstacle_class == "text"
    assert found["as-of"].geometry == ObstacleSegment((0, 0), (0, 10))
    assert found["deadline-tick:x:segment:1"].geometry == ObstacleSegment((10, 10), (15, 10))


def test_each_surface_starts_with_an_independent_empty_index():
    one = seed_surface_obstacles(marks=(), text=(), shapes=())
    two = seed_surface_obstacles(marks=(), text=(), shapes=())
    assert one is not two and one.all() == two.all() == ()
