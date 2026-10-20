from __future__ import annotations

import json

from chrona.presentation.layout.relation_style import (
    complete_relation_style, curved_path_segments,
)
from chrona.presentation.layout.surface_quality import PathCommand, RelationPlacement


def _relation(points, *, commands=(), radius=3.0):
    return RelationPlacement(
        "relation-1", "source:end", "target:start", points,
        corner_radius=radius, path_commands=commands,
    )


def test_orthogonal_style_returns_the_same_placement_without_calling_reject():
    placement = _relation(((0, 0), (0, 10), (10, 10)),
                          commands=(PathCommand("move", ((0, 0),)),
                                    PathCommand("line", ((0, 10),)),
                                    PathCommand("line", ((10, 10),))) )

    completed, cover = complete_relation_style(
        placement, style="orthogonal", stroke_width=2,
        start_run=0, end_run=0, recovery=False,
        reject=lambda *_: (_ for _ in ()).throw(AssertionError("unexpected callback")),
    )

    assert completed is placement
    assert cover == ()


def test_straight_curved_style_stays_straight_without_fallback():
    placement = _relation(((0, 0), (0, 10), (0, 20)))
    calls = []

    completed, cover = complete_relation_style(
        placement, style="curved", stroke_width=2,
        start_run=3, end_run=4, recovery=False,
        reject=lambda candidate, segments: calls.append((candidate, segments)) or None,
    )

    assert completed.style_fallback is None
    assert tuple(command.kind for command in completed.path_commands) == ("move", "line")
    assert completed.path_commands[-1].points == ((0.0, 20.0),)
    assert len(cover) == 1
    assert cover[0].start == (0.0, 0.0) and cover[0].end == (0.0, 20.0)
    assert len(calls) == 1


def test_curved_style_accepts_an_s_path_and_returns_a_conservative_arc_cover():
    placement = _relation(((0, 0), (0, 10), (10, 10), (10, 0)))
    seen = []

    completed, cover = complete_relation_style(
        placement, style="curved", stroke_width=2,
        start_run=0, end_run=0, recovery=False,
        reject=lambda candidate, segments: seen.append((candidate, segments)) or None,
    )

    assert tuple(command.kind for command in completed.path_commands) == (
        "move", "line", "quadratic", "quadratic", "line")
    assert completed.corner_radius == 0
    assert completed.style_fallback is None
    assert len(cover) >= 8
    assert len(seen) == 1 and seen[0] == (completed, cover)
    assert all(segment.stroke_width >= 2 for segment in cover)
    assert any(segment.stroke_width > 2 for segment in cover)


def test_reject_callback_reason_falls_back_to_exact_prior_commands_and_radius():
    old_commands = (PathCommand("move", ((0, 0),)),
                    PathCommand("line", ((0, 10),)),
                    PathCommand("line", ((10, 10),)))
    placement = _relation(((0, 0), (0, 10), (10, 10)), commands=old_commands)
    callback_args = []

    completed, cover = complete_relation_style(
        placement, style="curved", stroke_width=2,
        start_run=0, end_run=0, recovery=False,
        reject=lambda candidate, segments: callback_args.append((candidate, segments)) or "clearance",
    )

    assert completed.points == placement.points
    assert completed.path_commands == old_commands
    assert completed.corner_radius == placement.corner_radius
    assert completed.style_fallback.reason == "clearance"
    assert cover == ()
    assert callback_args and callback_args[0][0].path_commands != old_commands


def test_nonorthogonal_recovery_keeps_baseline_and_reports_recovery():
    placement = _relation(((0, 0), (5, 5)),
                          commands=(PathCommand("move", ((0, 0),)),
                                    PathCommand("line", ((5, 5),))) )

    completed, cover = complete_relation_style(
        placement, style="curved", stroke_width=2,
        start_run=0, end_run=0, recovery=True,
        reject=lambda *_: (_ for _ in ()).throw(AssertionError("recovery must not be curved")),
    )

    assert completed.path_commands == placement.path_commands
    assert completed.corner_radius == placement.corner_radius
    assert completed.style_fallback.reason == "recovery"
    assert cover == ()

    orthogonal = _relation(
        ((0, 0), (0, 10), (10, 10)),
        commands=(PathCommand("move", ((0, 0),)),
                  PathCommand("line", ((0, 5),)),
                  PathCommand("quadratic", ((0, 10), (5, 10))),
                  PathCommand("line", ((10, 10),))),
    )
    completed_orthogonal, orthogonal_cover = complete_relation_style(
        orthogonal, style="curved", stroke_width=2,
        start_run=0, end_run=0, recovery=True,
        reject=lambda *_: (_ for _ in ()).throw(AssertionError("recovery must not be curved")),
    )
    assert completed_orthogonal.path_commands == orthogonal.path_commands
    assert completed_orthogonal.style_fallback.reason == "recovery"
    assert orthogonal_cover == ()


def test_terminal_reserves_that_leave_no_curve_report_terminal_fallback():
    placement = _relation(((0, 0), (0, 10), (10, 10), (10, 0)))

    completed, cover = complete_relation_style(
        placement, style="curved", stroke_width=2,
        start_run=10, end_run=10, recovery=False,
        reject=lambda *_: (_ for _ in ()).throw(AssertionError("no candidate curve exists")),
    )

    assert completed.path_commands == placement.path_commands
    assert completed.corner_radius == placement.corner_radius
    assert completed.style_fallback.reason == "terminal"
    assert cover == ()


def test_fallback_receipt_is_typed_stable_and_countable():
    placement = _relation(((0, 0), (0, 10), (10, 10)))
    completed, _ = complete_relation_style(
        placement, style="curved", stroke_width=2,
        start_run=0, end_run=0, recovery=False,
        reject=lambda *_: "bounds",
    )

    receipt = json.loads(completed.style_fallback.diagnostic.split(":", 1)[1])
    assert completed.style_fallback.relation_id == placement.relation_id
    assert completed.style_fallback.reason == "bounds"
    assert receipt == {
        "actual": "orthogonal", "reason": "bounds",
        "relationId": "relation-1", "requested": "curved",
    }


def test_genuine_self_crossing_curved_skeleton_falls_back_but_nearby_joins_do_not():
    crossing = _relation(((0, 0), (10, 0), (10, 10), (0, 10),
                          (0, -5), (5, -5), (5, 5)))
    crossing_result, crossing_cover = complete_relation_style(
        crossing, style="curved", stroke_width=1,
        start_run=0, end_run=0, recovery=False,
        reject=lambda *_: None,
    )
    ordinary_s = _relation(((0, 0), (0, 10), (10, 10), (10, 0)))
    s_result, s_cover = complete_relation_style(
        ordinary_s, style="curved", stroke_width=1,
        start_run=0, end_run=0, recovery=False,
        reject=lambda *_: None,
    )

    assert crossing_result.style_fallback.reason == "self-overlap"
    assert crossing_result.path_commands == crossing.path_commands
    assert crossing_cover == ()
    assert s_result.style_fallback is None
    assert s_cover


def test_curved_path_segments_contains_only_the_changed_arcs():
    commands = (PathCommand("move", ((0, 0),)),
                PathCommand("line", ((0, 5),)),
                PathCommand("quadratic", ((0, 10), (5, 10))),
                PathCommand("line", ((10, 10),)))

    segments = curved_path_segments(commands, 3)

    assert len(segments) > 1
    assert all(segment.stroke_width > 3 for segment in segments)
    assert min(segment.start[0] for segment in segments) >= 0
    assert max(segment.end[0] for segment in segments) <= 5
