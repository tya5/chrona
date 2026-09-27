import pytest

from chrona.presentation.layout.labels import LabelObstacle, LabelRect, place_label
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.text import wrap_text


class _Metrics:
    def width(self, value, size):
        return len(value) * size


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
