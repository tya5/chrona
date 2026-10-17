"""Completed annotation geometry remains truthful and readable across callout outcomes."""
from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal

from chrona.presentation.layout.labels import CollisionDomain, LabelRect, LabelRequest
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex, obstacles_intersect
from chrona.presentation.layout.surface_quality import MarkPlacement
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import serialize_scene
from tests.integration.test_annotation_list_status import _by_id, _fixture
from tests.unit.chrona.presentation.layout.test_member_label_required_phase import _placement_context
from tests.support import synthetic_review as sr


def _point_on_rect(point, rect):
    x, y = point
    left, top, width, height = rect
    right, bottom = left + width, top + height
    epsilon = 1e-6
    return (
        (abs(x - left) <= epsilon or abs(x - right) <= epsilon) and top - epsilon <= y <= bottom + epsilon
        or (abs(y - top) <= epsilon or abs(y - bottom) <= epsilon) and left - epsilon <= x <= right + epsilon
    )


def test_completed_plot_callouts_keep_safe_leaders_and_contrast_valid_text(tmp_path):
    source, parts = _fixture()
    rendered = sr.render(tmp_path, source, presentation=parts, viewport=(2400, 1400))
    ids = _by_id(rendered)

    findings = evaluate_scene_contrast(json.loads(serialize_scene(rendered.scene)))
    by_primitive = {item.primitive_id: item for item in findings}
    for index in range(4):
        identifier = f"note-{index}"
        assert f"annotation-box:{identifier}" in ids
        assert f"annotation-text:{identifier}" in ids
        assert f"annotation-leader:{identifier}" in ids
        assert f"note-index:{identifier}" in ids
        text = by_primitive[f"annotation-text:{identifier}"]
        assert text.severity == "info" and text.contrast_ratio >= 4.5
        box = ids[f"annotation-box:{identifier}"].bounds
        leader = ids[f"annotation-leader:{identifier}"]
        assert _point_on_rect(leader.points[-1], box) or _point_on_rect(leader.points[0], box)

    assert not any(item.startswith("W_LAYOUT_ANNOTATION_SUPPRESSED:")
                   for item in rendered.scene.diagnostics)


def test_inside_route_collision_selects_declared_above_candidate_with_host_and_contrast():
    from chrona.presentation.layout.surface_member_labels import place_member_labels

    context = _placement_context()
    host = MarkPlacement("planned:a", "a", Rect(Decimal(50), Decimal(40), Decimal(100), Decimal(20)),
                         (50, 50), (150, 50), mark_shape="span", slot_id="timeline",
                         semantic_id="planned", paint_order=100)
    context = replace(context, marks=(host,))
    request = LabelRequest("member-label:a", "a", "Owner", LabelRect(50, 40, 100, 20),
        ("inside", "above"), "text", "plot-label", CollisionDomain("timeline", "overlay"),
        "suppress", inside_host_obstacle_id="planned:a", semantic_id="memberLabel")
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("planned:a", "mark", "timeline", ObstacleRect(50, 40, 150, 60)))
    route = ObstacleSegment((80, 50), (120, 50), stroke_width=1)
    obstacles.add(SurfaceObstacle("dependency:a", "dependency-route", "timeline", route))

    batch = place_member_labels(context, (request,), obstacles)
    (placed,) = batch.text
    assert placed.selected_rung == "above"
    assert placed.typography_role == "text"
    assert placed.host_placement_id == "planned:a"
    bounds = placed.bounds
    text_rect = ObstacleRect(float(bounds.inline), float(bounds.block),
        float(bounds.inline + bounds.inline_size), float(bounds.block + bounds.block_size))
    assert not obstacles_intersect(text_rect, route)

    scene = {"version": "chrona/scene/v0.7", "kind": "scene", "surfaces": [{
        "id": "review", "canvasPaint": {"fill": "#FFFFFF", "opacity": 1}, "decorationDispositions": [],
        "primitives": [
            {"id": "planned:a", "kind": "Rect", "purpose": "planned", "visualRole": "planned",
             "paintOrder": 100, "bounds": {"inline": 50, "block": 40, "inlineSize": 100, "blockSize": 20},
             "paint": {"fill": "#3986E6", "opacity": 1}},
            {"id": "member-label:a", "kind": "Text", "purpose": "member-label", "visualRole": placed.typography_role,
             "paintOrder": 300, "bounds": {"inline": float(bounds.inline), "block": float(bounds.block),
                 "inlineSize": float(bounds.inline_size), "blockSize": float(bounds.block_size)},
             "textLayout": {"bounds": {"inline": float(bounds.inline), "block": float(bounds.block),
                 "inlineSize": float(bounds.inline_size), "blockSize": float(bounds.block_size), "fontSize": 10},
                 "fontSize": 10}, "hostPlacementId": "planned:a", "paint": {"fill": "#000000", "opacity": 1}},
        ],
    }]}
    finding, = [item for item in evaluate_scene_contrast(scene) if item.primitive_id == "member-label:a"]
    assert finding.severity == "info" and finding.contrast_ratio >= 4.5
