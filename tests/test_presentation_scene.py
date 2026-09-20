from copy import deepcopy
from dataclasses import replace
from datetime import date
from hashlib import sha256
from pathlib import Path
import subprocess
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import pytest

from chrona.presentation_lanes import lane_stack_offset
from chrona.presentation_scene import SurfaceContentInput, build_presentation_scene
from chrona.presentation_scene import presentation_scene_from_schedule
from chrona.presentation_svg import render_scene_surface_svg
from chrona.presentation_settings import builtin_bases
from chrona.review_svg import render_review_svg, render_table_timeline_svg


def item():
    return SimpleNamespace(object_id="a", title="A", source_type="span", planned={"start": date(2026, 1, 1), "end": date(2026, 1, 10)}, actual={"start": date(2026, 1, 2), "finish": date(2026, 1, 12)}, finish_delta=2, group_id="", group_label="", fields={})


def scene_settings():
    settings = builtin_bases()["executive-v0.2"]
    for asset, style in zip(settings["context"]["fontMetrics"]["assets"], ("Regular", "Bold")):
        path = Path(subprocess.run(["fc-match", "-f", "%{file}", f"Nimbus Sans:style={style}"], capture_output=True, text=True, check=True).stdout)
        asset["contentIdentity"] = "sha256:" + sha256(path.read_bytes()).hexdigest()
    return settings


def test_scene_joins_axis_ticks_and_marks_without_svg_geometry():
    settings = scene_settings()
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
    settings = scene_settings()
    scene = build_presentation_scene("Roadmap", [item()], (date(2026, 1, 1), date(2026, 2, 1)), settings)
    assert any(node.scene_id == "axis:primary:month:0:band" and node.kind == "Rect" for node in scene.primitives)
    planned = next(node for node in scene.primitives if node.scene_id == "timeline:a:planned:mark")
    actual = next(node for node in scene.primitives if node.scene_id == "timeline:a:actual:mark")
    assert planned.source_ref == actual.source_ref == "a"
    assert planned.semantic_facet == "planned"
    assert actual.semantic_facet == "actual"
    assert planned.bounds != actual.bounds


def test_scene_manifest_closes_inputs_and_per_surface_scale_evidence():
    settings = scene_settings()
    content = SurfaceContentInput(
        relations=({"id": "r", "type": "reference"},),
        annotations=({"id": "a", "purpose": "highlight",
                      "anchor": {"kind": "object", "id": "a", "facet": "planned", "endpoint": "body"}},),
        notes=(("n", "Note"),),
        legend_entries=(("planned", "Planned"),),
        summary_panels=(("summary", "Summary", (("count", "One"),)),),
    )
    window = (date(2026, 1, 1), date(2026, 2, 1))
    scene = build_presentation_scene("Roadmap", [item()], window, settings, content)
    manifest = scene.manifest
    assert manifest.version == "chrona/presentation-scene-manifest/v0.1"
    assert manifest.settings_version == "chrona/presentation-settings/v0.2"
    assert manifest.viewport == (1600.0, 900.0)
    assert manifest.selected_object_ids == ("a",)
    assert manifest.font_asset_identities == tuple(
        asset["contentIdentity"] for asset in settings["context"]["fontMetrics"]["assets"]
    )
    assert manifest.content_family_counts.__dict__ == {
        "relations": 1, "annotations": 1, "notes": 1,
        "legend_entries": 1, "summary_panels": 1,
    }
    assert scene.diagnostics == ()
    assert manifest.surface_scales == tuple(surface.scale_manifest for surface in scene.surfaces)
    assert [scale.surface_id for scale in manifest.surface_scales] == ["table-timeline", "review", "minimal"]
    assert all((scale.domain_start, scale.domain_end) == window for scale in manifest.surface_scales)
    assert all(scale.origin == scale.range_start and scale.range_end > scale.range_start
               for scale in manifest.surface_scales)
    assert len({(scale.range_start, scale.range_end, scale.unit_ratio)
                for scale in manifest.surface_scales}) == 2


