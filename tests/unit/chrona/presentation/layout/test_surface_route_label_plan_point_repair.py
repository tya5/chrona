"""Real point-target witness for on-demand route/name coordination."""
from dataclasses import replace
from datetime import date
from decimal import Decimal

from chrona.presentation.layout.labels import LabelRect, LabelRequest
from chrona.presentation.layout.sources import MeasuredSources, SourceInput
from chrona.presentation.layout.surface_geometry import bounds_from_rect
from chrona.presentation.layout.surface_quality import CollisionDomain
from chrona.presentation.model.projection import build_review_projection
from chrona.presentation.surface_pipeline import compose_review_surface
from chrona.presentation.layout import surface_composer
from chrona.presentation.layout import surface_route_label_plan as plan
from tests.unit.chrona.presentation.layout.test_surface_route_label_plan import _empty_annotations
from tests.unit.chrona.presentation.scene.test_relation_ghost_endpoints import PROJECT as PROJECT_BASE, _view
from tests.unit.chrona.presentation.scene.test_relation_entry_acceptance import _theme_with_route_fixture_geometry
from tests.unit.chrona.presentation.scene.test_v05_builder import (
    _Font, _manifest, _title_measurement, build_surface_input, surface_content,
)


def test_route_repair_for_span_to_point_preserves_the_at_arrival_and_optional_name(monkeypatch):
    objects = {"a": PROJECT_BASE["objects"]["a"],
        "c": {"title": "Second source", "fields": {"owner": "x"}},
        "b": {**PROJECT_BASE["objects"]["b"], "type": "milestone"},
        "d": {"title": "Third source", "fields": {"owner": "x"}},
        "e": {"title": "Later work", "fields": {"owner": "x"}}}
    project = {**PROJECT_BASE, "objects": objects,
        "relations": [{"id": "dep-a", "type": "dependency",
            "from": {"object": "a", "endpoint": "end"},
            "to": {"object": "b", "endpoint": "at"}},
            {"id": "dep-c", "type": "dependency",
             "from": {"object": "c", "endpoint": "end"},
             "to": {"object": "b", "endpoint": "at"}},
            {"id": "dep-d", "type": "dependency",
             "from": {"object": "d", "endpoint": "end"},
             "to": {"object": "b", "endpoint": "at"}}]}
    placed = {"a": {"start": date(2026, 2, 22), "end": date(2026, 2, 24)},
              "b": {"at": date(2026, 2, 27)},
              "c": {"start": date(2026, 2, 11), "end": date(2026, 2, 17)},
              "d": {"start": date(2026, 2, 12), "end": date(2026, 2, 18)},
              "e": {"start": date(2026, 2, 24), "end": date(2026, 3, 10)}}
    view = _view("automatic")
    # This geometry-sensitive witness needs the former derived-window span;
    # zero is now an exact authored margin, so request the three days directly.
    view = replace(view,
        window=replace(view.window, margin_days=3),
        comparison=replace(view.comparison, baseline_marks=None))
    projection = build_review_projection(project, placed, view, None)
    measured = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
        {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
         "timeline.row.minBlockSize": Decimal(68), "timeline.row.paddingBlock": Decimal(0),
         "timeline.mark.blockSize": Decimal(24)})
    manifest = replace(_manifest("title", "table", "timeline", "timeline-axis"),
        relation_entry="side-when-free", row_distribution="pack", relation_max_bends=4,
        relation_max_detour_ratio=2, relation_search="first-fit")
    content = surface_content(relations=project["relations"], show_member_labels=False,
        label_placement="plot", label_content=(), label_side="inside", label_overflow="suppress")
    theme = _theme_with_route_fixture_geometry()
    theme["body"]["values"]["dependency-halo-width"] = {"type": "number", "value": 3}
    theme["body"]["roles"]["dependency-halo"]["strokeWidth"] = "dependency-halo-width"
    scene_input = build_surface_input(projection=projection, surface_content=content, layout_manifest=manifest,
        resolved_theme=theme, font_metrics=_Font(), measured_sources=measured,
        capabilities={"svg": True})

    captured = {}
    original = surface_composer.compose_routes_and_member_labels

    def capture(context):
        captured["context"] = context
        return original(context)

    monkeypatch.setattr(surface_composer, "compose_routes_and_member_labels", capture)
    compose_review_surface(scene_input)
    context = captured["context"]
    target = next(mark for mark in context.member_labels.marks if mark.placement_id == "planned:b:b")
    _, y, _, height = context.member_labels.timeline_bounds
    x, mark_y, mark_width, mark_height = bounds_from_rect(target.bounds)
    name = LabelRequest("member-label:neutral-b", "b", "A neutral milestone",
        LabelRect(x, mark_y, mark_width, mark_height), ("below", "above"), "text", "plot-label",
        CollisionDomain("timeline", "overlay"), "suppress",
        bounds=LabelRect(x - 70, y, 140, height), semantic_id="memberLabel")
    source = next(mark for mark in context.member_labels.marks if mark.placement_id == "planned:a:a")
    ax, ay, aw, ah = bounds_from_rect(source.bounds)
    second_name = LabelRequest("member-label:neutral-a", "a", "Neutral source plan",
        LabelRect(ax, ay, aw, ah), ("below", "above"), "text", "plot-label",
        CollisionDomain("timeline", "overlay"), "suppress",
        bounds=LabelRect(ax - 70, y, 140, height), semantic_id="memberLabel")
    context = replace(context, post_route_requests=(name, second_name))

    options = plan.compose_routes_and_member_labels(context)

    assert options.retry is not None
    # In this fixture the below rung intersects more incoming route instances;
    # the candidate ranking must reserve the lower-disruption above rung.
    proposals = options.first.members.route_blocked_candidates
    assert [item.text.placement_id for item in proposals] == [
        "member-label:neutral-b", "member-label:neutral-b"]
    assert [item.text.selected_rung for item in proposals] == ["above", "below"]
    admitted = plan._admissible_reservations(options.first, proposals)
    assert len(admitted) == 1 and admitted[0].text.selected_rung == "above"
    assert [item.overflow for item in options.retry.members.text] == ["fit", "fit"]
    selected, _ = plan.select_completed_route_label_plan(options, _empty_annotations(), _empty_annotations())
    assert [item.overflow for item in selected.members.text] == ["fit", "fit"]
    assert {item.content for item in selected.members.text} == {
        "A neutral milestone", "Neutral source plan"}
    routes = selected.routes.relations
    assert len(routes) == 3 and not any(item.suppressed for item in routes)
    route = routes[0]
    old_route = options.first.routes.relations[0]
    assert route.points != old_route.points
    assert route.points[0] == old_route.points[0]
    assert route.points[-1] == old_route.points[-1]
    # An `at` endpoint enters at the left vertex, not from the point's right.
    for route in routes:
        assert route.points[-1] == (x, mark_y + mark_height / 2)
        assert route.points[-1][0] < x + mark_width
        assert route.points[-2][0] == route.points[-1][0]
