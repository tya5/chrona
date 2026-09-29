import pytest

from chrona.presentation.layout.labels import (
    LabelObstacle, LabelPlacement, LabelRect, MemberNameAssociation, nearest_rect_perimeters, place_label, place_member_name,
)
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_member_labels import _member_association_outcome
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.text import wrap_text


class _Metrics:
    def width(self, value, size):
        return len(value) * size


def test_nearest_member_label_perimeter_points_are_stable_on_both_inline_sides():
    mark = LabelRect(50, 40, 10, 10)
    start = LabelRect(20, 42, 20, 6)
    end = LabelRect(70, 42, 20, 6)
    assert nearest_rect_perimeters(start, mark) == (10, (40, 45), (50, 45))
    assert nearest_rect_perimeters(end, mark) == (10, (70, 45), (60, 45))


def test_labels_use_declared_finite_candidate_order_and_obstacles():
    result = place_label(LabelRect(40, 40, 20, 10), (30, 8), ["above", "end"],
                         bounds=LabelRect(0, 0, 120, 100),
                         obstacles=[LabelRect(30, 30, 40, 10)], gap=2)
    assert result.side == "end"
    assert result.bounds == LabelRect(62, 41, 30, 8)


def test_inside_retains_measured_text_when_visible_overflow_is_selected():
    result = place_label(LabelRect(10, 10, 10, 8), (12, 6), ["inside"], bounds=LabelRect(0, 0, 100, 100))
    assert result.bounds == LabelRect(9, 11, 12, 6)
    assert result.visible_overflow


def test_inside_exempts_only_its_identified_host_mark_obstacle():
    anchor = LabelRect(10, 10, 20, 10)
    host = LabelObstacle("planned:a", anchor)
    assert place_label(anchor, (10, 8), ["inside"], bounds=LabelRect(0, 0, 100, 100),
                       obstacles=[host], inside_host_obstacle_id="planned:a").side == "inside"
    result = place_label(anchor, (10, 8), ["inside"], bounds=LabelRect(0, 0, 100, 100),
                         obstacles=[host, LabelObstacle("planned:b", anchor)],
                         inside_host_obstacle_id="planned:a")
    assert result.visible_overflow


def test_optional_label_can_be_omitted_only_by_explicit_policy():
    anchor = LabelRect(10, 10, 10, 10)
    assert place_label(anchor, (40, 10), ["above"], bounds=LabelRect(0, 0, 30, 30),
                       required=False, overflow="clip-optional") is None
    result = place_label(anchor, (40, 10), ["above"], bounds=LabelRect(0, 0, 30, 30), required=False)
    assert result.visible_overflow


def test_declared_visible_fallback_side_is_used_only_after_legal_candidates_fail():
    anchor = LabelRect(50, 40, 0, 10)
    bounds = LabelRect(0, 0, 100, 100)
    obstacles = [LabelRect(0, 0, 100, 100)]
    fallback = place_label(anchor, (20, 8), ("end",), bounds=bounds,
                           obstacles=obstacles, visible_fallback_side="above")
    assert fallback.side == "above" and fallback.visible_overflow
    first = place_label(anchor, (20, 8), ("end",), bounds=bounds, obstacles=obstacles)
    assert first.side == "end" and first.visible_overflow
    legal = place_label(anchor, (20, 8), ("end",), bounds=bounds,
                        visible_fallback_side="above")
    assert legal.side == "end" and not legal.visible_overflow
    with pytest.raises(ValueError, match="E_PRESENTATION_LABEL_INPUT"):
        place_label(anchor, (20, 8), ("end",), bounds=bounds, visible_fallback_side="diagonal")
    with pytest.raises(ValueError, match="E_PRESENTATION_LABEL_INPUT"):
        place_label(anchor, (20, 8), ("end",), bounds=bounds, overflow="suppress",
                    visible_fallback_side="above")


def test_member_name_end_candidate_is_capped_and_uses_start_before_suppression():
    anchor = LabelRect(40, 45, 10, 10)
    bounds = LabelRect(0, 0, 100, 100)
    end = place_member_name(anchor, (20, 8), ("end", "start"), bounds=bounds,
                            obstacles=(), gap=2, maximum_end_gap=20,
                            text_inline_inset=5)
    assert end is not None and end.side == "end"
    assert end.bounds.x + 5 - anchor.right <= 20

    # Every end placement at an inline gap of at most 2em is blocked, but the
    # declared start rung remains clear.
    result = place_member_name(
        anchor, (20, 8), ("end", "start"), bounds=bounds,
        obstacles=(LabelRect(50, 0, 41, 100),), gap=2, maximum_end_gap=20,
    )
    assert result is not None and result.side == "start"
    assert result.bounds.right <= anchor.x - 2


def test_member_name_returns_suppression_when_bounded_end_and_start_are_blocked():
    anchor = LabelRect(40, 45, 10, 10)
    result = place_member_name(
        anchor, (20, 8), ("end", "start"), bounds=LabelRect(0, 0, 100, 100),
        obstacles=(LabelRect(0, 0, 100, 100),), gap=2, maximum_end_gap=20,
    )
    assert result is None


