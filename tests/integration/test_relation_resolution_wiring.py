"""A synthetic collision-domain constraint tests Layout-to-Scene wiring.

The injected obstacle is a Layout fixture, not a claim about a painted gallery
obstacle. Visible-obstacle four-mode release evidence remains a separate gate.
"""
from datetime import date
import xml.etree.ElementTree as ET

import pytest

from chrona.presentation.layout import surface_lane_route_plan, surface_route_label_plan, surface_routes
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle
from chrona.presentation.layout.relation_resolution import RelationResolutionStage
from tests.support import synthetic_review as sr


@pytest.mark.parametrize("mode,drawn,max_bends", (
    ("suppress", False, 4), ("relax", True, 4), ("overlap", True, 4), ("relax", True, 0),
))
def test_completed_search_domains_reach_real_scene_and_svg(tmp_path, monkeypatch, mode, drawn, max_bends):
    source = sr.project({
        "source": sr.span("source", date(2027, 1, 4), 10),
        "target": sr.span("target", date(2027, 2, 1), 10),
    }, [{"id": "link", "type": "dependency", "lag": "0d",
         "from": {"object": "source", "endpoint": "end"},
         "to": {"object": "target", "endpoint": "start"}}])
    parts = sr.bundle()
    parts["layout"]["relationRouting"] = {
        "search": "first-fit", "unroutable": mode, "maxBends": max_bends, "maxDetourRatio": 100,
    }
    compose, resolve = surface_routes.compose_surface_routes, surface_routes.search_relation_resolution
    resolutions = []

    def blocked(context):
        left, top, inline, block = context.timeline_bounds
        if not context.obstacles.has("synthetic:blocker"):
            context.obstacles.add(SurfaceObstacle("synthetic:blocker", "mark", "timeline",
                ObstacleRect(left - 1000, top - 1000, left + inline + 1000, top + block + 1000)))
        return compose(context)

    def observed(*args, **kwargs):
        result = resolve(*args, **kwargs)
        resolutions.append(result)
        return result

    monkeypatch.setattr(surface_route_label_plan, "compose_surface_routes", blocked)
    monkeypatch.setattr(surface_lane_route_plan, "compose_surface_routes", blocked)
    monkeypatch.setattr(surface_routes, "search_relation_resolution", observed)
    if mode == "overlap":
        def forbidden(*args, **kwargs):
            raise AssertionError("explicit overlap must not search")
        monkeypatch.setattr(surface_routes, "select_relation_route", forbidden)
    result = sr.render(tmp_path, source, presentation=parts)
    paths = [p for p in result.surface.primitives if p.source_kind == "relation" and ":link:" in p.scene_id]
    assert bool(paths) is drawn
    assert resolutions
    for resolution in resolutions:
        expected = (
            (RelationResolutionStage.NORMAL, RelationResolutionStage.LABEL_VISUALS,
             RelationResolutionStage.TEXT, RelationResolutionStage.MARKS)
            if mode == "relax" else () if mode == "overlap" else (RelationResolutionStage.NORMAL,))
        assert tuple(item.stage for item in resolution.attempts) == expected
        if mode == "relax" and max_bends:
            assert resolution.accepted.stage is RelationResolutionStage.MARKS
        elif mode == "relax":
            assert resolution.accepted is None
            assert resolution.terminal_fallback is RelationResolutionStage.OVERLAP
    if drawn:
        svg = ET.fromstring(result.artifact.content)
        assert any(element.get("data-scene-id", element.get("id")) == paths[0].scene_id
                   for element in svg.iter())
    else:
        assert any(item.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for item in result.scene.diagnostics)
