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


@pytest.mark.parametrize("mode,drawn,max_bends,unavailable_overlap", (
    ("suppress", False, 4, False), ("relax", True, 4, False), ("overlap", True, 4, False),
    ("relax", True, 0, False), ("stub", True, 4, False), ("overlap", True, 4, True),
))
def test_completed_search_domains_reach_real_scene_and_svg(
        tmp_path, monkeypatch, mode, drawn, max_bends, unavailable_overlap):
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
    if unavailable_overlap:
        monkeypatch.setattr(surface_routes, "complete_fixed_connector", lambda *args, **kwargs: None)
    if mode in {"overlap", "stub"}:
        def forbidden(*args, **kwargs):
            raise AssertionError("explicit overlap/stub must not search")
        monkeypatch.setattr(surface_routes, "select_relation_route", forbidden)
    result = sr.render(tmp_path, source, presentation=parts)
    paths = [p for p in result.surface.primitives if p.source_kind == "relation" and ":link:" in p.scene_id]
    assert bool(paths) is drawn
    assert resolutions
    for resolution in resolutions:
        expected = (
            (RelationResolutionStage.NORMAL, RelationResolutionStage.LABEL_VISUALS,
             RelationResolutionStage.TEXT, RelationResolutionStage.MARKS)
            if mode == "relax" else () if mode in {"overlap", "stub"} else (RelationResolutionStage.NORMAL,))
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
        if mode == "stub" or unavailable_overlap:
            assert len(paths) == 2
            outgoing = next(p for p in paths if p.scene_id.endswith(":stub-source"))
            incoming = next(p for p in paths if p.scene_id.endswith(":stub-target"))
            assert outgoing.from_instance_id is None and outgoing.to_instance_id is None
            assert incoming.from_instance_id is None and incoming.to_instance_id is None
            assert outgoing.source_ref == incoming.source_ref
            labels = [p for p in result.surface.primitives if p.scene_id.startswith("relation-label:")]
            assert len(labels) == 2
            text = "".join(svg.itertext()).upper()
            assert "-> TARGET" in text and "SOURCE ->" in text
    else:
        assert any(item.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for item in result.scene.diagnostics)
