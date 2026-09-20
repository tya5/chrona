from copy import deepcopy
from datetime import date
from hashlib import sha256
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from chrona.presentation_lanes import lane_stack_offset
from chrona.presentation_scene import build_presentation_scene
from chrona.presentation_scene import presentation_scene_from_schedule
from chrona.presentation_settings import builtin_bases
from chrona.review_svg import render_table_timeline_svg


def item():
    return SimpleNamespace(object_id="a", title="A", source_type="span", planned={"start": date(2026, 1, 1), "end": date(2026, 1, 10)}, actual={"start": date(2026, 1, 2), "finish": date(2026, 1, 12)}, finish_delta=2, group_id="", group_label="", fields={})


def test_scene_joins_axis_ticks_and_marks_without_svg_geometry():
    settings = builtin_bases()["executive-v0.2"]
    scene = build_presentation_scene("Roadmap", [item()], (date(2026, 1, 1), date(2026, 2, 1)), settings)
    assert [mark.facet for mark in scene.marks] == ["planned", "actual", "finish-delta"]
    assert scene.axes[0].level == "month"
    assert scene.ticks[0].start == date(2026, 1, 1)
    assert scene.lanes[0].stack == 0
    assert scene.lane_tracks == ()
    slots = {slot.slot_id: slot for slot in scene.slots}
    assert slots["timeline"].source == "timeline"
    assert slots["timeline"].scale_id == slots["timelineAxis"].scale_id == "primary"
    assert scene.rows[0].object_id == "a"
    assert scene.rows[0].bounds[3] > 0
    surfaces = {surface.surface_id: surface for surface in scene.surfaces}
    assert {"table-timeline", "review", "minimal"} == set(surfaces)
    assert surfaces["review"].rows[0].bounds[2] > 0


def test_scene_materializes_stable_primitives_without_adapter_identity():
    settings = builtin_bases()["executive-v0.2"]
    scene = build_presentation_scene("Roadmap", [item()], (date(2026, 1, 1), date(2026, 2, 1)), settings)
    assert any(node.scene_id == "axis:primary:month:0:band" and node.kind == "Rect" for node in scene.primitives)
    planned = next(node for node in scene.primitives if node.scene_id == "timeline:a:planned:mark")
    actual = next(node for node in scene.primitives if node.scene_id == "timeline:a:actual:mark")
    assert planned.source_ref == actual.source_ref == "a"
    assert planned.semantic_facet == "planned"
    assert actual.semantic_facet == "actual"
    assert planned.bounds != actual.bounds


def test_every_public_surface_owns_completed_core_primitives():
    settings = builtin_bases()["executive-v0.2"]
    scene = build_presentation_scene("Roadmap", [item()], (date(2026, 1, 1), date(2026, 2, 1)), settings)
    for surface in scene.surfaces:
        primitives = surface.primitives
        assert {primitive.purpose for primitive in primitives} >= {
            "title-text", "axis-band", "axis-label", "tick", "comparison-mark", "item-label",
        }
        assert all(primitive.surface_id == surface.surface_id for primitive in primitives)
        assert all(primitive.projection_instance_id and primitive.scene_id.startswith(primitive.projection_instance_id)
                   for primitive in primitives)
        assert next(primitive for primitive in primitives if primitive.purpose == "title-text").text == "Roadmap"
        assert next(primitive for primitive in primitives if primitive.purpose == "item-label").text == "A"
    review, minimal = (next(surface for surface in scene.surfaces if surface.surface_id == name)
                       for name in ("review", "minimal"))
    review_mark = next(primitive for primitive in review.primitives if primitive.source_ref == "a" and primitive.semantic_facet == "planned")
    minimal_mark = next(primitive for primitive in minimal.primitives if primitive.source_ref == "a" and primitive.semantic_facet == "planned")
    assert review_mark.projection_instance_id != minimal_mark.projection_instance_id


def test_surface_primitives_never_fabricate_missing_actual():
    settings = builtin_bases()["executive-v0.2"]
    no_actual = item()
    no_actual.actual = None
    scene = build_presentation_scene("Roadmap", [no_actual], (date(2026, 1, 1), date(2026, 2, 1)), settings)
    assert all(primitive.semantic_facet not in {"actual", "finish-delta"}
               for surface in scene.surfaces for primitive in surface.primitives)


def test_independent_lane_tracks_preserve_view_group_order_and_stack_geometry():
    settings = builtin_bases()["executive-v0.2"]
    settings["layout"]["lanes"].update(surface="independent-lane-track", trackPadding=8)
    left = item()
    right = item()
    left.object_id, left.group_id = "z", "first"
    right.object_id, right.group_id = "a", "first"
    right.planned = {"start": date(2026, 1, 2), "end": date(2026, 1, 11)}
    scene = build_presentation_scene("Roadmap", [left, right], (date(2026, 1, 1), date(2026, 2, 1)), settings)
    assert [lane.stack for lane in scene.lanes] == [0, 1]
    assert scene.lane_tracks[0].group_id == "first"
    assert scene.lane_tracks[0].height == 2 * 8 + scene.lane_tracks[0].mark_extent + scene.lane_tracks[0].pitch
    assert lane_stack_offset(scene.lane_tracks[0], stack=1, padding=8) == 8 + scene.lane_tracks[0].pitch


