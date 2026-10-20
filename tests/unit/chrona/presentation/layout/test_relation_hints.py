from decimal import Decimal

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.ports import ConnectorEgress
from chrona.presentation.layout.relation_hint_model import (
    HintMark, HintMarker, HintRelation, HintSurface, PreviousRouteHints,
)
from chrona.presentation.layout.relation_hints import propose_hint
from chrona.presentation.layout.relation_terminals import complete_centred_terminals
from chrona.presentation.layout.surface_quality import MarkPlacement, MarkerGeometry, PathCommand


SURFACE = "table-timeline"
RELATION = "r0"
SOURCE = "source-instance"
TARGET = "target-instance"


def _mark(placement_id, source_ref, bounds, *, shape="span", kind=None):
    x, y, width, height = bounds
    rect = Rect(*(Decimal(str(value)) for value in bounds))
    return MarkPlacement(placement_id, source_ref, rect,
        (x, y + height / 2), (x + width, y + height / 2),
        mark_shape=shape, semantic_id="planned")


def _hint_mark(mark, *, kind=None, source_ref=None):
    return HintMark(mark.placement_id, source_ref or mark.source_ref,
        kind or ("Symbol" if mark.mark_shape == "point" else "Rect"), "planned",
        (float(mark.bounds.inline), float(mark.bounds.block),
         float(mark.bounds.inline_size), float(mark.bounds.block_size)))


def _route(source_mark, target_mark, *, source_side="start", target_side="end",
           source_endpoint="start", target_endpoint="finish", channel=None,
           source_exposed=None, target_exposed=None, marker_start=None, marker_end=None,
           stroke_width=1.0):
    sx, sy = (source_mark.start_port if source_endpoint == "start" else source_mark.end_port)
    tx, ty = (target_mark.start_port if target_endpoint == "start" else target_mark.end_port)
    source_exposed = source_exposed or (sx, sy)
    target_exposed = target_exposed or (tx, ty)
    source = ConnectorEgress(source_side, (sx, sy), source_exposed, (source_mark.placement_id,))
    target = ConnectorEgress(target_side, (tx, ty), target_exposed, (target_mark.placement_id,))
    middle = channel or (source_exposed, target_exposed)
    raw = tuple(dict.fromkeys((*source.corridor, *middle, *reversed(target.corridor))))
    drawn, marker_start, marker_end = complete_centred_terminals(raw, marker_start, marker_end, stroke_width)
    return source, target, drawn, marker_start, marker_end


def _hints(marks, points, marker_start=None, marker_end=None, *, endpoint_identity=True,
           terminal_compatible=True, duplicate_relation=False, mark_kinds=None):
    relation = HintRelation(RELATION, SOURCE, TARGET, tuple(points),
                           marker_start, marker_end)
    relations = (relation, relation) if duplicate_relation else (relation,)
    hint_marks = tuple(_hint_mark(mark, kind=kind) for mark, kind in zip(marks, mark_kinds)) if mark_kinds else tuple(
        _hint_mark(mark) for mark in marks)
    return PreviousRouteHints(endpoint_identity,
        (HintSurface(SURFACE, hint_marks, relations),),
        "theme-sha256", terminal_compatible)


def _propose(hints, source_mark, target_mark, source_pair, target_pair, *,
             source_endpoint="start", target_endpoint="finish", marker_start=None,
             marker_end=None, source_siblings=(), target_siblings=(), stroke_width=1.0):
    return propose_hint(hints, surface_id=SURFACE, source_ref=RELATION,
        source_id=SOURCE, target_id=TARGET, source_mark=source_mark, target_mark=target_mark,
        source_endpoint=source_endpoint, target_endpoint=target_endpoint,
        source_siblings=source_siblings, target_siblings=target_siblings,
        port_pairs=((source_pair, target_pair),), marker_start=marker_start,
        marker_end=marker_end, stroke_width=stroke_width)


def _round_marker():
    outline = (PathCommand("move", ((1.0, 0.0),)),
        PathCommand("quadratic", ((2.0, 0.0), (2.0, 1.0))),
        PathCommand("quadratic", ((2.0, 2.0), (1.0, 2.0))),
        PathCommand("quadratic", ((0.0, 2.0), (0.0, 1.0))),
        PathCommand("quadratic", ((0.0, 0.0), (1.0, 0.0))))
    return MarkerGeometry(outline, 2.0, 2.0, 1.0, "fill", centred=True)


