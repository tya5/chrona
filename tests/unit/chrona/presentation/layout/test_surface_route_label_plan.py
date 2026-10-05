from types import SimpleNamespace
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from chrona.presentation.layout.labels import LabelRect, LabelRequest
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacleIndex
from chrona.presentation.layout.surface_member_labels import SurfaceMemberLabelsBatch
from chrona.presentation.layout.surface_routes import SurfaceRelationLabelsBatch, SurfaceRoutesBatch
from chrona.presentation.layout import surface_route_label_plan as plan


def _request(name="member-label:a"):
    return LabelRequest(name, "a", "A long member name", LabelRect(0, 0, 4, 4),
        ("above", "suppress"), "text", "plot-label", None, "suppress", semantic_id="memberLabel")


def _members(*texts):
    return SurfaceMemberLabelsBatch(tuple(texts), (), (), (), (), (), (), frozenset())


def _routes(suppressed=False):
    relation = SimpleNamespace(relation_id="relation:r", suppressed=suppressed)
    return SurfaceRoutesBatch((relation,), (), {}, {}, {}, ())


def _text(identifier, overflow="fit", semantic_id="memberLabel"):
    return SimpleNamespace(placement_id=identifier, overflow=overflow, semantic_id=semantic_id)


def _install_trial_owners(monkeypatch, *, recover, relation_ids_same=True,
                          retry_route_status=None, retry_loses_relation_label=False):
    calls = {"routes": 0, "labels": 0, "relation_labels": 0}
    recovery_enabled = recover

    def place_members(_context, requests, obstacles):
        calls["labels"] += 1
        is_recovery = calls["labels"] > 1 and recovery_enabled
        result = []
        for request in requests:
            if request.placement_id == "member-label:a" and not is_recovery:
                result.append(_text(request.placement_id, "suppressed"))
            else:
                obstacles.add(SimpleNamespace(placement_id="recovered-name" if is_recovery else "post-name"))
                result.append(_text(request.placement_id))
        return _members(*result)

    def compose_routes(context):
        calls["routes"] += 1
        recovered = context.obstacles.has("recovered-name")
        relation_id = "relation:r" if relation_ids_same or not recovered else "relation:changed"
        suppressed = bool(recovered and retry_route_status == "suppressed")
        relation = SimpleNamespace(relation_id=relation_id, suppressed=suppressed)
        fallbacks = (relation,) if recovered and retry_route_status == "fallback" else ()
        return SurfaceRoutesBatch((relation,), fallbacks, {}, {}, {}, ())

    def relation_labels(_context, routes):
        calls["relation_labels"] += 1
        if retry_loses_relation_label and calls["relation_labels"] > 1:
            return SurfaceRelationLabelsBatch((), (), ())
        identifiers = tuple(_text(item.relation_id.replace("relation:", "relation-label:"), semantic_id="relationLabel")
                           for item in routes.relations)
        return SurfaceRelationLabelsBatch(identifiers, (), ())

    monkeypatch.setattr(plan, "place_member_labels", place_members)
    monkeypatch.setattr(plan, "compose_surface_routes", compose_routes)
    monkeypatch.setattr(plan, "place_relation_labels", relation_labels)
    return calls


def _context():
    return plan.RouteLabelPlanContext(None, (_request(),), (), SurfaceObstacleIndex(),
        lambda obstacles, _text: SimpleNamespace(obstacles=obstacles))


def test_retries_only_lost_name_and_returns_winning_trial_without_replaying(monkeypatch):
    calls = _install_trial_owners(monkeypatch, recover=True)

    result = plan.compose_routes_and_member_labels(_context())

    assert calls == {"routes": 2, "labels": 2, "relation_labels": 2}
    assert [item.placement_id for item in result.members.text] == ["member-label:a"]
    assert result.members.text[0].overflow == "fit"
    assert result.obstacles.has("recovered-name")
    assert not result.obstacles.has("post-name")
    assert result.relation_labels.text[0].placement_id == "relation-label:r"


def test_irrecoverable_retry_preserves_baseline_result_and_route_inventory(monkeypatch):
    calls = _install_trial_owners(monkeypatch, recover=False)

    result = plan.compose_routes_and_member_labels(_context())

    assert calls == {"routes": 2, "labels": 2, "relation_labels": 2}
    assert result.members.text[0].overflow == "suppressed"
    assert not result.obstacles.has("recovered-name")
    assert result.relation_labels.text[0].placement_id == "relation-label:r"


def test_retry_with_changed_relation_inventory_is_rejected(monkeypatch):
    calls = _install_trial_owners(monkeypatch, recover=True, relation_ids_same=False)

    result = plan.compose_routes_and_member_labels(_context())

    assert calls["routes"] == 2
    assert result.members.text[0].overflow == "suppressed"
    assert not result.obstacles.has("recovered-name")


@pytest.mark.parametrize("route_status", ("suppressed", "fallback"))
def test_retry_that_worsens_route_status_is_rejected(monkeypatch, route_status):
    calls = _install_trial_owners(monkeypatch, recover=True, retry_route_status=route_status)

    result = plan.compose_routes_and_member_labels(_context())

    assert calls["routes"] == 2
    assert result.members.text[0].overflow == "suppressed"
    assert not result.obstacles.has("recovered-name")


