import pytest

from chrona.presentation.layout.labels import LabelObstacle, LabelRect, place_label
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


def test_label_candidates_are_bounded_and_unique():
    with pytest.raises(ValueError, match="E_PRESENTATION_LABEL_INPUT"):
        place_label(LabelRect(1, 1, 1, 1), (1, 1), ["above"] * 17, bounds=LabelRect(0, 0, 10, 10))


def test_wrap_uses_measured_words_and_never_splits_a_token():
    assert wrap_text("alpha beta gamma", available_inline=10, font_size=1, font_metrics=_Metrics()) == ("alpha beta", "gamma")


def test_wrap_breaks_cjk_at_declared_character_boundaries_without_orphaning_closers():
    assert wrap_text("日本語、計画", available_inline=2, font_size=1, font_metrics=_Metrics()) == ("日本", "語、", "計画")
