"""Atomic annotation connector topology and visible bridge geometry."""
from __future__ import annotations

from itertools import islice

import pytest

from chrona.presentation.layout.annotation_topology import (
    _sparse_elbows, local_route_bounds, route_annotation_candidate,
    strict_route_candidates, visible_segments,
)
from chrona.presentation.layout.annotation_search import _route_crosses_rule_once
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.ports import ConnectorEgress
from chrona.presentation.layout.annotation_topology import rail_leader_crossings


def test_opposite_side_axial_interleave_reaches_y_first_before_four_bend_routes() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("axis-source", "mark", "plot", ObstacleRect(40, 20, 50, 30)))
    common = dict(index=index, bounds=(0, 0, 120, 70), max_bends=4,
                  max_detour_ratio=10.0, candidate_limit=64)
    start, end = (10.0, 10.0), (100.0, 50.0)
    legacy = tuple(strict_route_candidates(start, end, **common))
    interleaved = tuple(strict_route_candidates(start, end, interleave_axial=True, **common))

    # The legacy sequence stays X-family, then Y-family, then XY-family.
    assert legacy[:2] == (
        ((10.0, 10.0), (100.0, 10.0), (100.0, 50.0)),
        ((10.0, 10.0), (10.0, 50.0), (100.0, 50.0)),
    )
    y_axis_route = ((10.0, 10.0), (10.0, 18.0), (100.0, 18.0), (100.0, 50.0))
    assert y_axis_route in interleaved[:6]
    assert y_axis_route not in legacy[:4]


def test_strict_route_candidates_are_lazy_before_xy_family(monkeypatch) -> None:
    import chrona.presentation.layout.annotation_topology as topology

    index = SurfaceObstacleIndex()
    for number in range(8):
        index.add(SurfaceObstacle(f"axis-{number}", "mark", "plot",
                                  ObstacleRect(20 + number * 5, 15 + number * 4,
                                               21 + number * 5, 16 + number * 4)))
    calls = 0
    original = topology._compact_path

    def count_compaction(points):
        nonlocal calls
        calls += 1
        return original(points)

    monkeypatch.setattr(topology, "_compact_path", count_compaction)
    routes = strict_route_candidates((10.0, 10.0), (100.0, 50.0), index,
                                     bounds=(0, 0, 120, 80), max_bends=4,
                                     max_detour_ratio=10.0, candidate_limit=1024,
                                     interleave_axial=True)
    next(routes)
    assert calls <= 2


def test_interleaved_axial_prefix_finds_vertical_first_fit_under_same_cap() -> None:
    index = SurfaceObstacleIndex()
    rule = ObstacleSegment((1000.0, -10.0), (1000.0, 120.0))
    index.add(SurfaceObstacle("as-of", "rule", "plot", rule))
    # X-first horizontal runs meet the near-rule blocker or their vertical
    # corridor meets the long barrier. A low Y-first corridor at y=3 is clear.
    index.add(SurfaceObstacle("barrier", "mark", "plot",
                              ObstacleRect(-2.0, 49.0, 1990.0, 51.0)))
    index.add(SurfaceObstacle("near-rule", "text", "plot",
                              ObstacleRect(999.0, -1.0, 1001.0, 1.0)))
    for number in range(520):
        x = 10.0 + number * 3.0
        index.add(SurfaceObstacle(f"x-corridor-{number}", "mark", "plot",
                                  ObstacleRect(x, 200.0, x + 1.0, 201.0)))
    expected = ((0.0, 0.0), (0.0, 3.0), (2000.0, 3.0), (2000.0, 100.0))
    common = dict(bounds=(0.0, -10.0, 2000.0, 300.0), max_bends=4,
                  max_detour_ratio=2.0, candidate_limit=1024)
    legacy_prefix = tuple(islice(strict_route_candidates(
        (0.0, 0.0), (2000.0, 100.0), index, **common), 1025))
    axial_prefix = tuple(islice(strict_route_candidates(
        (0.0, 0.0), (2000.0, 100.0), index, interleave_axial=True, **common), 1025))

    assert len(legacy_prefix) == len(axial_prefix) == 1025
    assert expected not in legacy_prefix
    assert expected in axial_prefix
    assert _route_crosses_rule_once(expected, rule)
    assert not any(index.collisions(ObstacleSegment(a, b), rule_host_id="as-of")
                   for a, b in zip(expected, expected[1:]))
    assert all(any(index.collisions(ObstacleSegment(a, b), rule_host_id="as-of")
                   for a, b in zip(path, path[1:]))
               for path in legacy_prefix[:1024])