@pytest.mark.parametrize("side", ("start", "end"))
def test_member_name_checks_completed_text_against_its_exact_mark_on_both_sides(side):
    mark = LabelRect(50, 40, 10, 10)
    association = MemberNameAssociation(mark, 2, 1, 20, 8, 4)
    result = place_member_name(
        mark, (24, 10), (side,), bounds=LabelRect(0, 0, 120, 100),
        gap=2, maximum_end_gap=30, association=association)
    assert result is not None and result.side == side
    assert association.allows(result.bounds)
    farther = MemberNameAssociation(mark, 2, 1, 20, 8, 1)
    assert place_member_name(
        mark, (24, 10), (side,), bounds=LabelRect(0, 0, 120, 100),
        gap=2, maximum_end_gap=30, association=farther) is None


def test_member_name_full_band_never_uses_a_second_stagger_step():
    mark = LabelRect(50, 40, 10, 10)
    association = MemberNameAssociation(mark, 0, 0, 20, 8, 20)
    obstacle = LabelRect(62, 20, 20, 35)
    result = place_member_name(
        mark, (20, 8), ("end", "start"), bounds=LabelRect(0, 0, 120, 100),
        obstacles=(obstacle,), gap=2, maximum_end_gap=30, full_band=True,
        association=association, maximum_stagger=10)
    assert result is not None and result.side == "start"
    assert association.allows(result.bounds)


def test_member_association_exhaustion_suppresses_optional_and_fails_required():
    association = MemberNameAssociation(LabelRect(50, 40, 10, 10), 0, 0, 20, 8, 20)
    far = LabelPlacement("end", LabelRect(80, 80, 20, 8))
    assert _member_association_outcome(far, association, overflow="suppress",
                                       placement_id="member-label:a") is None
    assert _member_association_outcome(None, association, overflow="suppress",
                                       placement_id="member-label:a") is None
    with pytest.raises(LayoutError, match="E_LAYOUT_LABEL_ASSOCIATION_UNPLACEABLE"):
        _member_association_outcome(far, association, overflow="visible-overflow",
                                    placement_id="member-label:a")
    with pytest.raises(LayoutError, match="E_LAYOUT_LABEL_ASSOCIATION_UNPLACEABLE"):
        _member_association_outcome(None, association, overflow="diagnose",
                                    placement_id="member-label:a")


def test_declared_visible_overflow_keeps_colliding_near_name_but_not_detached_name():
    mark = LabelRect(50, 40, 10, 10)
    association = MemberNameAssociation(mark, 0, 0, 20, 8, 20)
    blocked = (LabelRect(0, 0, 120, 100),)
    near = place_member_name(mark, (20, 8), ("end", "start"),
                             bounds=LabelRect(0, 0, 120, 100), obstacles=blocked,
                             gap=2, maximum_end_gap=30, association=association,
                             overflow="visible-overflow")
    assert near is not None and near.side == "end" and near.visible_overflow
    assert association.allows(near.bounds)
    detached = MemberNameAssociation(mark, 0, 0, 20, 8, 1)
    assert place_member_name(mark, (20, 8), ("end", "start"),
                             bounds=LabelRect(0, 0, 120, 100), obstacles=blocked,
                             gap=2, maximum_end_gap=30, association=detached,
                             overflow="visible-overflow") is None


def test_member_name_full_band_search_matches_axis_aligned_interval_oracle():
    # The oracle merges the forbidden y intervals for a fixed end-side x,
    # then chooses the legal point nearest the preferred y (lower y breaks ties).
    anchor = LabelRect(20, 42, 10, 8)
    bounds = LabelRect(0, 0, 100, 100)
    obstacles = (LabelRect(32, 30, 20, 18), LabelRect(32, 55, 20, 12),
                 LabelRect(0, 10, 25, 20))
    size = (18, 6)
    gap = 2
    preferred_y = anchor.y + (anchor.height - size[1]) / 2
    forbidden = sorted((item.y - size[1], item.bottom) for item in obstacles
                       if 32 < item.right and item.x < 32 + size[0])
    merged = []
    for low, high in forbidden:
        if merged and low < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], high))
        else:
            merged.append((low, high))
    legal_events = [bounds.y, bounds.bottom - size[1], preferred_y]
    for low, high in merged:
        legal_events.extend((low, high))
    oracle = min((y for y in legal_events
                  if bounds.y <= y <= bounds.bottom - size[1]
                  and not any(low < y < high for low, high in merged)),
                 key=lambda y: (abs(y - preferred_y), y))
    result = place_member_name(anchor, size, ("end",), bounds=bounds, obstacles=obstacles,
                               gap=gap, maximum_end_gap=30, full_band=True)
    assert result is not None and result.bounds.y == oracle
    assert result.bounds.x == anchor.right + gap
    assert result.bounds.y >= bounds.y and result.bounds.bottom <= bounds.bottom


