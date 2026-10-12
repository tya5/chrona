"""One real routing pass and producer-owned counts through Scene and CLI."""
import json

import pytest

from chrona.presentation.layout import surface_lane_route_plan as lane_plan
from chrona.presentation.layout import surface_route_label_plan as label_plan
from chrona.presentation.layout import surface_routes
from chrona.presentation.model.info_diagnostics import RelationRoutingSummary
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
    original_routes = surface_routes.compose_surface_routes
    def observe(context):
        calls.append((context.progress_pass, tuple(item.semantic_id for item in context.text)))
        return original_routes(context)
    monkeypatch.setattr(lane_plan, "compose_surface_routes", observe)
    monkeypatch.setattr(label_plan, "compose_surface_routes", observe)
    results = []
    original_select = surface_routes.select_relation_route
    def select(*args, **kwargs):
        result = original_select(*args, **kwargs)
        results.append(result)
        return result
    monkeypatch.setattr(surface_routes, "select_relation_route", select)
    rendered = sr.render(tmp_path, sr.chain_project(groups=1, per_group=3), presentation=parts)
    infos = [item for item in rendered.info_diagnostics if isinstance(item, RelationRoutingSummary)]
    payloads = [item for item in warning_payloads(rendered) if item["code"] == "I_LAYOUT_RELATION_ROUTING"]
    if policy == "best":
        assert infos == payloads == []
        if lane:
            assert calls[0][0] == "lane-rehearsal"
        return
    assert [name for name, _ in calls] == ["route-label-baseline"]
    assert not ({"memberLabel", "finishDelta"} & set(calls[0][1]))
    assert len(infos) == len(payloads) == 1
    info, payload = infos[0], payloads[0]
    assert info.relation_instances == len(results) == 2
    assert info.shape_settled == sum(item.settled_by_shape and not item.search_used for item in results)
    assert info.fallback_search == sum(item.search_used for item in results)
    assert payload["severity"] == "info"
    assert payload["shapeSettled"] == info.shape_settled
    scene_info = [item for item in rendered.scene.diagnostics if item.startswith("I_LAYOUT_RELATION_ROUTING:")]
    assert scene_info == [info.scene_diagnostic()]
    assert json.loads(scene_info[0].split(":", 1)[1])["fallbackSearch"] == info.fallback_search
    assert rendered.artifact.content.startswith(b"<svg")


@pytest.mark.parametrize("counts", [(1, 1, 1), (0, -1, 0), (True, 0, 0), (1, 0, 1.0)])
def test_summary_rejects_overlapping_negative_and_noninteger_counts(counts):
    with pytest.raises(ValueError, match="E_PRESENTATION_INFO_INVALID"):
        RelationRoutingSummary("table-timeline", *counts)
