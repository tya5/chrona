"""#1130: preserve all numbered annotation entries when plot output is suppressed."""
from __future__ import annotations

from datetime import date, timedelta
from dataclasses import replace
import hashlib
from pathlib import Path
from xml.etree import ElementTree

from chrona.presentation.layout import surface_annotations
from chrona.presentation.scene.serialization import serialize_scene
from chrona.resources.semantic_vocabulary import builtin_semantic_vocabulary
from tests.support import synthetic_review as sr
from tests.support.legacy_axis import use_legacy_six_tier_axis


# #1936 completes painted-mark bounds, changing scale/anchor geometry only:
# all 61 primitive IDs, text, paint, note indexes and leaders remain present.
# The unused annotations slot stays pruned; note primitives belong to timeline.
NO_SUPPRESSION_SCENE_SHA256 = "a6df76419154ffee418870ed9f0976d2a84e07feeb1c350d0c7292ca9f9f39d9"
NO_SUPPRESSION_SVG_SHA256 = "af9c567ae7db6104df042895cb5f51b8630980082c2453e183f54ca8d59dada4"


def _fixture():
    source = sr.project({
        f"gate-{index}": sr.point(
            f"gate-{index}", date(2026, 1, 5) + timedelta(days=25 * index),
            owner=f"team-{index}", title=f"Gate {index}",
        )
        for index in range(4)
    })
    parts = use_legacy_six_tier_axis(sr.bundle())
    parts["layout"].setdefault("relationRouting", {"maxBends": 4, "maxDetourRatio": 2})["unroutable"] = "suppress"
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


def _suppress_second_index_per_trial(monkeypatch):
    """Inject the same failure into each fresh source trial, not only the first."""
    real_place_label = surface_annotations.place_label
    real_place_annotations = surface_annotations.place_annotations
    index_calls = 0

    def suppress_second_index(*args, **kwargs):
        nonlocal index_calls
        index_calls += 1
        return None if index_calls == 2 else real_place_label(*args, **kwargs)

    def place_annotations(context):
        nonlocal index_calls
        index_calls = 0
        # Internal suppression/reflow remains part of this single trial.
        return real_place_annotations(context)

    monkeypatch.setattr(surface_annotations, "place_label", suppress_second_index)
    monkeypatch.setattr(surface_annotations, "place_annotations", place_annotations)


def test_unsuppressed_scene_and_svg_match_the_characterized_bytes(tmp_path):
    source, parts = _fixture()
    rendered = sr.render(tmp_path, source, presentation=parts, viewport=(2400, 1400))

    assert rendered.scene.diagnostics == ('I_LAYOUT_RELATION_ROUTING:{"fallbackSearch":0,"relationInstances":0,"shapeSettled":0,"surfaceId":"table-timeline"}',)
    ids = _by_id(rendered)
    assert {f"note-index:note-{index}" for index in range(4)} <= ids.keys()
    assert {f"annotation-leader:note-{index}" for index in range(4)} <= ids.keys()
    vocabulary = builtin_semantic_vocabulary()
    assert [resource for resource in rendered.scene.provenance.resources if resource[0] == "semantic-vocabulary"] == [
        ("semantic-vocabulary", vocabulary.id, "v0.1", vocabulary.content_identity),
    ]
    assert hashlib.sha256(serialize_scene(rendered.scene)).hexdigest() == NO_SUPPRESSION_SCENE_SHA256
    assert hashlib.sha256(rendered.artifact.content).hexdigest() == NO_SUPPRESSION_SVG_SHA256


def test_one_index_only_suppression_keeps_the_other_three_indexes_and_svg_status(tmp_path, monkeypatch):
    source, parts = _fixture()
    sr.with_note_rail(parts, width=300)
    baseline = _render_at(tmp_path / "before", source, parts)
    _suppress_second_index_per_trial(monkeypatch)
    rendered = _render_at(tmp_path / "after", source, parts)

    assert "W_LAYOUT_NOTE_INDEX_SUPPRESSED:note-1" in rendered.scene.diagnostics
    ids = _by_id(rendered)
    baseline_ids = _by_id(baseline)
    assert "annotation-text:note-1" in ids and "annotation-box:note-1" in ids
    assert "annotation-leader:note-1" in ids and "note-index:note-1" not in ids
    for prefix in ("annotation-text", "annotation-box", "annotation-leader"):
        key = f"{prefix}:note-1"
        # The status activates the declared annotations source. Only its slot
        # association changes; the accepted plot callout is byte-for-byte the
        # same primitive in every other field.
        assert baseline_ids[key].slot_id == "timeline"
        assert ids[key].slot_id == "annotations"
        assert replace(ids[key], slot_id="timeline") == baseline_ids[key]
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
    _suppress_second_index_per_trial(monkeypatch)
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

    real_project_box = surface_annotations.project_annotation_box

    def suppress_note_two(annotation, *args, **kwargs):
        if annotation.annotation_id == "note-2":
            return None
        return real_project_box(annotation, *args, **kwargs)

    _suppress_second_index_per_trial(monkeypatch)
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

    real_project_box = surface_annotations.project_annotation_box

    def suppress_note_two(annotation, *args, **kwargs):
        if annotation.annotation_id == "note-2":
            return None
        return real_project_box(annotation, *args, **kwargs)

    _suppress_second_index_per_trial(monkeypatch)
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
