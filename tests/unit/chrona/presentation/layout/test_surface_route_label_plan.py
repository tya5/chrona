"""Bounded member-label recovery and completed-plan preservation safety."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.labels import LabelRect, LabelRequest
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.surface_annotations import SurfaceAnnotationBatch
from chrona.presentation.layout.surface_member_labels import MemberLabelReservation, SurfaceMemberLabelsBatch
from chrona.presentation.layout.surface_quality import CollisionDomain, PathCommand, TextPlacement
from chrona.presentation.layout.surface_routes import (
    SurfaceRelationLabelsBatch, SurfaceRoutesBatch, SurfaceRoutesContext, TerminalLabelPlacementError,
)
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


def _reservation(identifier):
    text = _text(identifier)
    left = float(text.bounds.inline)
    box = ObstacleRect(left, 10, left + 20, 20)
    return MemberLabelReservation(text, (
        SurfaceObstacle(identifier, "text", "timeline", box),
        SurfaceObstacle(f"label-footprint:{identifier}", "label-visual", "timeline", box),
    ))


def _reservation_at(identifier, bounds):
    left, top, right, bottom = bounds
    text = replace(_text(identifier), bounds=Rect(Decimal(str(left)), Decimal(str(top)),
        Decimal(str(right - left)), Decimal(str(bottom - top))))
    geometry = ObstacleRect(left, top, right, bottom)
    return MemberLabelReservation(text, (
        SurfaceObstacle(identifier, "text", "timeline", geometry),
        SurfaceObstacle(f"label-footprint:{identifier}", "label-visual", "timeline", geometry),
    ))


def _annotations(*, text=(), shapes=(), relations=(), icons=(), decisions=()):
    return SurfaceAnnotationBatch(tuple(text), tuple(shapes), tuple(relations), tuple(icons), tuple(decisions),
        (), (), (), frozenset(), frozenset(), frozenset())


def _empty_annotations():
    return _annotations()


def _assert_selected_inventory(result, expected, facts):
    assert result.obstacles is expected.obstacles
    assert result.members is expected.members
    assert result.relation_labels is expected.relation_labels
    assert result.routes.relations == expected.routes.relations
    assert result.routes.visible_route_fallbacks == expected.routes.visible_route_fallbacks
    assert result.routes.resolution_info == expected.routes.resolution_info
    assert result.routes.diagnostics == expected.routes.diagnostics
    assert result.routes.routing_info == tuple(facts)


def _install(monkeypatch, *, repair=False, retry_bad=False, lose_member_label=False,
             lose_relation_label=False, change_member_content=False,
             change_relation_content=False):
    calls = []
    name_calls = []
    required = SurfaceObstacle("required", "text", "timeline", ObstacleRect(120, 30, 140, 40))
    clean = SurfaceObstacleIndex()
    clean.add(required)
    facts = []

    def names(_context, requests, obstacles, *, reserve_only=False):
        name_calls.append(tuple(item.placement_id for item in requests))
        texts = []
        blocked = []
        for request in requests:
            text = _text(request.placement_id)
            box = ObstacleRect(float(text.bounds.inline), 10, float(text.bounds.inline + 20), 20)
            if not reserve_only and obstacles.collisions(box, classes=("dependency-route",)):
                texts.append(replace(text, overflow="suppressed", required=False))
                blocked.append(_reservation(request.placement_id))
                continue
            if lose_member_label and request.placement_id == "b" and len(name_calls) > 1:
                texts.append(replace(text, overflow="suppressed", required=False))
                continue
            if change_member_content and request.placement_id == "b" and len(name_calls) > 1:
                text = replace(text, content="Changed member name")
            obstacles.add(SurfaceObstacle(text.placement_id, "text", "timeline", box))
            obstacles.add(SurfaceObstacle(f"label-footprint:{text.placement_id}", "label-visual", "timeline", box))
            texts.append(text)
        return SurfaceMemberLabelsBatch(tuple(texts), (), (), (), (), (), (), frozenset(),
                                        route_blocked_candidates=tuple(blocked))

    def routes(context):
        calls.append(context.progress_pass)
        assert context.obstacles.has(required.placement_id)
        if context.progress_pass == "route-label-baseline":
            assert not context.label_repair_obstacle_ids
        if repair and context.progress_pass == "route-label-recovery":
            assert context.obstacles.has("b")
            assert {"b", "label-footprint:b"} <= context.required_label_obstacle_ids
            assert {"a", "label-footprint:a"} <= context.required_label_obstacle_ids
            assert context.label_repair_obstacle_ids == {"a", "label-footprint:a"}
        suppressed = retry_bad and context.progress_pass == "route-label-recovery"
        relation = SimpleNamespace(relation_id="relation:r", suppressed=suppressed)
        if not suppressed:
            y = 15 if repair and not context.obstacles.has("a") else 50
            context.obstacles.add(SurfaceObstacle("relation:r:segment:0", "dependency-route", "timeline",
                ObstacleSegment((0, y), (50, y), 1)))
        fact = RelationSearchBudgetHit("table-timeline", "relation:r", context.progress_pass, 1, 1)
        facts.append(fact)
        resolution = (RelationResolutionInfo("table-timeline", "relation:r", RelationResolutionStage.TEXT, False),) if suppressed else ()
        return SurfaceRoutesBatch((relation,), (), {}, {}, {}, (), (fact,), resolution)

    def relation_labels(context, _routes, *, terminal=None):
        if terminal:
            return SurfaceRelationLabelsBatch((), (), ())
        if lose_relation_label and context.progress_pass == "route-label-recovery":
            return SurfaceRelationLabelsBatch((), (), ())
        text = replace(_text("relation-label:r"), semantic_id="relationLabel")
        if change_relation_content and context.progress_pass == "route-label-recovery":
            text = replace(text, content="Changed relation label")
        return SurfaceRelationLabelsBatch((text,), (), ())

    monkeypatch.setattr(plan, "place_member_labels", names)
    monkeypatch.setattr(plan, "compose_surface_routes", routes)
    monkeypatch.setattr(plan, "place_relation_labels", relation_labels)
    context = plan.RouteLabelPlanContext(None, (_request("a"), _request("b")), (), clean,
        lambda obstacles, texts: SurfaceRoutesContext(None, None, (), (), (), (), (0, 0, 200, 100),
            None, {}, texts, obstacles))
    return context, calls, facts, name_calls


def test_unblocked_baseline_needs_one_trial_and_emits_no_ghosts(monkeypatch):
    context, calls, facts, _name_calls = _install(monkeypatch)
    options = plan.compose_routes_and_member_labels(context)
    result, annotations = plan.select_completed_route_label_plan(options, _empty_annotations())
    assert options.retry is None and calls == ["route-label-baseline"]
    assert [item.overflow for item in result.members.text] == ["fit", "fit"]
    _assert_selected_inventory(result, options.first, facts)
    assert result.obstacles.has("a") and not context.clean_obstacles.has("a")
    assert annotations == _empty_annotations()


def test_terminal_stub_text_is_reserved_before_names_and_ordinary_labels_follow(monkeypatch):
    context, _calls, _facts, _name_calls = _install(monkeypatch)
    events = []

    def terminal_labels(route_context, _routes, *, terminal=None):
        if terminal:
            events.append("terminal")
            text = replace(_text("relation-label:stub"), semantic_id="relationLabel")
            route_context.obstacles.add(SurfaceObstacle("relation-label:stub", "text", "timeline",
                ObstacleRect(35, 10, 55, 20)))
            route_context.obstacles.add(SurfaceObstacle("label-footprint:relation-label:stub",
                "label-visual", "timeline", ObstacleRect(35, 10, 55, 20)))
            return SurfaceRelationLabelsBatch((text,), (), ())
        events.append("ordinary")
        assert route_context.obstacles.has("a")
        return SurfaceRelationLabelsBatch((), (), ())

    original_names = plan.place_member_labels

    def names(label_context, requests, obstacles, *, reserve_only=False):
        events.append("members")
        assert obstacles.has("relation-label:stub")
        assert obstacles.has("label-footprint:relation-label:stub")
        return original_names(label_context, requests, obstacles, reserve_only=reserve_only)

    monkeypatch.setattr(plan, "place_relation_labels", terminal_labels)
    monkeypatch.setattr(plan, "place_member_labels", names)
    result = plan._trial(context, (), context.post_route_requests)

    assert events == ["terminal", "members", "ordinary"]
    assert any(item.placement_id == "relation-label:stub" for item in result.relation_labels.text)
    assert result.obstacles.has("a")


def test_retry_terminal_label_failure_keeps_baseline_and_all_route_receipts(monkeypatch):
    context, calls, facts, _name_calls = _install(monkeypatch, repair=True)
    original = plan.place_relation_labels

    def fail_retry_terminal(route_context, routes, *, terminal=None):
        if terminal and route_context.progress_pass == "route-label-recovery":
            raise TerminalLabelPlacementError("relation-label:stub-source", routes)
        return original(route_context, routes, terminal=terminal)

    monkeypatch.setattr(plan, "place_relation_labels", fail_retry_terminal)
    options = plan.compose_routes_and_member_labels(context)

    assert calls == ["route-label-baseline", "route-label-recovery"]
    assert options.retry is None
    assert options.first.routes.routing_info == tuple(facts)
    selected, _annotations = plan.select_completed_route_label_plan(options, _empty_annotations())
    assert selected is options.first


def test_baseline_terminal_failure_is_not_suppressed_or_retried(monkeypatch):
    context, calls, _facts, _name_calls = _install(monkeypatch, repair=True)

    def fail_terminal(_context, routes, *, terminal=None):
        raise TerminalLabelPlacementError("relation-label:blocked-terminal", routes)

    monkeypatch.setattr(plan, "place_relation_labels", fail_terminal)
    with pytest.raises(TerminalLabelPlacementError) as caught:
        plan.compose_routes_and_member_labels(context)
    assert caught.value.placement_id == "relation-label:blocked-terminal"
    assert calls == ["route-label-baseline"]


def test_unrelated_retry_errors_are_not_hidden(monkeypatch):
    context, calls, _facts, _name_calls = _install(monkeypatch, repair=True)
    original = plan.place_relation_labels

    def fail_retry(route_context, routes, *, terminal=None):
        if terminal and route_context.progress_pass == "route-label-recovery":
            raise ValueError("unrelated broken geometry")
        return original(route_context, routes, terminal=terminal)

    monkeypatch.setattr(plan, "place_relation_labels", fail_retry)
    with pytest.raises(ValueError, match="unrelated broken geometry"):
        plan.compose_routes_and_member_labels(context)
    assert calls == ["route-label-baseline", "route-label-recovery"]


def test_one_recovery_reserves_only_the_route_blocked_candidate_and_emits_no_ghosts(monkeypatch):
    context, calls, facts, name_calls = _install(monkeypatch, repair=True)
    options = plan.compose_routes_and_member_labels(context)
    assert options.retry is not None
    result, annotations = plan.select_completed_route_label_plan(options, _empty_annotations(), _empty_annotations())
    assert calls == ["route-label-baseline", "route-label-recovery"]
    assert name_calls == [("a", "b"), ("b", "a")]
    assert not result.routes.relations[0].suppressed
    assert [item.overflow for item in result.members.text] == ["fit", "fit"]
    assert result.obstacles.has("a") and result.obstacles.has("label-footprint:a")
    assert result.obstacles.has("b") and result.obstacles.has("required")
    assert result.routes.routing_info == tuple(facts)
    assert not result.routes.resolution_info
    assert not context.clean_obstacles.has("a")
    assert not options.first.obstacles.has("a")  # no provisional first-pass box leaks
    assert result.obstacles is options.retry.obstacles
    assert result.members is options.retry.members
    assert result.relation_labels is options.retry.relation_labels
    assert annotations == _empty_annotations()


def test_proposal_admission_uses_later_completed_visible_text_and_keeps_declared_alternative():
    obstacles = SurfaceObstacleIndex()
    # This is a later-completed variance label retained by the retry. CDR's
    # lower-cost `end` rung overlaps it; its declared `start` rung is clear.
    obstacles.extend((
        SurfaceObstacle("variance:bus-test", "text", "timeline",
                        ObstacleRect(657.769, 302.6, 691.369, 322.2)),
        SurfaceObstacle("label-footprint:variance:bus-test", "label-visual", "timeline",
                        ObstacleRect(657.769, 302.6, 691.369, 322.2)),
    ))
    first = SimpleNamespace(obstacles=obstacles)
    proposals = (_reservation_at("member-label:cdr", (616.933, 315.6, 766.678, 336.6)),
                 _reservation_at("member-label:cdr", (449.688, 315.6, 599.433, 336.6)))

    admitted = plan._admissible_reservations(first, proposals)

    assert len(admitted) == 1
    assert admitted[0].obstacles[0].geometry == ObstacleRect(449.688, 315.6, 599.433, 336.6)
    obstacles.add(SurfaceObstacle("later-text", "text", "timeline", ObstacleRect(440, 310, 610, 340)))
    assert plan._admissible_reservations(first, proposals) == ()


@pytest.mark.parametrize("reason", ("route", "member-label", "relation-label"))
def test_completed_candidate_falls_back_to_the_unchanged_baseline_when_it_regresses(monkeypatch, reason):
    context, calls, facts, _name_calls = _install(monkeypatch, repair=True, retry_bad=reason == "route",
        lose_member_label=reason == "member-label", lose_relation_label=reason == "relation-label")
    options = plan.compose_routes_and_member_labels(context)
    result, annotations = plan.select_completed_route_label_plan(options, _empty_annotations(), _empty_annotations())
    assert len(calls) == 2 and options.retry is not None
    _assert_selected_inventory(result, options.first, facts)
    assert not result.obstacles.has("a") and not result.obstacles.has("label-footprint:a")
    assert not context.clean_obstacles.has("a")
    assert result.routes.relations[0].suppressed is False
    assert result.relation_labels.text[0].placement_id == "relation-label:r"
    assert annotations == _empty_annotations()


@pytest.mark.parametrize("changed", ("member-label", "relation-label"))
def test_candidate_with_same_visible_label_identity_but_changed_content_falls_back(monkeypatch, changed):
    context, _calls, facts, _name_calls = _install(monkeypatch, repair=True,
        change_member_content=changed == "member-label",
        change_relation_content=changed == "relation-label")
    options = plan.compose_routes_and_member_labels(context)
    assert options.retry is not None
    result, _annotations = plan.select_completed_route_label_plan(
        options, _empty_annotations(), _empty_annotations())
    _assert_selected_inventory(result, options.first, facts)
    if changed == "member-label":
        assert next(item for item in result.members.text if item.placement_id == "b").content == "Name"
    else:
        assert result.relation_labels.text[0].content == "Name"


@pytest.mark.parametrize("lost", ("note", "callout", "connector"))
def test_candidate_that_loses_a_visible_annotation_component_falls_back(monkeypatch, lost):
    context, calls, facts, _name_calls = _install(monkeypatch, repair=True)
    options = plan.compose_routes_and_member_labels(context)
    assert options.retry is not None and len(calls) == 2
    if lost == "note":
        first = _annotations(text=(SimpleNamespace(placement_id="annotation-note-text:n", content="Note", overflow="fit"),))
        retry = _empty_annotations()
    elif lost == "callout":
        first = _annotations(shapes=(SimpleNamespace(placement_id="annotation-callout:n", suppressed=False),))
        retry = _empty_annotations()
    else:
        first = _annotations(relations=(SimpleNamespace(relation_id="annotation-connector:n", suppressed=False),))
        retry = _empty_annotations()
    result, selected_annotations = plan.select_completed_route_label_plan(options, first, retry)
    _assert_selected_inventory(result, options.first, facts)
    assert selected_annotations is first
    assert not result.obstacles.has("a")


@pytest.mark.parametrize("topology", ("disconnected", "later-rung", "changed-ladder", "unknown-rung"))
def test_candidate_cannot_drop_a_connected_annotation_or_move_it_later(monkeypatch, topology):
    context, calls, facts, _name_calls = _install(monkeypatch, repair=True)
    options = plan.compose_routes_and_member_labels(context)
    assert options.retry is not None and len(calls) == 2
    first_decision = SimpleNamespace(decision_id="annotation:n", outcome="placed",
        selected_topology="direct-tail", requested_ladder=("plot-near", "rail"), selected_rung="plot-near")
    retry_decision = SimpleNamespace(decision_id="annotation:n", outcome="placed",
        selected_topology=None if topology == "disconnected" else "direct-tail",
        requested_ladder=(("plot-near", "other") if topology == "changed-ladder"
                          else ("plot-near", "rail")),
        selected_rung=("rail" if topology == "later-rung" else
                       "unknown" if topology == "unknown-rung" else "plot-near"))
    first = _annotations(text=(SimpleNamespace(placement_id="annotation-note-text:n", content="Note", overflow="fit"),),
                         decisions=(first_decision,))
    retry = _annotations(text=(SimpleNamespace(placement_id="annotation-note-text:n", content="Note", overflow="fit"),),
                         decisions=(retry_decision,))
    result, selected_annotations = plan.select_completed_route_label_plan(options, first, retry)
    _assert_selected_inventory(result, options.first, facts)
    assert selected_annotations is first


def test_legacy_annotation_decision_without_a_known_selected_rung_remains_accepted(monkeypatch):
    context, _calls, facts, _name_calls = _install(monkeypatch, repair=True)
    options = plan.compose_routes_and_member_labels(context)
    first_decision = SimpleNamespace(decision_id="annotation:n", outcome="placed",
        selected_topology=None, requested_ladder=(), selected_rung=None)
    retry_decision = SimpleNamespace(decision_id="annotation:n", outcome="placed",
        selected_topology=None, requested_ladder=("rail",), selected_rung="rail")
    first = _annotations(decisions=(first_decision,))
    retry = _annotations(decisions=(retry_decision,))
    result, selected_annotations = plan.select_completed_route_label_plan(options, first, retry)
    _assert_selected_inventory(result, options.retry, facts)
    assert selected_annotations is retry


def test_candidate_with_same_visible_note_identity_but_changed_content_falls_back(monkeypatch):
    context, _calls, facts, _name_calls = _install(monkeypatch, repair=True)
    options = plan.compose_routes_and_member_labels(context)
    first = _annotations(text=(SimpleNamespace(placement_id="annotation-note-text:n",
        content="Keep this note", overflow="fit"),))
    retry = _annotations(text=(SimpleNamespace(placement_id="annotation-note-text:n",
        content="Changed note", overflow="fit"),))
    result, selected_annotations = plan.select_completed_route_label_plan(options, first, retry)
    _assert_selected_inventory(result, options.first, facts)
    assert selected_annotations is first


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
    options = plan.compose_routes_and_member_labels(context)
    assert options.retry is not None
    first = options.first
    retry = options.retry
    assert [item.overflow for item in baseline.members.text] == ["suppressed"]
    assert [item.overflow for item in retry.members.text] == ["fit"]
    chosen, _annotations = plan.select_completed_route_label_plan(options, _empty_annotations(), _empty_annotations())
    assert [item.overflow for item in chosen.members.text] == ["fit"]
    assert not chosen.routes.relations[0].suppressed
    assert chosen.routes.relations[0].relation_id == baseline.routes.relations[0].relation_id
    assert chosen.routes.relations[0].points != baseline.routes.relations[0].points
    assert chosen.routes.relations[0].points[0] == baseline.routes.relations[0].points[0]
    assert chosen.routes.relations[0].points[-1] == baseline.routes.relations[0].points[-1]
    assert first.routes.relations[0].points == baseline.routes.relations[0].points
    logical_routes = {item.relation_id.removesuffix(
        f":stub-{getattr(item, 'fragment_endpoint', None)}")
        if getattr(item, "fragment_endpoint", None) else item.relation_id
        for item in chosen.routes.relations if not item.suppressed}
    route_paint = chosen.obstacles.select(classes=("dependency-route",))
    assert len(route_paint) > 1
    assert route_paint and all(item.route_owner_id in logical_routes for item in route_paint)
    bounds = chosen.members.text[0].bounds
    assert not chosen.obstacles.collisions(ObstacleRect(float(bounds.inline), float(bounds.block),
        float(bounds.inline + bounds.inline_size), float(bounds.block + bounds.block_size)),
        classes=("dependency-route",), regions=("timeline",))


def test_completed_stub_fragments_and_flattened_arcs_keep_one_logical_route_owner():
    from chrona.presentation.layout.surface_routes import _register_route_paint

    index = SurfaceObstacleIndex()
    owner = "relation:logical-instance"
    curve = (PathCommand("move", ((0, 0),)), PathCommand("line", ((10, 0),)),
        PathCommand("quadratic", ((12, 0), (10, 2))), PathCommand("line", ((10, 10),)))
    _register_route_paint(index, f"{owner}:stub-source", ((0, 0), (10, 0), (10, 10)), 1,
        curve, route_owner_id=owner)
    _register_route_paint(index, f"{owner}:stub-target", ((20, 0), (30, 0), (30, 10)), 1,
        tuple(PathCommand(command.kind, tuple((x + 20, y) for x, y in command.points))
              for command in curve), route_owner_id=owner)

    route_paint = index.select(classes=("dependency-route",))
    assert any(":stub-source:segment:" in item.placement_id for item in route_paint)
    assert any(":stub-target:segment:" in item.placement_id for item in route_paint)
    assert any(":arc:" in item.placement_id for item in route_paint)
    assert {item.route_owner_id for item in route_paint} == {owner}
