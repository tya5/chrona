from chrona.presentation.layout.labels import (
    LabelRect,
    LabelObstacle,
    start_member_name_search,
)
from chrona.presentation.layout.obstacles import (
    ObstacleRect,
    SurfaceObstacle,
    SurfaceObstacleIndex,
)


def _index(*items: SurfaceObstacle) -> SurfaceObstacleIndex:
    result = SurfaceObstacleIndex()
    result.extend(items)
    return result


def test_cursor_retains_blocked_candidate_and_resumes_suffix_against_new_probe():
    bounds = LabelRect(0, 0, 100, 100)
    end_blocker = SurfaceObstacle("prior-name", "text", "plot",
                                  ObstacleRect(20, 40, 40, 50))
    cursor = start_member_name_search(
        LabelRect(10, 40, 10, 10), (20, 10), ("end", "start"), bounds=bounds,
        obstacles=_index(end_blocker), gap=0, maximum_end_gap=100)

    blocked = cursor.next_candidate()
    assert blocked is not None
    assert blocked.placement.side == "end"
    assert blocked.occupied
    assert blocked.blocker_placement_ids == ("prior-name",)

    # The domain remains the original request's domain, while collision status
    # is checked against the updated probe inventory on the unconsumed suffix.
    resumed = cursor.next_candidate(_index())
    assert resumed is not None
    assert resumed.placement.side == "end"
    assert resumed.placement.bounds != blocked.placement.bounds
    assert not resumed.occupied
    assert [item.placement.bounds for item in cursor.evaluated_candidates] == [
        blocked.placement.bounds, resumed.placement.bounds]


def test_cursor_reports_anonymous_iterable_occupancy_without_fabricated_ids():
    bounds = LabelRect(0, 0, 100, 100)
    cursor = start_member_name_search(
        LabelRect(10, 40, 10, 10), (20, 10), ("end",), bounds=bounds,
        obstacles=(LabelRect(20, 40, 30, 50),), gap=0, maximum_end_gap=100)

    candidate = cursor.next_candidate()
    assert candidate is not None
    assert candidate.occupied
    assert candidate.blocker_placement_ids == ()


def test_fallback_is_a_separate_post_normal_rung():
    bounds = LabelRect(20, 40, 20, 10)
    blocker = LabelRect(20, 40, 40, 50)
    cursor = start_member_name_search(
        LabelRect(10, 40, 10, 10), (20, 10), ("end",), bounds=bounds,
        obstacles=(blocker,), gap=0, maximum_end_gap=100, overflow="visible-overflow")

    assert cursor.next_fallback() is None  # normal candidates have not been exhausted
    assert cursor.next_clear() is None
    fallback = cursor.next_fallback()
    assert fallback is not None
    assert fallback.is_fallback
    assert fallback.occupied
    assert cursor.next_fallback() is None


def test_full_band_cursor_preserves_event_count_and_nearest_y_order():
    bounds = LabelRect(0, 0, 100, 100)
    obstacle = SurfaceObstacle("obstacle", "mark", "plot",
                               ObstacleRect(20, 60, 40, 70))
    cursor = start_member_name_search(
        LabelRect(10, 40, 10, 10), (20, 10), ("end",), bounds=bounds,
        obstacles=_index(obstacle), gap=0, maximum_end_gap=100, full_band=True)

    first = cursor.next_candidate()
    assert first is not None
    # preferred y=40 is the closest event and carries the historical count of
    # the complete event set, even though other events may be filtered/blocked.
    assert first.placement.bounds.y == 40
    assert first.placement.search_count == len({40, 0, 90, 50, 70})


def test_start_neighborhood_does_not_inherit_end_reach_limit():
    blocker = LabelRect(30, 0, 10, 100)
    cursor = start_member_name_search(
        LabelRect(50, 40, 10, 10), (20, 10), ("start",),
        bounds=LabelRect(0, 0, 100, 100), obstacles=(blocker,),
        gap=0, maximum_end_gap=0)

    candidate = cursor.next_clear()
    assert candidate is not None
    assert candidate.placement.side == "start"
    assert candidate.placement.bounds.x == 10
    assert candidate.placement.search_count == 11

