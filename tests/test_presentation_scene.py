from copy import deepcopy
from dataclasses import replace
from datetime import date
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
    return builtin_bases()["executive-v0.2"]


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
        "group_details": 0, "milestones": 0, "observation_rows": 0,
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
        render_scene_surface_svg(invalid, viewport=settings["context"]["viewport"], theme=settings["theme"], output=settings["output"])


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


def test_variance_statuses_and_missing_actual_are_explicit_scene_families():
    settings = scene_settings()
    settings["layout"]["variance"]["showZero"] = True
    settings["layout"]["missingActual"]["mode"] = "label-and-pattern"
    settings["theme"]["paints"]["varianceAhead"].update(color="#123456", opacity=.3)
    settings["theme"]["missingPattern"].update(spacing=9, angle=30)
    settings["theme"]["missingPattern"]["stroke"].update(color="#654321", opacity=.4, width=3, dash=[2, 5])
    subjects = []
    for object_id, finish in (("ahead", date(2026, 1, 8)), ("track", date(2026, 1, 10)),
                              ("behind", date(2026, 1, 12))):
        subject = item()
        subject.object_id = subject.title = object_id
        subject.actual = {"start": date(2026, 1, 2), "finish": finish}
        subjects.append(subject)
    partial = item()
    partial.object_id = partial.title = "unknown"
    partial.actual = {"start": date(2026, 1, 2)}
    subjects.append(partial)

    scene = build_presentation_scene("Roadmap", subjects,
                                     (date(2026, 1, 1), date(2026, 2, 1)), settings)
    surface = next(value for value in scene.surfaces if value.surface_id == "minimal")
    markers = {node.source_ref: node for node in surface.primitives if node.purpose == "variance-marker"}
    assert {key: value.visual_role for key, value in markers.items()} == {
        "ahead": "variance-ahead", "track": "variance-on-track",
        "behind": "variance-behind", "unknown": "variance-unknown",
    }
    assert all(node.bounds[2] == settings["theme"]["varianceMarkerWidth"] for node in markers.values())
    assert {node.purpose for node in surface.primitives if node.source_ref == "unknown"} >= {
        "variance-marker", "variance-label", "missing-actual-pattern", "missing-actual-label",
    }
    svg = render_scene_surface_svg(surface, viewport=settings["context"]["viewport"], theme=settings["theme"], output=settings["output"])
    root = ET.fromstring(svg)
    pattern = next(value for value in root.iter() if value.get("id") == "missing-actual-pattern")
    hatch = next(value for value in pattern if value.tag.endswith("path"))
    assert (pattern.get("width"), pattern.get("patternTransform")) == ("9", "rotate(30)")
    assert (hatch.get("stroke"), hatch.get("stroke-width"), hatch.get("stroke-opacity"),
            hatch.get("stroke-dasharray")) == ("#654321", "3", "0.4", "2 5")
    ahead = next(value for value in root.iter()
                 if value.get("data-purpose") == "variance-marker"
                 and value.get("data-source-ref") == "ahead")
    assert (ahead.get("fill"), ahead.get("opacity")) == ("#123456", "0.3")
    assert next(value for value in root.iter()
                if value.get("data-purpose") == "missing-actual-pattern").get("fill") == "url(#missing-actual-pattern)"


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
    projection = SimpleNamespace(items=(item(),), window=(date(2026, 1, 1), date(2026, 2, 1)), unmatched_actual_ids=())
    project = {"objects": {"a": {"title": "A"}}, "relations": []}
    view = {"body": {"tableColumns": [{"id": "Task", "source": "title", "missing": "em-dash"}]}}
    theme = {"body": {"roles": {}, "values": {}}}
    svg = render_table_timeline_svg("Roadmap", projection, project, view, theme, {"sourceMetadata", "accessibleText", "semanticRoles", "marker", "tableSemantics", "hierarchicalAxis"}, {}, settings=settings)
    assert 'data-presentation-scene="v0.2"' in svg
    assert 'data-axis-scale-id="primary"' in svg