def test_surface_serializer_preserves_scale_manifest_without_reconstruction():
    settings = scene_settings()
    scene = build_presentation_scene("Roadmap", [item()],
                                     (date(2026, 1, 1), date(2026, 2, 1)), settings)
    surface = next(value for value in scene.surfaces if value.surface_id == "review")
    svg = render_review_svg("Roadmap",
                            SimpleNamespace(items=(item(),), window=scene.window, unmatched_actual_ids=()),
                            {"body": {"roles": {}}},
                            {"sourceMetadata", "accessibleText", "semanticRoles", "marker"}, settings=settings)
    root = ET.fromstring(svg)
    metadata = next(value for value in root.iter() if value.tag.endswith("metadata"))
    assert metadata.get("data-axis-scale-id") == surface.scale_manifest.scale_id
    assert metadata.get("data-scale-domain-start") == surface.scale_manifest.domain_start.isoformat()
    assert metadata.get("data-scale-domain-end") == surface.scale_manifest.domain_end.isoformat()
    assert float(metadata.get("data-scale-range-start")) == surface.scale_manifest.range_start
    assert float(metadata.get("data-scale-range-end")) == surface.scale_manifest.range_end
    assert float(metadata.get("data-scale-origin")) == surface.scale_manifest.origin
    assert float(metadata.get("data-scale-unit-ratio")) == pytest.approx(surface.scale_manifest.unit_ratio, abs=0.01)


def test_surface_serializer_rejects_missing_scale_identity_instead_of_reconstructing_it():
    settings = scene_settings()
    scene = build_presentation_scene("Roadmap", [item()],
                                     (date(2026, 1, 1), date(2026, 2, 1)), settings)
    surface = scene.surfaces[0]
    invalid = replace(surface, scale_manifest=replace(surface.scale_manifest, scale_id=""))
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_MISSING"):
        render_scene_surface_svg(invalid, viewport=settings["context"]["viewport"], theme=settings["theme"])


def test_japanese_item_text_is_measured_once_and_long_unbreakable_text_diagnoses():
    settings = scene_settings()
    japanese = item()
    japanese.title = "量産認定レビュー"
    scene = build_presentation_scene("製品ロードマップ", [japanese],
                                     (date(2026, 1, 1), date(2026, 2, 1)), settings)
    assert all(any(node.purpose == "item-label" and node.text == "量産認定レビュー"
                   and node.text_layout is not None for node in surface.primitives)
               for surface in scene.surfaces)

    japanese.title = "超長期検証項目" * 100
    with pytest.raises(ValueError, match="E_LAYOUT_REQUIRED_OVERFLOW:text"):
        build_presentation_scene("製品ロードマップ", [japanese],
                                 (date(2026, 1, 1), date(2026, 2, 1)), settings)


def test_every_public_surface_owns_completed_core_primitives():
    settings = scene_settings()
    scene = build_presentation_scene("Roadmap", [item()], (date(2026, 1, 1), date(2026, 2, 1)), settings)
    for surface in scene.surfaces:
        primitives = surface.primitives
        assert {primitive.purpose for primitive in primitives} >= {
            "title-text", "axis-band", "axis-label", "tick", "comparison-mark", "item-label",
        }
        assert all(primitive.surface_id == surface.surface_id for primitive in primitives)
        assert all(primitive.projection_instance_id and primitive.scene_id.startswith(primitive.projection_instance_id)
                   for primitive in primitives)
        title = next(primitive for primitive in primitives if primitive.purpose == "title-text")
        label = next(primitive for primitive in primitives if primitive.purpose == "item-label")
        assert title.text == "Roadmap" and label.text == "A"
        assert title.text_layout is not None and label.text_layout is not None
        assert title.bounds == title.text_layout.bounds
        assert label.baseline == label.text_layout.baseline
        assert title.text_layout.asset_identity.startswith("sha256:")
    review, minimal = (next(surface for surface in scene.surfaces if surface.surface_id == name)
                       for name in ("review", "minimal"))
    review_mark = next(primitive for primitive in review.primitives if primitive.source_ref == "a" and primitive.semantic_facet == "planned")
    minimal_mark = next(primitive for primitive in minimal.primitives if primitive.source_ref == "a" and primitive.semantic_facet == "planned")
    assert review_mark.projection_instance_id != minimal_mark.projection_instance_id