def test_retry_that_loses_a_visible_relation_label_is_rejected(monkeypatch):
    calls = _install_trial_owners(monkeypatch, recover=True, retry_loses_relation_label=True)

    result = plan.compose_routes_and_member_labels(_context())

    assert calls["routes"] == 2
    assert result.members.text[0].overflow == "suppressed"
    assert result.relation_labels.text[0].placement_id == "relation-label:r"
    assert not result.obstacles.has("recovered-name")


def test_real_owners_recover_centered_name_by_rerouting_a_vertical_dependency(monkeypatch):
    import chrona.presentation.layout.surface_composer as surface_composer
    import tests.unit.chrona.presentation.scene.test_relation_entry_acceptance as fixture
    from chrona.presentation.contracts.resources import ViewWindow
    from chrona.presentation.layout.labels import LabelRect
    from chrona.presentation.layout.sources import MeasuredSources, SourceInput
    from chrona.presentation.layout.surface_geometry import bounds_from_rect
    from chrona.presentation.layout.surface_quality import CollisionDomain
    from chrona.presentation.scene.v05_builder import build_scene_input, compose_review_surface
    from tests.unit.chrona.presentation.scene.test_v05_builder import (
        _Font, _manifest, _title_measurement, surface_content,
    )

    monkeypatch.setattr(fixture, "RELATION", {
        "id": "dep", "type": "dependency",
        "from": {"object": "a", "endpoint": "start"},
        "to": {"object": "b", "endpoint": "start"},
    })
    monkeypatch.setattr(fixture, "PLACED", {
        "a": {"start": date(2026, 2, 10), "end": date(2026, 2, 20)},
        "b": {"start": date(2026, 2, 10), "end": date(2026, 2, 14)},
    })
    monkeypatch.setattr(fixture, "WINDOW", ViewWindow("explicit", "2026-02-01", "2026-03-01", 0))
    monkeypatch.setattr(fixture, "PROJECT_BASE", {
        "objects": {"a": {"title": "A", "fields": {"owner": "x"}},
                    "b": {"title": "Long verification name", "fields": {"owner": "x"}}},
        "entities": {}, "relations": [],
    })
    measured = MeasuredSources(
        {"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
        {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
         "timeline.row.minBlockSize": Decimal(160), "timeline.row.paddingBlock": Decimal(0),
         "timeline.mark.blockSize": Decimal(24)},
    )
    project, _placed, _actual, _view, projection = fixture._project()
    manifest = replace(_manifest("title", "table", "timeline", "timeline-axis"),
        relation_entry="side-when-free", row_distribution="fill", relation_max_bends=4,
        relation_max_detour_ratio=6)
    content = surface_content(relations=project["relations"], show_member_labels=False,
        label_placement="plot", label_content=(), label_side="inside", label_overflow="suppress")
    scene_input = build_scene_input(projection=projection, surface_content=content, layout_manifest=manifest,
        resolved_theme=fixture._theme_with_route_fixture_geometry(), font_metrics=_Font(),
        measured_sources=measured, capabilities={"svg": True})
    captured = {}
    actual_coordinator = surface_composer.compose_routes_and_member_labels

    def capture(context):
        captured["context"] = context
        return actual_coordinator(context)

    monkeypatch.setattr(surface_composer, "compose_routes_and_member_labels", capture)
    compose_review_surface(scene_input)
    original_context = captured["context"]
    target = next(mark for mark in original_context.member_labels.marks
                  if mark.placement_id == "planned:b:b")
    anchor = LabelRect(*bounds_from_rect(target.bounds))
    _, timeline_y, _, timeline_height = original_context.member_labels.timeline_bounds
    text_width = 154.0
    centered_bounds = LabelRect(target.start_port[0] - text_width / 2, timeline_y,
        text_width, timeline_height)
    manual_name = LabelRequest("member-label:neutral-b", "b", "Long verification name", anchor,
        ("above",), "text", "plot-label", CollisionDomain("timeline", "overlay"),
        "suppress", bounds=centered_bounds, semantic_id="memberLabel")
    context = replace(original_context, post_route_requests=(manual_name,))

    baseline = plan._trial(context, (), context.post_route_requests)
    chosen = plan.compose_routes_and_member_labels(context)

    assert [item.overflow for item in baseline.members.text] == ["suppressed"]
    assert [item.overflow for item in chosen.members.text] == ["fit"]
    assert chosen.routes.relations[0].relation_id == baseline.routes.relations[0].relation_id
    assert not chosen.routes.relations[0].suppressed
    assert chosen.routes.relations[0].points != baseline.routes.relations[0].points
    assert chosen.routes.relations[0].points[0] == baseline.routes.relations[0].points[0]
    assert chosen.routes.relations[0].points[-1] == baseline.routes.relations[0].points[-1]
    label_bounds = chosen.members.text[0].bounds
    collisions = chosen.obstacles.collisions(ObstacleRect(
        float(label_bounds.inline), float(label_bounds.block),
        float(label_bounds.inline + label_bounds.inline_size),
        float(label_bounds.block + label_bounds.block_size)),
        classes=("dependency-route",), regions=("timeline",))
    assert not collisions
