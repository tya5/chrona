"""`relationRouting.entry: side` back-routes an abutting chain through the row gap (#1060).

Synthetic Projects only, routed by the real surface composer; the published Scene is what is asserted.
"""

from datetime import date
import json

import pytest

from chrona.presentation.layout.relation_hint_model import (
    HintMark, HintMarker, HintRelation, HintSurface, PreviousRouteHints,
)
from tests.unit.chrona.presentation.scene.test_relation_entry_side import (
    D, DEP, _assert_closed_contact_free, _bends, _item, _route, _rows,
)
from tests.unit.chrona.presentation.scene.test_relation_route_invariant import gate, reverses


def run(source, target, relation=DEP, *, entry="side", rows=None, max_bends=4, max_detour=6.0,
        window=(D(2026, 1, 25), D(2026, 2, 25)), search="first-fit", previous_route_hints=None,
        return_surface=False, allow_suppressed=False):
    first, second = (source, target) if rows is None else rows
    return _route((source, target), _rows((first,), (second,)), relation, entry, distribution="pack",
                  max_bends=max_bends, max_detour=max_detour, window=window, diagnostics=True, search=search,
                  previous_route_hints=previous_route_hints, return_surface=return_surface,
                  allow_suppressed=allow_suppressed)


def enters_from_side(points, *, start=True) -> bool:
    return points[-1][1] == points[-2][1] and ((points[-2][0] < points[-1][0]) if start else (points[-2][0] > points[-1][0]))


def gap_leg(points):
    """The longest horizontal segment that is not the entry."""
    legs = [(a, b) for a, b in zip(points, points[1:-1]) if a[1] == b[1] and a != b]
    return max(legs, key=lambda leg: abs(leg[1][0] - leg[0][0])) if legs else None


def band(marks, key):
    mark = marks[key]
    return mark.bounds[1], mark.bounds[1] + mark.bounds[3]


def fell_back(diagnostics) -> bool:
    return any(item.startswith("I_LAYOUT_RELATION_ENTRY_FALLBACK") for item in diagnostics)


A = _item("a", D(2026, 2, 1), D(2026, 2, 8))


def _hint_receipt(diagnostics):
    line = next(item for item in diagnostics if item.startswith("I_LAYOUT_RELATION_HINT:{"))
    return json.loads(line.split(":", 1)[1])


def _hint_summary(diagnostics):
    line = next(item for item in diagnostics if item.startswith("I_LAYOUT_RELATION_HINT_SUMMARY:{"))
    return json.loads(line.split(":", 1)[1])


def _hints(surface):
    marks = tuple(HintMark(item.scene_id, item.source_ref, item.kind.value,
                           item.purpose, item.bounds)
                  for item in surface.primitives if item.scene_id.startswith("planned:"))
    relation = next(item for item in surface.primitives
                    if item.scene_id.startswith("relation:dep:"))

    def marker(value):
        if value is None:
            return None
        return HintMarker(tuple((command.kind, command.points) for command in value.outline),
                          value.head_length, value.head_width, value.attachment_offset,
                          value.paint_mode)

    prior = HintRelation(relation.source_ref, relation.from_instance_id,
                         relation.to_instance_id, relation.points,
                         marker(relation.marker_start), marker(relation.marker_end))
    return PreviousRouteHints(True, (HintSurface("table-timeline", marks, (prior,)),), None)


@pytest.mark.parametrize("target_start", [D(2026, 2, 8), D(2026, 2, 5)], ids=["abutting", "overlapping"])
def test_an_abutting_or_overlapping_chain_enters_the_start_from_the_side_through_the_row_gap(target_start):
    target = _item("b", target_start, D(2026, 2, 16))
    # A generous detour allowance admits a shorter-bend searched side entry.
    # The strict allowance rejects it and exercises the canonical gap route.
    points, marks, diagnostics = run(A, target, max_detour=2.0)
    assert enters_from_side(points) and not reverses(points) and _bends(points) <= 4
    leg = gap_leg(points)
    _, source_bottom = band(marks, "planned:a:a")
    target_top, _ = band(marks, "planned:b:b")
    assert source_bottom < leg[0][1] < target_top, "the back leg lies in the gap between the row mark bands"
    assert not fell_back(diagnostics)


def test_searched_and_back_route_candidates_both_keep_the_minimal_legal_bends():
    target = _item("b", D(2026, 2, 5), D(2026, 2, 16))
    points, marks, diagnostics = run(A, target, max_detour=6.0, search="best")
    canonical, _, _ = run(A, target, max_detour=2.0, search="best")
    assert enters_from_side(points) and not reverses(points)
    assert _bends(points) == _bends(canonical) == 4
    length = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(points, points[1:]))
    direct = abs(points[-1][0] - points[0][0]) + abs(points[-1][1] - points[0][1])
    assert length <= 6.0 * direct
    _assert_closed_contact_free(points, marks)
    assert not fell_back(diagnostics)


