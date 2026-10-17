"""Paint-width checks for dependency routes against retained label footprints."""

import pytest

from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.relation_resolution import RelationResolutionStage as Stage, relaxed_domain
from chrona.presentation.layout.surface_routes import route_clears_retained_label_ink


@pytest.mark.parametrize("obstacle_class", ("text", "label-visual", "relation-label"))
def test_actual_stroke_rejects_centerline_near_label_and_accepts_clear_alternative(obstacle_class):
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("label", obstacle_class, "timeline", ObstacleRect(0., 0., 10., 10.)))
    before = index.all()

    assert not route_clears_retained_label_ink(((-2., -0.2), (12., -0.2)), index, 1.)
    assert route_clears_retained_label_ink(((-2., -0.6), (12., -0.6)), index, 1.)
    assert index.all() == before


@pytest.mark.parametrize("stage", (Stage.LABEL_VISUALS, Stage.TEXT, Stage.MARKS))
def test_actual_stroke_sees_required_labels_and_only_labels_retained_at_stage(stage):
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("required-text", "text", "timeline", ObstacleRect(0., 0., 10., 10.)))
    index.add(SurfaceObstacle("label-footprint:required-text", "label-visual", "timeline",
                              ObstacleRect(0., 0., 10., 10.)))
    index.add(SurfaceObstacle("optional-text", "text", "timeline", ObstacleRect(20., 0., 30., 10.)))
    index.add(SurfaceObstacle("label-footprint:optional-text", "label-visual", "timeline",
                              ObstacleRect(20., 0., 30., 10.)))
    protected = frozenset({"required-text", "label-footprint:required-text"})
    domain = relaxed_domain(index, stage, frozenset(), protected)

    assert not route_clears_retained_label_ink(((-2., -0.2), (12., -0.2)), domain.obstacles, 1.)
    optional_crossing = ((18., -0.2), (32., -0.2))
    assert route_clears_retained_label_ink(optional_crossing, domain.obstacles, 1.) is (
        stage in {Stage.TEXT, Stage.MARKS})


def test_normal_domain_retains_required_and_optional_label_ink_without_mutating_source_index():
    index = SurfaceObstacleIndex()
    for identity, left in (("required", 0.), ("optional", 20.)):
        index.add(SurfaceObstacle(identity, "text", "timeline", ObstacleRect(left, 0., left + 10., 10.)))
    before = index.all()
    domain = relaxed_domain(index, Stage.NORMAL, frozenset(), frozenset({"required"}))

    assert not route_clears_retained_label_ink(((-2., -0.2), (12., -0.2)), domain.obstacles, 1.)
    assert not route_clears_retained_label_ink(((18., -0.2), (32., -0.2)), domain.obstacles, 1.)
    assert index.all() == before


def test_route_pipeline_forwards_theme_stroke_and_rejects_full_paint_overlap(monkeypatch):
    """Exercise the selector's real prepare callback against a narrow synthetic label."""
    from tests.unit.chrona.presentation.layout.test_window_relation_completion import (
        _surviving_relation_request,
    )
    import chrona.presentation.layout.surface_routes as owner
    from chrona.presentation.layout.surface_composer import compose_surface_layout

    original = owner.select_relation_route
    captured = []

    def observe(port_pairs, **kwargs):
        result = original(port_pairs, **kwargs)
        if result.selected_pair is not None:
            captured.append((kwargs, result))
        return result

    monkeypatch.setattr(owner, "select_relation_route", observe)
    request = _surviving_relation_request()
    compose_surface_layout(request)

    assert captured
    kwargs, selection = captured[0]
    width = kwargs["route_stroke_width"]
    assert width > 0
    prepare = kwargs["prepare"]
    source, target = selection.selected_pair
    assert prepare(selection.points, source, target) is not None

    # Put a tiny label box 0.6 units off an interior segment. The original route
    # clears, but a 0.2-unit terminal-completion displacement makes its painted
    # path overlap the label, exercising the post-completion guard.
    segment = next(((left, right) for left, right in zip(selection.points, selection.points[1:])
                    if ((right[0] - left[0]) ** 2 + (right[1] - left[1]) ** 2) ** 0.5 > 2.)
                   , None)
    assert segment is not None
    left, right = segment
    dx, dy = right[0] - left[0], right[1] - left[1]
    length = (dx * dx + dy * dy) ** 0.5
    mid_x, mid_y = (left[0] + right[0]) / 2, (left[1] + right[1]) / 2
    offset = (-dy / length * 0.2, dx / length * 0.2)
    center = (mid_x + offset[0] * 3, mid_y + offset[1] * 3)
    label = ObstacleRect(center[0] - 0.01, center[1] - 0.01,
                         center[0] + 0.01, center[1] + 0.01)
    obstacles = kwargs["obstacles"]
    assert not obstacles.collisions(ObstacleSegment(left, right),
                                    classes=("text", "label-visual", "relation-label"),
                                    regions=("timeline", "group-header"))
    obstacles.add(SurfaceObstacle("synthetic-near-label", "text", "timeline", label))
    assert prepare(selection.points, source, target) is not None

    complete = owner.complete_centred_terminals

    def shifted_completion(points, *args, **kwargs):
        drawn, start_terminal, end_terminal = complete(points, *args, **kwargs)
        shifted = tuple((x + offset[0], y + offset[1]) for x, y in drawn)
        return shifted, start_terminal, end_terminal

    monkeypatch.setattr(owner, "complete_centred_terminals", shifted_completion)
    assert prepare(selection.points, source, target) is None
