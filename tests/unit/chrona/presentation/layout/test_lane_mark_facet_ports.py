from decimal import Decimal
from types import SimpleNamespace

from chrona.presentation.layout.lane_mark_facets import _facet
from chrona.presentation.layout.lane_projection import LaneProjectionInstance
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import ObstacleRect
from chrona.presentation.layout.surface_quality import MarkPlacement


def _facet_for(mark):
    instance = LaneProjectionInstance("row", "item", "object", "actual")
    item = SimpleNamespace(item_id="item", object_id="object", source_kind="actual")
    return _facet(
        instance, item, mark, "actual:row:item", "Rect",
        (("move", ((10.0, 20.0),)),), (10.0, 20.0, 18.0, 28.0),
        ObstacleRect(10.0, 20.0, 18.0, 28.0), mark,
    )


def test_lane_facet_emits_only_available_temporal_ports():
    mark = MarkPlacement("actual:item", "object", Rect(Decimal(10), Decimal(20),
                          Decimal(8), Decimal(8)), None, (18.0, 24.0))

    facet = _facet_for(mark)

    assert [(port.purpose, port.position) for port in facet.ports] == [("end", (18.0, 24.0))]
    assert facet.port_host_bounds == (10.0, 20.0, 18.0, 28.0)
    assert all(port.position is not None for port in facet.ports)


def test_lane_facet_with_no_available_temporal_ports_emits_no_port_host():
    mark = MarkPlacement("actual:item", "object", Rect(Decimal(10), Decimal(20),
                          Decimal(8), Decimal(8)), None, None)

    facet = _facet_for(mark)

    assert facet.ports == ()
    assert facet.port_host_bounds is None