def _hint_marker(marker):
    return HintMarker(tuple((command.kind, command.points) for command in marker.outline),
        marker.head_length, marker.head_width, marker.attachment_offset, marker.paint_mode)


def test_whole_translation_preserves_the_old_port_sides_and_translates_route():
    old_source, old_target = _mark("planned:source-instance", "source", (0, 0, 10, 4)), _mark(
        "planned:target-instance", "target", (20, 0, 10, 4))
    old_s, old_t, points, _, _ = _route(old_source, old_target,
        channel=((0, 2), (-5, 2), (-5, 6), (35, 6), (35, 2), (30, 2)))
    # Source and target move together; both preserved sides are horizontal.
    source = _mark(old_source.placement_id, "source", (3, 5, 10, 4))
    target = _mark(old_target.placement_id, "target", (23, 5, 10, 4))
    new_s = ConnectorEgress("start", source.start_port, source.start_port, (source.placement_id,))
    new_t = ConnectorEgress("end", target.end_port, target.end_port, (target.placement_id,))
    proposal = _propose(_hints((old_source, old_target), points), source, target,
                        new_s, new_t)

    assert proposal.disposition == "proposed"
    assert proposal.candidates[0].pair == (new_s, new_t)
    assert proposal.candidates[0].middle == tuple((x + 3, y + 5) for x, y in points)
    assert (old_s.side, old_t.side) == (new_s.side, new_t.side)


def test_differential_endpoint_reanchor_keeps_interior_l_channel_coordinates():
    old_source, old_target = _mark("planned:source-instance", "source", (0, 0, 10, 4)), _mark(
        "planned:target-instance", "target", (20, 0, 10, 4))
    _, _, points, _, _ = _route(old_source, old_target,
        channel=((0, 2), (-5, 2), (-5, 6), (35, 6), (35, 2), (30, 2)))
    source = _mark(old_source.placement_id, "source", (1, 0, 10, 4))
    target = _mark(old_target.placement_id, "target", (20, 2, 10, 4))
    new_s = ConnectorEgress("start", source.start_port, source.start_port, (source.placement_id,))
    new_t = ConnectorEgress("end", target.end_port, target.end_port, (target.placement_id,))
    proposal = _propose(_hints((old_source, old_target), points), source, target, new_s, new_t)

    assert proposal.disposition == "proposed"
    assert proposal.candidates[0].pair == (new_s, new_t)
    assert (-5, 6) in proposal.candidates[0].middle and (35, 6) in proposal.candidates[0].middle
    assert all(a[0] == b[0] or a[1] == b[1]
               for a, b in zip(proposal.candidates[0].middle, proposal.candidates[0].middle[1:]))


def test_short_two_point_centered_round_terminals_are_inverted_exactly():
    start, end = _round_marker(), _round_marker()
    raw = ((0.0, 0.0), (2.0, 0.0))
    old_points, start, end = complete_centred_terminals(raw, start, end, 1.0)
    hints = _hints((), old_points, _hint_marker(start), _hint_marker(end))
    source = ConnectorEgress("end", (0.0, 0.0), (0.0, 0.0), ())
    target = ConnectorEgress("start", (2.0, 0.0), (2.0, 0.0), ())

    proposal = _propose(hints, None, None, source, target,
        source_endpoint="at", target_endpoint="at", marker_start=start,
        marker_end=end, stroke_width=1.0)

    assert proposal.disposition == "proposed"
    assert proposal.candidates[0].pair == (source, target)
    assert proposal.candidates[0].middle == ((0.0, 0.0), (2.0, 0.0))


def test_painted_rect_and_symbol_hosts_propose_supported_geometry():
    source = _mark("planned:source-instance", "source", (0, 0, 4, 4), shape="point")
    target = _mark("planned:target-instance", "target", (20, 0, 10, 4))
    old_s = ConnectorEgress("end", (4, 2), (4, 2), (source.placement_id,))
    old_t = ConnectorEgress("start", target.start_port, target.start_port, (target.placement_id,))
    points = ((4, 2), (10, 2), (20, 2))
    hints = _hints((source, target), points)

    proposal = _propose(hints, source, target, old_s, old_t,
        source_endpoint="at", target_endpoint="start")

    assert proposal.disposition == "proposed"
    assert proposal.candidates[0].pair == (old_s, old_t)


