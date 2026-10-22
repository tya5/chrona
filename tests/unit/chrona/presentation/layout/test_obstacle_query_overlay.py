from __future__ import annotations

import pytest

from chrona.presentation.layout.obstacles import (
    ObstacleRect,
    ObstacleSegment,
    SurfaceObstacle,
    SurfaceObstacleIndex,
    SurfaceObstacleQueryOverlay,
)
from chrona.presentation.layout.annotation_search import nearest_free_routed_tail_box
from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.route_search import orthogonal_route_candidates
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_quality import MarkPlacement


def _obstacle(placement_id: str, x: float, *, obstacle_class: str = "mark",
              region_id: str = "plot", clearance: float = 0.0) -> SurfaceObstacle:
    return SurfaceObstacle(placement_id, obstacle_class, region_id,
                           ObstacleRect(x, 0, x + 4, 8), clearance)


def _reference(base: SurfaceObstacleIndex,
               overlay: SurfaceObstacle) -> SurfaceObstacleIndex:
    copied = base.copy()
    copied.add(overlay)
    return copied


def test_query_overlay_collisions_match_added_copy_with_sorted_results_and_filters():
    base = SurfaceObstacleIndex()
    base.extend(_obstacle(f"mark:{index:02}", index * 5)
                for index in range(18))
    base.add(_obstacle("rule:divider", 28, obstacle_class="rule", region_id="plot"))
    overlay = SurfaceObstacle("candidate:box", "annotation-box", "plot",
                              ObstacleRect(20, 1, 35, 7), clearance=0.5)
    query = SurfaceObstacleQueryOverlay(base, overlay)
    expected = _reference(base, overlay)

    for geometry, classes, regions, clearance in (
            (ObstacleRect(24, 2, 30, 6), None, None, 0.0),
            (ObstacleSegment((0, 4), (40, 4), 1), ("mark", "annotation-box"), ("plot",), 0.25),
            (ObstacleRect(24, 2, 30, 6), ("mark",), ("plot",), 1.0),
            (ObstacleRect(24, 2, 30, 6), ("mark",), ("other",), 0.0)):
        assert query.collisions(geometry, classes=classes, regions=regions,
                                clearance=clearance) == expected.collisions(
                                    geometry, classes=classes, regions=regions,
                                    clearance=clearance)

    assert query.all() == expected.all()
    assert query.select(classes=("annotation-box",)) == (overlay,)


def test_overlay_reuses_base_prepared_grid_and_never_mutates_base_inventory():
    base = SurfaceObstacleIndex()
    base.extend(_obstacle(f"mark:{index:02}", index * 5) for index in range(24))
    geometry = ObstacleRect(10, 1, 17, 7)
    # Warm the actual base selection/grid before constructing the overlay.
    for _ in range(5):
        base.collisions(geometry)
    selection = base._selection(None, None)
    assert selection._grid is not None
    grid = selection._grid
    original = base.all()
    overlay = SurfaceObstacle("candidate:box", "annotation-box", "plot",
                              ObstacleRect(40, 1, 45, 7))
    query = SurfaceObstacleQueryOverlay(base, overlay)
    for _ in range(8):
        query.collisions(geometry)
    assert base._selection(None, None) is selection
    assert selection._grid is grid
    assert base.all() == original
    assert overlay not in base.all()
    with pytest.raises(ValueError, match="read-only query overlay"):
        query.add(_obstacle("mark:new", 100))
    with pytest.raises(ValueError, match="read-only query overlay"):
        query.extend((_obstacle("mark:new", 100),))
    with pytest.raises(ValueError, match="read-only query overlay"):
        query.copy()
    with pytest.raises(ValueError, match="read-only query overlay"):
        query._overlay = _obstacle("mark:changed", 100)


def test_overlay_cannot_forge_host_or_port_exemptions():
    base = SurfaceObstacleIndex()
    base.add(_obstacle("mark:host", 0))
    base.add(SurfaceObstacle("port:host:end", "port", "plot",
                             ObstacleSegment((4, 4), (6, 4))))
    overlay = SurfaceObstacle("candidate:box", "annotation-box", "plot",
                              ObstacleRect(12, 0, 20, 10))
    query = SurfaceObstacleQueryOverlay(base, overlay)

    assert query.collisions(ObstacleSegment((0, 5), (15, 5)),
                            host_id="mark:host", port_ids=("port:host:end",)) == (overlay,)
    with pytest.raises(ValueError, match="E_LAYOUT_OBSTACLE_EXEMPTION_INVALID"):
        query.collisions(ObstacleSegment((0, 5), (15, 5)), host_id=overlay.placement_id)
    with pytest.raises(ValueError, match="E_LAYOUT_OBSTACLE_EXEMPTION_INVALID"):
        query.collisions(ObstacleSegment((0, 5), (15, 5)), port_ids=(overlay.placement_id,))


def test_overlay_egress_collisions_match_added_copy_and_keep_shared_branch_exemption():
    base = SurfaceObstacleIndex()
    base.add(_obstacle("mark:host", -2))
    base.add(SurfaceObstacle("route:branch", "dependency-route", "plot",
                             ObstacleSegment((0, 0), (5, 5))))
    overlay = SurfaceObstacle("candidate:box", "annotation-box", "plot",
                              ObstacleRect(10, -1, 14, 1))
    query = SurfaceObstacleQueryOverlay(base, overlay)
    expected = _reference(base, overlay)
    segment = ObstacleSegment((0, 0), (20, 0))

    assert query.egress_collisions(segment, host_ids=("mark:host",)) == expected.egress_collisions(
        segment, host_ids=("mark:host",)) == (overlay,)


