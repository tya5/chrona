from datetime import date
from decimal import Decimal

from chrona.presentation.layout.lane_bundle_mapper import _mark_facets
from chrona.presentation.layout.lane_projection import LaneProjectionInstance
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import ObstacleRect
from chrona.presentation.layout.surface_quality import MarkPlacement
from chrona.presentation.model.projection import ReviewItem


class _Theme:
    def optional_number(self, role, name):
        return Decimal("2") if name == "strokeWidth" else None


def test_mapper_closes_span_as_source_keyed_plain_facet_with_ports_and_footprint():
    item = ReviewItem(
        "work", "Work", "span",
        {"start": date(2026, 1, 1), "end": date(2026, 1, 4)},
        None, None, ("planned",), item_id="work-view", source_kind="primary",
    )
    instance = LaneProjectionInstance("row:1", "work-view", "work", "primary")
    mark = MarkPlacement(
        "planned:row%3A1:work-view", "work",
        Rect(Decimal("10"), Decimal("1"), Decimal("20"), Decimal("4")),
        (10, 3), (30, 3), mark_shape="span", semantic_id="planned",
        paint_order=7,
    )

    facets = _mark_facets(item, instance, mark, _Theme())

    assert len(facets) == 1
    facet = facets[0]
    assert facet.projection_instance_id == instance.placement_key
    assert facet.source_item_id == "work-view"
    assert facet.source_ref == "work"
    assert facet.visible_footprint == ObstacleRect(9, 0, 31, 6)
    assert tuple(port.purpose for port in facet.ports) == ("start", "end")
    assert facet.plain_mark_projection.shape == "span"
    assert facet.plain_mark_projection.paint_order == 7
