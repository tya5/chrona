"""Member-name final rung: end after the item's last own drawn mark (#679, I679-1)."""
import pytest

from chrona.presentation.layout.labels import LabelRect, MemberNameAssociation, place_member_name

HOST = LabelRect(0, 0, 10, 10)
ACTUAL = LabelRect(20, 2, 40, 6)          # the item's own actual mark, past the host
BOUNDS = LabelRect(0, -1, 400, 12)         # a tight row band: no room to dodge above or below
SIZE = (40.0, 10.0)


def _association(reach=20.0, also=(ACTUAL,)):
    return MemberNameAssociation(HOST, 0.0, 0.0, SIZE[0], SIZE[1], reach, also)


def _place(*, own=True, maximum_end_gap=20.0, obstacles=(ACTUAL,), sides=("end",), **kwargs):
    host_only = _association(maximum_end_gap, ())
    return place_member_name(
        HOST, SIZE, sides, bounds=BOUNDS, obstacles=obstacles, gap=4.0, maximum_end_gap=maximum_end_gap,
        association=host_only,
        own_mark_right=ACTUAL.right if own else None,
        final_association=_association(maximum_end_gap) if own else None, **kwargs)


def test_the_final_rung_places_a_name_the_ladder_cannot():
    assert _place(own=False) is None
    placed = _place()
    assert placed is not None and placed.side == "end" and placed.final_rung
    assert placed.bounds.x == pytest.approx(ACTUAL.right + 4.0)
    assert not (placed.bounds.x < ACTUAL.right and ACTUAL.x < placed.bounds.right)


def test_a_name_with_a_legal_ladder_candidate_is_unchanged():
    # `end` is illegal (the actual is in the way) but `start` is legal: the name stays on the ladder.
    wide = LabelRect(-100, -1, 500, 12)
    kwargs = dict(bounds=wide, obstacles=(ACTUAL,), gap=4.0, maximum_end_gap=20.0, association=_association(20.0, ()))
    with_rung = place_member_name(HOST, SIZE, ("end", "start"), own_mark_right=ACTUAL.right,
                                  final_association=_association(), **kwargs)
    without = place_member_name(HOST, SIZE, ("end", "start"), **kwargs)
    assert with_rung == without and with_rung.side == "start" and not with_rung.final_rung


def test_a_legal_end_candidate_is_unchanged():
    free = place_member_name(HOST, SIZE, ("end",), bounds=BOUNDS, obstacles=(), gap=4.0, maximum_end_gap=20.0,
                             association=_association(20.0, ()), own_mark_right=5.0,
                             final_association=_association())
    assert free == place_member_name(HOST, SIZE, ("end",), bounds=BOUNDS, obstacles=(), gap=4.0,
                                     maximum_end_gap=20.0, association=_association(20.0, ()))
    assert not free.final_rung


def test_the_reach_still_bounds_detached_text_from_the_last_own_mark():
    wide = LabelRect(20, 0, 80, 10)   # the first free position is 40 past the mark: detached
    assert _place(obstacles=(wide,)) is None
    assert _place(obstacles=(wide,), maximum_end_gap=48.0) is not None


def test_the_final_rung_needs_end_on_the_declared_ladder():
    assert _place(sides=("start",)) is None


def test_the_final_rung_is_tried_before_the_visible_overflow_fallback():
    placed = _place(overflow="visible-overflow")
    assert placed is not None and placed.final_rung and not placed.visible_overflow
    assert placed.bounds.x >= ACTUAL.right


def test_visible_overflow_fallback_is_unchanged_without_a_later_own_mark():
    wide = LabelRect(20, 0, 80, 10)
    kwargs = dict(bounds=BOUNDS, obstacles=(wide,), gap=4.0, maximum_end_gap=20.0,
                  association=_association(20.0, ()), overflow="visible-overflow")
    assert (place_member_name(HOST, SIZE, ("end",), own_mark_right=5.0, final_association=_association(), **kwargs)
            == place_member_name(HOST, SIZE, ("end",), **kwargs))


def test_the_visible_overflow_fallback_is_measured_from_the_last_own_mark():
    # Nothing is legal (a wide obstacle covers the row): the overflowing name still starts after the
    # item's own actual mark instead of on it.
    wide = LabelRect(20, 0, 200, 10)
    placed = place_member_name(HOST, SIZE, ("end",), bounds=BOUNDS, obstacles=(wide,), gap=4.0,
                               maximum_end_gap=20.0, association=_association(20.0, ()),
                               overflow="visible-overflow", own_mark_right=ACTUAL.right,
                               final_association=_association())
    assert placed.visible_overflow and placed.final_rung and placed.bounds.x == pytest.approx(ACTUAL.right + 4.0)


def test_full_band_final_rung():
    placed = _place(full_band=True)
    assert placed is not None and placed.final_rung and placed.bounds.x == pytest.approx(ACTUAL.right + 4.0)


def test_association_accepts_text_near_any_own_mark_and_names_the_nearest():
    association = _association(6.0)
    near_actual, near_host = LabelRect(64, 0, 40, 10), LabelRect(-44, 0, 40, 10)
    assert association.allows(near_actual) and association.allows(near_host)
    assert not association.allows(LabelRect(200, 0, 40, 10))
    assert association.nearest_mark_index(near_actual) == 1
    assert association.nearest_mark_index(near_host) == 0
    assert not _association(6.0, ()).allows(near_actual)


def test_a_tie_keeps_the_requested_host():
    association = MemberNameAssociation(HOST, 0.0, 0.0, 10.0, 10.0, 50.0, (LabelRect(30, 0, 10, 10),))
    assert association.nearest_mark_index(LabelRect(15, 0, 10, 10)) == 0


def test_a_non_finite_own_mark_right_is_rejected():
    with pytest.raises(ValueError, match="E_PRESENTATION_LABEL_INPUT"):
        place_member_name(HOST, SIZE, ("end",), bounds=BOUNDS, gap=4.0, maximum_end_gap=20.0,
                          own_mark_right=float("nan"))