def test_overlay_route_search_matches_added_copy_and_memo_identity_includes_body():
    base = SurfaceObstacleIndex()
    base.add(_obstacle("mark:remote", 40))
    first = SurfaceObstacle("candidate:box", "annotation-box", "plot",
                            ObstacleRect(8, -2, 12, 2))
    second = SurfaceObstacle("candidate:box", "annotation-box", "plot",
                             ObstacleRect(8, 8, 12, 12))
    query = SurfaceObstacleQueryOverlay(base, first)
    expected = _reference(base, first)
    args = dict(start=(0.0, 0.0), end=(20.0, 0.0), grid_offset=2.0,
                bounds=(-5.0, -8.0, 25.0, 16.0), limit=32)
    # Seed the accepted inventory's visibility cache; the overlay must use it
    # as the base generation and account for the candidate as its delta.
    next(orthogonal_route_candidates(**args, obstacles=base))
    prior_route = next(orthogonal_route_candidates(**args, obstacles=query))
    assert prior_route == next(
        orthogonal_route_candidates(**args, obstacles=expected))

    port = SurfaceObstacle("port:route", "port", "plot", ObstacleSegment((4, 0), (6, 0)))
    base.add(port)
    expected_with_port = _reference(base, first)
    for port_ids in ((), ("port:route",)):
        assert next(orthogonal_route_candidates(**args, obstacles=query,
                                                 port_ids=port_ids)) == next(
            orthogonal_route_candidates(**args, obstacles=expected_with_port,
                                        port_ids=port_ids))

    # An accepted mutation advances the base selection generation. The same
    # overlay object must not retain its previous generation's visibility graph.
    base.add(SurfaceObstacle("mark:new", "mark", "plot", ObstacleRect(14, -7, 16, 7)))
    expected_after_add = _reference(base, first)
    assert next(orthogonal_route_candidates(**args, obstacles=query)) == next(
        orthogonal_route_candidates(**args, obstacles=expected_after_add))

    scope_a = query.route_memo_scope(None, None, ())
    scope_b = SurfaceObstacleQueryOverlay(base, second).route_memo_scope(None, None, ())
    assert scope_a is not None and scope_b is not None
    assert scope_a[0] is scope_b[0]
    assert scope_a[1] != scope_b[1]


def test_overlay_visibility_cache_is_private_and_invalidated_by_base_selection_change():
    base = SurfaceObstacleIndex()
    base.add(_obstacle("mark:first", 0))
    base.add(SurfaceObstacle("port:first", "port", "plot",
                             ObstacleSegment((6, 4), (8, 4))))
    overlay = SurfaceObstacle("candidate:box", "annotation-box", "plot",
                              ObstacleRect(10, 1, 14, 7))
    query = SurfaceObstacleQueryOverlay(base, overlay)

    accepted_scope = base.route_visibility_scope(None, None, ())
    first = query.route_visibility_scope(None, None, ())
    first.bases[("test",)] = object()
    assert first.additions == (overlay,)
    assert first.previous_bases is accepted_scope.bases
    assert not accepted_scope.additions
    with_port = query.route_visibility_scope(None, None, ("port:first",))
    assert with_port.port_ids == frozenset({"port:first"})
    # One body/base generation may keep visibility entries for multiple
    # exemption sets; the port set is explicit in each scope and graph key.
    assert with_port.bases is first.bases
    assert with_port.additions == (overlay,)

    base.add(_obstacle("mark:second", 20))
    later = query.route_visibility_scope(None, None, ())
    assert later.bases is not first.bases
    assert later.additions == (overlay,)


def test_annotation_candidate_search_uses_overlays_without_copying_or_mutating_index(monkeypatch):
    base = SurfaceObstacleIndex()
    mark = MarkPlacement("mark:anchor", "anchor", Rect(40, 40, 10, 10),
                         (40, 45), (50, 45), mark_shape="point")
    base.add(SurfaceObstacle("mark:anchor", "mark", "plot", ObstacleRect(40, 40, 50, 50)))
    original = base.all()

    def forbidden(*args, **kwargs):
        raise AssertionError("annotation candidate search must not copy/add to the accepted index")

    monkeypatch.setattr(SurfaceObstacleIndex, "copy", forbidden)
    monkeypatch.setattr(SurfaceObstacleIndex, "add", forbidden)
    monkeypatch.setattr(SurfaceObstacleIndex, "extend", forbidden)
    result = nearest_free_routed_tail_box(
        region=LabelRect(0, 0, 120, 100), anchor=mark, endpoint="at", siblings=(mark,),
        box_size=(30, 20), max_positions=64, obstacles=base,
        obstacle_classes=("mark", "text", "dependency-route"), corner_radius=3,
        tail_base=8, content_bounds=(0, 0, 120, 100), host_id="mark:anchor",
        route_state_limit=512)

    assert result.box is not None and result.route is not None
    assert base.all() == original
    assert not base.has("candidate:balloon-box")
