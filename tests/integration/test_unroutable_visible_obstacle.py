"""A completed Layout mark fixture blocks a relation and is really painted.

Bounds are replaced before shared obstacle registration. This fixture does not
claim that normal lane packing creates overlap, or supply a public witness.
"""
from dataclasses import replace
from datetime import date
import json
import xml.etree.ElementTree as ET

import pytest

from chrona.presentation.layout import surface_composer
from tests.support import synthetic_review as sr


@pytest.mark.parametrize("mode", ("suppress", "relax", "overlap", "stub"))
def test_visible_completed_mark_blocks_normal_routing(tmp_path, monkeypatch, mode):
    source = sr.project({
        "source": sr.span("source", date(2027, 1, 4), 2),
        "target": sr.span("target", date(2027, 2, 1), 2),
        "blocker": sr.span("blocker", date(2027, 1, 5), 2),
    }, [{"id": "link", "type": "dependency", "lag": "0d",
         "from": {"object": "source", "endpoint": "end"},
         "to": {"object": "target", "endpoint": "start"}}])
    parts = sr.bundle()
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["layout"]["relationRouting"] = {"search": "first-fit", "unroutable": mode,
                                            "maxBends": 4, "maxDetourRatio": 100}
    compose = surface_composer.compose_surface_marks
    fixture_bounds = []

    def completed_blocker(base, **kwargs):
        batch = compose(base, **kwargs)
        fixture_bounds.append(base.timeline.bounds)
        return replace(batch, marks=tuple(
            replace(mark, bounds=base.timeline.bounds, corner_radius=0)
            if mark.source_ref == "blocker" else mark for mark in batch.marks))

    monkeypatch.setattr(surface_composer, "compose_surface_marks", completed_blocker)
    rendered = sr.render(tmp_path, source, presentation=parts)
    blocker, = [p for p in rendered.surface.primitives
                if p.source_ref == "blocker" and p.kind.value == "Rect"]
    bounds = fixture_bounds[-1]
    assert blocker.bounds == tuple(float(value) for value in (
        bounds.inline, bounds.block, bounds.inline_size, bounds.block_size))
    svg = ET.fromstring(rendered.artifact.content)
    ids = [e.get("data-scene-id", e.get("id")) for e in svg.iter()]
    assert blocker.scene_id in ids
    element = next(e for e in svg.iter() if e.get("data-scene-id", e.get("id")) == blocker.scene_id)
    assert float(element.get("width")) == pytest.approx(blocker.bounds[2])
    assert float(element.get("height")) == pytest.approx(blocker.bounds[3])
    paths = [p for p in rendered.surface.primitives
             if p.source_kind == "relation" and ":link:" in p.scene_id]
    facts = [json.loads(d.split(":", 1)[1]) for d in rendered.scene.diagnostics
             if d.startswith("I_LAYOUT_RELATION_RESOLUTION:")]
    if mode == "suppress":
        assert not paths and not facts
        assert any(d.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for d in rendered.scene.diagnostics)
    else:
        assert len(paths) == (2 if mode == "stub" else 1)
        assert len(facts) == 1
        assert facts[0]["stage"] == ("marks" if mode == "relax" else mode)
        summary, = [json.loads(d.split(":", 1)[1]) for d in rendered.scene.diagnostics
                    if d.startswith("I_LAYOUT_RELATION_RESOLUTION_SUMMARY:")]
        assert summary["count"] == 1 and summary["stages"] == {facts[0]["stage"]: 1}
        halos = [p for p in rendered.surface.primitives if p.visual_role == "dependency-halo"]
        assert len(halos) == len(paths)
        assert all(h.scene_id in ids for h in halos)
        assert all(p.scene_id in ids and ids.index(blocker.scene_id) < ids.index(p.scene_id) for p in paths)
        assert not any(d.startswith("W_LAYOUT_RELATION_SUPPRESSED:") for d in rendered.scene.diagnostics)
