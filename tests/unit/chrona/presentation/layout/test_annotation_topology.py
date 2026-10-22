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
