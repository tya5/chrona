"""Single-candidate reservation, selective release and no-extra-unroutable safety."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.labels import LabelRect, LabelRequest
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.surface_member_labels import SurfaceMemberLabelsBatch
from chrona.presentation.layout.surface_quality import CollisionDomain, TextPlacement
from chrona.presentation.layout.surface_routes import SurfaceRelationLabelsBatch, SurfaceRoutesBatch, SurfaceRoutesContext
from chrona.presentation.layout import surface_route_label_plan as plan
from chrona.presentation.model.info_diagnostics import RelationSearchBudgetHit, RelationResolutionInfo, RelationResolutionStage


def _request(identifier):
    return LabelRequest(identifier, identifier, "Name", LabelRect(0, 0, 4, 4),
        ("end", "start"), "text", "plot-label", CollisionDomain("timeline", "overlay"),
        "suppress", semantic_id="memberLabel")


def _text(identifier):
    x = 10 if identifier == "a" else 60
    return TextPlacement(identifier, identifier, "Name", Rect(Decimal(x), Decimal(10), Decimal(20), Decimal(10)),
        "text", semantic_id="memberLabel", collision_domain=CollisionDomain("timeline", "overlay"))


def _install(monkeypatch, *, repair=False, retry_bad=False, lose_relation_label=False, reference_bad=False):
    calls = []
    required = SurfaceObstacle("required", "text", "timeline", ObstacleRect(120, 30, 140, 40))
    clean = SurfaceObstacleIndex()
    clean.add(required)
    facts = []

    def names(_context, requests, obstacles, *, reserve_only=False):
        texts = []
        for request in requests:
            text = _text(request.placement_id)
            box = ObstacleRect(float(text.bounds.inline), 10, float(text.bounds.inline + 20), 20)
            if not reserve_only and obstacles.collisions(box, classes=("dependency-route",)):
                texts.append(replace(text, overflow="suppressed", required=False))
                continue
            obstacles.add(SurfaceObstacle(text.placement_id, "text", "timeline", box))
            obstacles.add(SurfaceObstacle(f"label-footprint:{text.placement_id}", "label-visual", "timeline", box))
            texts.append(text)
        return SurfaceMemberLabelsBatch(tuple(texts), (), (), (), (), (), (), frozenset())

    def routes(context):
        calls.append(context.progress_pass)
        assert context.obstacles.has(required.placement_id)
        assert not any(item.required for item in context.text)  # only provisional optional text
        suppressed = ((repair and context.obstacles.has("a"))
                      or (retry_bad and context.progress_pass == "route-label-release")
                      or (reference_bad and context.progress_pass == "route-label-reference"))
        relation = SimpleNamespace(relation_id="relation:r", suppressed=suppressed)
        if not suppressed:
            y = 15 if repair else 50
            context.obstacles.add(SurfaceObstacle("relation:r:segment:0", "dependency-route", "timeline",
                ObstacleSegment((0, y), (50, y), 1)))
        fact = RelationSearchBudgetHit("table-timeline", "relation:r", context.progress_pass, 1, 1)
        facts.append(fact)
        resolution = (RelationResolutionInfo("table-timeline", "relation:r", RelationResolutionStage.TEXT, False),) if suppressed else ()
        return SurfaceRoutesBatch((relation,), (), {}, {}, {}, (), (fact,), resolution)

    def relation_labels(context, _routes):
        if lose_relation_label and context.progress_pass == "route-label-release":
            return SurfaceRelationLabelsBatch((), (), ())
        return SurfaceRelationLabelsBatch((replace(_text("relation-label:r"), semantic_id="relationLabel"),), (), ())

    monkeypatch.setattr(plan, "place_member_labels", names)
    monkeypatch.setattr(plan, "compose_surface_routes", routes)
    monkeypatch.setattr(plan, "place_relation_labels", relation_labels)
    context = plan.RouteLabelPlanContext(None, (_request("a"), _request("b")), (), clean,
        lambda obstacles, texts: SurfaceRoutesContext(None, None, (), (), (), (), (0, 0, 200, 100),
            None, {}, texts, obstacles))
    return context, calls, facts


def test_normal_reserved_route_needs_one_trial_and_emits_no_ghosts(monkeypatch):
    context, calls, facts = _install(monkeypatch)
    result = plan.compose_routes_and_member_labels(context)
    assert calls == ["route-label-reserved"]
    assert [item.overflow for item in result.members.text] == ["fit", "fit"]
    assert result.routes.routing_info == tuple(facts)
    assert result.obstacles.has("a") and not context.clean_obstacles.has("a")
    assert all(item.required for item in result.members.text)


def test_releases_only_reference_ink_blockers_then_revalidates_names(monkeypatch):
    context, calls, facts = _install(monkeypatch, repair=True)
    result = plan.compose_routes_and_member_labels(context)
    assert calls == ["route-label-reserved", "route-label-reference", "route-label-release"]
    assert not result.routes.relations[0].suppressed
    assert [item.overflow for item in result.members.text] == ["suppressed", "fit"]
    assert not result.obstacles.has("a") and not result.obstacles.has("label-footprint:a")
    assert result.obstacles.has("b") and result.obstacles.has("required")
    assert result.routes.routing_info == tuple(facts)
    assert not result.routes.resolution_info  # discarded trial's resolution is not output


@pytest.mark.parametrize("reason", ("route", "relation-label"))
def test_reference_is_safety_net_when_selective_retry_regresses(monkeypatch, reason):
    context, calls, facts = _install(monkeypatch, repair=True,
        retry_bad=reason == "route", lose_relation_label=reason == "relation-label")
    result = plan.compose_routes_and_member_labels(context)
    assert len(calls) == 3
    assert not result.routes.relations[0].suppressed
    assert result.relation_labels.text[0].placement_id == "relation-label:r"
    assert result.routes.routing_info == tuple(facts)
    assert not result.routes.resolution_info


def test_reference_does_not_release_arbitrary_boxes_if_route_is_already_unroutable(monkeypatch):
    context, calls, _facts = _install(monkeypatch, repair=True, reference_bad=True)
    result = plan.compose_routes_and_member_labels(context)
    assert len(calls) == 2
    assert result.routes.relations[0].suppressed
    assert [item.overflow for item in result.members.text] == ["fit", "fit"]


def test_all_released_reference_is_reused_without_third_replay(monkeypatch):
    context, calls, _facts = _install(monkeypatch, repair=True)
    context = replace(context, post_route_requests=context.post_route_requests[:1])
    result = plan.compose_routes_and_member_labels(context)
    assert len(calls) == 2
    assert not result.routes.relations[0].suppressed


def test_crossing_one_reserve_cannot_release_a_different_routes_reserve(monkeypatch):
    context, calls, _facts = _install(monkeypatch)

    def routes(route_context):
        calls.append(route_context.progress_pass)
        # r crosses A's provisional box. s does not cross B when B is reserved,
        # but its unreserved reference does; s must not enter r's release set.
        for identifier, start, end in (("r", (0, 15), (50, 15)),
                ("s", (55, 50 if route_context.obstacles.has("b") else 15),
                      (100, 50 if route_context.obstacles.has("b") else 15))):
            route_context.obstacles.add(SurfaceObstacle(f"relation:{identifier}:segment:0",
                "dependency-route", "timeline", ObstacleSegment(start, end, 1)))
        return SurfaceRoutesBatch(tuple(SimpleNamespace(relation_id=f"relation:{identifier}", suppressed=False)
            for identifier in ("r", "s")), (), {}, {}, {}, ())

    monkeypatch.setattr(plan, "compose_surface_routes", routes)
    result = plan.compose_routes_and_member_labels(context)
    assert calls == ["route-label-reserved", "route-label-reference", "route-label-release"]
    assert [item.overflow for item in result.members.text] == ["suppressed", "fit"]
    assert result.obstacles.has("b")
    assert not result.obstacles.has("a")


def test_status_keeps_stable_stub_identity_and_typed_recovery_order():
    fragments = tuple(SimpleNamespace(relation_id=f"relation:r:stub-{endpoint}",
        fragment_endpoint=endpoint, suppressed=False) for endpoint in ("source", "target"))
    batch = SurfaceRoutesBatch(fragments, (), {}, {}, {}, (), resolution_info=(
        RelationResolutionInfo("table-timeline", "relation:r", RelationResolutionStage.STUB, False),))
    assert plan._relation_status(batch) == {"relation:r": 5}
    text_recovery = replace(batch, relations=(SimpleNamespace(relation_id="relation:r", suppressed=False),),
        resolution_info=(RelationResolutionInfo("table-timeline", "relation:r", RelationResolutionStage.TEXT, False),))
    assert plan._relation_status(text_recovery) == {"relation:r": 2}


@pytest.mark.parametrize("search", ("first-fit", "best"))
def test_real_owners_reserve_centered_name_before_rerouting_vertical_dependency(monkeypatch, search):
    import chrona.presentation.layout.surface_composer as surface_composer
    import tests.unit.chrona.presentation.scene.test_relation_entry_acceptance as fixture
    from chrona.presentation.contracts.resources import ViewWindow
    from chrona.presentation.layout.sources import MeasuredSources, SourceInput
    from chrona.presentation.layout.surface_geometry import bounds_from_rect
    from chrona.presentation.surface_pipeline import compose_review_surface
    from tests.unit.chrona.presentation.scene.test_v05_builder import (
        _Font, _manifest, _title_measurement, build_surface_input, surface_content,
    )
    monkeypatch.setattr(fixture, "RELATION", {"id": "dep", "type": "dependency",
        "from": {"object": "a", "endpoint": "start"}, "to": {"object": "b", "endpoint": "start"}})
    monkeypatch.setattr(fixture, "PLACED", {
        "a": {"start": date(2026, 2, 10), "end": date(2026, 2, 20)},
        "b": {"start": date(2026, 2, 10), "end": date(2026, 2, 14)}})
    monkeypatch.setattr(fixture, "WINDOW", ViewWindow("explicit", "2026-02-01", "2026-03-01", 0))
    monkeypatch.setattr(fixture, "PROJECT_BASE", {"objects": {
        "a": {"title": "A", "fields": {"owner": "x"}},
        "b": {"title": "Long verification name", "fields": {"owner": "x"}}}, "entities": {}, "relations": []})
    measured = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
        {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
         "timeline.row.minBlockSize": Decimal(160), "timeline.row.paddingBlock": Decimal(0),
         "timeline.mark.blockSize": Decimal(24)})
    project, _placed, _actual, _view, projection = fixture._project()
    manifest = replace(_manifest("title", "table", "timeline", "timeline-axis"),
        relation_entry="side-when-free", row_distribution="fill", relation_max_bends=4,
        relation_max_detour_ratio=6, relation_search=search)
    content = surface_content(relations=project["relations"], show_member_labels=False,
        label_placement="plot", label_content=(), label_side="inside", label_overflow="suppress")
    scene_input = build_surface_input(projection=projection, surface_content=content, layout_manifest=manifest,
        resolved_theme=fixture._theme_with_route_fixture_geometry(), font_metrics=_Font(),
        measured_sources=measured, capabilities={"svg": True})
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
    name = LabelRequest("member-label:neutral-b", "b", "Long verification name",
        LabelRect(*bounds_from_rect(target.bounds)), ("above",), "text", "plot-label",
        CollisionDomain("timeline", "overlay"), "suppress",
        bounds=LabelRect(target.start_port[0] - 77, y, 154, height), semantic_id="memberLabel")
    context = replace(context, post_route_requests=(name,))
    baseline = plan._trial(context, (), context.post_route_requests)
    chosen = plan.compose_routes_and_member_labels(context)
    assert [item.overflow for item in baseline.members.text] == ["suppressed"]
    assert [item.overflow for item in chosen.members.text] == ["fit"]
    assert not chosen.routes.relations[0].suppressed
    assert chosen.routes.relations[0].relation_id == baseline.routes.relations[0].relation_id
    assert chosen.routes.relations[0].points != baseline.routes.relations[0].points
    assert chosen.routes.relations[0].points[0] == baseline.routes.relations[0].points[0]
    assert chosen.routes.relations[0].points[-1] == baseline.routes.relations[0].points[-1]
    bounds = chosen.members.text[0].bounds
    assert not chosen.obstacles.collisions(ObstacleRect(float(bounds.inline), float(bounds.block),
        float(bounds.inline + bounds.inline_size), float(bounds.block + bounds.block_size)),
        classes=("dependency-route",), regions=("timeline",))