def test_explicit_facet_annotation_emits_common_box_and_leader():
    settings = builtin_bases()["executive-v0.2"]
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
    settings["theme"]["annotation"]["boxFill"].update(color="#102030", opacity=.4)
    settings["theme"]["annotation"]["boxStroke"].update(color="#405060", opacity=.5)
    settings["theme"]["annotation"]["leader"].update(color="#708090", opacity=.6)
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
    svg = render_scene_surface_svg(surface, viewport=settings["context"]["viewport"], theme=settings["theme"], output=settings["output"])
    elements = list(ET.fromstring(svg).iter())
    box = next(value for value in elements if value.tag.endswith("rect")
               and value.get("data-purpose") == "presentation-annotation"
               and value.get("data-source-ref") == "risk")
    leader = next(value for value in elements if value.get("data-purpose") == "annotation-leader")
    assert (box.get("fill"), box.get("fill-opacity"), box.get("stroke"), box.get("stroke-opacity")) == (
        "#102030", "0.4", "#405060", "0.5")
    assert (leader.get("stroke"), leader.get("stroke-opacity")) == ("#708090", "0.6")


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


def test_axis_formats_and_year_band_are_consumed_by_the_completed_scene():
    settings = scene_settings()
    settings["layout"]["axis"].update(levels=["year", "month"], bandHeights=[24, 24])
    settings["detail"]["formatting"]["month"] = "short-month"
    scene = build_presentation_scene("Roadmap", [item()],
                                     (date(2026, 1, 1), date(2026, 2, 1)), settings)
    surface = next(value for value in scene.surfaces if value.surface_id == "minimal")
    labels = [node for node in surface.primitives if node.purpose == "axis-label"]
    assert [(node.visual_role, node.text) for node in labels] == [("year", "2026"), ("month", "Jan")]
    assert labels[0].text_layout.weight == settings["theme"]["typography"]["year"]["weight"]


@pytest.mark.parametrize("shape,tag", [("circle", "ellipse"), ("square", "rect"), ("diamond", "path")])
def test_point_shape_and_facet_opacity_are_scene_owned_and_serialized(shape, tag):
    settings = scene_settings()
    settings["theme"]["point"]["shape"] = shape
    settings["theme"]["paints"]["milestone"] = {"color": "#123456", "opacity": 0.37}
    milestone = item()
    milestone.source_type = "point"
    milestone.planned = {"at": date(2026, 1, 8)}
    milestone.actual = None
    milestone.finish_delta = None
    scene = build_presentation_scene("Roadmap", [milestone],
                                     (date(2026, 1, 1), date(2026, 2, 1)), settings)
    surface = next(value for value in scene.surfaces if value.surface_id == "minimal")
    symbol = next(node for node in surface.primitives if node.purpose == "comparison-mark")
    assert (symbol.shape, symbol.color, symbol.opacity) == (shape, "#123456", 0.37)
    svg = render_scene_surface_svg(surface, viewport=settings["context"]["viewport"], theme=settings["theme"], output=settings["output"])
    element = next(value for value in ET.fromstring(svg).iter() if value.get("data-purpose") == "milestone")
    assert element.tag.endswith(tag)
    assert element.get("fill") == "#123456" and element.get("opacity") == "0.37"


def test_row_shade_preserves_theme_opacity_and_table_title_has_no_implicit_plot_copy():
    settings = scene_settings()
    settings["theme"]["paints"]["rowShade"] = {"color": "#123456", "opacity": 0.23}
    settings["detail"]["labelRules"] = [
        rule for rule in settings["detail"]["labelRules"] if rule["source"] != "title"
    ]
    first, second = item(), item()
    first.object_id, second.object_id = "first", "second"
    second.title = "Second"
    content = SurfaceContentInput(
        table_columns=(("title", "Title"),),
        table_cells=(("first", "title", "A"), ("second", "title", "Second")),
    )
    scene = build_presentation_scene("Roadmap", (first, second),
                                     (date(2026, 1, 1), date(2026, 2, 1)), settings, content)
    surface = next(value for value in scene.surfaces if value.surface_id == "table-timeline")
    shade = next(node for node in surface.primitives if node.purpose == "row-shade")
    assert (shade.color, shade.opacity) == ("#123456", 0.23)
    assert not any(node.purpose == "item-label" for node in surface.primitives)
    svg = render_scene_surface_svg(surface, viewport=settings["context"]["viewport"],
                                   theme=settings["theme"], output=settings["output"])
    element = next(value for value in ET.fromstring(svg).iter()
                   if value.get("data-purpose") == "row-shade")
    assert (element.get("fill"), element.get("opacity")) == ("#123456", "0.23")