def test_strict_connector_uses_one_shared_index() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("dep", "dependency-route", "timeline",
                              ObstacleSegment((20, 20), (80, 20))))
    trial = route_annotation_candidate((10, 10), (90, 10), index,
                                       bounds=(0, 0, 100, 40), max_bends=2,
                                       max_detour_ratio=2)
    assert trial is not None and trial.topology == "strict"
    assert trial.points == ((10, 10), (90, 10))
    assert trial.crossing_ids == ()


def test_bridge_gaps_only_later_connector_at_transverse_crossing() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("dep", "dependency-route", "timeline",
                              ObstacleSegment((50, 0), (50, 40))))
    trial = route_annotation_candidate((10, 20), (90, 20), index,
                                       bounds=(0, 0, 100, 40), max_bends=2,
                                       max_detour_ratio=2, allow_bridge=True)
    assert trial is not None and trial.topology == "bridge"
    assert trial.crossing_ids == ("dep",)
    assert [command.kind for command in trial.commands] == ["move", "line", "move", "line"]
    assert index.collisions(ObstacleSegment(*visible_segments(trial)[0]), classes=("dependency-route",)) == ()
    assert index.collisions(ObstacleSegment(*visible_segments(trial)[1]), classes=("dependency-route",)) == ()
    assert index.has("dep")


def test_bridge_never_exempts_text_or_rule() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("dep", "dependency-route", "timeline",
                              ObstacleSegment((50, 0), (50, 40))))
    index.add(SurfaceObstacle("text", "text", "timeline", ObstacleRect(45, 15, 55, 25)))
    index.add(SurfaceObstacle("rule", "rule", "timeline", ObstacleSegment((0, 30), (100, 30))))
    trial = route_annotation_candidate((10, 20), (90, 20), index,
                                       bounds=(0, 0, 100, 40), max_bends=2,
                                       max_detour_ratio=1.5, allow_bridge=True)
    assert trial is None or not any(index.collisions(ObstacleSegment(a, b), classes=("text", "rule"))
                                    for a, b in visible_segments(trial))


@pytest.mark.parametrize("obstacle_class", ["leader-route", "rule"])
def test_next_leader_cannot_cross_completed_leader_or_bar(obstacle_class: str) -> None:
    index = SurfaceObstacleIndex()
    segment = ((5, 0), (5, 10)) if obstacle_class == "leader-route" else ((0, 5), (10, 5))
    index.add(SurfaceObstacle("already-completed", obstacle_class, "annotations",
                              ObstacleSegment(*segment)))

    trial = route_annotation_candidate(
        (0, 5), (10, 5), index, bounds=(0, 0, 10, 10), max_bends=0,
        max_detour_ratio=1, dense=False)

    assert trial is None


def test_local_corridor_excludes_slide_perimeter() -> None:
    assert local_route_bounds((1200, 300, 20, 20), (24, 1130, 312, 20),
                              (336, 1140), (0, 0, 1600, 1200)) == (180.0, 144.0, 1376.0, 1200)


