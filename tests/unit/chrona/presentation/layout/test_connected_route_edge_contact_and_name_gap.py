"""Connected recovery before a paired stub, mark-edge contact and the member-name gap (#1908)."""
from dataclasses import replace

import pytest

from chrona.presentation.layout.member_name_yield import MemberNameYieldRequest
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle
from chrona.presentation.layout.ports import ConnectorEgress
from chrona.presentation.layout.surface_member_labels import place_member_labels, prepare_member_labels
from chrona.presentation.layout.surface_routes import (
    _primary_egress_blockers, _primary_mark_contact_is_clear,
)
from tests.unit.chrona.presentation.layout.test_member_label_exchange import (
    _hosted_context_and_obstacles, _request,
)


def _bounds(placement_id="planned:source", *, left=0, top=0, right=100, bottom=10):
    return ((placement_id, ObstacleRect(left, top, right, bottom)),)


def _parts(points):
    return tuple((start, end, ()) for start, end in zip(points, points[1:]))


def _clear(points, *, edge, source=None, target=None):
    return _primary_mark_contact_is_clear(_parts(points), _bounds(), route_start=points[0],
        route_end=points[-1], source_egress=source, target_egress=target, edge_contact=edge)


# --- the exact edge-contact exception ---------------------------------------------------------

@pytest.mark.parametrize("route", (
    ((100, 5), (105, 5), (105, 0), (50, 0), (50, -15)),   # runs along the top edge
    ((100, 5), (100, 0), (115, 0), (115, -15)),           # runs along the end face
    ((50, -15), (50, 0), (50, -3)),                       # touches the edge and leaves
))
def test_boundary_travel_is_blocked_normally_and_allowed_only_under_edge_contact(route):
    source = ConnectorEgress("end", (100, 5), (100, 5), ("planned:source",))
    assert not _clear(route, edge=False, source=source)
    assert _clear(route, edge=True, source=source)


@pytest.mark.parametrize("route", (
    ((-10, 5), (50, 5)),                 # enters the interior through the left face
    ((50, -15), (50, 25)),               # crosses top to bottom
    ((10, 0), (10, 5), (90, 5)),         # starts on the edge, then runs inside
))
def test_interior_travel_is_never_allowed_by_the_edge_exception(route):
    assert not _clear(route, edge=True)
    assert not _clear(route, edge=False)


def test_edge_exception_leaves_physical_corridor_authorization_and_other_marks_alone():
    bounds = (*_bounds(), *_bounds("planned:other", left=200, right=300))
    route = ((150, 5), (250, 5))
    assert not _primary_mark_contact_is_clear(_parts(route), bounds, route_start=route[0],
        route_end=route[-1], edge_contact=True)
    along_other_edge = ((150, 0), (250, 0))
    assert _primary_mark_contact_is_clear(_parts(along_other_edge), bounds, route_start=along_other_edge[0],
        route_end=along_other_edge[-1], edge_contact=True)


def test_end_face_egress_corridor_is_a_blocker_only_without_the_edge_exception():
    invalid = ConnectorEgress("above", (100, 5), (100, 0), ("planned:source",))
    assert _primary_egress_blockers(invalid, _bounds()) == ("planned:source",)
    assert _primary_egress_blockers(invalid, _bounds(), edge_contact=True) == ()


# --- placed member-name groups keep the declared label gap ------------------------------------

def _gap_of(context):
    treatment = context.request.theme_tokens.text_treatment("text")
    return max(1.0, float(treatment.font_size) * 0.25)


def _group_distance(batch, first_id, second_id):
    first, = (item.bounds for item in batch.shapes if item.source_ref == first_id)
    second, = (item.bounds for item in batch.shapes if item.source_ref == second_id)
    left, right = sorted((first, second), key=lambda box: box.inline)
    return float(right.inline - (left.inline + left.inline_size))


def _two_names(second_x, *, icon_on=None):
    context, obstacles = _hosted_context_and_obstacles(first_x=50, second_x=second_x, icon_on=icon_on)
    first = _request("member-label:first", "planned:first:first", "AAAA", 50, ("end",))
    second = _request("member-label:second", "planned:second:second", "BB", second_x, ("start",))
    return context, obstacles, first, second


def test_two_names_that_would_abut_do_not_touch_and_a_gap_wide_fit_is_kept():
    # first's end footprint ends at 106.5; second's start footprint begins at second_x - 26.5.
    context, obstacles, first, second = _two_names(133)  # abutting: distance 0
    batch = place_member_labels(context, (first, second), obstacles)
    by_id = {item.placement_id: item for item in batch.text}
    assert by_id[first.placement_id].overflow == "fit"
    assert by_id[second.placement_id].overflow == "suppressed"

    gap = _gap_of(context)
    context, obstacles, first, second = _two_names(133 + gap - 1)  # closer than the gap
    batch = place_member_labels(context, (first, second), obstacles)
    assert {item.placement_id: item.overflow for item in batch.text}[second.placement_id] == "suppressed"

    context, obstacles, first, second = _two_names(133 + gap)  # exactly the gap
    batch = place_member_labels(context, (first, second), obstacles)
    assert all(item.overflow == "fit" for item in batch.text)
    assert _group_distance(batch, first.placement_id, second.placement_id) == pytest.approx(gap)