def test_explicit_plot_title_avoids_existing_variance_label():
    settings = scene_settings()
    settings["layout"]["labelPlacement"].update(
        candidateSides=["end", "above", "below"], maxCandidates=3)
    subject = item()
    subject.title = "Long delivery title"
    scene = build_presentation_scene("Roadmap", [subject],
                                     (date(2026, 1, 1), date(2026, 2, 1)), settings)
    surface = next(value for value in scene.surfaces if value.surface_id == "table-timeline")
    title = next(node for node in surface.primitives if node.purpose == "item-label")
    variance = next(node for node in surface.primitives if node.purpose == "variance-label")
    ax, ay, aw, ah = title.bounds
    bx, by, bw, bh = variance.bounds
    assert ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay


def test_arrow_shape_none_and_independent_actual_height_are_consumed():
    settings = scene_settings()
    settings["theme"]["bar"].update(plannedHeight=11, actualHeight=5)
    settings["theme"]["arrow"]["shape"] = "none"
    left, right = item(), item()
    left.object_id = "left"
    right.object_id = "right"
    right.planned = {"start": date(2026, 1, 16), "end": date(2026, 1, 24)}
    content = SurfaceContentInput(relations=({
        "id": "left-to-right", "type": "dependency",
        "from": {"object": "left", "endpoint": "end"},
        "to": {"object": "right", "endpoint": "start"},
    },))
    scene = build_presentation_scene("Roadmap", [left, right],
                                     (date(2026, 1, 1), date(2026, 2, 1)), settings, content)
    surface = next(value for value in scene.surfaces if value.surface_id == "table-timeline")
    left_marks = {node.semantic_facet: node for node in surface.primitives
                  if node.source_ref == "left" and node.purpose == "comparison-mark"}
    assert left_marks["planned"].bounds[3] == 11
    assert left_marks["actual"].bounds[3] == 5
    connector = next(node for node in surface.primitives if node.purpose == "dependency-connector")
    assert connector.shape == "none"
    svg = render_scene_surface_svg(surface, viewport=settings["context"]["viewport"], theme=settings["theme"], output=settings["output"])
    assert 'marker-end=' not in svg and '<defs/>' in svg

    settings["theme"]["arrow"]["shape"] = "chevron"
    chevron_scene = build_presentation_scene("Roadmap", [left, right],
                                             (date(2026, 1, 1), date(2026, 2, 1)), settings, content)
    chevron_surface = next(value for value in chevron_scene.surfaces if value.surface_id == "table-timeline")
    connector = next(node for node in chevron_surface.primitives if node.purpose == "dependency-connector")
    assert connector.shape == "chevron"
    svg = render_scene_surface_svg(chevron_surface, viewport=settings["context"]["viewport"], theme=settings["theme"], output=settings["output"])
    assert 'marker-end="url(#dependency-arrow)"' in svg
    assert '<path d="M0 0L6 3.0L0 6" fill="none"' in svg


def test_bar_radius_minimum_width_and_stack_metadata_are_scene_owned():
    settings = scene_settings()
    settings["theme"]["bar"].update(radius=20, minWidth=60)
    subject = item()
    subject.group_id = "delivery"
    scene = build_presentation_scene("Roadmap", [subject],
                                     (date(2026, 1, 1), date(2026, 12, 31)), settings)
    surface = next(value for value in scene.surfaces if value.surface_id == "table-timeline")
    mark = next(node for node in surface.primitives
                if node.purpose == "comparison-mark" and node.semantic_facet == "planned")
    assert mark.bounds[2] == 60
    assert mark.corner_radius == 8.5
    assert (mark.lane_group_id, mark.stack_index) == ("delivery", 0)

    svg = render_scene_surface_svg(surface, viewport=settings["context"]["viewport"], theme=settings["theme"], output=settings["output"])
    element = next(value for value in ET.fromstring(svg).iter() if value.get("data-purpose") == "planned")
    assert element.get("rx") == element.get("ry") == "8.5"
    assert element.get("data-lane-group-id") == "delivery"
    assert element.get("data-stack") == "0"


