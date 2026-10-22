"""A connector-free card rung preserves Theme presentation before an explicit list fallback."""
from __future__ import annotations

from xml.etree import ElementTree

import pytest

from chrona.presentation.layout import surface_annotations
from chrona.usecases.render_review import RenderFailed
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr


OBSTACLES = ["mark", "text", "label-visual", "dependency-route", "leader-route",
             "annotation-box", "port", "rule"]
BODY = "Required callout body remains complete through safe fallback."


def _candidate(candidate_id: str, connector: str) -> dict:
    return {
        "id": candidate_id,
        "region": {"kind": "slot", "source": "annotations"},
        "search": {"kind": "row-aligned"},
        "obstacles": {"classes": list(OBSTACLES)},
        "connector": {"kind": connector},
    }


def _fixture():
    source = ak.project(kinds=("risk",), text=BODY)
    parts = sr.bundle()
    sr.with_note_rail(parts, width=360)
    ak.with_view_notes(parts, source)
    kinds = {key: dict(value) for key, value in ak.KINDS.items()}
    kinds["risk"]["heading"] = "Launch window opens"
    ak.with_kind_theme(parts, kinds=kinds)
    theme = parts["theme"]["body"]
    theme["roles"]["annotation-heading"] = {
        **theme["roles"]["annotation-kind-label"],
        "fontSize": "kind-heading-size", "lineHeight": "kind-heading-line",
    }
    theme["values"].update({"kind-heading-size": {"type": "number", "value": 24},
                            "kind-heading-line": {"type": "number", "value": 1.3}})
    theme["colorBindings"]["annotation-heading.fill"] = "text"
    parts["view"]["body"]["annotations"][0]["candidates"] = [
        _candidate("preferred", "leader"),
        # IDs are opaque; this nonterminal connector-free rung is still a card.
        _candidate("unconnected-card", "none"),
        _candidate("declared-list", "none"),
    ]
    return source, parts


def _svg_ids(rendered):
    root = ElementTree.fromstring(rendered.artifact.content)
    return {item.get("data-scene-id"): item for item in root.iter()
            if item.get("data-scene-id")}


def test_failed_leader_uses_full_card_rung_in_scene_and_svg(tmp_path, monkeypatch):
    source, parts = _fixture()
    monkeypatch.setattr(surface_annotations, "route_annotation_candidate", lambda *args, **kwargs: None)

    rendered = ak.render(tmp_path, source, parts)

    ids = {item.scene_id: item for item in rendered.surface.primitives}
    svg = _svg_ids(rendered)
    assert "annotation-box:view-n0" in ids and "annotation-box:view-n0" in svg
    assert ids["annotation-kind-text:view-n0:0"].text == "RISK · Task 0"
    assert ids["annotation-kind-text:view-n0:1"].text == "WARNING"
    assert "annotation-heading:view-n0" in ids
    assert ids["annotation-heading:view-n0"].text == "Launch window opens"
    assert BODY in ids["annotation-text:view-n0"].text
    assert ids["annotation-text:view-n0"].text_layout is not None
    assert "annotation-list:view-n0" not in ids
    assert "annotation-leader:view-n0" not in ids
    assert "annotation-kind-text:view-n0:0" in svg
    assert "annotation-kind-text:view-n0:1" in svg
    assert "annotation-heading:view-n0" in svg
    assert "annotation-text:view-n0" in svg
    assert "annotation-list:view-n0" not in svg
    heading_text = " ".join(" ".join(svg["annotation-heading:view-n0"].itertext()).split())
    body_text = " ".join(" ".join(svg["annotation-text:view-n0"].itertext()).split())
    assert heading_text == "Launch window opens"
    assert BODY in body_text
    assert any("W_LAYOUT_ANNOTATION_CANDIDATE_FALLBACK:view-n0:unconnected-card" in item
               for item in rendered.scene.diagnostics)


def test_blocked_card_reaches_explicit_list_with_complete_body_once(tmp_path, monkeypatch):
    source, parts = _fixture()
    monkeypatch.setattr(surface_annotations, "annotation_rail_candidates", lambda *args, **kwargs: ())
    monkeypatch.setattr(surface_annotations, "route_annotation_candidate", lambda *args, **kwargs: None)

    rendered = ak.render(tmp_path, source, parts)

    ids = {item.scene_id: item for item in rendered.surface.primitives}
    svg = _svg_ids(rendered)
    assert "annotation-list:view-n0" in ids and "annotation-list:view-n0" in svg
    assert "annotation-box:view-n0" not in ids
    visible_text = " ".join(" ".join(" ".join(element.itertext()).split()) for element in svg.values())
    assert visible_text.count(BODY) == 1
    overflow = [item for item in rendered.surface.fit_warnings
                if item.placement_id == "annotation-list:view-n0"]
    assert len(overflow) == 1 and overflow[0].behaviour == "visible-overflow"


def test_no_terminal_list_keeps_required_fallback_error(tmp_path, monkeypatch):
    source, parts = _fixture()
    parts["view"]["body"]["annotations"][0]["candidates"] = [_candidate("preferred", "leader")]
    monkeypatch.setattr(surface_annotations, "route_annotation_candidate", lambda *args, **kwargs: None)

    with pytest.raises(RenderFailed) as failure:
        ak.render(tmp_path, source, parts)

    assert failure.value.code == "E_LAYOUT_ANNOTATION_FALLBACK_REQUIRED"