def test_surface_primitives_never_fabricate_missing_actual():
    settings = scene_settings()
    no_actual = item()
    no_actual.actual = None
    scene = build_presentation_scene("Roadmap", [no_actual], (date(2026, 1, 1), date(2026, 2, 1)), settings)
    assert all(primitive.semantic_facet not in {"actual", "finish-delta"}
               for surface in scene.surfaces for primitive in surface.primitives)


def test_independent_lane_tracks_preserve_view_group_order_and_stack_geometry():
    settings = scene_settings()
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
    settings = scene_settings()
    settings["layout"]["lanes"].update(surface="independent-lane-track", trackPadding=8)
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
    settings = scene_settings()
    scene = presentation_scene_from_schedule("Roadmap", {"gate": {"at": date(2026, 1, 3)}}, settings)
    assert scene.window == (date(2026, 1, 3), date(2026, 1, 10))
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
    assert 'data-presentation-scene="v0.2"' in svg
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


def test_table_surface_owns_content_routes_annotations_and_legend_geometry():
    settings = scene_settings()
    left, right = item(), item()
    left.object_id, left.title, left.group_id, left.group_label = "left", "Left task", "team", "Team"
    right.object_id, right.title, right.group_id, right.group_label = "right", "Right task", "team", "Team"
    right.planned = {"start": date(2026, 1, 14), "end": date(2026, 1, 24)}
    right.actual = None
    right.finish_delta = None
    content = SurfaceContentInput(
        table_columns=(("Task", "Task"),),
        table_cells=(("left", "Task", "Left task"), ("right", "Task", "Right task")),
        relations=({"id": "left-to-right", "type": "dependency",
                    "from": {"object": "left", "endpoint": "end"},
                    "to": {"object": "right", "endpoint": "start"}},),
        annotations=({"id": "risk", "purpose": "callout", "text": "Check supplier",
                      "anchor": {"kind": "object", "id": "left", "facet": "planned", "endpoint": "finish"}},),
        legend_entries=(("planned", "Planned"), ("dependency", "Dependency")),
        coverage_text="Actual unavailable: 1/2 items",
    )
    scene = build_presentation_scene("Roadmap", (left, right),
                                     (date(2026, 1, 1), date(2026, 2, 1)), settings, content)
    surface = next(value for value in scene.surfaces if value.surface_id == "table-timeline")
    purposes = {node.purpose for node in surface.primitives}
    assert purposes >= {"table-frame", "table-header-band", "table-column-label", "group-surface",
                        "group-header", "row-shade", "table-row-rule", "table-cell",
                        "dependency-connector", "annotation-box", "annotation-text", "annotation-leader",
                        "legend-swatch", "legend-label", "coverage-text"}
    connector = next(node for node in surface.primitives if node.purpose == "dependency-connector")
    assert len(connector.points) >= 2 and connector.from_port_id and connector.to_port_id
    assert connector.bounds[2] >= 0 and connector.bounds[3] >= 0
    assert [node.z_order for node in surface.primitives] == list(range(len(surface.primitives)))