@pytest.mark.parametrize(("shape", "old_kind"), [
    ("span", "Rect"), ("span", "Symbol"), ("point", "Rect"), ("point", "Symbol"),
])
def test_host_primitive_kind_does_not_override_temporal_point_or_span_ports(shape, old_kind):
    source = _mark("planned:source-instance", "source", (0, 0, 10, 4), shape=shape)
    target = _mark("planned:target-instance", "target", (20, 0, 10, 4), shape=shape)
    source_endpoint = "at" if shape == "point" else "start"
    target_endpoint = "at" if shape == "point" else "finish"
    source_egress = ConnectorEgress("end" if shape == "point" else "start",
        source.end_port if shape == "point" else source.start_port,
        source.end_port if shape == "point" else source.start_port, (source.placement_id,))
    target_egress = ConnectorEgress("start" if shape == "point" else "end",
        target.start_port if shape == "point" else target.end_port,
        target.start_port if shape == "point" else target.end_port, (target.placement_id,))
    old_scene = _hints((source, target), (source_egress.semantic_port, target_egress.semantic_port),
                       mark_kinds=(old_kind, old_kind))

    proposal = _propose(old_scene, source, target, source_egress, target_egress,
                        source_endpoint=source_endpoint, target_endpoint=target_endpoint)

    assert proposal.disposition == "proposed"
    assert proposal.candidates[0].pair == (source_egress, target_egress)


def test_unknown_old_host_geometry_still_refuses_the_hint():
    source, target = _mark("planned:source-instance", "source", (0, 0, 10, 4)), _mark(
        "planned:target-instance", "target", (20, 0, 10, 4))
    source_egress = ConnectorEgress("end", source.end_port, source.end_port, (source.placement_id,))
    target_egress = ConnectorEgress("start", target.start_port, target.start_port, (target.placement_id,))
    hints = _hints((source, target), (source.end_port, target.start_port), mark_kinds=("Glyph", "Rect"))

    proposal = _propose(hints, source, target, source_egress, target_egress)

    assert proposal.disposition == "unusable"
    assert proposal.reason == "host-geometry"


