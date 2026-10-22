"""Short straight connectors still use marker-fit completion (#1841)."""
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from chrona.presentation.layout.sources import MeasuredSources, SourceInput
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, segment_closed_rect_contact_interval
from chrona.presentation.model.info_diagnostics import RelationResolutionInfo
from chrona.presentation.model.projection import ReviewItem, ReviewProjection, ReviewRowProjection
from chrona.presentation.surface_pipeline import compose_review_surface

from tests.unit.chrona.presentation.scene.test_v05_builder import (
    _Font, _manifest, _theme, _title_measurement, build_surface_input, surface_content,
)


def _item(object_id, start, end):
    return ReviewItem(object_id, object_id.upper(), "span", {"start": start, "end": end},
                      None, None, (), item_id=object_id, source_kind="primary", track="stacked")


def _compose_short_gap(search_policy):
    # With the test timeline's 500px interior and 382-day window, this four-day
    # inter-mark gap is about 5.24px: enough for the existing round-source setback,
    # but shorter than the target triangle's nominal run.
    source = _item("source", date(2026, 2, 1), date(2026, 2, 8))
    target = _item("target", date(2026, 2, 12), date(2026, 2, 20))
    source = replace(source, track="shared")
    target = replace(target, track="shared")
    rows = (ReviewRowProjection("both", "BOTH", "", "both", (source, target)),)
    relation = {"id": "short-gap", "from": {"object": "source", "endpoint": "end"},
                "to": {"object": "target", "endpoint": "start"}}
    theme = _theme()
    theme["body"]["values"]["shortSource"] = {
        "type": "marker", "value": {"shape": "circle", "headLength": 5,
                                    "headWidth": 5, "attachmentOffset": 0},
    }
    theme["body"]["values"]["longTarget"] = {
        "type": "marker", "value": {"shape": "triangle", "headLength": 10,
                                    "headWidth": 10, "attachmentOffset": 0},
    }
    theme["body"]["roles"]["relationSourceTerminal"] = {"marker": "shortSource"}
    theme["body"]["roles"]["relationTargetTerminal"] = {"marker": "longTarget"}

    projection = ReviewProjection((source, target),
        (date(2026, 1, 1), date(2027, 1, 18)), (), (), rows)
    measured = MeasuredSources(
        {"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
        {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
         "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8),
         "timeline.mark.blockSize": Decimal(8)},
    )
    manifest = replace(_manifest("title", "table", "timeline", "timeline-axis"),
                       relation_search=search_policy)
    value = build_surface_input(projection=projection,
        surface_content=surface_content(relations=(relation,)), layout_manifest=manifest,
        resolved_theme=theme, font_metrics=_Font(), measured_sources=measured,
        capabilities={"svg": True})
    surface = compose_review_surface(value)
    paths = [primitive for primitive in surface.primitives
             if primitive.scene_id.startswith("relation:")
             and not primitive.scene_id.startswith("relation-label:")
             and not primitive.scene_id.endswith(":halo")]
    marks = {primitive.source_ref: primitive for primitive in surface.primitives
             if primitive.scene_id.startswith("planned:")}
    return surface, paths, marks


@pytest.mark.parametrize("search_policy", ("first-fit", "best"))
def test_short_two_point_gap_keeps_round_source_and_triangle_target(search_policy):
    surface, paths, marks = _compose_short_gap(search_policy)

    assert len(paths) == 1
    path = paths[0]
    source = marks["source"]
    target = marks["target"]
    source_port = (source.bounds[0] + source.bounds[2], source.bounds[1] + source.bounds[3] / 2)
    target_port = (target.bounds[0], target.bounds[1] + target.bounds[3] / 2)
    assert target_port[1] == pytest.approx(source_port[1])
    direct_gap = target_port[0] - source_port[0]
    assert len(path.points) == 2
    assert path.marker_start is not None and path.marker_start.centred
    assert path.marker_start.head_length == pytest.approx(5)
    assert path.marker_end is not None and not path.marker_end.centred
    assert path.marker_end.head_length == pytest.approx(10)
    source_radius = path.marker_start.head_length / 2
    assert source_radius + path.paint.stroke_width < direct_gap < path.marker_end.head_length
    # The completed round source is centered at its semantic port; the triangle
    # tip remains at the target port. No stub fragment or recovery stage is used.
    from tests.unit.chrona.presentation.scene.test_relation_round_terminals import _centre
    assert _centre(path, "source") == pytest.approx(source_port)
    assert path.points[0] == pytest.approx((source_port[0] + source_radius, source_port[1]))
    assert path.points[-1] == pytest.approx(target_port)
    assert all(point[1] == pytest.approx(source_port[1])
               and source_port[0] <= point[0] <= target_port[0] for point in path.points)
    for placement_id, mark in marks.items():
        x, y, width, height = mark.bounds
        contact = segment_closed_rect_contact_interval(
            ObstacleSegment(path.points[0], path.points[1]),
            ObstacleRect(x, y, x + width, y + height),
        )
        if contact is not None:
            assert placement_id == "target" and contact == (1.0, 1.0)
    assert not any(isinstance(item, RelationResolutionInfo) for item in surface.info_diagnostics)
    assert not any("stub-" in primitive.scene_id for primitive in surface.primitives)
    assert not any(item.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for item in surface.diagnostics)

