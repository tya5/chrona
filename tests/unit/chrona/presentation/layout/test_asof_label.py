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