def test_sparse_priority_uses_the_completed_stroke_envelope() -> None:
    for horizontal in (False, True):
        for mirrored in (False, True):
            start, end = ((90, 90), (10, 10)) if mirrored else ((10, 10), (90, 90))
            index = SurfaceObstacleIndex()
            endpoints = ((20, 50), (80, 50)) if horizontal else ((50, 20), (50, 80))
            index.add(SurfaceObstacle("accepted", "leader-route", "annotations",
                                      ObstacleSegment(*endpoints, stroke_width=4)))
            paths = _sparse_elbows(start, end, index, bounds=(0, 0, 100, 100))
            axis = (54 if mirrored else 46) if horizontal else (46 if mirrored else 54)
            expected = ((start, (start[0], axis), (end[0], axis), end) if horizontal
                        else (start, (axis, start[1]), (axis, end[1]), end))
            assert paths[0] == expected
            assert not any(index.collisions(ObstacleSegment(a, b))
                           for a, b in zip(expected, expected[1:]))
def test_collinear_retrace_and_duplicates_never_create_zero_length_legs():
    from chrona.presentation.layout.annotation_topology import _compact_path, _sparse_elbows
    assert _compact_path(((0, 0), (5, 0), (0, 0), (0, 3))) == ((0, 0), (0, 3))
    assert _compact_path(((0, 0), (0, 0), (0, 3))) == ((0, 0), (0, 3))
    for start, end in (((0, 0), (0, 3)), ((0, 0), (3, 0)), ((0, 0), (3, 3))):
        candidates = _sparse_elbows(start, end, SurfaceObstacleIndex(), bounds=(-5, -5, 5, 5))
        assert candidates
        assert all(path[0] == start and path[-1] == end
                   and all(a != b for a, b in zip(path, path[1:])) for path in candidates)


def test_rail_leader_crossings_reports_all_obstacle_classes_and_stroke_envelope() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("a-mark", "mark", "plot", ObstacleRect(4, 11, 6, 12)))
    index.add(SurfaceObstacle("known-port", "port", "plot", ObstacleRect(2, 9, 3, 11)))
    index.add(SurfaceObstacle("unexpected-port", "port", "plot", ObstacleRect(3, 9, 4, 11)))
    index.add(SurfaceObstacle("b-rule", "rule", "plot",
                              ObstacleSegment((8, 0), (8, 20), stroke_width=1)))
    index.add(SurfaceObstacle("c-text", "text", "annotations", ObstacleRect(12, 9, 13, 11)))
    index.add(SurfaceObstacle("d-leader", "leader-route", "annotations",
                              ObstacleSegment((16, 0), (16, 20), stroke_width=1)))
    # The mark's lower edge is 1.5px from the centerline; the leader stroke
    # radius is 2px, so its painted envelope crosses it.
    found = rail_leader_crossings(((0, 10), (20, 10)), index, stroke_width=4,
                                  source=ConnectorEgress("end", (0, 10), (0, 10), ()),
                                  target_id="note", port_ids=("known-port",))
    assert tuple(item.placement_id for item in found) == (
        "a-mark", "b-rule", "c-text", "d-leader", "unexpected-port")