def test_resolved_table_adapter_serializes_scene_ids_for_every_geometry_family():
    settings = scene_settings()
    projection = SimpleNamespace(items=(item(),), window=(date(2026, 1, 1), date(2026, 2, 1)), unmatched_actual_ids=())
    project = {"objects": {"a": {"title": "A"}}, "relations": []}
    view = {"body": {"tableColumns": [{"id": "Task", "source": "title", "missing": "em-dash"}]}}
    svg = render_table_timeline_svg("Roadmap", projection, project, view, {"body": {"roles": {}, "values": {}}},
                                    {"sourceMetadata", "accessibleText", "semanticRoles", "marker", "tableSemantics", "hierarchicalAxis"},
                                    {}, settings=settings)
    assert 'data-presentation-scene="v0.2"' in svg
    for purpose in ("table-cell", "axis-band", "axis-major", "planned", "actual", "legend-label", "data-coverage"):
        element = next(value for value in ET.fromstring(svg).iter()
                       if value.get("data-purpose") == purpose)
        assert element.get("data-scene-id")
    root = ET.fromstring(svg)
    axis_background = next(value for value in root.iter()
                           if value.tag.endswith("rect") and value.get("data-purpose") == "axis-band")
    axis_foreground = next(value for value in root.iter()
                           if value.tag.endswith("text") and value.get("data-purpose") == "axis-band")
    header_background = next(value for value in root.iter()
                             if value.tag.endswith("rect") and value.get("data-purpose") == "table-header")
    header_foreground = next(value for value in root.iter()
                             if value.tag.endswith("text") and value.get("data-purpose") == "table-header")
    assert axis_foreground.get("fill") != axis_background.get("fill")
    assert header_foreground.get("fill") != header_background.get("fill")
    timeline_x = next(slot.bounds[0] for slot in build_presentation_scene(
        "Roadmap", projection.items, projection.window, settings
    ).surfaces[0].slots if slot.source == "timeline")
    item_labels = [value for value in root.iter() if value.get("data-purpose") == "item-label"]
    assert item_labels and all(float(value.get("x")) >= timeline_x for value in item_labels)


def test_review_adapter_selects_completed_review_surface():
    settings = scene_settings()
    projection = SimpleNamespace(items=(item(),), window=(date(2026, 1, 1), date(2026, 2, 1)), unmatched_actual_ids=())
    svg = render_review_svg("Roadmap", projection, {"body": {"roles": {}}},
                            {"sourceMetadata", "accessibleText", "semanticRoles", "marker"}, settings=settings)
    root = ET.fromstring(svg)
    metadata = next(value for value in root.iter() if value.tag.endswith("metadata"))
    assert metadata.get("data-surface-id") == "review"
    assert all(value.get("data-scene-id") for value in root.iter()
               if value.get("data-purpose") in {"heading", "axis-band", "axis-major", "planned", "actual", "item-label"})


def test_i3_f_review_and_table_surfaces_own_routes_annotations_and_formatted_summary():
    settings = scene_settings()
    settings["layout"]["slots"]["legend"]["source"] = "summary"
    left, right = item(), item()
    left.object_id, left.title = "left", "Left"
    right.object_id, right.title = "right", "Right"
    right.planned = {"start": date(2026, 1, 16), "end": date(2026, 1, 24)}
    content = SurfaceContentInput(
        relations=({"id": "left-to-right", "type": "dependency",
                    "from": {"object": "left", "endpoint": "end"},
                    "to": {"object": "right", "endpoint": "start"}},),
        annotations=({"id": "risk", "purpose": "callout", "text": "Check supplier",
                      "anchor": {"kind": "object", "id": "left", "facet": "planned",
                                 "endpoint": "finish"}},),
        summary_panels=(("next", "Next review", (("selectedCount", "Selected work: 2"),)),),
    )
    projection = SimpleNamespace(items=(left, right),
                                 window=(date(2026, 1, 1), date(2026, 2, 1)),
                                 unmatched_actual_ids=())
    svg = render_review_svg("Roadmap", projection, {"body": {"roles": {}}},
                            {"sourceMetadata", "accessibleText", "semanticRoles", "marker"},
                            settings=settings, surface_content=content)
    root = ET.fromstring(svg)
    purposes = {node.get("data-purpose") for node in root.iter()}
    assert purposes >= {"routed-connector", "presentation-annotation",
                        "annotation-leader", "summary-panel", "summary-header", "summary-metric"}
    assert "Next review" in svg and "Selected work: 2" in svg
    assert "selectedCount: Selected work: 2" not in svg

    scene = build_presentation_scene("Roadmap", (left, right), projection.window, settings, content)
    table = next(surface for surface in scene.surfaces if surface.surface_id == "table-timeline")
    assert {node.purpose for node in table.primitives} >= {
        "dependency-connector", "annotation-box", "summary-panel", "summary-header", "summary-metric"
    }