def test_unpainted_rollup_uses_only_compatible_theme_terminal_provenance():
    start, end = _round_marker(), _round_marker()
    raw = ((0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (20.0, 5.0), (20.0, 0.0))
    points, completed_start, completed_end = complete_centred_terminals(raw, start, end, 1.0)
    source = ConnectorEgress("end", raw[0], raw[0], ())
    target = ConnectorEgress("start", raw[-1], raw[-1], ())
    args = dict(source_endpoint="at", target_endpoint="at", marker_start=start,
                marker_end=end, stroke_width=1.0)

    compatible = _propose(_hints((), points, _hint_marker(completed_start),
        _hint_marker(completed_end), terminal_compatible=True), None, None, source, target, **args)
    incompatible = _propose(_hints((), points, _hint_marker(completed_start),
        _hint_marker(completed_end), terminal_compatible=False), None, None, source, target, **args)

    assert compatible.disposition == "proposed"
    assert incompatible.disposition == "unusable"
    assert incompatible.reason == "unpainted-terminal-provenance"


@pytest.mark.parametrize(("change", "reason"), [
    ("missing-host", "host-geometry"),
    ("wrong-relation", "relation-identity"),
    ("v06", "missing-endpoint-identity"),
    ("duplicate", "relation-identity"),
])
def test_missing_or_untrusted_identity_is_not_guessed(change, reason):
    source, target = _mark("planned:source-instance", "source", (0, 0, 10, 4)), _mark(
        "planned:target-instance", "target", (20, 0, 10, 4))
    s = ConnectorEgress("end", source.end_port, source.end_port, (source.placement_id,))
    t = ConnectorEgress("start", target.start_port, target.start_port, (target.placement_id,))
    points = (source.end_port, target.start_port)
    marks = (source, target)
    hints = _hints(marks, points,
        endpoint_identity=change != "v06", duplicate_relation=change == "duplicate")
    if change == "missing-host":
        hints = _hints((target,), points)
    elif change == "wrong-relation":
        surface = hints.surfaces[0]
        relation = HintRelation("other-relation", SOURCE, TARGET, points, None, None)
        hints = PreviousRouteHints(True, (HintSurface(SURFACE, surface.marks, (relation,)),),
                                   "theme-sha256", True)

    proposal = _propose(hints, source, target, s, t)

    assert proposal.disposition in {"unusable", "absent"}
    assert proposal.reason == reason


def test_multiple_current_span_egress_choices_are_offered_in_first_fit_order():
    source, target = _mark("planned:source-instance", "source", (0, 0, 10, 4)), _mark(
        "planned:target-instance", "target", (20, 0, 10, 4))
    points = ((0, 2), (0, 0), (5, 0), (20, 0), (30, 0), (30, 2))
    start_egress = ConnectorEgress("start", (0, 2), (0, 2), (source.placement_id,))
    above_egress = ConnectorEgress("above", (0, 2), (5, 0), (source.placement_id,))
    target_egress = ConnectorEgress("end", target.end_port, target.end_port, (target.placement_id,))
    proposal = propose_hint(_hints((source, target), points), surface_id=SURFACE,
        source_ref=RELATION, source_id=SOURCE, target_id=TARGET,
        source_mark=source, target_mark=target, source_endpoint="start", target_endpoint="finish",
        source_siblings=(), target_siblings=(),
        port_pairs=((start_egress, target_egress), (above_egress, target_egress)),
        marker_start=None, marker_end=None, stroke_width=1.0)

    assert proposal.disposition == "proposed"
    assert tuple(item.pair for item in proposal.candidates) == (
        (start_egress, target_egress), (above_egress, target_egress))


def test_point_left_port_is_recovered_when_route_arrives_vertically():
    source = _mark("planned:source-instance", "source", (0, 0, 4, 4), shape="point")
    points = ((0, 2), (0, 0), (20, 0))
    source_egress = ConnectorEgress("start", (0, 2), (0, 2), (source.placement_id,))
    target_egress = ConnectorEgress("end", (20, 0), (20, 0), ())

    proposal = _propose(_hints((source,), points), source, None, source_egress, target_egress,
                        source_endpoint="at", target_endpoint="at")

    assert proposal.disposition == "proposed"
    assert proposal.candidates[0].pair == (source_egress, target_egress)


@pytest.mark.parametrize("points", [
    ((0, 0), (1, 1)),
    ((0, 0), (0, 0)),
])
def test_diagonal_or_degenerate_old_geometry_is_not_a_hint(points):
    source, target = _mark("planned:source-instance", "source", (0, 0, 4, 4), shape="point"), _mark(
        "planned:target-instance", "target", (20, 0, 4, 4), shape="point")
    hints = _hints((source, target), points)
    s = ConnectorEgress("end", (2, 2), (4, 2), (source.placement_id,))
    t = ConnectorEgress("start", (22, 2), (20, 2), (target.placement_id,))

    proposal = _propose(hints, source, target, s, t, source_endpoint="at", target_endpoint="at")

    assert proposal.disposition == "unusable"
    assert proposal.reason == "unsupported-shape"


def test_changed_egress_corridor_invalidates_instead_of_reanchoring_through_host():
    old_source, old_target = _mark("planned:source-instance", "source", (0, 0, 10, 4)), _mark(
        "planned:target-instance", "target", (20, 0, 10, 4))
    _, _, points, _, _ = _route(old_source, old_target,
        channel=((0, 2), (-5, 2), (-5, 6), (35, 6), (35, 2), (30, 2)))
    source, target = old_source, old_target
    s = ConnectorEgress("start", source.start_port, (-10, source.start_port[1]), (source.placement_id,))
    t = ConnectorEgress("end", target.end_port, target.end_port, (target.placement_id,))

    proposal = _propose(_hints((old_source, old_target), points), source, target, s, t)

    assert proposal.disposition == "invalidated"
    assert proposal.reason == "changed-egress-corridor"


def test_reanchoring_that_reverses_a_two_point_port_side_is_invalidated():
    old_source, old_target = _mark("planned:source-instance", "source", (0, 0, 4, 4), shape="point"), _mark(
        "planned:target-instance", "target", (10, 0, 4, 4), shape="point")
    old_s = ConnectorEgress("end", (4, 2), (4, 2), (old_source.placement_id,))
    old_t = ConnectorEgress("start", (10, 2), (10, 2), (old_target.placement_id,))
    points = ((4, 2), (10, 2))
    source, target = _mark(old_source.placement_id, "source", (20, 0, 4, 4), shape="point"), _mark(
        old_target.placement_id, "target", (10, 0, 4, 4), shape="point")
    new_s = ConnectorEgress("end", (24, 2), (24, 2), (source.placement_id,))
    new_t = ConnectorEgress("start", (10, 2), (10, 2), (target.placement_id,))

    proposal = _propose(_hints((old_source, old_target), points), source, target,
                        new_s, new_t, source_endpoint="at", target_endpoint="at")

    assert proposal.disposition == "invalidated"
    assert proposal.reason == "shape-degenerated"
