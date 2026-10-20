"""Omitted geometry never deletes a dependency from the source ledger."""
from datetime import date

import pytest

from chrona.presentation.layout import surface_routes
from tests.integration.test_window_row_admission_render import _parts
from tests.support import synthetic_review as sr


@pytest.mark.parametrize("lanes", [False, True], ids=["automatic", "fixed-lanes"])
def test_compacted_rows_keep_every_relation_with_truthful_omission_proof(tmp_path, monkeypatch, lanes):
    objects = {
        "before": sr.span("before", date(2026, 3, 1), 4),
        "inside": sr.span("inside", date(2026, 3, 12), 4),
        "after": sr.span("after", date(2026, 3, 24), 4),
    }
    edges = [("before", "inside"), ("inside", "after"), ("before", "after")]
    source = sr.project(objects, [
        {"id": f"dep-{i}", "type": "dependency", "lag": "0d",
         "from": {"object": left, "endpoint": "end"},
         "to": {"object": right, "endpoint": "start"}}
        for i, (left, right) in enumerate(edges)
    ])
    batches = []
    compose = surface_routes.compose_surface_routes

    def capture(context):
        result = compose(context)
        batches.append(result)
        return result

    monkeypatch.setattr("chrona.presentation.layout.surface_route_label_plan.compose_surface_routes", capture)
    monkeypatch.setattr("chrona.presentation.layout.surface_lane_route_plan.compose_surface_routes", capture)
    monkeypatch.setattr(surface_routes, "select_relation_route",
                        lambda *a, **k: pytest.fail("omitted endpoints must not enter route search"))
    rendered = sr.render(tmp_path, source, presentation=_parts(lanes=lanes))

    assert len(rendered.surface.rows) == 1
    relations = batches[-1].relations
    assert {item.source_ref for item in relations} == {f"relation:id:dep-{i}" for i in range(3)}
    assert all(item.suppressed and not item.points and item.window_endpoint_absences
               and item.window_suppression_reason == "outside-window" for item in relations)
    assert all(item.from_instance_id and item.to_instance_id for item in relations)
    assert len([value for value in batches[-1].diagnostics
                if value.startswith("W_LAYOUT_RELATION_SUPPRESSED:")]) == 3
