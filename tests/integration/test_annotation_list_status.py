"""#1130: preserve all numbered annotation entries when plot output is suppressed."""
from __future__ import annotations

from datetime import date, timedelta
import hashlib
from pathlib import Path
from xml.etree import ElementTree

from chrona.presentation.layout import surface_annotations
from chrona.presentation.scene.serialization import serialize_scene
from tests.support import synthetic_review as sr


# #1271 centers four group-header lines (+0.2 px); annotation boxes,
# leaders, numbering and diagnostics remain unchanged.
NO_SUPPRESSION_SCENE_SHA256 = "f26aa7955ae1beabc9c26b2b26a98222ecde177a610ad8c5740d94187a6e9dbc"
NO_SUPPRESSION_SVG_SHA256 = "9d13fb41f70395a185d500fc1283429140a9ef9f44c6cd005c89950dd25ed43c"


def _fixture():
    source = sr.project({
        f"gate-{index}": sr.point(
            f"gate-{index}", date(2026, 1, 5) + timedelta(days=25 * index),
            owner=f"team-{index}", title=f"Gate {index}",
        )
        for index in range(4)
    })
    parts = sr.bundle()
    parts["view"] = sr.lane_view(parts["view"])
    sr.add_notes(
        source, parts["view"], [f"gate-{index}" for index in range(4)],
        [sr.candidate("plot-near", connector="leader", max_positions=256)], words=0,
    )
    return source, parts


def _rail_fixture():
    source, parts = _fixture()
    sr.with_note_rail(parts, width=300)
    theme = parts["theme"]["body"]
    for key, value in tuple(theme.get("values", {}).items()):
        if value.get("type") == "annotationContainer":
            del theme["values"][key]
    for role in theme.get("roles", {}).values():
        role.pop("annotationContainer", None)
    for annotation in parts["view"]["body"]["annotations"]:
        annotation.pop("candidates")
        annotation["placement"] = {"side": "end", "alignment": "center"}
    return source, parts


def _by_id(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives}


def _render_at(directory: Path, source, parts, *, viewport=(2400, 1400)):
    directory.mkdir()
    return sr.render(directory, source, presentation=parts, viewport=viewport)


def _svg_text(rendered, scene_id):
    root = ElementTree.fromstring(rendered.artifact.content)
    element = next(item for item in root.iter() if item.get("data-scene-id") == scene_id)
    return " ".join(" ".join(element.itertext()).split())


def test_unsuppressed_scene_and_svg_match_the_characterized_bytes(tmp_path):
    source, parts = _fixture()
    rendered = sr.render(tmp_path, source, presentation=parts, viewport=(2400, 1400))

    assert rendered.scene.diagnostics == ()
    ids = _by_id(rendered)
    assert {f"note-index:note-{index}" for index in range(4)} <= ids.keys()
    assert {f"annotation-leader:note-{index}" for index in range(4)} <= ids.keys()
    assert hashlib.sha256(serialize_scene(rendered.scene)).hexdigest() == NO_SUPPRESSION_SCENE_SHA256
    assert hashlib.sha256(rendered.artifact.content).hexdigest() == NO_SUPPRESSION_SVG_SHA256


def test_one_index_only_suppression_keeps_the_other_three_indexes_and_svg_status(tmp_path, monkeypatch):
    source, parts = _fixture()
    sr.with_note_rail(parts, width=300)
    baseline = _render_at(tmp_path / "before", source, parts)
    real_place_label = surface_annotations.place_label
    index_calls = 0

    def suppress_second_index(*args, **kwargs):
        nonlocal index_calls
        index_calls += 1
        if index_calls == 2:
            return None
        return real_place_label(*args, **kwargs)

    monkeypatch.setattr(surface_annotations, "place_label", suppress_second_index)
    rendered = _render_at(tmp_path / "after", source, parts)

    assert "W_LAYOUT_NOTE_INDEX_SUPPRESSED:note-1" in rendered.scene.diagnostics
    ids = _by_id(rendered)
    baseline_ids = _by_id(baseline)
    assert "annotation-text:note-1" in ids and "annotation-box:note-1" in ids
    assert "annotation-leader:note-1" in ids and "note-index:note-1" not in ids
    assert ids["annotation-text:note-1"] == baseline_ids["annotation-text:note-1"]
    assert ids["annotation-box:note-1"] == baseline_ids["annotation-box:note-1"]
    assert ids["annotation-leader:note-1"] == baseline_ids["annotation-leader:note-1"]
    status = ids["annotation-status:note-1"]
    assert status.text == "2. index not shown on plot"
    assert status.slot_id == "annotations"
    slot = next(item for item in rendered.surface.slots if item.source == "annotations")
    sx, sy, sw, sh = slot.bounds
    x, y, width, height = status.bounds
    assert sx <= x and x + width <= sx + sw and sy <= y and y + height <= sy + sh
    assert {"note-index:note-0", "note-index:note-2", "note-index:note-3"} <= ids.keys()
    assert sum(item.startswith("W_LAYOUT_NOTE_INDEX_SUPPRESSED:")
               for item in rendered.scene.diagnostics) == 1
    assert _svg_text(rendered, "annotation-text:note-1").endswith("Synthetic note 1 on gate-1.")
    assert _svg_text(rendered, "annotation-status:note-1") == "2. index not shown on plot"


