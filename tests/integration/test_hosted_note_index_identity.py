"""Hosted note indexes follow the actual emitted mark identity (#1287)."""
from __future__ import annotations

from datetime import date, timedelta
from xml.etree import ElementTree

import pytest

from tests.support import synthetic_review as sr


def _parts(*, multipart: bool):
    parts = sr.bundle("executive-light")
    parts["view"] = sr.lane_view(parts["view"])
    if multipart:
        body = parts["theme"]["body"]
        body["values"]["note-index-test-glyph"] = {
            "type": "symbol",
            "value": {
                "shape": "glyph",
                "viewBox": [10, 10],
                "parts": [
                    {"d": "M0 5L5 0L10 5L5 10Z", "paint": "fill"},
                    {"d": "M0 5L5 0L10 5L5 10Z", "paint": "fill"},
                ],
            },
        }
        body["roles"]["milestoneSymbol"]["symbol"] = "note-index-test-glyph"
        body["colorBindings"]["milestone.fill"] = "surface"
        body["colorBindings"]["gate.fill"] = "surface"
        body["colorBindings"]["gate.stroke"] = "text"
        body["values"]["note-index-test-outline-width"] = {"type": "number", "value": 1}
        body["roles"]["gate"] = {"strokeWidth": "note-index-test-outline-width"}
    return parts


@pytest.mark.parametrize(
    ("multipart", "expected_host"),
    [(False, ":gate-0"), (True, ":gate-0:part:0")],
    ids=("single-part", "multipart-outline-glyph"),
)
def test_note_index_scene_and_svg_reference_exact_emitted_mark_host(
    tmp_path, multipart, expected_host,
):
    targets = [f"gate-{index}" for index in range(4)]
    source = sr.project({
        target: sr.point(target, date(2026, 1, 5) + timedelta(days=25 * index))
        for index, target in enumerate(targets)
    })
    parts = _parts(multipart=multipart)
    sr.add_notes(
        source,
        parts["view"],
        targets,
        [sr.candidate("plot-near", connector="leader", max_positions=256)],
        words=0,
    )
    rendered = sr.render(
        tmp_path,
        source,
        presentation=parts,
        viewport=(2400, 1400),
    )

    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    index = primitives["note-index:note-0"]
    mark_parts = [item for item in rendered.surface.primitives
                  if item.kind == "Symbol" and item.source_kind == "object"
                  and item.source_ref == "gate-0"]
    assert mark_parts
    host_id = mark_parts[0].scene_id
    if multipart:
        assert len(mark_parts) == 3  # two declared fills plus the role outline
        assert mark_parts[0].scene_id.endswith(":part:0")
        assert mark_parts[1].scene_id.endswith(":part:1")
        assert mark_parts[2].paint.stroke is not None
    else:
        assert len(mark_parts) == 1
        assert ":part:" not in host_id
    assert index.host_placement_id == host_id
    assert index.host_placement_id.endswith(expected_host)
    assert host_id in primitives
    host = primitives[host_id]
    assert host.paint_order < index.paint_order
    svg = ElementTree.fromstring(rendered.artifact.content)
    svg_ids = {item.get("data-scene-id") for item in svg.iter()}
    assert host_id in svg_ids
    assert index.scene_id in svg_ids