def test_a_target_row_above_the_source_uses_the_gap_below_it():
    source, target = _item("a", D(2026, 2, 1), D(2026, 2, 8)), _item("b", D(2026, 2, 8), D(2026, 2, 16))
    points, marks, _ = run(source, target, rows=(target, source))
    assert enters_from_side(points) and not reverses(points)
    _, target_bottom = band(marks, "planned:b:b")
    source_top, _ = band(marks, "planned:a:a")
    assert target_bottom < gap_leg(points)[0][1] < source_top


def test_the_mirrored_end_endpoint_enters_from_the_right():
    relation = {"id": "ff", "from": {"object": "a", "endpoint": "end"}, "to": {"object": "b", "endpoint": "end"}}
    points, _, _ = run(_item("a", D(2026, 2, 10), D(2026, 2, 12)), _item("b", D(2026, 2, 1), D(2026, 2, 12)), relation)
    assert enters_from_side(points, start=False) and not reverses(points) and _bends(points) <= 4


def test_a_gate_target_can_use_the_safe_horizontal_route_with_both_side_preferences():
    target = gate("b", date(2026, 2, 8))
    side, marks, diagnostics = run(A, target)
    assert enters_from_side(side) and not reverses(side)
    _assert_closed_contact_free(side, marks)
    free, _, _ = run(A, target, entry="side-when-free")
    assert free == side
    assert not fell_back(diagnostics)


def test_a_marked_row_that_blocks_the_back_leg_causes_declared_suppression():
    # Rows a, c, b: the gap line before b's row is clear, but the drop beside a passes through c's long mark.
    blocker = _item("c", D(2026, 1, 25), D(2026, 2, 20))
    target = _item("b", D(2026, 2, 8), D(2026, 2, 16))
    points, _, diagnostics = _route((A, blocker, target), _rows((A,), (blocker,), (target,)), DEP, "side",
                                        distribution="pack", max_detour=6.0, window=(D(2026, 1, 25), D(2026, 2, 25)),
                                        diagnostics=True, allow_suppressed=True)
    assert points == ()
    assert any(item.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for item in diagnostics)


@pytest.mark.parametrize("kwargs", [{"max_bends": 2}, {"max_detour": 0.5}], ids=["max-bends", "max-detour"])
def test_over_quality_back_route_uses_an_alternative_or_declared_suppression(kwargs):
    target = _item("b", D(2026, 2, 8), D(2026, 2, 16))
    if "max_detour" in kwargs:
        points, _, diagnostics = _route((A, target), _rows((A,), (target,)), DEP, "side",
            distribution="pack", max_detour=kwargs["max_detour"],
            window=(D(2026, 1, 25), D(2026, 2, 25)), diagnostics=True, allow_suppressed=True)
        assert not points
        assert any(d.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for d in diagnostics)
        return
    points, _, diagnostics = _route((A, target), _rows((A,), (target,)), DEP, "side",
        distribution="pack", max_bends=kwargs["max_bends"], max_detour=6.0,
        window=(D(2026, 1, 25), D(2026, 2, 25)), diagnostics=True, allow_suppressed=True)
    assert points == ()
    assert any(item.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for item in diagnostics)


@pytest.mark.parametrize("entry", ["any", "side-when-free"])
def test_the_other_entry_values_never_back_route_and_never_report(entry):
    target = _item("b", D(2026, 2, 8), D(2026, 2, 16))
    points, marks, diagnostics = _route((A, target), _rows((A,), (target,)), DEP, entry,
        distribution="pack", max_detour=6.0, window=(D(2026, 1, 25), D(2026, 2, 25)),
        diagnostics=True, allow_suppressed=True)
    assert not fell_back(diagnostics)
    assert points
    assert points == run(A, target, entry="side")[0]
    _assert_closed_contact_free(points, marks)


@pytest.mark.parametrize("target_start", [D(2026, 2, 8), D(2026, 2, 5), D(2026, 2, 9)],
                         ids=["abutting", "overlapping", "slightly-right"])
def test_the_declared_detour_ratio_of_two_admits_the_back_route_1084(target_start):
    # The two stubs and the sideways leg are mandatory for a side entry, so the detour is measured against the
    # shortest route that keeps them; the profile's ratio 2 therefore admits the canonical shape.
    points, _, diagnostics = run(A, _item("b", target_start, D(2026, 2, 16)), max_detour=2.0)
    assert enters_from_side(points) and not reverses(points) and not fell_back(diagnostics)


def test_a_source_just_left_of_the_start_is_back_routed_when_the_forward_entry_has_no_room_1084():
    # The forward entry needs a stub between the source and the start; a gate one day before the start on a long
    # window leaves less than a stub, and the back-route is tried after the forward entry.
    source, target = gate("a", date(2026, 2, 8)), _item("b", D(2026, 2, 9), D(2026, 2, 16))
    points, _, diagnostics = _route((source, target), _rows((source,), (target,)), DEP, "side", distribution="pack",
                                    max_detour=2.0, window=(D(2026, 1, 1), D(2027, 2, 1)), diagnostics=True)
    assert enters_from_side(points) and not reverses(points) and not fell_back(diagnostics)