def test_stroke_tokens_are_selected_by_primitive_purpose():
    settings = scene_settings()
    settings["theme"]["strokes"]["axisMajor"].update(color="#112233", width=2.5, dash=[1, 5])
    settings["theme"]["strokes"]["frame"].update(color="#223344", width=3, dash=[2, 6])
    settings["theme"]["strokes"]["rowRule"].update(color="#334455", width=4, dash=[3, 7])
    settings["theme"]["strokes"]["groupSeparator"].update(color="#445566", width=5, dash=[4, 8])
    settings["theme"]["strokes"]["dependency"].update(color="#556677", width=6, dash=[5, 9])
    left, right = item(), item()
    left.object_id = "left"
    right.object_id = "right"
    right.planned = {"start": date(2026, 1, 16), "end": date(2026, 1, 24)}
    content = SurfaceContentInput(
        table_columns=(("title", "Title"),),
        table_cells=(("left", "title", "Left"), ("right", "title", "Right")),
        relations=({"id": "left-to-right", "type": "dependency",
                    "from": {"object": "left", "endpoint": "end"},
                    "to": {"object": "right", "endpoint": "start"}},),
    )
    scene = build_presentation_scene("Roadmap", [left, right],
                                     (date(2026, 1, 1), date(2026, 2, 1)), settings, content)
    surface = next(value for value in scene.surfaces if value.surface_id == "table-timeline")
    root = ET.fromstring(render_scene_surface_svg(
        surface, viewport=settings["context"]["viewport"], theme=settings["theme"], output=settings["output"]))
    by_purpose = {}
    for node in root.iter():
        by_purpose.setdefault(node.get("data-purpose"), node)
    expected = {
        "axis-major": ("#112233", "2.5", "1 5"),
        "table-frame": ("#223344", "3", "2 6"),
        "table-row": ("#334455", "4", "3 7"),
        "group-separator": ("#445566", "5", "4 8"),
        "routed-connector": ("#556677", "6", "5 9"),
    }
    for purpose, values in expected.items():
        assert purpose in by_purpose
        assert (by_purpose[purpose].get("stroke"), by_purpose[purpose].get("stroke-width"),
                by_purpose[purpose].get("stroke-dasharray")) == values


def test_minor_ticks_use_next_finer_level_and_axis_minor_stroke():
    settings = scene_settings()
    settings["layout"]["axis"].update(minorVisible=True, tickUnit="month", tickStep=1)
    settings["theme"]["strokes"]["axisMinor"].update(
        color="#102938", opacity=.4, width=2.5, dash=[2, 3])
    scene = build_presentation_scene("Roadmap", [item()],
                                     (date(2026, 1, 1), date(2026, 2, 1)), settings)
    surface = next(value for value in scene.surfaces if value.surface_id == "minimal")
    minor = [node for node in surface.primitives if node.purpose == "minor-tick"]
    assert minor and all(node.visual_role == "week" for node in minor)
    svg = render_scene_surface_svg(surface, viewport=settings["context"]["viewport"], theme=settings["theme"], output=settings["output"])
    element = next(value for value in ET.fromstring(svg).iter() if value.get("data-purpose") == "axis-minor")
    assert (element.get("stroke"), element.get("stroke-width"), element.get("stroke-opacity"),
            element.get("stroke-dasharray")) == ("#102938", "2.5", "0.4", "2 3")


def test_variance_and_routing_visibility_gate_only_their_owned_families():
    settings = scene_settings()
    settings["layout"]["variance"]["visible"] = False
    settings["layout"]["routing"]["enabled"] = False
    left, right = item(), item()
    left.object_id = "left"
    right.object_id = "right"
    right.planned = {"start": date(2026, 1, 14), "end": date(2026, 1, 24)}
    content = SurfaceContentInput(
        relations=({"id": "edge", "type": "dependency",
                    "from": {"object": "left", "endpoint": "end"},
                    "to": {"object": "right", "endpoint": "start"}},),
        annotations=({"id": "risk", "purpose": "callout", "text": "Review",
                      "anchor": {"kind": "object", "id": "left", "facet": "planned",
                                 "endpoint": "finish"}},),
    )
    scene = build_presentation_scene("Roadmap", (left, right),
                                     (date(2026, 1, 1), date(2026, 2, 1)), settings, content)
    surface = next(value for value in scene.surfaces if value.surface_id == "table-timeline")
    purposes = {node.purpose for node in surface.primitives}
    assert "annotation-box" in purposes
    assert purposes.isdisjoint({"variance-marker", "variance-label", "dependency-connector",
                                "annotation-leader", "explanatory-arrow"})