def test_index_status_reflows_the_ordered_rail_entries_inside_the_declared_slot(tmp_path, monkeypatch):
    source, parts = _rail_fixture()
    assert not any(value.get("type") == "annotationContainer"
                   for value in parts["theme"]["body"]["values"].values())
    real_place_label = surface_annotations.place_label
    index_calls = 0

    def suppress_second_index(*args, **kwargs):
        nonlocal index_calls
        index_calls += 1
        if index_calls == 2:
            return None
        return real_place_label(*args, **kwargs)

    monkeypatch.setattr(surface_annotations, "place_label", suppress_second_index)
    rendered = _render_at(tmp_path / "after", source, parts)
    ids = _by_id(rendered)
    slot = next(item for item in rendered.surface.slots if item.source == "annotations")
    x, y, width, height = slot.bounds
    entries = [ids[f"annotation-text:note-{index}"] for index in range(4)]

    assert [entry.text.split(".", 1)[0] for entry in entries] == ["1", "2", "3", "4"]
    assert [entry.bounds[1] for entry in entries] == sorted(entry.bounds[1] for entry in entries)
    assert all(entry.slot_id == "annotations" for entry in entries)
    assert all(x <= entry.bounds[0] and entry.bounds[0] + entry.bounds[2] <= x + width
               and y <= entry.bounds[1] and entry.bounds[1] + entry.bounds[3] <= y + height
               for entry in entries)
    assert entries[1].text.endswith("(index not shown on plot)")
    assert {"note-index:note-0", "note-index:note-2", "note-index:note-3"} <= ids.keys()
    assert "note-index:note-1" not in ids
    assert "annotation-leader:note-1" in ids
    assert rendered.scene.diagnostics.count("W_LAYOUT_NOTE_INDEX_SUPPRESSED:note-1") == 1
    assert _svg_text(rendered, "annotation-text:note-1").endswith("(index not shown on plot)")


