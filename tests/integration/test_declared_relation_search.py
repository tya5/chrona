"""Real routing passes and producer-owned counts through Scene and CLI."""
import json

import pytest

from chrona.presentation.layout import surface_route_label_plan as label_plan
from chrona.presentation.layout import surface_routes
from chrona.presentation.model.info_diagnostics import RelationRoutingSummary, RelationSearchBudgetHit
from chrona.usecases.draft_render import warning_payloads
from tests.support import synthetic_review as sr


@pytest.mark.parametrize("lane", [False, True])
@pytest.mark.parametrize("policy", [None, "first-fit", "best"])
def test_declared_policy_controls_real_pass_order_and_info_projection(tmp_path, monkeypatch, lane, policy):
    parts = sr.bundle()
    if lane:
        parts["view"] = sr.lane_view(parts["view"])
    routing = parts["layout"].setdefault("relationRouting", {"maxBends": 4, "maxDetourRatio": 2})
    if policy is not None:
        routing["search"] = policy
    calls = []
    composed = []
    active_pass = [None]
    original_routes = surface_routes.compose_surface_routes
    def observe(context):
        calls.append((context.progress_pass, tuple(item.semantic_id for item in context.text)))
        active_pass[0] = context.progress_pass
        result = original_routes(context)
        composed.append((context.progress_pass, result))
        return result
    monkeypatch.setattr(label_plan, "compose_surface_routes", observe)
    results = []
    original_select = surface_routes.select_relation_route
    def select(*args, **kwargs):
        result = original_select(*args, **kwargs)
        results.append((active_pass[0], kwargs.get("relation_scene_id"), result))
        return result
    monkeypatch.setattr(surface_routes, "select_relation_route", select)
    rendered = sr.render(tmp_path, sr.chain_project(groups=1, per_group=3), presentation=parts)
    infos = [item for item in rendered.info_diagnostics if isinstance(item, RelationRoutingSummary)]
    payloads = [item for item in warning_payloads(rendered) if item["code"] == "I_LAYOUT_RELATION_ROUTING"]
    passes = [name.split(":", 1)[0] for name, _ in calls]
    assert passes == ["route-content-baseline"]
    if policy == "best":
        assert infos == payloads == []
        assert len(composed) == len(calls) == 1
        return
    assert len(composed) == len(calls) == 1
    assert "memberLabel" in calls[0][1]
    assert len(infos) == len(payloads) == len(composed) == len(calls)
    emitted_infos = []
    for pass_name, batch in composed:
        summary, = [item for item in batch.routing_info if isinstance(item, RelationRoutingSummary)]
        emitted_infos.append(summary)
        selected = [(relation_id, item) for name, relation_id, item in results if name == pass_name]
        grouped = {}
        for relation_id, item in selected:
            grouped.setdefault(relation_id, []).append(item)
        assert summary.relation_instances == len(grouped)
        assert summary.relation_instances == sum(not item.suppressed for item in batch.relations)
        assert summary.fallback_search == sum(any(item.search_used for item in attempts)
                                              for attempts in grouped.values())
        shape_settled = 0
        for attempts in grouped.values():
            final = next((item for item in attempts if item.selected_pair is not None), attempts[-1])
            shape_settled += int(final.selected_pair is not None and final.settled_by_shape
                                 and not any(item.search_used for item in attempts))
        assert summary.shape_settled == shape_settled
    assert infos == emitted_infos
    assert all(payload["severity"] == "info" for payload in payloads)
    assert [payload["shapeSettled"] for payload in payloads] == [info.shape_settled for info in infos]
    scene_info = [item for item in rendered.scene.diagnostics if item.startswith("I_LAYOUT_RELATION_ROUTING:")]
    assert scene_info == [info.scene_diagnostic() for info in infos]
    assert [json.loads(item.split(":", 1)[1])["fallbackSearch"] for item in scene_info] == [
        info.fallback_search for info in infos]
    assert rendered.artifact.content.startswith(b"<svg")


@pytest.mark.parametrize("counts", [(1, 1, 1), (0, -1, 0), (True, 0, 0), (1, 0, 1.0)])
def test_summary_rejects_overlapping_negative_and_noninteger_counts(counts):
    with pytest.raises(ValueError, match="E_PRESENTATION_INFO_INVALID"):
        RelationRoutingSummary("table-timeline", *counts)


@pytest.mark.parametrize("lane", [False, True])
@pytest.mark.parametrize("policy", ["first-fit", "best"])
def test_budget_hit_facts_survive_all_real_passes_and_project_to_scene_cli(tmp_path, monkeypatch, lane, policy):
    from chrona.presentation.layout import routing
    parts = sr.bundle()
    if lane:
        parts["view"] = sr.lane_view(parts["view"])
    parts["layout"]["relationRouting"] = {"maxBends": 4, "maxDetourRatio": 2,
                                           "search": policy, "searchBudget": 1}
    # Negative control: force the actual fallback iterator rather than a shape.
    monkeypatch.setattr(routing, "relation_shape_candidates", lambda *args, **kwargs: iter(()))
    original_routes = surface_routes.compose_surface_routes
    seen = []
    compose_passes = []
    def observe(context):
        compose_passes.append(context.progress_pass)
        result = original_routes(context)
        seen.extend(item for item in result.routing_info if isinstance(item, RelationSearchBudgetHit))
        return result
    monkeypatch.setattr(label_plan, "compose_surface_routes", observe)
    rendered = sr.render(tmp_path, sr.chain_project(groups=1, per_group=3), presentation=parts)
    facts = [item for item in rendered.info_diagnostics if isinstance(item, RelationSearchBudgetHit)]
    assert facts == seen and facts
    assert all(item.budget == item.expansions == 1 for item in facts)
    passes = {item.pass_name.split(":", 1)[0] for item in facts}
    assert passes <= set(compose_passes)
    assert compose_passes == ["route-content-baseline"]
    assert passes == {"route-content-baseline"}
    assert [item for item in rendered.scene.diagnostics
            if item.startswith("I_LAYOUT_RELATION_SEARCH_BUDGET:")] == [item.scene_diagnostic() for item in facts]
    payloads = [item for item in warning_payloads(rendered) if item["code"] == facts[0].code]
    assert len(payloads) == len(facts)
    for payload, fact in zip(payloads, facts):
        assert payload["severity"] == "info"
        assert {key: payload[key] for key in fact.payload()} == fact.payload()


@pytest.mark.parametrize("budget, expansions", [(0, 0), (2, 1), (True, 1), (1, 1.0)])
def test_budget_hit_rejects_invalid_receipts(budget, expansions):
    with pytest.raises(ValueError, match="E_PRESENTATION_INFO_INVALID"):
        RelationSearchBudgetHit("table-timeline", "relation:r", "relations", budget, expansions)
