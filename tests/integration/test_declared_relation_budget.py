"""Producer-owned budget exhaustion through all real routing passes, Scene and CLI."""
import pytest

from chrona.presentation.layout import surface_lane_route_plan as lane_plan
from chrona.presentation.layout import surface_route_label_plan as label_plan
from chrona.presentation.layout import surface_routes
from chrona.presentation.model.info_diagnostics import RelationSearchBudgetHit
from chrona.usecases.draft_render import warning_payloads
from tests.support import synthetic_review as sr


@pytest.mark.parametrize("lane", [False, True])
def test_budget_hit_facts_survive_all_real_passes_and_project_to_scene_cli(tmp_path, monkeypatch, lane):
    parts = sr.bundle()
    if lane:
        parts["view"] = sr.lane_view(parts["view"])
    parts["layout"]["relationRouting"] = {"maxBends": 4, "maxDetourRatio": 2, "searchBudget": 1}
    original_routes = surface_routes.compose_surface_routes
    seen = []
    def observe(context):
        result = original_routes(context)
        seen.extend(result.routing_info)
        return result
    monkeypatch.setattr(lane_plan, "compose_surface_routes", observe)
    monkeypatch.setattr(label_plan, "compose_surface_routes", observe)
    rendered = sr.render(tmp_path, sr.chain_project(groups=1, per_group=3), presentation=parts)
    facts = [item for item in rendered.info_diagnostics if isinstance(item, RelationSearchBudgetHit)]
    assert facts == seen and facts
    assert all(item.budget == item.expansions == 1 for item in facts)
    passes = {item.pass_name for item in facts}
    assert "route-label-baseline" in passes
    if lane:
        assert "lane-rehearsal" in passes
    assert [item for item in rendered.scene.diagnostics
            if item.startswith("I_LAYOUT_RELATION_SEARCH_BUDGET:")] == [item.scene_diagnostic() for item in facts]
    payloads = [item for item in warning_payloads(rendered) if item["code"] == facts[0].code]
    assert len(payloads) == len(facts)
    for payload, fact in zip(payloads, facts):
        assert payload["severity"] == "info"
        assert {key: payload[key] for key in fact.payload()} == fact.payload()
        assert "search" not in payload


def test_budget_stop_without_admitted_route_preserves_current_suppression(tmp_path):
    parts = sr.bundle()
    # Distinct rows require a bend; the first admitted seed exhausts the
    # declared ceiling and fails the author's zero-bend quality requirement.
    parts["layout"]["relationRouting"] = {"maxBends": 0, "maxDetourRatio": 2, "searchBudget": 1}
    parts["view"]["body"]["visibility"]["relations"]["overflow"] = "suppress"
    rendered = sr.render(tmp_path, sr.chain_project(groups=1, per_group=2), presentation=parts)
    facts = [item for item in rendered.info_diagnostics if isinstance(item, RelationSearchBudgetHit)]
    assert facts and all(item.budget == item.expansions == 1 for item in facts)
    assert any(item.startswith("W_LAYOUT_RELATION_SUPPRESSED") for item in rendered.scene.diagnostics)
    assert not any(primitive.source_kind == "relation" and primitive.kind == "Path"
                   for surface in rendered.scene.surfaces for primitive in surface.primitives)


@pytest.mark.parametrize("budget, expansions", [(0, 0), (2, 1), (True, 1), (1, 1.0)])
def test_budget_hit_rejects_invalid_receipts(budget, expansions):
    with pytest.raises(ValueError, match="E_PRESENTATION_INFO_INVALID"):
        RelationSearchBudgetHit("table-timeline", "relation:r", "relations", budget, expansions)
