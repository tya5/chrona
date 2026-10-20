from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, obstacles_intersect
from chrona.presentation.layout.relation_endpoint_geometry import (
    endpoint_lead_run, endpoint_tangent_minimum, intrinsic_span_endpoint_ink,
)
from chrona.presentation.layout.relation_terminals import centred_on_route, marker_geometry
import pytest


def test_span_endpoint_footprints_use_outward_normal_and_terminal_minimum():
    centred = marker_geometry({"shape": "circle", "headLength": 5, "headWidth": 5,
                               "attachmentOffset": 0})
    start_lead, = intrinsic_span_endpoint_ink((10, 20), "start", 1, centred,
                                               terminal_side="source")[:1]
    end_lead, end_terminal = intrinsic_span_endpoint_ink((10, 20), "end", 1, centred,
                                                           terminal_side="source")
    finish_lead, = intrinsic_span_endpoint_ink((10, 20), "finish", 1, None,
                                                terminal_side="target")
    assert start_lead == ObstacleSegment((10, 20), (6.5, 20), 1)
    assert end_lead == ObstacleSegment((10, 20), (13.5, 20), 1)
    assert isinstance(end_terminal, ObstacleRect)
    assert finish_lead == ObstacleSegment((10, 20), (11, 20), 1)
    assert endpoint_tangent_minimum(1, centred) == 3.5


def test_endpoint_geometry_shares_stroke_terminal_and_existing_corridor_calculation():
    triangle = marker_geometry({"shape": "triangle", "headLength": 8, "headWidth": 6,
                                "attachmentOffset": 0})
    assert endpoint_tangent_minimum(2, triangle) == 10
    assert endpoint_lead_run((15, 20), (10, 20), 2, triangle) == 5
    assert endpoint_lead_run((20, 20), (10, 20), 2, triangle) == 0
    lead, _ = intrinsic_span_endpoint_ink((10, 20), "end", 2, triangle,
                                           terminal_side="target")
    assert lead == ObstacleSegment((10, 20), (20, 20), 2)


def test_mandatory_lead_is_a_stroked_closed_contact_obstacle():
    marker = marker_geometry({"shape": "circle", "headLength": 5, "headWidth": 5,
                              "attachmentOffset": 0})
    lead, terminal = intrinsic_span_endpoint_ink((10, 20), "end", 1, marker,
                                                  terminal_side="source")
    label_touching = ObstacleRect(13.5, 18, 20, 22)
    label_clear = ObstacleRect(14.01, 18, 20, 22)
    assert obstacles_intersect(lead, label_touching)
    assert not obstacles_intersect(lead, label_clear)
    assert obstacles_intersect(terminal, ObstacleRect(9.8, 22.4, 10.2, 24))


def test_physical_terminal_stroke_width_expands_completed_marker_ink():
    thin = marker_geometry({"shape": "open-circle", "headLength": 5, "headWidth": 5},
                           stroke_width=1)
    thick = marker_geometry({"shape": "open-circle", "headLength": 5, "headWidth": 5},
                            stroke_width=4)
    _, thin_bounds = intrinsic_span_endpoint_ink((10, 20), "end", 1, thin,
                                                  terminal_side="target")
    _, thick_bounds = intrinsic_span_endpoint_ink((10, 20), "end", 4, thick,
                                                   terminal_side="target")
    assert thin_bounds.left > thick_bounds.left
    assert thin_bounds.top > thick_bounds.top
    assert thin_bounds.right < thick_bounds.right
    assert thin_bounds.bottom < thick_bounds.bottom


@pytest.mark.parametrize("terminal_side", ("source", "target"))
@pytest.mark.parametrize("endpoint", ("start", "end"))
def test_round_terminal_bounds_are_centred_on_the_actual_semantic_port(endpoint, terminal_side):
    marker = centred_on_route(marker_geometry(
        {"shape": "circle", "headLength": 5, "headWidth": 5}, stroke_width=1), terminal_side)
    _, bounds = intrinsic_span_endpoint_ink((10, 20), endpoint, 1, marker,
                                           terminal_side=terminal_side)
    assert bounds == ObstacleRect(7.5, 17.5, 12.5, 22.5)


def test_point_or_body_has_no_intrinsic_span_endpoint_geometry():
    # Endpoint geometry deliberately accepts only semantic span endpoints;
    # callers must filter point/body hosts before invoking it.
    import pytest

    with pytest.raises(ValueError, match="span endpoint"):
        intrinsic_span_endpoint_ink((10, 20), "at", 1, None, terminal_side="source")