def test_label_rule_required_controls_diagnostic_versus_optional_omission():
    optional = scene_settings()
    optional["layout"]["labelPlacement"].update(candidateSides=["inside"], maxCandidates=1,
                                                  overflow="clip-optional")
    optional["detail"]["labelRules"][0]["required"] = False
    subject = item()
    subject.title = "Label wider than a one-day bar"
    subject.planned = {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}
    scene = build_presentation_scene("Roadmap", [subject],
                                     (date(2026, 1, 1), date(2026, 2, 1)), optional)
    table = next(value for value in scene.surfaces if value.surface_id == "table-timeline")
    assert not any(node.purpose == "item-label" for node in table.primitives)

    required = deepcopy(optional)
    required["detail"]["labelRules"][0]["required"] = True
    with pytest.raises(ValueError, match="E_PRESENTATION_LABEL_UNPLACEABLE"):
        build_presentation_scene("Roadmap", [subject],
                                 (date(2026, 1, 1), date(2026, 2, 1)), required)


def test_date_label_rule_and_notes_typography_are_conditional_observers():
    settings = scene_settings()
    settings["layout"]["slots"]["legend"]["source"] = "annotations"
    settings["theme"]["typography"]["notes"]["size"] = 21
    content = SurfaceContentInput(notes=(("n1", "Review note"),))
    scene = build_presentation_scene("Roadmap", [item()],
                                     (date(2026, 1, 1), date(2026, 2, 1)), settings, content)
    table = next(value for value in scene.surfaces if value.surface_id == "table-timeline")
    assert any(node.purpose == "actual-date-label" for node in table.primitives)
    note = next(node for node in table.primitives if node.purpose == "project-note")
    assert note.text_layout is not None and note.text_layout.bounds[3] == pytest.approx(
        21 * settings["theme"]["typography"]["notes"]["lineHeight"])
    svg = render_scene_surface_svg(table, viewport=settings["context"]["viewport"], theme=settings["theme"], output=settings["output"])
    element = next(value for value in ET.fromstring(svg).iter()
                   if value.get("data-purpose") == "presentation-annotation"
                   and value.get("data-source-ref") == "n1")
    assert element.get("font-size") == "21"


def test_output_precision_font_capability_and_optional_overflow_are_explicit():
    settings = scene_settings()
    scene = build_presentation_scene("Roadmap", [item()],
                                     (date(2026, 1, 1), date(2026, 2, 1)), settings)
    surface = next(value for value in scene.surfaces if value.surface_id == "table-timeline")
    planned = next(node for node in surface.primitives
                   if node.purpose == "comparison-mark" and node.semantic_facet == "planned")

    integer_output = deepcopy(settings["output"])
    integer_output["coordinateDecimals"] = 0
    svg = render_scene_surface_svg(surface, viewport=settings["context"]["viewport"],
                                   theme=settings["theme"], output=integer_output)
    element = next(value for value in ET.fromstring(svg).iter()
                   if value.get("data-purpose") == "planned")
    assert "." not in element.get("x")

    unsupported = deepcopy(settings["output"])
    unsupported["fontPolicy"] = "embed"
    with pytest.raises(ValueError, match="E_PRESENTATION_OUTPUT_CAPABILITY"):
        render_scene_surface_svg(surface, viewport=settings["context"]["viewport"],
                                 theme=settings["theme"], output=unsupported)

    outside = replace(planned, bounds=(settings["context"]["viewport"]["width"] + 1, 0, 10, 10),
                      optional=True)
    optional_surface = replace(surface, primitives=(outside,))
    clipped = deepcopy(settings["output"])
    clipped["overflow"] = "clip-optional"
    svg = render_scene_surface_svg(optional_surface, viewport=settings["context"]["viewport"],
                                   theme=settings["theme"], output=clipped)
    assert 'data-source-ref="a"' not in svg

    with pytest.raises(ValueError, match="E_PRESENTATION_OUTPUT_OVERFLOW"):
        render_scene_surface_svg(optional_surface, viewport=settings["context"]["viewport"],
                                 theme=settings["theme"], output=settings["output"])
    with pytest.raises(ValueError, match="E_PRESENTATION_OUTPUT_OVERFLOW"):
        render_scene_surface_svg(replace(optional_surface, primitives=(replace(outside, optional=False),)),
                                 viewport=settings["context"]["viewport"], theme=settings["theme"], output=clipped)
