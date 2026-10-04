"""`relationRouting.entry: side` back-routes an abutting chain through the row gap (#1060).

Synthetic Projects only, routed by the real surface composer; the published Scene is what is asserted.
"""
from datetime import date

import pytest

from tests.unit.chrona.presentation.scene.test_relation_entry_side import D, DEP, _bends, _item, _route, _rows
from tests.unit.chrona.presentation.scene.test_relation_route_invariant import gate, reverses


def run(source, target, relation=DEP, *, entry="side", rows=None, max_bends=4, max_detour=6.0,
        window=(D(2026, 1, 25), D(2026, 2, 25))):
    first, second = (source, target) if rows is None else rows
    return _route((source, target), _rows((first,), (second,)), relation, entry, distribution="pack",
                  max_bends=max_bends, max_detour=max_detour, window=window, diagnostics=True)


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


@pytest.mark.parametrize("target_start", [D(2026, 2, 8), D(2026, 2, 5)], ids=["abutting", "overlapping"])
def test_an_abutting_or_overlapping_chain_enters_the_start_from_the_side_through_the_row_gap(target_start):
    target = _item("b", target_start, D(2026, 2, 16))
    points, marks, diagnostics = run(A, target)
    assert enters_from_side(points) and not reverses(points) and _bends(points) <= 4
    leg = gap_leg(points)
    _, source_bottom = band(marks, "planned:a:a")
    target_top, _ = band(marks, "planned:b:b")
    assert source_bottom < leg[0][1] < target_top, "the back leg lies in the gap between the row mark bands"
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


def test_a_gate_target_is_entered_at_its_start_vertex_horizontally_only_with_side():
    target = gate("b", date(2026, 2, 8))
    side, _, _ = run(A, target)
    assert enters_from_side(side) and not reverses(side)
    free, _, _ = run(A, target, entry="side-when-free")
    assert free != side


def test_a_back_leg_through_a_marked_row_falls_back_with_a_diagnostic():
    # Rows a, c, b: the gap line before b's row is clear, but the drop beside a passes through c's long mark.
    blocker = _item("c", D(2026, 1, 25), D(2026, 2, 20))
    target = _item("b", D(2026, 2, 8), D(2026, 2, 16))
    points, marks, diagnostics = _route((A, blocker, target), _rows((A,), (blocker,), (target,)), DEP, "side",
                                        distribution="pack", max_detour=6.0, window=(D(2026, 1, 25), D(2026, 2, 25)),
                                        diagnostics=True)
    assert not reverses(points)
    assert fell_back(diagnostics)
    left, top, width, height = marks["planned:c:c"].bounds
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        crosses = (x1 == x2 and left < x1 < left + width and min(y1, y2) < top + height and max(y1, y2) > top)
        assert not crosses, "no route segment crosses the blocking mark"


@pytest.mark.parametrize("kwargs", [{"max_bends": 3}, {"max_detour": 0.5}], ids=["max-bends", "max-detour"])
def test_a_back_route_over_the_limits_falls_back_with_a_diagnostic(kwargs):
    points, _, diagnostics = run(A, _item("b", D(2026, 2, 8), D(2026, 2, 16)), **kwargs)
    assert not reverses(points)
    assert fell_back(diagnostics)


@pytest.mark.parametrize("entry", ["any", "side-when-free"])
def test_the_other_entry_values_never_back_route_and_never_report(entry):
    target = _item("b", D(2026, 2, 8), D(2026, 2, 16))
    points, _, diagnostics = run(A, target, entry=entry)
    side, _, _ = run(A, target, entry="side")
    assert points != side and not fell_back(diagnostics)


def reason(diagnostics) -> str:
    return next(item.split("reason=", 1)[1] for item in diagnostics if item.startswith("I_LAYOUT_RELATION_ENTRY_FALLBACK"))


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


def test_the_fallback_diagnostic_names_its_reason_1084():
    target = _item("b", D(2026, 2, 8), D(2026, 2, 16))
    _, _, diagnostics = run(A, target, max_bends=3)
    assert reason(diagnostics) == "bends-or-detour"
    blocker = _item("c", D(2026, 1, 25), D(2026, 2, 20))
    _, _, blocked = _route((A, blocker, target), _rows((A,), (blocker,), (target,)), DEP, "side", distribution="pack",
                           max_detour=2.0, window=(D(2026, 1, 25), D(2026, 2, 25)), diagnostics=True,
                           allow_suppressed=True)
    assert any(item.startswith("I_LAYOUT_RELATION_MARK_BLOCKED:") for item in blocked)
    assert any(item.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for item in blocked)


def test_a_mark_after_the_source_end_blocks_the_exit_stub_and_falls_back_with_a_reason_1084():
    # A proxy for a delta label beside the source end: a mark in the exit stub (the stub check treats mark, text and
    # label classes alike).
    source = _item("a", D(2026, 2, 1), D(2026, 2, 8), "shared")
    beside = _item("c", D(2026, 2, 8), D(2026, 2, 12), "shared")
    target = _item("b", D(2026, 2, 8), D(2026, 2, 16))
    points, _, diagnostics = _route((source, beside, target), _rows((source, beside), (target,)), DEP, "side",
                                    distribution="pack", max_detour=2.0, window=(D(2026, 1, 25), D(2026, 2, 25)),
                                    diagnostics=True)
    assert not reverses(points)
    assert fell_back(diagnostics) and reason(diagnostics).startswith("blocked:mark=")
