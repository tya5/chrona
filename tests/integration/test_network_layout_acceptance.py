"""Synthetic Project → completed network Layout/Scene/SVG acceptance for #1727."""
from datetime import date
from xml.etree import ElementTree

from chrona.presentation.layout.path_geometry import flatten_path
from chrona.presentation.layout.relation_terminals import project_marker_outline
from chrona.presentation.model.semantic_registry import semantic_binding
from tests.integration.test_title_ink import _network_parts
from tests.support import synthetic_review as sr


def _fixture():
    parts = _network_parts()
    parts["view"]["body"]["selection"] = {"include": {"ids": ["team", "alpha", "beta"]}}
    parts["view"]["body"]["deadlines"] = {"show": "all"}
    parts["theme"]["body"]["values"].update({
        "network-inline-inset": {"type": "number", "value": 9},
        "network-block-inset": {"type": "number", "value": 11},
        "critical-edge-test-width": {"type": "number", "value": 3},
    })
    parts["theme"]["body"]["metrics"].update({
        "network.node.paddingInline": "network-inline-inset",
        "network.node.paddingBlock": "network-block-inset",
    })
    parts["theme"]["body"]["roles"]["critical-edge"]["strokeWidth"] = "critical-edge-test-width"
    parts["theme"]["body"]["colorBindings"]["critical-edge.stroke"] = "negative"
    source = sr.project({
        "team": {"type": "group", "title": "Team Alpha", "schedule": {"mode": "rollup"}},
        "alpha": {**sr.span("alpha", date(2026, 1, 1), 4, title="Alpha"),
                  "parent": "team", "deadline": "2026-01-05"},
        "beta": {**sr.span("beta", date(2026, 1, 5), 4, title="Beta"),
                 "deadline": "2026-01-09"},
    }, ({"id": "handoff", "type": "dependency", "lag": "0d",
         "from": {"object": "alpha", "endpoint": "end"},
         "to": {"object": "beta", "endpoint": "start"}},))
    return parts, source


def test_network_layout_closes_groups_critical_key_footer_and_terminals_in_real_svg(tmp_path):
    parts, source = _fixture()
    rendered = sr.render(tmp_path, source, presentation=parts)
    scene = rendered.surface
    primitives = {item.scene_id: item for item in scene.primitives}
    svg = ElementTree.fromstring(rendered.artifact.content)
    svg_by_id = {item.attrib["data-scene-id"]: item for item in svg.iter()
                 if item.attrib.get("data-scene-id")}
    x0, y0, width, height = map(float, svg.attrib["viewBox"].split())
    x1, y1 = x0 + width, y0 + height

    # Project membership is represented by one Scene group, not a task-shaped
    # container rectangle, while the actual child task remains visible.
    assert {item.group_id for item in scene.groups} == {"team"}
    assert "network-node:team" not in primitives
    assert "network-node:alpha" in primitives and "network-node:beta" in primitives
    group_band = primitives["network-groupBand:team"]
    assert group_band.source_ref == "team"
    assert group_band.purpose == semantic_binding("groupBand").purpose
    assert group_band.paint.fill is not None
    assert any(item.text == "Team Alpha" for item in scene.primitives)

    node = primitives["network-node:alpha"]
    label = primitives["network-label:alpha"]
    footer = primitives["deadline-network-label:alpha"]
    nx, ny, nw, nh = node.bounds
    for text in (label, footer):
        tx, ty, tw, th = text.bounds
        assert tx >= nx + 9 and ty >= ny + 11
        assert tx + tw <= nx + nw - 9 and ty + th <= ny + nh - 11
    glyph = next(item for item in scene.primitives
                 if item.scene_id.startswith("deadline-network-tick:alpha"))
    assert glyph.bounds[0] >= nx + 9 and glyph.bounds[1] >= ny + 11

    edge = next(item for item in scene.primitives if item.scene_id.startswith("network-edge:"))
    assert edge.purpose == "critical-edge"
    assert edge.visual_role == "critical-edge"
    key = next(item for item in scene.primitives
               if item.source_ref == "critical-edge" and item.kind == "Path")
    assert key.paint.stroke == edge.paint.stroke
    assert edge.paint.stroke is not None
    assert edge.points[0][0] < edge.points[-1][0]
    assert edge.marker_end is not None
    assert "marker-end" in svg_by_id[edge.scene_id].attrib
    assert group_band.scene_id in svg_by_id and key.scene_id in svg_by_id

    # Every completed rectangle and the actual routed marker contours fit in
    # the serialized viewport, including the deadline glyph and intrinsic key.
    for item in scene.primitives:
        x, y, w, h = item.bounds
        if w == 0 and h == 0:
            continue
        assert x >= x0 - 1e-6 and y >= y0 - 1e-6
        assert x + w <= x1 + 1e-6 and y + h <= y1 + 1e-6, item.scene_id
    terminal_points = []
    for marker, side in ((edge.marker_start, "start"), (edge.marker_end, "end")):
        if marker is not None:
            outline = project_marker_outline(marker, side=side, points=edge.points,
                                             path_commands=edge.path_commands,
                                             stroke_width=edge.paint.stroke_width)
            terminal_points.extend(flatten_path(outline))
    assert terminal_points
    assert all(x0 - 1e-6 <= x <= x1 + 1e-6 and y0 - 1e-6 <= y <= y1 + 1e-6
               for x, y in terminal_points)
    assert "critical-edge" in rendered.artifact.content.decode()
