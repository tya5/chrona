"""Member-name reach is measured from the item's last own drawn mark (#679, I679-1)."""
import pytest

from chrona.presentation.layout.labels import LabelRect, MemberNameAssociation, place_member_name

HOST = LabelRect(0, 0, 10, 10)
ACTUAL = LabelRect(20, 2, 40, 6)          # the item's own actual mark, past the host
BOUNDS = LabelRect(0, -1, 400, 12)         # a tight row band: no room to dodge above or below
SIZE = (40.0, 10.0)


def _place(*, own_mark_right=None, maximum_end_gap=20.0, obstacles=(ACTUAL,), association=None, **kwargs):
    return place_member_name(HOST, SIZE, ("end",), bounds=BOUNDS, obstacles=obstacles, gap=4.0,
                             maximum_end_gap=maximum_end_gap, association=association,
                             own_mark_right=own_mark_right, **kwargs)


def test_end_gap_is_measured_from_the_last_own_mark_not_the_host():
    # The own actual mark ends at 60. Measured from the host (right edge 10) the first free end
    # position is 50 away, beyond a 20 reach; measured from the mark it is 4 away.
    assert _place() is None
    placed = _place(own_mark_right=ACTUAL.right)
    assert placed is not None and placed.side == "end"
    assert placed.bounds.x == pytest.approx(ACTUAL.right + 4.0)
    assert not (placed.bounds.x < ACTUAL.right and ACTUAL.x < placed.bounds.right)


def test_the_reach_still_bounds_detached_text_from_the_last_own_mark():
    # A wide obstacle after the mark pushes the first free position 40 past the mark: still detached.
    wide = LabelRect(20, 0, 80, 10)
    assert _place(own_mark_right=ACTUAL.right, obstacles=(wide,)) is None
    assert _place(own_mark_right=ACTUAL.right, obstacles=(wide,), maximum_end_gap=48.0) is not None


@pytest.mark.parametrize("own_mark_right", [None, 5.0, HOST.right])
def test_a_mark_that_does_not_pass_the_host_changes_nothing(own_mark_right):
    plain = _place(obstacles=())
    assert _place(obstacles=(), own_mark_right=own_mark_right) == plain


def test_only_the_end_side_uses_the_last_mark():
    above = place_member_name(HOST, SIZE, ("above",), bounds=BOUNDS, obstacles=(), gap=4.0,
                              maximum_end_gap=20.0, own_mark_right=ACTUAL.right)
    assert above == place_member_name(HOST, SIZE, ("above",), bounds=BOUNDS, obstacles=(), gap=4.0,
                                      maximum_end_gap=20.0)


def test_full_band_measures_from_the_last_own_mark_too():
    placed = _place(own_mark_right=ACTUAL.right, full_band=True)
    assert placed is not None and placed.bounds.x == pytest.approx(ACTUAL.right + 4.0)
    assert _place(full_band=True) is None


def test_visible_overflow_fallback_does_not_land_on_the_own_mark():
    wide = LabelRect(20, 0, 80, 10)
    placed = _place(own_mark_right=ACTUAL.right, obstacles=(wide,), overflow="visible-overflow",
                    association=MemberNameAssociation(HOST, 0.0, 0.0, SIZE[0], SIZE[1], 20.0, (ACTUAL,)))
    assert placed is not None and placed.visible_overflow
    assert placed.bounds.x >= ACTUAL.right


def test_association_accepts_text_near_any_own_mark_and_names_the_nearest():
    association = MemberNameAssociation(HOST, 0.0, 0.0, 40.0, 10.0, 6.0, (ACTUAL,))
    near_actual = LabelRect(64, 0, 40, 10)
    near_host = LabelRect(-44, 0, 40, 10)
    detached = LabelRect(200, 0, 40, 10)
    assert association.allows(near_actual) and association.allows(near_host)
    assert not association.allows(detached)
    assert association.nearest_mark_index(near_actual) == 1
    assert association.nearest_mark_index(near_host) == 0
    # Without the extra mark the same text is detached: the previous rule.
    assert not MemberNameAssociation(HOST, 0.0, 0.0, 40.0, 10.0, 6.0).allows(near_actual)


def test_a_tie_keeps_the_requested_host():
    association = MemberNameAssociation(HOST, 0.0, 0.0, 10.0, 10.0, 50.0, (LabelRect(30, 0, 10, 10),))
    assert association.nearest_mark_index(LabelRect(15, 0, 10, 10)) == 0


def test_a_non_finite_own_mark_right_is_rejected():
    with pytest.raises(ValueError, match="E_PRESENTATION_LABEL_INPUT"):
        _place(own_mark_right=float("nan"))