def test_unroutable_quality_limit_has_a_declared_suppression_1084():
    target = _item("b", D(2026, 2, 8), D(2026, 2, 16))
    points, _, diagnostics = _route((A, target), _rows((A,), (target,)), DEP, "side",
        distribution="pack", max_bends=2, max_detour=6.0,
        window=(D(2026, 1, 25), D(2026, 2, 25)), diagnostics=True, allow_suppressed=True)
    assert points == ()
    assert any(item.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for item in diagnostics)
    blocker = _item("c", D(2026, 1, 25), D(2026, 2, 20))
    _, _, blocked = _route((A, blocker, target), _rows((A,), (blocker,), (target,)), DEP, "side", distribution="pack",
                           max_detour=2.0, window=(D(2026, 1, 25), D(2026, 2, 25)), diagnostics=True,
                           allow_suppressed=True)
    assert any(item.startswith("I_LAYOUT_RELATION_POLICY_SUPERSEDED:") for item in blocked)
    assert any(item.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for item in blocked)


def test_a_mark_occupying_the_source_exit_causes_declared_suppression():
    # The adjacent same-lane mark occupies the only available outward exit.
    source = _item("a", D(2026, 2, 1), D(2026, 2, 8), "shared")
    beside = _item("c", D(2026, 2, 8), D(2026, 2, 12), "shared")
    target = _item("b", D(2026, 2, 8), D(2026, 2, 16))
    points, _, diagnostics = _route((source, beside, target), _rows((source, beside), (target,)), DEP, "side",
                                    distribution="pack", max_detour=2.0, window=(D(2026, 1, 25), D(2026, 2, 25)),
                                    diagnostics=True, allow_suppressed=True)
    assert points == ()
    assert any(item.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for item in diagnostics)


@pytest.mark.parametrize("search", ("first-fit", "best"))
def test_safe_canonical_back_route_hint_is_preferred_before_normal_search(search):
    # This is the original canonical back-route fixture: source and target
    # abut, so its corridor reference differs from generic direct-route quality.
    target = _item("b", D(2026, 2, 8), D(2026, 2, 16))
    old_points, _, old_surface = run(A, target, max_detour=2.0, search=search, return_surface=True)
    hinted, _, diagnostics = run(A, target, max_detour=2.0, search=search,
                                previous_route_hints=_hints(old_surface))

    assert hinted == old_points
    assert enters_from_side(old_points) and _bends(old_points) == 4
    assert _hint_receipt(diagnostics) == {
        "disposition": "accepted", "reason": "revalidated", "relationId": "relation:dep:a:a:b:b",
        "searched": False, "surfaceId": "table-timeline",
    }
    assert _hint_summary(diagnostics)["accepted"] == 1
    assert _hint_summary(diagnostics)["actualSearch"] == 0
    assert not any(item.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for item in diagnostics)


def test_blocked_prior_back_route_is_rejected_and_does_not_bypass_obstacle_validation():
    target = _item("b", D(2026, 2, 8), D(2026, 2, 16))
    old_points, _, old_surface = run(A, target, max_detour=6.0, return_surface=True)
    blocker = _item("c", D(2026, 1, 25), D(2026, 2, 20))
    points, _, diagnostics = _route(
        (A, blocker, target), _rows((A,), (blocker,), (target,)), DEP, "side",
        distribution="pack", max_detour=6.0, window=(D(2026, 1, 25), D(2026, 2, 25)),
        diagnostics=True, allow_suppressed=True,
        previous_route_hints=_hints(old_surface),
    )
    receipt = _hint_receipt(diagnostics)
    assert receipt["disposition"] == "invalidated"
    assert receipt["reason"] == "E_LAYOUT_ROUTE_THROUGH_MARK"
    assert receipt["searched"] is True
    assert _hint_summary(diagnostics)["accepted"] == 0
    assert _hint_summary(diagnostics)["actualSearch"] == 1
    assert points == ()
    assert points != old_points
    assert "W_LAYOUT_RELATION_SUPPRESSED:relation:dep:a:a:b:b" in diagnostics


def test_back_route_hint_that_exceeds_the_current_quality_bound_is_not_accepted():
    target = _item("b", D(2026, 2, 8), D(2026, 2, 16))
    old_points, _, old_surface = run(A, target, max_detour=2.0, return_surface=True)
    points, _, diagnostics = run(A, target, max_detour=0.5, allow_suppressed=True,
                                 previous_route_hints=_hints(old_surface))
    receipt = _hint_receipt(diagnostics)
    assert receipt["disposition"] == "invalidated"
    assert receipt["reason"] == "quality-rejected"
    assert receipt["searched"] is True
    assert _hint_summary(diagnostics)["accepted"] == 0
    assert _hint_summary(diagnostics)["actualSearch"] == 1
    assert points == ()
    assert points != old_points
    assert "W_LAYOUT_RELATION_SUPPRESSED:relation:dep:a:a:b:b" in diagnostics
