import pytest

from chrona.presentation.layout.labels import (
    LabelRect,
    LabelObstacle,
    MemberNameAssociation,
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


@pytest.mark.parametrize("sides", [("end",), ("end", "start")])
def test_exhausted_side_domains_cannot_restart_with_a_clear_probe(sides):
    anchor = LabelRect(500, 500, 10, 10)
    association = MemberNameAssociation(anchor, 0, 0, 100, 20, 400)
    wall = SurfaceObstacle("wall", "mark", "timeline", ObstacleRect(0, 0, 1000, 1000))
    cursor = start_member_name_search(anchor, (100, 20), sides,
        bounds=LabelRect(0, 0, 1000, 1000), obstacles=_index(wall), gap=0,
        maximum_end_gap=400, association=association)

    assert cursor.next_clear() is None
    assert cursor.neighborhood_evaluated_count == 512 * len(sides)
    evaluated = cursor.evaluated_count
    assert cursor.next_clear(_index()) is None
    assert cursor.neighborhood_evaluated_count == 512 * len(sides)
    assert cursor.evaluated_count == evaluated
    neighborhood = cursor.evaluated_normal_candidates[-1]
    assert neighborhood.provenance.kind == "neighborhood"
    actual_evaluations = cursor.total_actual_evaluations
    assert cursor.revalidate(neighborhood, _index()) is None
    assert cursor.total_actual_evaluations == actual_evaluations


def test_final_own_mark_neighbor_retains_its_canonical_blocker_evidence():
    anchor = LabelRect(10, 40, 10, 10)
    association = MemberNameAssociation(anchor, 0, 0, 10, 10, 20,
        also_marks=(LabelRect(70, 40, 10, 10),))
    blocker = SurfaceObstacle("blocker", "text", "timeline", ObstacleRect(80, 40, 90, 50))
    cursor = start_member_name_search(anchor, (10, 10), ("end",),
        bounds=LabelRect(80, 0, 100, 100), obstacles=_index(blocker), gap=0,
        maximum_end_gap=20, association=association, final_association=association,
        own_mark_right=80)

    candidate = cursor.next_clear()
    assert candidate is not None and candidate.placement.final_rung
    assert candidate.placement.bounds == LabelRect(80, 30, 10, 10)
    obstruction, = candidate.placement.canonical_obstructions
    assert obstruction.occupied
    assert obstruction.blocker_placement_ids == ("blocker",)
    assert candidate.provenance.kind == "neighborhood"
    assert candidate.provenance.side == "end"
    assert candidate.provenance.domain == "final"
    spend_before = cursor.neighborhood_domain_spend
    assert spend_before.get(("normal", "end"), 0) <= 512
    assert spend_before.get(("final", "end"), 0) > 0
    refreshed = cursor.revalidate(candidate, _index())
    assert refreshed is not None
    spend_after = cursor.neighborhood_domain_spend
    assert spend_after[("final", "end")] == spend_before[("final", "end")] + 1
    assert spend_after.get(("normal", "end"), 0) == spend_before.get(("normal", "end"), 0)


def test_repair_probe_after_a_clear_selection_consumes_only_the_unsearched_suffix():
    anchor = LabelRect(500, 500, 10, 10)
    association = MemberNameAssociation(anchor, 0, 0, 100, 20, 400)
    wall = SurfaceObstacle("wall", "mark", "timeline", ObstacleRect(0, 0, 1000, 1000))
    cursor = start_member_name_search(anchor, (100, 20), ("end",),
        bounds=LabelRect(0, 0, 1000, 1000), obstacles=_index(), gap=0,
        maximum_end_gap=400, association=association)
    accepted = cursor.next_clear()
    assert accepted is not None
    assert accepted.placement.bounds == LabelRect(510, 495, 100, 20)
    assert cursor.neighborhood_evaluated_count == 0

    assert cursor.next_clear(_index(wall)) is None
    assert cursor.neighborhood_evaluated_count == 512
    assert cursor.evaluated_count == 513
    assert cursor.next_clear(_index()) is None
    assert cursor.evaluated_count == 513
    assert cursor.evaluated_candidates[0] is accepted


def test_revalidation_charges_neighborhood_ledger_and_resume_reads_the_shared_spend():
    anchor = LabelRect(50, 50, 10, 10)
    blocker = SurfaceObstacle("blocker", "mark", "timeline", ObstacleRect(60, 50, 80, 60))
    cursor = start_member_name_search(anchor, (20, 10), ("end",),
        bounds=LabelRect(0, 0, 200, 120), obstacles=_index(blocker), gap=0,
        maximum_end_gap=100)

    canonical = cursor.next_candidate()
    neighbor = cursor.next_candidate()
    assert canonical is not None and canonical.provenance.kind == "canonical"
    assert neighbor is not None and neighbor.provenance.kind == "neighborhood"
    assert neighbor.provenance.domain == "normal"
    history_before = cursor.evaluated_candidates
    actual_before = cursor.total_actual_evaluations
    spent_before = cursor.neighborhood_evaluated_count

    refreshed = cursor.revalidate(neighbor, _index())
    assert refreshed is not None and not refreshed.occupied
    assert refreshed.placement == neighbor.placement
    assert cursor.evaluated_candidates == history_before
    assert cursor.total_actual_evaluations == actual_before + 1
    assert cursor.neighborhood_evaluated_count == spent_before + 1

    resumed = cursor.next_candidate()
    assert resumed is not None and resumed.provenance.kind == "neighborhood"
    assert resumed.placement.search_count == cursor.neighborhood_evaluated_count


def test_uncapped_canonical_and_full_band_revalidation_does_not_spend_neighborhood_quota():
    anchor = LabelRect(10, 40, 10, 10)
    cursor = start_member_name_search(anchor, (20, 10), ("end",),
        bounds=LabelRect(0, 0, 100, 100), obstacles=_index(), gap=0,
        maximum_end_gap=100)
    canonical = cursor.next_candidate()
    assert canonical is not None and canonical.provenance.kind == "canonical"
    history_size = cursor.evaluated_count
    actual_count = cursor.total_actual_evaluations
    assert cursor.revalidate(canonical, _index()) is not None
    assert cursor.revalidate(canonical, _index()) is not None
    assert cursor.neighborhood_evaluated_count == 0
    assert cursor.evaluated_count == history_size
    assert cursor.total_actual_evaluations == actual_count + 2

    full_band = start_member_name_search(anchor, (20, 10), ("end",),
        bounds=LabelRect(0, 0, 100, 100), obstacles=_index(), gap=0,
        maximum_end_gap=100, full_band=True)
    event = full_band.next_candidate()
    assert event is not None and event.provenance.kind == "full-band"
    full_band_history = full_band.evaluated_count
    full_band_actual = full_band.total_actual_evaluations
    refreshed_event = full_band.revalidate(event, _index())
    assert refreshed_event is not None
    assert refreshed_event.placement == event.placement
    assert full_band.neighborhood_evaluated_count == 0
    assert full_band.evaluated_count == full_band_history
    assert full_band.total_actual_evaluations == full_band_actual + 1
    assert event.placement.search_count == len({40, 0, 90})


def test_revalidation_refuses_foreign_and_fallback_evidence():
    args = dict(anchor=LabelRect(10, 40, 10, 10), size=(20, 10), candidates=("end",),
                bounds=LabelRect(0, 0, 100, 100), gap=0, maximum_end_gap=100)
    first = start_member_name_search(**args)
    second = start_member_name_search(**args)
    candidate = first.next_candidate()
    assert candidate is not None
    assert second.revalidate(candidate, _index()) is None

    blocked = start_member_name_search(
        anchor=LabelRect(10, 40, 10, 10), size=(20, 10), candidates=("end",),
        bounds=LabelRect(20, 40, 20, 10), obstacles=(LabelRect(20, 40, 40, 50),),
        gap=0, maximum_end_gap=100, overflow="visible-overflow")
    assert blocked.next_clear() is None
    fallback = blocked.next_fallback()
    assert fallback is not None and fallback.is_fallback
    assert blocked.revalidate(fallback, _index()) is None
