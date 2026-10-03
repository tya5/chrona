from chrona.presentation.layout.asof_label import find_asof_label_candidate
from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)


CLASSES = ("rule", "mark", "axis-text", "axis-band", "required-label")


def _index(*items):
    result = SurfaceObstacleIndex()
    result.extend(items)
    return result


def _rule():
    return SurfaceObstacle("asof-rule", "rule", "plot",
                           ObstacleSegment((50, 0), (50, 100), 2))


def _candidate(index, plot=LabelRect(0, 0, 100, 100)):
    return find_asof_label_candidate(plot, (20, 10), rule_x=50, gap=3,
                                     rule_host_id="asof-rule", obstacles=index,
                                     obstacle_classes=CLASSES)


def test_prefers_clear_plot_top_end_and_avoids_rule_without_host_exemption():
    result = _candidate(_index(_rule()))
    assert result is not None
    assert result.side == "plot-top-end"
    assert result.bounds == LabelRect(53, 3, 20, 10)


def test_rule_hosted_candidate_exempts_only_named_rule():
    # Fill the top row on both sides. The chip can fit lower on the rule;
    # its overlap with the thick rule is legal only through rule-host exemption.
    index = _index(
        _rule(),
        SurfaceObstacle("top-left", "mark", "plot", ObstacleRect(0, 0, 47, 10)),
        SurfaceObstacle("top-right", "axis-text", "plot", ObstacleRect(53, 0, 100, 10)),
    )
    result = _candidate(index)
    assert result is not None
    assert result.side == "rule-hosted"
    assert result.bounds.x == 40
    assert result.bounds.x + result.bounds.width / 2 == 50
    assert result.bounds.y >= 10


def test_mark_and_axis_text_contacts_are_blockers_and_order_is_deterministic():
    items = (
        _rule(),
        SurfaceObstacle("mark", "mark", "plot", ObstacleRect(40, 0, 70, 20)),
        SurfaceObstacle("axis", "axis-text", "plot", ObstacleRect(30, 30, 70, 45)),
    )
    forward = _candidate(_index(*items))
    reverse = _candidate(_index(*reversed(items)))
    assert forward == reverse
    assert forward is not None
    assert forward.bounds.y >= 20


def test_candidate_must_fit_wholly_inside_plot_bounds():
    result = _candidate(_index(_rule()), plot=LabelRect(0, 0, 60, 100))
    assert result is not None
    assert result.bounds.x >= 0
    assert result.bounds.right <= 60
    assert result.bounds.y >= 0
    assert result.bounds.bottom <= 100


def test_returns_none_when_every_plot_position_is_blocked():
    index = _index(
        _rule(),
        SurfaceObstacle("solid", "mark", "plot", ObstacleRect(0, 0, 100, 100)),
    )
    assert _candidate(index) is None


# --- #991: the plot foot -----------------------------------------------------------------------------------


def _foot(index, plot=LabelRect(0, 0, 100, 100)):
    return find_asof_label_candidate(plot, (20, 10), rule_x=50, gap=3, rule_host_id="asof-rule", obstacles=index,
                                     obstacle_classes=CLASSES, placement="foot")


def test_foot_placement_centres_the_chip_on_the_rule_at_the_plot_foot():
    result = _foot(_index(_rule()))
    assert result is not None
    assert result.side == "plot-bottom-center"
    assert result.bounds == LabelRect(40, 87, 20, 10)  # centred on x 50, `gap` above the plot's last edge


def test_foot_placement_moves_beside_the_rule_when_the_foot_is_taken_then_falls_back_to_the_rule_host():
    taken = SurfaceObstacle("mark", "mark", "plot", ObstacleRect(35, 80, 65, 100))
    beside = _foot(_index(_rule(), taken))
    assert beside is not None and beside.side in {"plot-bottom-end", "plot-bottom-start", "rule-hosted"}
    assert beside.bounds.bottom <= 97 or beside.side == "rule-hosted"
    wall = SurfaceObstacle("wall", "mark", "plot", ObstacleRect(0, 80, 100, 100))
    hosted = _foot(_index(_rule(), wall))
    assert hosted is not None and hosted.side == "rule-hosted" and hosted.bounds.bottom <= 80


def test_the_default_placement_is_still_the_top_margin():
    assert _candidate(_index(_rule())).side == "plot-top-end"


# --- #1063: below the plot ---------------------------------------------------------------------------------


def _below(index, plot=LabelRect(0, 0, 100, 100), rows_bottom=80.0, rule_x=50):
    return find_asof_label_candidate(plot, (20, 10), rule_x=rule_x, gap=3, rule_host_id="asof-rule", obstacles=index,
                                     obstacle_classes=CLASSES, placement="below-plot", rows_bottom=rows_bottom)


def test_below_plot_centres_the_chip_one_gap_under_the_last_row_inside_the_slot():
    result = _below(_index(_rule()))
    assert result is not None and result.side == "plot-below-center"
    assert result.bounds == LabelRect(40, 83, 20, 10)  # top = rows_bottom + gap, centred on x 50


def test_below_plot_moves_beside_the_rule_when_the_centre_leaves_the_slot_or_is_taken():
    edge = _below(_index(_rule()), rule_x=5)  # centred, the chip would start at x -5
    assert edge is not None and edge.side == "plot-below-end" and edge.bounds.x == 8
    taken = SurfaceObstacle("mark", "mark", "plot", ObstacleRect(40, 83, 49, 93))
    beside = _below(_index(_rule(), taken))
    assert beside is not None and beside.side == "plot-below-end"


def test_below_plot_without_room_in_the_slot_continues_with_the_plot_foot():
    # rows end at 95: the chip (top 98, bottom 108) does not fit in a slot that ends at 100.
    result = _below(_index(_rule()), rows_bottom=95.0)
    assert result is not None and result.side == "plot-bottom-center"


def test_below_plot_requires_the_rows_bottom():
    import pytest
    with pytest.raises(ValueError, match="E_LAYOUT_ASOF_LABEL_GEOMETRY"):
        find_asof_label_candidate(LabelRect(0, 0, 100, 100), (20, 10), rule_x=50, gap=3, rule_host_id="asof-rule",
                                  obstacles=_index(), obstacle_classes=CLASSES, placement="below-plot")
