import pytest

from chrona.presentation.model.info_diagnostics import (
    RoutingCostAdvisory,
)


def test_routing_cost_advisory_has_stable_scene_diagnostic():
    advisory = RoutingCostAdvisory("table-timeline", 336)

    assert advisory.code == "W_LAYOUT_ROUTING_COST"
    assert advisory.scene_diagnostic() == (
        "W_LAYOUT_ROUTING_COST:surface=table-timeline;potentialPairs=336")


@pytest.mark.parametrize("surface,count", [
    ("", 1),
    ("invalid;surface", 1),
    ("table-timeline", 0),
    ("table-timeline", True),
])
def test_routing_cost_advisory_rejects_invalid_surface_or_nonpositive_count(surface, count):
    with pytest.raises(ValueError, match="E_PRESENTATION_INFO_INVALID"):
        RoutingCostAdvisory(surface, count)