def test_member_name_full_band_search_has_no_512_contact_cutoff():
    index = SurfaceObstacleIndex()
    # These overlapping bands create more than 512 distinct contact events;
    # their union blocks the preferred placement until the final top contact.
    for number in range(600):
        index.add(SurfaceObstacle(f"band:{number:04d}", "mark", "timeline",
                                  ObstacleRect(32, 400 + number, 52, 402 + number)))
    anchor = LabelRect(20, 700, 10, 8)
    result = place_member_name(anchor, (18, 6), ("end",), bounds=LabelRect(0, 0, 100, 1200),
                               obstacles=index, gap=2, maximum_end_gap=30, full_band=True)
    assert result is not None
    assert result.bounds.y == 1001
    assert result.search_count > 512
    assert not index.collisions(ObstacleRect(result.bounds.x, result.bounds.y,
                                             result.bounds.right, result.bounds.bottom))


def test_member_name_full_band_search_respects_inline_row_bounds():
    result = place_member_name(LabelRect(40, 40, 10, 8), (20, 6), ("end",),
                               bounds=LabelRect(0, 0, 60, 100), obstacles=(),
                               gap=2, maximum_end_gap=30, full_band=True)
    assert result is None


def test_member_name_full_band_search_accepts_declared_start_only():
    result = place_member_name(LabelRect(50, 40, 10, 8), (20, 6), ("start",),
                               bounds=LabelRect(0, 0, 100, 100), obstacles=(),
                               gap=2, maximum_end_gap=30, full_band=True)
    assert result is not None and result.side == "start"
    assert result.bounds.right == 48


def test_member_name_contact_events_include_selected_segment_envelopes():
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("route:1", "dependency-route", "timeline",
                              ObstacleSegment((32, 45), (52, 45))))
    result = place_member_name(LabelRect(20, 41, 10, 8), (18, 6), ("end",),
                               bounds=LabelRect(0, 0, 100, 100), obstacles=index,
                               gap=2, maximum_end_gap=30, classes=("dependency-route",), full_band=True)
    assert result is not None and result.bounds.y == 39
    assert not index.collisions(ObstacleRect(result.bounds.x, result.bounds.y,
                                             result.bounds.right, result.bounds.bottom),
                                classes=("dependency-route",))


def test_label_candidates_are_bounded_and_unique():
    with pytest.raises(ValueError, match="E_PRESENTATION_LABEL_INPUT"):
        place_label(LabelRect(1, 1, 1, 1), (1, 1), ["above"] * 17, bounds=LabelRect(0, 0, 10, 10))


def test_optional_side_search_preserves_canonical_first_and_avoids_route_stroke():
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("route:1", "dependency-route", "timeline",
                              ObstacleSegment((30, 45), (90, 45))))
    anchor = LabelRect(50, 50, 10, 10)
    original = place_label(anchor, (20, 8), ("above",), bounds=LabelRect(0, 0, 120, 100),
                           obstacles=index, classes=("dependency-route",), overflow="suppress", required=False)
    assert original is None
    moved = place_label(anchor, (20, 8), ("above",), bounds=LabelRect(0, 0, 120, 100),
                        obstacles=index, classes=("dependency-route",), overflow="suppress", required=False,
                        search_side_neighborhood=True)
    assert moved is not None and moved.side == "above" and moved.search_count > 0
    assert moved.bounds.bottom <= anchor.y
    assert not index.collisions(ObstacleRect(moved.bounds.x, moved.bounds.y,
                                             moved.bounds.right, moved.bounds.bottom))
    canonical = place_label(anchor, (20, 8), ("below",), bounds=LabelRect(0, 0, 120, 100),
                            obstacles=index, classes=("dependency-route",), search_side_neighborhood=True)
    assert canonical is not None and canonical.search_count == 0


def test_optional_side_search_has_a_finite_512_candidate_cap(monkeypatch):
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("blocked", "mark", "timeline", ObstacleRect(0, 0, 3000, 3000)))
    count = 0
    original = index.collisions

    def counted(*args, **kwargs):
        nonlocal count
        count += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(index, "collisions", counted)
    result = place_label(LabelRect(1000, 1000, 10, 10), (600, 80), ("above", "below", "start", "end"),
                         bounds=LabelRect(0, 0, 3000, 3000), obstacles=index, classes=("mark",),
                         overflow="suppress", required=False, search_side_neighborhood=True)
    assert result is None
    assert count == 4 + 512


def test_wrap_uses_measured_words_and_never_splits_a_token():
    assert wrap_text("alpha beta gamma", available_inline=10, font_size=1, font_metrics=_Metrics()) == ("alpha beta", "gamma")


def test_wrap_breaks_cjk_at_declared_character_boundaries_without_orphaning_closers():
    assert wrap_text("日本語、計画", available_inline=2, font_size=1, font_metrics=_Metrics()) == ("日本", "語、", "計画")
