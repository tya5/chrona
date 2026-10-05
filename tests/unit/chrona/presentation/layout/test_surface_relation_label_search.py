from __future__ import annotations

from types import SimpleNamespace

from chrona.presentation.layout.obstacles import (
    ObstacleRect,
    ObstacleSegment,
    SurfaceObstacle,
    SurfaceObstacleIndex,
    obstacles_intersect,
)
from chrona.presentation.layout.labels import LabelRect, place_label
from chrona.presentation.layout.surface_quality import RelationPlacement
from chrona.presentation.layout.surface_routes import (
    SurfaceRelationLabelsBatch,
    SurfaceRoutesBatch,
    place_relation_labels,
)


class _Metrics:
    content_identity = "synthetic-metric"

    def width(self, value, size, **_kwargs):
        return len(value) * size * 0.5


class _Theme:
    def text_treatment(self, _role):
        return SimpleNamespace(font_size=10, line_height=1.2, letter_spacing=0,
                               transform="none", family="synthetic", weight=400,
                               numeric_spacing="proportional", horizontal_scale=1)


def _context(obstacles: SurfaceObstacleIndex):
    request = SimpleNamespace(
        surface_content=SimpleNamespace(relation_overflow="suppress"),
        theme_tokens=_Theme(),
        font_metrics=_Metrics(),
    )
    return SimpleNamespace(request=request, timeline_bounds=(0, 0, 140, 100), obstacles=obstacles)


def _routes():
    # The same completed horizontal route is both the label anchor and indexed path.
    relation = RelationPlacement(
        "relation:a-to-b", "port:a:end", "port:b:start", points=((40, 50), (100, 50)),
        label_content="+1d", source_ref="a-to-b",
    )
    return SurfaceRoutesBatch((relation,), (), {}, {}, {}, ()), relation


def _index(*, canonical_blockers: bool) -> SurfaceObstacleIndex:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("route:a-to-b", "dependency-route", "timeline",
                              ObstacleSegment((40, 50), (100, 50), stroke_width=1)))
    if canonical_blockers:
        # With 15px text and 2.5px gap, these occupy the canonical above,
        # below, start, and end placements. A 15px rightward above move is clear.
        index.extend((
            SurfaceObstacle("block:above", "mark", "timeline", ObstacleRect(45, 23.5, 77.5, 48)),
            SurfaceObstacle("block:below", "mark", "timeline", ObstacleRect(42, 52, 100, 78)),
            SurfaceObstacle("block:start", "mark", "timeline", ObstacleRect(5, 32, 24, 58)),
            SurfaceObstacle("block:end", "mark", "timeline", ObstacleRect(101, 32, 120, 58)),
        ))
    return index


def test_relation_label_uses_shared_bounded_search_after_all_four_canonical_sides_fail():
    obstacles = _index(canonical_blockers=True)
    original_obstacles = obstacles.all()
    routes, relation = _routes()
    assert place_label(LabelRect(40, 50, 60, 1), (15, 12),
                       ("above", "below", "start", "end"),
                       bounds=LabelRect(0, 0, 140, 100), obstacles=obstacles,
                       gap=2.5, classes=("mark", "dependency-route"),
                       overflow="suppress", required=False) is None

    result = place_relation_labels(_context(obstacles), routes)

    assert result.diagnostics == ()
    assert len(result.text) == 1
    label = result.text[0]
    assert label.placement_id == "relation-label:a-to-b"
    assert label.selected_rung == "above"
    assert float(label.bounds.inline) == 77.5
    assert float(label.bounds.inline) - 62.5 <= 15  # measured text-width displacement bound
    rect = ObstacleRect(float(label.bounds.inline), float(label.bounds.block),
                        float(label.bounds.inline + label.bounds.inline_size),
                        float(label.bounds.block + label.bounds.block_size))
    assert all(not obstacles_intersect(rect, item.geometry, item.clearance)
               for item in original_obstacles)
    assert relation.points == ((40, 50), (100, 50))


def test_relation_label_search_preserves_canonical_first_and_suppresses_deterministically():
    routes, _ = _routes()
    canonical_obstacles = _index(canonical_blockers=False)
    canonical = place_relation_labels(_context(canonical_obstacles), routes)
    assert canonical.diagnostics == ()
    assert len(canonical.text) == 1
    assert canonical.text[0].selected_rung == "above"
    assert canonical.text[0].bounds.inline == 62.5

    def no_space_result():
        blocked = SurfaceObstacleIndex()
        blocked.add(SurfaceObstacle("route:a-to-b", "dependency-route", "timeline",
                                    ObstacleSegment((40, 50), (100, 50), stroke_width=1)))
        blocked.add(SurfaceObstacle("all-space", "mark", "timeline", ObstacleRect(0, 0, 140, 100)))
        return place_relation_labels(_context(blocked), routes)

    first = no_space_result()
    second = no_space_result()
    assert first == second
    assert first.text == ()
    assert first.diagnostics == ("W_LAYOUT_RELATION_LABEL_SUPPRESSED:relation:a-to-b",)