def test_gap_is_measured_from_the_complete_text_chip_and_icon_group():
    context, obstacles, first, second = _two_names(150, icon_on="member-label:second")
    batch = place_member_labels(context, (first, second), obstacles)
    icon, = (item for item in batch.icons if item.host_placement_id == second.placement_id)
    chip, = (item for item in batch.shapes if item.source_ref == second.placement_id)
    # the icon lies inside the chip footprint, so the gap to the neighbour is the footprint's, not the text's
    assert chip.bounds.inline <= icon.bounds.inline
    if all(item.overflow == "fit" for item in batch.text):
        assert _group_distance(batch, first.placement_id, second.placement_id) >= _gap_of(context) - 1e-9
    text = {item.placement_id: item for item in batch.text}
    assert float(chip.bounds.inline) <= float(text[second.placement_id].bounds.inline)


def test_gap_adds_no_clearance_to_what_routes_and_other_labels_see():
    context, obstacles, first, second = _two_names(140)
    session = prepare_member_labels(context, (first, second), obstacles)
    assert all(item.clearance == 0.0 for item in session.obstacles.all()
               if item.placement_id.startswith(("member-label:", "label-footprint:member-label:")))
    session.finish()


# --- yield: relocation, one local displacement, no recursion ------------------------------------

def test_yield_moves_a_name_off_the_route_ink_and_keeps_the_gap():
    context, obstacles = _hosted_context_and_obstacles(first_x=60, second_x=200)
    request = _request("member-label:first", "planned:first:first", "AAAA", 60, ("end", "start"))
    session = prepare_member_labels(context, (request,), obstacles)
    before = session.text[0]
    footprint = session.obstacles.get("label-footprint:member-label:first")
    ink = SurfaceObstacle("route-candidate:r:segment:0", "dependency-route", "timeline",
        replace_rect(footprint.geometry))
    yielded = session.yield_for_endpoint(MemberNameYieldRequest(("member-label:first",), (ink,)),
                                         session.obstacles)
    assert yielded is not None and yielded.text[0].overflow != "suppressed"
    assert yielded.text[0].bounds != before.bounds
    moved = yielded.obstacles.get("label-footprint:member-label:first").geometry
    assert moved.right <= ink.geometry.left or moved.left >= ink.geometry.right or (
        moved.bottom <= ink.geometry.top or moved.top >= ink.geometry.bottom)
    session.finish()


def replace_rect(geometry):
    return ObstacleRect(geometry.left, geometry.top, geometry.right, geometry.bottom)


def _displacement_session(first_ladder, *, first_required=False, displace=True):
    context, obstacles = _hosted_context_and_obstacles(first_x=50, second_x=110)
    first = _request("member-label:first", "planned:first:first", "AAAA", 50, first_ladder,
                     required=first_required)
    second = _request("member-label:second", "planned:second:second", "BB", 110, ("start", "end"))
    session = prepare_member_labels(context, (first, second), obstacles)
    placed = {item.placement_id: item for item in session.text}
    # `second` holds its end pose because `first` solely holds its start pose.
    assert placed["member-label:first"].selected_rung == "end"
    assert placed["member-label:second"].selected_rung == "end"
    held = session.obstacles.get("label-footprint:member-label:second").geometry
    ink = SurfaceObstacle("route-candidate:r:segment:0", "dependency-route", "timeline",
        ObstacleRect(held.left - 1, held.top - 100, held.right + 1, held.bottom + 100))
    return context, session, MemberNameYieldRequest(("member-label:second",), (ink,), displace=displace)


def test_name_without_a_clear_pose_takes_the_pose_one_other_name_solely_holds_and_that_name_moves():
    context, session, request = _displacement_session(("end", "start"))
    result = session.yield_for_endpoint(request, session.obstacles)
    names = {item.placement_id: item for item in result.text}
    assert names["member-label:second"].selected_rung == "start"
    assert names["member-label:first"].selected_rung == "start"
    assert all(item.overflow == "fit" for item in names.values())
    first = result.obstacles.get("label-footprint:member-label:first").geometry
    second = result.obstacles.get("label-footprint:member-label:second").geometry
    assert second.left - first.right >= _gap_of(context)
    final = session.finish()
    assert not any(item.startswith("W_LAYOUT_LABEL_SUPPRESSED") for item in final.diagnostics)


def test_the_displaced_name_is_omitted_with_the_ordinary_diagnostic_when_it_has_no_other_pose():
    _, session, request = _displacement_session(("end",))
    result = session.yield_for_endpoint(request, session.obstacles)
    names = {item.placement_id: item for item in result.text}
    assert names["member-label:second"].selected_rung == "start" and names["member-label:second"].overflow == "fit"
    assert names["member-label:first"].overflow == "suppressed"
    assert not result.obstacles.has("label-footprint:member-label:first")
    final = session.finish()
    assert "W_LAYOUT_LABEL_SUPPRESSED:member-label:first" in final.diagnostics


def test_a_required_name_is_never_displaced_so_the_yielding_name_is_omitted_instead():
    _, session, request = _displacement_session(("end",), first_required=True)
    before = {item.placement_id: item for item in session.text}
    result = session.yield_for_endpoint(request, session.obstacles)
    names = {item.placement_id: item for item in result.text}
    assert names["member-label:first"].bounds == before["member-label:first"].bounds
    assert names["member-label:second"].overflow == "suppressed"
    final = session.finish()
    assert "W_LAYOUT_LABEL_SUPPRESSED:member-label:second" in final.diagnostics


def test_a_required_stub_endpoint_yield_never_displaces_another_name():
    _, session, request = _displacement_session(("end", "start"), displace=False)
    before = {item.placement_id: item for item in session.text}
    result = session.yield_for_endpoint(request, session.obstacles)
    names = {item.placement_id: item for item in result.text}
    assert names["member-label:first"].bounds == before["member-label:first"].bounds
    assert names["member-label:second"].overflow == "suppressed"
