"""#1936: terminal-list notes retain their independent optional plot index."""
from __future__ import annotations

from datetime import date
from xml.etree import ElementTree

from chrona.presentation.layout import surface_annotations
from chrona.presentation.layout.annotations import AnnotationBox
from chrona.presentation.layout.labels import LabelPlacement, LabelRect
from tests.support import synthetic_review as sr
from tests.support.legacy_axis import use_legacy_six_tier_axis


def _fixture(*, marker="numbered", targets=("a", "b")):
    source = sr.project({
        "a": sr.point("a", date(2026, 1, 5), owner="team-a", title="Early gate"),
        "b": sr.point("b", date(2026, 4, 5), owner="team-b", title="Later gate"),
    })
    parts = use_legacy_six_tier_axis(sr.bundle())
    parts["layout"].setdefault("relationRouting", {"maxBends": 4, "maxDetourRatio": 2})[
        "unroutable"] = "suppress"
    parts["view"] = sr.lane_view(parts["view"])
    sr.with_note_rail(parts, width=300)
    sr.add_notes(source, parts["view"], targets, [
        sr.candidate("terminal", region={"kind": "slot", "source": "annotations"},
                     connector="none", search_kind="row-aligned"),
    ], words=0)
    parts["view"]["body"]["visibility"]["annotations"]["marker"] = marker
    return source, parts


def _render(tmp_path, source, parts):
    tmp_path.mkdir(parents=True, exist_ok=True)
    return sr.render(tmp_path, source, presentation=parts, viewport=(1800, 1100))


def _by_id(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives}


def _svg_ids(rendered):
    root = ElementTree.fromstring(rendered.artifact.content)
    return {item.get("data-scene-id"): " ".join(" ".join(item.itertext()).split())
            for item in root.iter() if item.get("data-scene-id")}


def test_terminal_list_keeps_numbered_anchor_index_without_box_or_leader(tmp_path):
    source, parts = _fixture(targets=("b", "a"))

    rendered = _render(tmp_path, source, parts)

    ids, svg = _by_id(rendered), _svg_ids(rendered)
    assert ids["note-index:note-0"].text == "1"
    assert ids["note-index:note-1"].text == "2"
    assert ids["annotation-list:note-0"].text.startswith("1. ")
    assert ids["annotation-list:note-1"].text.startswith("2. ")
    assert ids["annotation-list:note-1"].bounds[1] < ids["annotation-list:note-0"].bounds[1]
    for note_id in ("note-0", "note-1"):
        assert f"note-index:{note_id}" in svg and f"annotation-list:{note_id}" in svg
        assert f"annotation-box:{note_id}" not in ids
        assert f"annotation-leader:{note_id}" not in ids


def test_terminal_list_keeps_list_when_optional_index_is_suppressed(tmp_path, monkeypatch):
    source, parts = _fixture(targets=("a",))
    monkeypatch.setattr(surface_annotations, "place_label", lambda *_args, **_kwargs: None)

    rendered = _render(tmp_path, source, parts)

    ids = _by_id(rendered)
    assert "W_LAYOUT_NOTE_INDEX_SUPPRESSED:note-0" in rendered.scene.diagnostics
    assert "note-index:note-0" not in ids
    assert ids["annotation-list:note-0"].text.endswith("(index not shown on plot)")
    assert "index not shown on plot" in _svg_ids(rendered)["annotation-list:note-0"]


def test_marker_none_and_explicit_whole_callout_suppression_do_not_make_an_index(tmp_path, monkeypatch):
    source, parts = _fixture(marker="none", targets=("a",))
    rendered = _render(tmp_path / "none", source, parts)
    assert "note-index:note-0" not in _by_id(rendered)

    source, parts = _fixture(targets=("a",))
    body = parts["view"]["body"]
    body["visibility"].setdefault("fallback", {})["annotations"] = ["end", "suppress"]
    note = body["annotations"][0]
    note.pop("candidates")
    note["placement"] = {"side": "end", "alignment": "center"}
    monkeypatch.setattr(surface_annotations, "project_annotation_box", lambda *_args, **_kwargs: None)

    suppressed = _render(tmp_path / "suppressed", source, parts)

    ids = _by_id(suppressed)
    assert "annotation-summary:note-0" in ids
    assert "note-index:note-0" not in ids
    assert "W_LAYOUT_ANNOTATION_SUPPRESSED:annotation:note-0" in suppressed.scene.diagnostics


def test_adjacent_search_uses_declared_side_not_opaque_candidate_id(tmp_path, monkeypatch):
    source, parts = _fixture(marker="none", targets=("a",))
    annotation = parts["view"]["body"]["annotations"][0]
    annotation["purpose"] = "highlight"
    candidate = annotation["candidates"][0]
    candidate.update({
        "id": "opaque-end-rung-name",
        "region": {"kind": "slot", "source": "annotations"},
        "search": {"kind": "adjacent", "side": "start"},
        "connector": {"kind": "none"},
    })
    candidate["obstacles"] = {"classes": [
        "mark", "text", "label-visual", "dependency-route", "leader-route",
        "annotation-box", "port", "rule",
    ]}
    real_project_box = surface_annotations.project_annotation_box
    seen_sides = []

    def capture_search_side(annotation, resolved, **kwargs):
        sides = tuple(kwargs["candidate_sides"])
        seen_sides.append(sides)
        if sides != ("start",):
            return real_project_box(annotation, resolved, **kwargs)
        anchor = kwargs["anchor_bounds"]
        width, height = kwargs["text_size"]
        placed = LabelRect(anchor.x - width - 4, anchor.y, width, height)
        return AnnotationBox(resolved, LabelPlacement("start", placed, False), False)

    monkeypatch.setattr(surface_annotations, "project_annotation_box", capture_search_side)
    rendered = _render(tmp_path, source, parts)

    ids = _by_id(rendered)
    assert seen_sides and all(item == ("start",) for item in seen_sides)
    assert ids["annotation-box:note-0"]