def test_index_and_whole_callout_suppression_keep_four_ordered_list_entries(tmp_path, monkeypatch):
    source, parts = _fixture()
    sr.with_note_rail(parts, width=300)
    view = parts["view"]["body"]
    # The third note uses the legacy candidate ladder so this test can force
    # the explicit whole-callout suppress outcome without changing Layout APIs.
    view["visibility"].setdefault("fallback", {})["annotations"] = ["end", "suppress"]
    whole_callout = view["annotations"][2]
    whole_callout.pop("candidates")
    whole_callout["placement"] = {"side": "end", "alignment": "center"}

    real_place_label = surface_annotations.place_label
    index_calls = 0

    def suppress_second_index(*args, **kwargs):
        nonlocal index_calls
        index_calls += 1
        # place_label's only direct use in this module is the note-index search.
        if index_calls == 2:
            return None
        return real_place_label(*args, **kwargs)

    real_project_box = surface_annotations.project_annotation_box

    def suppress_note_two(annotation, *args, **kwargs):
        if annotation.annotation_id == "note-2":
            return None
        return real_project_box(annotation, *args, **kwargs)

    monkeypatch.setattr(surface_annotations, "place_label", suppress_second_index)
    monkeypatch.setattr(surface_annotations, "project_annotation_box", suppress_note_two)
    rendered = sr.render(tmp_path, source, presentation=parts, viewport=(2400, 1400))

    diagnostics = set(rendered.scene.diagnostics)
    assert "W_LAYOUT_NOTE_INDEX_SUPPRESSED:note-1" in diagnostics
    assert "W_LAYOUT_ANNOTATION_SUPPRESSED:annotation:note-2" in diagnostics
    assert rendered.scene.diagnostics.count("W_LAYOUT_NOTE_INDEX_SUPPRESSED:note-1") == 1
    assert rendered.scene.diagnostics.count("W_LAYOUT_ANNOTATION_SUPPRESSED:annotation:note-2") == 1
    ids = _by_id(rendered)

    # The index-only failure keeps the accepted note, box, and mandatory leader.
    assert "(index not shown on plot)" not in ids["annotation-text:note-1"].text
    assert ids["annotation-status:note-1"].text == "2. index not shown on plot"
    assert "annotation-box:note-1" in ids
    assert "annotation-leader:note-1" in ids
    assert "note-index:note-1" not in ids

    # Whole-callout suppression retains only a compact numbered list summary.
    assert ids["annotation-summary:note-2"].text == (
        "3. Synthetic note 2 on gate-2. (callout not shown on plot)"
    )
    assert _svg_text(rendered, "annotation-summary:note-2").endswith("(callout not shown on plot)")
    assert not any(f"{prefix}:note-2" in ids for prefix in (
        "annotation-box", "annotation-text", "annotation-leader", "note-index",
    ))

    # The other visible indexes remain, all four original ordinals appear once,
    # and the later callout's leader ends on its finalized box after reflow.
    assert {"note-index:note-0", "note-index:note-3"} <= ids.keys()
    assert "annotation-text:note-0" in ids and "annotation-text:note-3" in ids
    entries = [
        ids[scene_id]
        for scene_id in (
            "annotation-text:note-0", "annotation-text:note-1",
            "annotation-summary:note-2", "annotation-text:note-3",
        )
    ]
    assert [entry.text.split(".", 1)[0] for entry in entries] == ["1", "2", "3", "4"]
    box = ids["annotation-box:note-3"].bounds
    tip_x, tip_y = ids["annotation-leader:note-3"].points[-1]
    left, top, width, height = box
    epsilon = 1e-6
    assert (
        (abs(tip_x - left) < epsilon and top - epsilon <= tip_y <= top + height + epsilon)
        or (abs(tip_x - (left + width)) < epsilon and top - epsilon <= tip_y <= top + height + epsilon)
        or (abs(tip_y - top) < epsilon and left - epsilon <= tip_x <= left + width + epsilon)
        or (abs(tip_y - (top + height)) < epsilon and left - epsilon <= tip_x <= left + width + epsilon)
    )


def test_insufficient_rail_retains_status_and_summary_with_explicit_overflow(tmp_path, monkeypatch):
    source, parts = _fixture()
    sr.with_note_rail(parts, width=1)
    view = parts["view"]["body"]
    view["visibility"].setdefault("fallback", {})["annotations"] = ["end", "suppress"]
    whole_callout = view["annotations"][2]
    whole_callout.pop("candidates")
    whole_callout["placement"] = {"side": "end", "alignment": "center"}
    baseline = _render_at(tmp_path / "before", source, parts)

    real_place_label = surface_annotations.place_label
    index_calls = 0

    def suppress_second_index(*args, **kwargs):
        nonlocal index_calls
        index_calls += 1
        if index_calls == 2:
            return None
        return real_place_label(*args, **kwargs)

    real_project_box = surface_annotations.project_annotation_box

    def suppress_note_two(annotation, *args, **kwargs):
        if annotation.annotation_id == "note-2":
            return None
        return real_project_box(annotation, *args, **kwargs)

    monkeypatch.setattr(surface_annotations, "place_label", suppress_second_index)
    monkeypatch.setattr(surface_annotations, "project_annotation_box", suppress_note_two)
    rendered = sr.render(tmp_path, source, presentation=parts, viewport=(2400, 1400))
    ids = _by_id(rendered)

    assert "W_LAYOUT_NOTE_INDEX_SUPPRESSED:note-1" in rendered.scene.diagnostics
    assert "W_LAYOUT_ANNOTATION_SUPPRESSED:annotation:note-2" in rendered.scene.diagnostics
    assert ids["annotation-status:note-1"].text == "2. index not shown on plot"
    assert ids["annotation-summary:note-2"].text == "3. Synthetic note 2 on gate-2. (callout not shown on plot)"
    assert ids["annotation-status:note-1"].slot_id == ids["annotation-summary:note-2"].slot_id == "annotations"
    status_warning = next(item for item in rendered.surface.fit_warnings
                          if item.placement_id == "annotation-status:note-1")
    summary_warning = next(item for item in rendered.surface.fit_warnings
                           if item.placement_id == "annotation-summary:note-2")
    assert status_warning.failure_kind == summary_warning.failure_kind == "label-collision"
    assert status_warning.behaviour == summary_warning.behaviour == "visible-overflow"
    assert rendered.surface.canvas_bounds == baseline.surface.canvas_bounds
    assert ids["annotation-status:note-1"].bounds[1] + ids["annotation-status:note-1"].bounds[3] <= (
        ids["annotation-summary:note-2"].bounds[1] + 1e-6
    )
