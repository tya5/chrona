"""Scheduler-derived protection reaches real Scene/SVG without adapter routing."""
from dataclasses import replace
from datetime import date
import json
import xml.etree.ElementTree as ET

import pytest

from chrona.presentation.layout import surface_composer
from tests.support import synthetic_review as sr


@pytest.mark.parametrize("blocked", (False, True))
def test_critical_quality_fallback_or_domain_exhaustion_reaches_render(tmp_path, monkeypatch, blocked):
    source = sr.with_calendar(sr.project({
        "source": sr.span("source", date(2027, 1, 4), 2),
        "target": {"type": "task", "title": "Target", "schedule": {"mode": "scheduled", "amount": "4d"}},
        "blocker": sr.span("blocker", date(2027, 1, 4), 1),
    }, [{"id": "critical", "type": "dependency", "lag": "2d", "from": {"object": "source", "endpoint": "end"},
         "to": {"object": "target", "endpoint": "start"}}]))
    parts = sr.bundle()
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["view"]["body"]["visibility"]["relations"] = "all"
    parts["layout"]["relationRouting"] = {
        "search": "first-fit", "unroutable": "suppress", "maxBends": 0,
        "maxDetourRatio": 100, "searchBudget": 1,
    }
    compose = surface_composer.compose_surface_marks
    def completed_blocker(base, **kwargs):
        batch = compose(base, **kwargs)
        return replace(batch, marks=tuple(replace(mark, bounds=base.timeline.bounds, corner_radius=0)
            if mark.source_ref == "blocker" else mark for mark in batch.marks))
    if blocked:
        monkeypatch.setattr(surface_composer, "compose_surface_marks", completed_blocker)
    rendered = sr.render(tmp_path, source, presentation=parts)
    expected = ("W_LAYOUT_CRITICAL_RELATION_SEARCH_DOMAIN_EXHAUSTED:" if blocked
                else "I_LAYOUT_CRITICAL_RELATION_QUALITY_FALLBACK:")
    assert any(item.startswith(expected) for item in rendered.scene.diagnostics), rendered.scene.diagnostics
    assert not [item for item in rendered.scene.diagnostics if item.startswith("E_")]
    summary = next(item for item in rendered.scene.diagnostics if item.startswith("I_LAYOUT_RELATION_ROUTING:"))
    if blocked:
        assert json.loads(summary.split(":", 1)[1])["fallbackSearch"] == 0
    routes = [item for item in rendered.surface.primitives if item.source_kind == "relation"]
    assert bool(routes) is not blocked
    svg = ET.fromstring(rendered.artifact.content)
    ids = {item.get("data-scene-id", item.get("id")) for item in svg.iter()}
    assert all(route.scene_id in ids for route in routes)