def test_independent_lane_tracks_change_svg_bar_offsets():
    settings = builtin_bases()["executive-v0.2"]
    settings["layout"]["lanes"].update(surface="independent-lane-track", trackPadding=8)
    for asset, style in zip(settings["context"]["fontMetrics"]["assets"], ("Regular", "Bold")):
        path = Path(subprocess.run(["fc-match", "-f", "%{file}", f"Nimbus Sans:style={style}"], capture_output=True, text=True, check=True).stdout)
        asset["contentIdentity"] = "sha256:" + sha256(path.read_bytes()).hexdigest()
    left, right = item(), item()
    left.object_id = "left"
    right.object_id, right.planned = "right", {"start": date(2026, 1, 2), "end": date(2026, 1, 11)}
    projection = SimpleNamespace(items=(left, right), window=(date(2026, 1, 1), date(2026, 2, 1)), unmatched_actual_ids=())
    project = {"objects": {"left": {"title": "Left"}, "right": {"title": "Right"}}, "relations": []}
    view = {"body": {"tableColumns": [{"id": "Task", "source": "title", "missing": "em-dash"}]}}
    svg = render_table_timeline_svg("Roadmap", projection, project, view, {"body": {"roles": {}, "values": {}}},
                                    {"sourceMetadata", "accessibleText", "semanticRoles", "marker", "tableSemantics", "hierarchicalAxis"}, {}, settings=settings)
    track = build_presentation_scene("Roadmap", projection.items, projection.window, settings).lane_tracks[0]
    assert 'data-lane-offset="8"' in svg
    assert f'data-lane-offset="{8 + track.pitch:g}"' in svg


def test_scene_rejects_invalid_axis_order_before_adapter_use():
    settings = deepcopy(builtin_bases()["executive-v0.2"])
    settings["layout"]["axis"]["levels"] = ["month", "quarter"]
    with pytest.raises(ValueError, match="E_PRESENTATION_AXIS_INVALID"):
        build_presentation_scene("Roadmap", [item()], (date(2026, 1, 1), date(2026, 2, 1)), settings)


def test_resolved_schedule_is_adapted_to_common_scene():
    settings = builtin_bases()["executive-v0.2"]
    scene = presentation_scene_from_schedule("Roadmap", {"gate": {"at": date(2026, 1, 3)}}, settings)
    assert scene.window == (date(2026, 1, 3), date(2026, 1, 4))
    assert [mark.facet for mark in scene.marks] == ["planned"]


def test_adapter_receives_common_scene_when_resolved_settings_are_supplied():
    settings = builtin_bases()["executive-v0.2"]
    for asset, style in zip(settings["context"]["fontMetrics"]["assets"], ("Regular", "Bold")):
        path = Path(subprocess.run(["fc-match", "-f", "%{file}", f"Nimbus Sans:style={style}"], capture_output=True, text=True, check=True).stdout)
        asset["contentIdentity"] = "sha256:" + sha256(path.read_bytes()).hexdigest()
    projection = SimpleNamespace(items=(item(),), window=(date(2026, 1, 1), date(2026, 2, 1)), unmatched_actual_ids=())
    project = {"objects": {"a": {"title": "A"}}, "relations": []}
    view = {"body": {"tableColumns": [{"id": "Task", "source": "title", "missing": "em-dash"}]}}
    theme = {"body": {"roles": {}, "values": {}}}
    svg = render_table_timeline_svg("Roadmap", projection, project, view, theme, {"sourceMetadata", "accessibleText", "semanticRoles", "marker", "tableSemantics", "hierarchicalAxis"}, {}, settings=settings)
    assert 'data-presentation-scene="v0.1"' in svg
    assert 'data-axis-scale-id="primary"' in svg


def test_explicit_facet_annotation_emits_common_box_and_leader():
    settings = builtin_bases()["executive-v0.2"]
    for asset, style in zip(settings["context"]["fontMetrics"]["assets"], ("Regular", "Bold")):
        path = Path(subprocess.run(["fc-match", "-f", "%{file}", f"Nimbus Sans:style={style}"], capture_output=True, text=True, check=True).stdout)
        asset["contentIdentity"] = "sha256:" + sha256(path.read_bytes()).hexdigest()
    projection = SimpleNamespace(items=(item(),), window=(date(2026, 1, 1), date(2026, 2, 1)), unmatched_actual_ids=())
    project = {"objects": {"a": {"title": "A"}}, "relations": []}
    view = {"body": {"tableColumns": [{"id": "Task", "source": "title", "missing": "em-dash"}],
                     "visibility": {"annotations": "all"},
                     "annotations": [{"id": "risk", "purpose": "callout", "text": "Explicit plan note",
                                      "anchor": {"kind": "object", "id": "a", "facet": "planned", "endpoint": "finish"}}]}}
    theme = {"body": {"roles": {}, "values": {}}}
    svg = render_table_timeline_svg("Roadmap", projection, project, view, theme,
                                    {"sourceMetadata", "accessibleText", "semanticRoles", "marker", "tableSemantics", "hierarchicalAxis"}, {}, settings=settings)
    assert 'data-purpose="presentation-annotation"' in svg
    assert 'data-purpose="annotation-leader"' in svg
