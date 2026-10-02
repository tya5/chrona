"""#884: the group header text is gated against the band it lies on, end to end.

A Project grouped by owner with header presentation goes through the packaged `control-room-dark` bundle. A tint
equal to the header ink is a gate error on that group's header text; a legible band is not. (No Theme role admits a
catalogue pattern on a group band today, so the pattern grounds are proved on Scene documents in
`tests/unit/chrona/presentation/scene/test_group_header_contrast.py`.) Synthetic Project; no `examples/` input.
"""
from __future__ import annotations

from datetime import date, timedelta

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from tests.support import synthetic_review as sr

INK = "#EAF0FA"  # the packaged `text` colour: the header ink
OWNERS = ("bus", "payload", "ground")


def _project():
    objects = {}
    for index, owner in enumerate(OWNERS):
        for number in range(2):
            key = f"t-{owner}-{number}"
            objects[key] = sr.span(key, date(2026, 1, 5) + timedelta(days=index * 20 + number * 15), 12, owner=owner)
    source = sr.project(objects)
    for owner in OWNERS:
        source["entities"][owner]["title"] = owner.title()
    return source


def _render(tmp_path, *, tint=None):
    parts = sr.bundle("control-room-dark")
    body = parts["theme"]["body"]
    if tint is not None:
        parts["scheme"]["body"]["categories"]["series-1"] = tint
        parts["view"]["body"]["grouping"]["tint"] = {"scale": "series"}
    return sr.render(tmp_path, _project(), presentation=parts)


def _headers(rendered):
    return [item for item in evaluate_scene_contrast(scene_document(rendered.scene))
            if item.purpose == "group-header" and item.primitive_id is not None]


def test_header_text_is_gated_in_every_render_with_a_group_header(tmp_path):
    findings = _headers(_render(tmp_path))
    assert {item.primitive_id for item in findings} == {f"group-header:{owner}" for owner in OWNERS}
    assert all(item.severity == "info" and item.floor == 4.5 and item.ground_id.startswith("group:")
               for item in findings)


def test_a_tint_equal_to_the_header_ink_is_a_gate_error_on_that_groups_header(tmp_path):
    findings = _headers(_render(tmp_path, tint=INK))
    failing = [item for item in findings if item.severity == "error"]
    assert [item.primitive_id for item in failing] == ["group-header:bus"]
    assert failing[0].ground_color.upper() == INK and failing[0].code == "E_SCENE_STATE_TEXT_CONTRAST"
    assert {item.severity for item in findings if item.primitive_id != "group-header:bus"} == {"info"}


def test_a_legible_tint_is_not_a_header_finding(tmp_path):
    findings = _headers(_render(tmp_path, tint="#1F3A66"))
    assert findings and {item.severity for item in findings} == {"info"}