def test_rail_leader_crossings_exempts_expected_source_and_terminal_target_legs() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("source-host", "mark", "plot", ObstacleRect(0, 0, 10, 10)))
    index.add(SurfaceObstacle("annotation-box:target-box", "annotation-box", "annotations",
                              ObstacleRect(20, 0, 30, 10)))
    source = ConnectorEgress("end", (10, 5), (10, 5), ("source-host",))
    assert rail_leader_crossings(((10, 5), (20, 5)), index, stroke_width=1,
                                 source=source, target_id="target-box") == ()

    # Returning through the source host on a later leg is not covered by the
    # first-leg egress exemption.
    reentry = rail_leader_crossings(((10, 5), (15, 5), (5, 5), (20, 5)), index,
                                    stroke_width=1, source=source, target_id="target-box")
    assert tuple(item.placement_id for item in reentry) == ("source-host",)

    # A tilted frame's exact final extension may end inside its indexed AABB.
    # Only the supplied target-to-tip segment is exempt; the preceding routed
    # leg still must terminate at the AABB boundary without traversing it.
    tilted_contact = rail_leader_crossings(
        ((10, 5), (20, 5), (22, 5)), index, stroke_width=1,
        source=source, target_id="target-box", target_extension=((20, 5), (22, 5)))
    assert tilted_contact == ()

    # Ending at the far edge after traversing the target interior is not a
    # terminal port contact, even though it is the last and only leg.
    through_target = rail_leader_crossings(((10, 5), (30, 5)), index, stroke_width=0,
                                           source=source, target_id="target-box")
    assert tuple(item.placement_id for item in through_target) == ("annotation-box:target-box",)

    # Target-box contact on a nonterminal leg remains reportable.
    earlier_target = rail_leader_crossings(((10, 5), (30, 5), (30, 15)), index,
                                           stroke_width=0, source=source,
                                           target_id="target-box")
    assert tuple(item.placement_id for item in earlier_target) == ("annotation-box:target-box",)


def test_rail_leader_crossings_allows_diagonal_outward_source_boundary_contact_only() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("source", "mark", "plot", ObstacleRect(0, 0, 10, 10)))
    source = ConnectorEgress("end", (10, 5), (10, 5), ("source",))
    diagonal_outward = rail_leader_crossings(((10, 5), (12, 3)), index, stroke_width=1,
                                             source=source, target_id="note")
    assert diagonal_outward == ()

    # Departing from an interior point is not authorized just because the
    # segment has a positive component along the declared side.
    interior_source = ConnectorEgress("end", (5, 5), (5, 5), ("source",))
    interior = rail_leader_crossings(((5, 5), (12, 3)), index, stroke_width=0,
                                     source=interior_source, target_id="note")
    assert tuple(item.placement_id for item in interior) == ("source",)


def test_rail_leader_crossings_exact_corridor_exemption_is_first_leg_only() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("anchor", "mark", "plot", ObstacleRect(0, 0, 10, 10)))
    index.add(SurfaceObstacle("comparison", "mark", "plot", ObstacleRect(10, 0, 12, 10)))
    source = ConnectorEgress("end", (10, 5), (12, 5), ("anchor",),
                             corridor_host_ids=("comparison",))
    corridor_points = ((10, 5), (12, 5), (20, 5))
    assert rail_leader_crossings(corridor_points, index, stroke_width=0,
                                 source=source, target_id="note") == ()

    # If the completed polyline re-enters a corridor host after the exact
    # initial corridor, that later contact is reportable.
    reentry = rail_leader_crossings(((10, 5), (12, 5), (15, 5), (11, 5), (20, 5)),
                                    index, stroke_width=0, source=source,
                                    target_id="note")
    assert tuple(item.placement_id for item in reentry) == ("comparison",)


def test_rail_leader_crossings_reads_late_additions_and_deduplicates_stably() -> None:
    index = SurfaceObstacleIndex()
    path = ((0, 10), (20, 10), (0, 10))
    # Warm the index's prepared collision selection before adding more content.
    index.collisions(ObstacleSegment((0, 0), (1, 0)))
    index.add(SurfaceObstacle("z-route", "dependency-route", "timeline",
                              ObstacleSegment((10, 0), (10, 20))))
    index.add(SurfaceObstacle("a-rule", "rule", "timeline",
                              ObstacleSegment((5, 0), (5, 20))))
    first = rail_leader_crossings(path, index, stroke_width=0,
                                 source=ConnectorEgress("end", (0, 10), (0, 10), ()),
                                 target_id="note")
    second = rail_leader_crossings(path, index, stroke_width=0,
                                  source=ConnectorEgress("end", (0, 10), (0, 10), ()),
                                  target_id="note")
    assert first == second
    assert tuple(item.placement_id for item in first) == ("a-rule", "z-route")
