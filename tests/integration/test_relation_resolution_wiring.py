"""A synthetic collision-domain constraint tests Layout-to-Scene wiring.

The injected obstacle is a Layout fixture, not a claim about a painted gallery
obstacle. Visible-obstacle four-mode release evidence remains a separate gate.
"""
from datetime import date
import json
import xml.etree.ElementTree as ET

import pytest

from chrona.presentation.layout import surface_lane_route_plan, surface_route_label_plan, surface_routes
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle
from chrona.presentation.layout.relation_resolution import RelationResolutionStage
from chrona.presentation.model.semantic_registry import ContrastClass, contrast_binding
from tests.support import synthetic_review as sr


@pytest.mark.parametrize("mode,drawn,max_bends,unavailable_overlap", (
    ("suppress", False, 4, False), ("relax", True, 4, False), ("overlap", True, 4, False),
    ("relax", True, 0, False), ("stub", True, 4, False), ("overlap", True, 4, True),
))
@pytest.mark.parametrize("view_overflow", (None, "suppress", "visible-overflow"))
def test_completed_search_domains_reach_real_scene_and_svg(
        tmp_path, monkeypatch, mode, drawn, max_bends, unavailable_overlap, view_overflow):
    source = sr.project({
        "source": sr.span("source", date(2027, 1, 4), 10),
        "target": sr.span("target", date(2027, 2, 1), 10),
    }, [{"id": "link", "type": "dependency", "lag": "0d",
         "from": {"object": "source", "endpoint": "end"},
         "to": {"object": "target", "endpoint": "start"}}])
    parts = sr.bundle()
    visibility = parts["view"]["body"]["visibility"]
    declared = visibility["relations"]
    if isinstance(declared, str):
        declared = visibility["relations"] = {"mode": declared}
    declared.pop("overflow", None)
    if view_overflow is not None:
        declared["overflow"] = view_overflow
    else:
        visibility["relations"] = declared["mode"]
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
    policy_facts = [json.loads(item.split(":", 1)[1]) for item in result.scene.diagnostics
                    if item.startswith("I_LAYOUT_RELATION_POLICY_SUPERSEDED:")]
    if view_overflow is not None and not (view_overflow == mode == "suppress"):
        assert len(policy_facts) == 1
        assert policy_facts[0]["viewValue"] == view_overflow
        assert policy_facts[0]["layoutValue"] == mode
        assert policy_facts[0]["layoutMember"] == "relationRouting.unroutable"
    else:
        assert policy_facts == []
    facts = [json.loads(item.split(":", 1)[1]) for item in result.scene.diagnostics
             if item.startswith("I_LAYOUT_RELATION_RESOLUTION:")]
    summaries = [json.loads(item.split(":", 1)[1]) for item in result.scene.diagnostics
                 if item.startswith("I_LAYOUT_RELATION_RESOLUTION_SUMMARY:")]
    if drawn:
        stage = ("stub" if mode == "stub" or unavailable_overlap else
                 "marks" if mode == "relax" and max_bends else "overlap")
        assert len(facts) == 1
        assert facts[0]["stage"] == stage
        assert isinstance(facts[0]["critical"], bool)
        assert summaries == [{"surfaceId": facts[0]["surfaceId"], "count": 1, "stages": {stage: 1}}]
    else:
        assert facts == summaries == []
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
        assert contrast_binding("dependency-halo").contrast_class is ContrastClass.DECORATION
        halos = [p for p in result.surface.primitives if p.visual_role == "dependency-halo"]
        assert len(halos) == len(paths)
        for line in paths:
            halo = next(p for p in halos if p.scene_id == line.scene_id + ":halo")
            assert halo.points == line.points and halo.path_commands == line.path_commands
            assert halo.paint_clip == line.paint_clip
            assert halo.paint_order == line.paint_order - 1
            assert halo.marker_start is None and halo.marker_end is None
            assert halo.from_instance_id is None and halo.to_instance_id is None
            assert halo.paint.stroke == result.surface.canvas_paint.fill
            assert halo.paint.stroke_width == 3 * line.paint.stroke_width
            texts = [p for p in result.surface.primitives if p.kind.value == "Text"]
            assert texts
            assert all(line.paint_order < p.paint_order for p in texts), [(p.scene_id, p.paint_order)
                for p in texts if p.paint_order <= line.paint_order]
            ordered_ids = [element.get("data-scene-id", element.get("id")) for element in svg.iter()]
            assert ordered_ids.index(halo.scene_id) < ordered_ids.index(line.scene_id)
            assert all(ordered_ids.index(line.scene_id) < ordered_ids.index(p.scene_id) for p in texts)
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
        assert not any(p.visual_role == "dependency-halo" for p in result.surface.primitives)
        assert any(item.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for item in result.scene.diagnostics)
