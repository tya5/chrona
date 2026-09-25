"""Current render-product integration evidence.

The former minimal schedule-SVG adapter is intentionally absent: this proves
authoring inputs enter the same review pipeline as immutable evidence renders.
"""
from pathlib import Path
from copy import deepcopy
from dataclasses import replace
import json
import re

import pytest
import yaml

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.presentation.review.detail import ReviewDetailError
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review
from chrona.presentation.scene.serialization import serialize_scene


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def _draft_request(*, project_path: Path | None = None, view_path: Path | None = None,
                   actual_path: Path | None = None, icon_catalog_paths: tuple[Path, ...] = (),
                   visual_profile: str = "chrona-output/visual/v0.5-baseline", theme_path: Path | None = None,
                   scheme_path: Path | None = None, layout_path: Path | None = None,
                   summary_path: Path | None = None, detail_path: Path | None = None,
                   viewport: tuple[int, int | None] = (1600, 900)) -> RenderRequest:
    root = _root()
    draft = resolve_draft_render(
        project_path=project_path or root / "examples/controller-z/project.yaml",
        view_path=view_path or root / "examples/controller-z/views/executive.yaml",
        theme_path=theme_path or root / "examples/controller-z/themes/executive-light.yaml",
        scheme_path=scheme_path or root / "examples/controller-z/schemes/executive-light.yaml",
        layout_path=layout_path or root / "conformance/layout-profile-intent-v0.2.yaml",
        actual_path=actual_path or root / "examples/controller-z/actual.yaml",
        summary_path=summary_path, detail_path=detail_path, viewport=viewport,
        icon_catalog_paths=icon_catalog_paths,
        visual_profile=visual_profile,
    )
    return RenderRequest(
        closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
        scheduler=ReferenceScheduler(), renderer=V05SvgRenderer(), draft_auto_block=draft.auto_block,
    )


def test_draft_render_materializes_the_review_surface():
    svg = render_review(_draft_request()).artifact.content.decode()
    assert '<svg ' in svg
    assert 'data-source-ref="firmware"' in svg
    assert 'data-presentation-adapter="legacy-v0.1"' not in svg


def test_draft_render_is_deterministic():
    assert render_review(_draft_request()).artifact.content == render_review(_draft_request()).artifact.content


def test_draft_scene_records_only_real_draft_resource_identities():
    scene = render_review(_draft_request()).scene
    document = json.loads(serialize_scene(scene))
    assert document["provenance"]["mode"] == "draft"
    assert all(item["kind"] != "render-context" for item in document["provenance"]["resources"])


@pytest.mark.parametrize("row_count", (30, 100))
def test_draft_auto_block_resolves_large_public_scale_inputs(tmp_path, row_count):
    """Curriculum-scale rows use finite Layout output rather than renderer sizing."""
    root = _root()
    project = yaml.safe_load((root / "examples/controller-z/project.yaml").read_text(encoding="utf-8"))
    exemplar = project["objects"]["architecture"]
    project["objects"] = {
        f"scale-{index:03}": {**deepcopy(exemplar), "title": f"Scale curriculum item {index:03}"}
        for index in range(1, row_count + 1)
    }
    project["relations"] = []
    project["annotations"] = {}
    project_path = tmp_path / f"scale-{row_count}.yaml"
    project_path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
    view = yaml.safe_load((root / "examples/controller-z/views/executive.yaml").read_text(encoding="utf-8"))
    view["body"]["visibility"] = {"labels": False, "relations": "none", "annotations": "none"}
    view_path = tmp_path / "scale-view.yaml"
    view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")

    fixed = render_review(_draft_request(project_path=project_path, view_path=view_path, viewport=(1600, 900)))
    assert any(item.code == "W_LAYOUT_ROW_DENSITY" for item in fixed.surface.fit_warnings)
    assert fixed.surface.canvas_bounds[3] > 900
    scene_warnings = json.loads(serialize_scene(fixed.scene))["surfaces"][0]["fitWarnings"]
    assert any(item["code"] == "W_LAYOUT_ROW_DENSITY" for item in scene_warnings)
    rendered = render_review(_draft_request(project_path=project_path, view_path=view_path, viewport=(1600, None)))
    height = int(re.search(r'height="(\d+)"', rendered.artifact.content.decode()).group(1))
    assert height >= row_count * 72


def test_draft_auto_block_closes_the_public_multi_lane_milestone_fixture():
    """Auto sizing derives the completed stacked-mark requirement, not a count heuristic."""
    root = _root() / "tests/fixtures/multi-lane-milestones"
    automatic = render_review(_draft_request(
        project_path=root / "project.yaml", view_path=root / "view.yaml",
        actual_path=root / "actual.yaml", viewport=(1600, None),
    ))
    assert automatic.artifact.content.count(b'data-purpose="planned"') == 3
    fixed = render_review(_draft_request(
        project_path=root / "project.yaml", view_path=root / "view.yaml",
        actual_path=root / "actual.yaml", viewport=(1600, 180),
    ))
    assert fixed.surface.canvas_bounds[3] > 180
    assert {item.code for item in fixed.surface.fit_warnings} >= {"W_LAYOUT_ROW_DENSITY", "W_LAYOUT_MARK_OVERFLOW"}


def test_immutable_context_overflow_has_no_render_ingress_viewport_remedy(tmp_path):
    """The renderer does not prescribe a Draft-only repair before Layout fallback."""
    root = _root()
    request = _draft_request(project_path=root / "examples/controller-z/curriculum/scale-30.yaml",
                             viewport=(1600, 900))
    context = replace(request.closure.context,
                      identity=replace(request.closure.context.identity, revision="snapshot"))
    request = replace(request, closure=replace(request.closure, context=context))
    rendered = render_review(request)
    assert rendered.surface.canvas_bounds[3] > 900
    assert any(item.code == "W_LAYOUT_ROW_DENSITY" for item in rendered.surface.fit_warnings)


def test_draft_visual_ref_reaches_layout_and_scene_icon(tmp_path):
    root = _root()
    view = yaml.safe_load((root / "examples/controller-z/views/executive.yaml").read_text(encoding="utf-8"))
    view["body"]["visuals"] = [{"target": {"kind": "title"}, "ref": "chrona:risk", "decorative": False}]
    path = tmp_path / "visual-view.yaml"; path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")

    svg = render_review(_draft_request(view_path=path, icon_catalog_paths=(root / "examples/controller-z/icons.yaml",),
                                       visual_profile="chrona-output/visual/v0.7-svg")).artifact.content.decode()

    assert 'data-asset-identity=' in svg
    assert 'aria-label="Delivery risk"' in svg

    surface = render_review(_draft_request(view_path=path, icon_catalog_paths=(root / "examples/controller-z/icons.yaml",),
                                           visual_profile="chrona-output/visual/v0.7-svg")).surface
    icon = next(item for item in surface.primitives if item.kind == "Icon")
    assert icon.icon_vector is None and icon.icon_stroke_scale is None and icon.icon_paths


def test_draft_mark_visual_reaches_the_selected_completed_mark(tmp_path):
    root = _root()
    view = yaml.safe_load((root / "examples/controller-z/views/executive.yaml").read_text(encoding="utf-8"))
    view["body"]["visuals"] = [{"target": {"kind": "mark", "object": "firmware", "facet": "planned"},
                                "ref": "chrona:risk", "decorative": False}]
    path = tmp_path / "mark-visual-view.yaml"; path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")

    rendered = render_review(_draft_request(view_path=path, icon_catalog_paths=(root / "examples/controller-z/icons.yaml",),
                                            visual_profile="chrona-output/visual/v0.7-svg"))
    svg = rendered.artifact.content.decode()

    assert 'data-scene-id="visual:planned:firmware:firmware"' in svg
    assert 'data-purpose="icon-mark"' in svg
    by_id = {primitive.scene_id: primitive for primitive in rendered.surface.primitives}
    assert by_id["visual:planned:firmware:firmware"].slot_id == by_id["planned:firmware:firmware"].slot_id


def test_draft_plot_label_visual_reserves_space_before_candidate_selection(tmp_path):
    root = _root()
    view = yaml.safe_load((root / "examples/controller-z/views/executive.yaml").read_text(encoding="utf-8"))
    view["body"]["visuals"] = [{"target": {"kind": "plot-label", "id": "firmware"},
                                "ref": "chrona:risk", "side": "leading", "decorative": True}]
    path = tmp_path / "plot-visual-view.yaml"; path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")

    rendered = render_review(_draft_request(view_path=path, icon_catalog_paths=(root / "examples/controller-z/icons.yaml",),
                                            visual_profile="chrona-output/visual/v0.7-svg"))
    by_id = {primitive.scene_id: primitive for primitive in rendered.surface.primitives}
    icon = by_id["visual:member-label:firmware:firmware:leading"]
    label = by_id["member-label:firmware:firmware"]
    assert icon.bounds[0] < label.bounds[0]
    assert icon.bounds[0] + icon.bounds[2] <= label.bounds[0]
    assert icon.slot_id == label.slot_id


def test_draft_variance_label_visual_reserves_space_before_candidate_selection(tmp_path):
    root = _root()
    view = yaml.safe_load((root / "examples/controller-z/views/executive.yaml").read_text(encoding="utf-8"))
    view["body"]["visuals"] = [{"target": {"kind": "variance-label", "object": "firmware"},
                                "ref": "chrona:risk", "side": "leading", "decorative": True}]
    path = tmp_path / "variance-visual-view.yaml"; path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")

    rendered = render_review(_draft_request(view_path=path, icon_catalog_paths=(root / "examples/controller-z/icons.yaml",),
                                            visual_profile="chrona-output/visual/v0.7-svg"))
    by_id = {primitive.scene_id: primitive for primitive in rendered.surface.primitives}
    icon = by_id["visual:variance:firmware:firmware:leading"]
    label = by_id["variance:firmware:firmware"]
    assert icon.bounds[0] + icon.bounds[2] <= label.bounds[0]
    assert icon.slot_id == label.slot_id


def test_draft_slot_visuals_reserve_their_declared_layout_extents(tmp_path):
    root = _root()
    view = yaml.safe_load((root / "examples/controller-z/views/executive.yaml").read_text(encoding="utf-8"))
    view["body"]["visuals"] = [
        {"target": {"kind": "column", "id": "Workstream"}, "ref": "chrona:risk", "decorative": True},
        {"target": {"kind": "cell", "object": "firmware", "column": "Workstream"}, "ref": "chrona:risk", "decorative": True},
        {"target": {"kind": "group-header", "id": "fw-team"}, "ref": "chrona:risk", "decorative": True},
    ]
    path = tmp_path / "slot-visual-view.yaml"; path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")

    rendered = render_review(_draft_request(view_path=path, icon_catalog_paths=(root / "examples/controller-z/icons.yaml",),
                                            visual_profile="chrona-output/visual/v0.7-svg"))
    by_id = {primitive.scene_id: primitive for primitive in rendered.surface.primitives}
    for placement_id in ("column:Workstream", "cell:firmware:Workstream", "group-header:fw-team"):
        icon = by_id[f"visual:{placement_id}:leading"]
        label = by_id[placement_id]
        assert icon.bounds[0] + icon.bounds[2] <= label.bounds[0]
        assert icon.slot_id == label.slot_id


def test_draft_wallboard_visual_inventory_reaches_completed_slots(tmp_path):
    root = _root(); example = root / "examples/halcyon-1"
    view = yaml.safe_load((example / "views/02-programme-board.yaml").read_text(encoding="utf-8"))
    view["body"]["visuals"] = [
        {"target": {"kind": "axis-band", "level": "quarter", "index": 0}, "ref": "chrona:risk", "decorative": True},
        {"target": {"kind": "axis-label", "level": "month", "index": 0}, "ref": "chrona:risk", "decorative": True},
        {"target": {"kind": "legend", "role": "planned"}, "ref": "chrona:risk", "decorative": True},
        {"target": {"kind": "as-of-label"}, "ref": "chrona:risk", "decorative": True},
        {"target": {"kind": "summary", "panel": "key-figures"}, "ref": "chrona:risk", "decorative": True},
        {"target": {"kind": "summary", "panel": "key-figures", "metric": "launch", "part": "value"}, "ref": "chrona:risk", "decorative": True},
        {"target": {"kind": "summary", "panel": "key-figures", "metric": "launch", "part": "caption"}, "ref": "chrona:risk", "decorative": True},
    ]
    path = tmp_path / "wallboard-visual-view.yaml"; path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")
    rendered = render_review(_draft_request(project_path=example / "project.yaml", view_path=path,
        actual_path=example / "actual.yaml", theme_path=example / "themes/wallboard.yaml",
        scheme_path=example / "schemes/control-room-dark.yaml", layout_path=example / "layouts/wallboard.yaml",
        summary_path=example / "profiles/summary.yaml", detail_path=example / "profiles/detail.yaml",
        icon_catalog_paths=(root / "examples/controller-z/icons.yaml",), visual_profile="chrona-output/visual/v0.7-svg",
        viewport=(1920, 1080)))
    by_id = {primitive.scene_id: primitive for primitive in rendered.surface.primitives}
    assert "visual:axis-band-rect:0:0" in by_id
    for placement_id in ("axis-label:3:0", "legend:planned", "summary:key-figures",
                          "summary:key-figures:launch:value", "summary:key-figures:launch:caption", "as-of-label"):
        assert f"visual:{placement_id}:leading" in by_id


def test_draft_project_note_visual_reaches_its_completed_slot(tmp_path):
    root = _root(); example = root / "examples/controller-z"
    view = yaml.safe_load((example / "views/executive.yaml").read_text(encoding="utf-8"))
    view["body"]["visuals"] = [{"target": {"kind": "note", "id": "evb-risk"}, "ref": "chrona:risk", "decorative": True}]
    path = tmp_path / "note-visual-view.yaml"; path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")
    rendered = render_review(_draft_request(view_path=path, icon_catalog_paths=(example / "icons.yaml",),
        visual_profile="chrona-output/visual/v0.7-svg"))
    by_id = {primitive.scene_id: primitive for primitive in rendered.surface.primitives}
    assert "visual:note:evb-risk:leading" in by_id


def test_draft_detail_visuals_reach_group_and_milestone_slots(tmp_path):
    root = _root(); example = root / "examples/controller-z"
    view = yaml.safe_load((example / "views/executive.yaml").read_text(encoding="utf-8"))
    view["body"]["visuals"] = [
        {"target": {"kind": "group-detail", "id": "fw-team"}, "ref": "chrona:risk", "decorative": True},
        {"target": {"kind": "milestone", "id": "evb-arrival"}, "ref": "chrona:risk", "decorative": True},
    ]
    view_path = tmp_path / "detail-visual-view.yaml"; view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")
    rendered = render_review(_draft_request(view_path=view_path, layout_path=example / "layouts/executive-review.yaml",
        detail_path=example / "profiles/review-detail.yaml", icon_catalog_paths=(example / "icons.yaml",),
        visual_profile="chrona-output/visual/v0.7-svg"))
    by_id = {primitive.scene_id: primitive for primitive in rendered.surface.primitives}
    assert "visual:group-detail:fw-team:leading" in by_id
    assert "visual:milestone:evb-arrival:leading" in by_id


@pytest.mark.parametrize(("overflow", "expected"), (("ellipsize-with-source", "ellipsized"),
                                                        ("clip-optional", "suppressed")))
def test_detail_panel_unbreakable_overflow_is_completed_in_layout(tmp_path, overflow, expected):
    root = _root(); example = root / "examples/controller-z"
    layout = yaml.safe_load((example / "layouts/executive-review.yaml").read_text(encoding="utf-8"))
    footer = next(node for node in layout["root"]["children"] if node["id"] == "footer")
    next(node for node in footer["children"] if node.get("source") == "group-details")["overflow"] = overflow
    detail = yaml.safe_load((example / "profiles/review-detail.yaml").read_text(encoding="utf-8"))
    detail["body"]["groupDetails"][0]["description"] = "X" * 1000
    layout_path = tmp_path / "layout.yaml"; layout_path.write_text(yaml.safe_dump(layout, sort_keys=False), encoding="utf-8")
    detail_path = tmp_path / "detail.yaml"; detail_path.write_text(yaml.safe_dump(detail, sort_keys=False), encoding="utf-8")
    rendered = render_review(_draft_request(layout_path=layout_path, detail_path=detail_path))
    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    placement_id = "group-detail:fw-team"
    if expected == "ellipsized":
        assert any(line.endswith("…") for line in primitives[placement_id].text_layout.lines)
    else:
        assert placement_id not in primitives
        assert any(item.code == "W_LAYOUT_DETAIL_PANEL_CLIPPED" and item.placement_id == placement_id
                   for item in rendered.surface.fit_warnings)


def test_detail_panels_stack_when_their_declared_inline_slots_overlap(tmp_path):
    root = _root(); example = root / "examples/controller-z"
    layout = yaml.safe_load((example / "layouts/executive-review.yaml").read_text(encoding="utf-8"))
    footer = next(node for node in layout["root"]["children"] if node["id"] == "footer")
    footer["kind"] = "overlay"
    for field in ("alignItems", "justifyContent", "itemMinInlineSize", "gap"):
        footer.pop(field)
    layout["requiredThemeTokens"].remove("panel.minimum")
    layout_path = tmp_path / "overlapping-detail-layout.yaml"
    layout_path.write_text(yaml.safe_dump(layout, sort_keys=False), encoding="utf-8")
    rendered = render_review(_draft_request(layout_path=layout_path, detail_path=example / "profiles/review-detail.yaml"))
    slots = {slot.slot_id: slot.bounds for slot in rendered.surface.slots}
    group = slots["group-details"]
    milestones = slots["milestones"]
    assert milestones[1] >= group[1] + group[3]


def test_completed_detail_footer_preserves_the_annotation_successor_gap():
    root = _root(); example = root / "examples/controller-z"
    rendered = render_review(_draft_request(
        view_path=example / "views/annotations.yaml",
        layout_path=example / "layouts/annotations-review.yaml",
        detail_path=example / "profiles/review-detail.yaml",
    ))
    slots = {slot.slot_id: slot.bounds for slot in rendered.surface.slots}
    annotations = slots["annotations"]
    footer_end = max(slots[slot_id][1] + slots[slot_id][3]
                     for slot_id in ("group-details", "milestones", "observations", "legend", "notes"))
    assert annotations[1] == footer_end + 16
    group_text = [item for item in rendered.surface.primitives if item.scene_id.startswith("group-detail:")]
    annotation_text = [item for item in rendered.surface.primitives if item.scene_id.startswith("annotation-text:")]
    assert all(not (left.bounds[0] < right.bounds[0] + right.bounds[2]
                    and right.bounds[0] < left.bounds[0] + left.bounds[2]
                    and left.bounds[1] < right.bounds[1] + right.bounds[3]
                    and right.bounds[1] < left.bounds[1] + left.bounds[3])
               for left in group_text for right in annotation_text)


def test_unexpanded_detail_footer_leaves_annotation_successor_at_manifest_position(tmp_path):
    """The downstream correction is inert when panel completion adds no extent."""
    root = _root(); example = root / "examples/controller-z"
    detail = yaml.safe_load((example / "profiles/review-detail.yaml").read_text(encoding="utf-8"))
    detail["body"].pop("groupDetails")
    detail["body"].pop("milestones")
    detail_path = tmp_path / "no-detail-panels.yaml"
    detail_path.write_text(yaml.safe_dump(detail, sort_keys=False), encoding="utf-8")

    rendered = render_review(_draft_request(
        view_path=example / "views/annotations.yaml",
        layout_path=example / "layouts/annotations-review.yaml",
        detail_path=detail_path,
    ))
    slots = {slot.slot_id: slot.bounds for slot in rendered.surface.slots}
    annotations = slots["annotations"]
    footer_end = max(slots[slot_id][1] + slots[slot_id][3]
                     for slot_id in ("group-details", "milestones", "observations", "legend", "notes"))
    assert annotations[1] == footer_end + 16


def test_project_notes_advance_by_their_completed_measured_block_extent():
    rendered = render_review(_draft_request())
    notes = [item for item in rendered.surface.primitives if item.scene_id.startswith("note:")]
    assert len(notes) > 1
    assert all(left.bounds[1] + left.bounds[3] <= right.bounds[1]
               for left, right in zip(notes, notes[1:]))


def test_draft_annotation_visual_is_measured_before_its_rail_is_allocated(tmp_path):
    root = _root(); example = root / "examples/controller-z"
    view = yaml.safe_load((example / "views/executive.yaml").read_text(encoding="utf-8"))
    view["body"]["visibility"]["annotations"] = {"mode": "presentation", "marker": "numbered"}
    view["body"]["annotations"] = [{
        "id": "firmware-callout", "purpose": "callout",
        "anchor": {"kind": "object", "id": "firmware", "facet": "planned", "endpoint": "finish"},
        "placement": {"side": "end", "alignment": "center"},
        "text": "Confirm supplier evidence.",
    }]
    view["body"]["visuals"] = [
        {"target": {"kind": "annotation", "id": "firmware-callout"}, "ref": "chrona:risk", "decorative": True},
        {"target": {"kind": "note-index", "id": "firmware-callout"}, "ref": "chrona:risk", "decorative": True},
    ]
    view_path = tmp_path / "annotation-visual-view.yaml"
    view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")

    rendered = render_review(_draft_request(view_path=view_path, layout_path=example / "layouts/executive-review.yaml",
        icon_catalog_paths=(example / "icons.yaml",), visual_profile="chrona-output/visual/v0.7-svg"))
    by_id = {primitive.scene_id: primitive for primitive in rendered.surface.primitives}
    icon = by_id["visual:annotation-text:firmware-callout:leading"]
    label = by_id["annotation-text:firmware-callout"]
    assert icon.bounds[0] + icon.bounds[2] <= label.bounds[0]
    assert icon.slot_id == label.slot_id == "annotations"
    note_icon = by_id["visual:note-index:firmware-callout:leading"]
    note_index = by_id["note-index:firmware-callout"]
    assert note_icon.bounds[0] + note_icon.bounds[2] <= note_index.bounds[0]
    assert note_icon.slot_id == "annotations"
    assert "annotation-leader:firmware-callout" in by_id


def test_detail_profile_and_layout_sources_close_before_scene(tmp_path):
    root = _root(); example = root / "examples/controller-z"
    layout = yaml.safe_load((example / "layouts/executive-review.yaml").read_text(encoding="utf-8"))
    footer = next(node for node in layout["root"]["children"] if node["id"] == "footer")
    footer["children"] = [node for node in footer["children"] if node.get("source") != "group-details"]
    missing_source = tmp_path / "missing-detail-source.yaml"
    missing_source.write_text(yaml.safe_dump(layout, sort_keys=False), encoding="utf-8")
    with pytest.raises(ReviewDetailError, match="E_DETAIL_SLOT_REQUIRED"):
        render_review(_draft_request(layout_path=missing_source, detail_path=example / "profiles/review-detail.yaml"))

    for node in footer["children"]:
        if node.get("source") in {"milestones", "observations"}:
            node["priority"] = "required"
    required_source = tmp_path / "required-detail-source.yaml"
    required_source.write_text(yaml.safe_dump(layout, sort_keys=False), encoding="utf-8")
    with pytest.raises(ReviewDetailError, match="E_LAYOUT_SOURCE_UNAVAILABLE"):
        render_review(_draft_request(layout_path=required_source))



def test_label_and_mark_visuals_use_distinct_completed_paint_roles(tmp_path):
    root = _root()
    view = yaml.safe_load((root / "examples/controller-z/views/executive.yaml").read_text(encoding="utf-8"))
    view["body"]["visuals"] = [
        {"target": {"kind": "title"}, "ref": "chrona:risk", "side": "trailing", "decorative": True},
        {"target": {"kind": "mark", "object": "firmware", "facet": "planned"}, "ref": "chrona:risk", "decorative": True},
    ]
    path = tmp_path / "paint-role-view.yaml"; path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")

    surface = render_review(_draft_request(view_path=path, icon_catalog_paths=(root / "examples/controller-z/icons.yaml",),
                                           visual_profile="chrona-output/visual/v0.7-svg")).surface
    by_id = {primitive.scene_id: primitive for primitive in surface.primitives}
    label, mark = by_id["visual:title:trailing"], by_id["visual:planned:firmware:firmware"]
    assert (label.visual_role, label.paint.fill) == ("text", "#172033")
    assert (mark.visual_role, mark.paint.fill) == ("icon-mark", "#FFFFFF")


def test_actual_progress_fill_uses_actual_set_progress_and_omits_absent_host(tmp_path):
    root = _root()
    actual_view = yaml.safe_load((root / "examples/controller-z/views/executive.yaml").read_text(encoding="utf-8"))
    actual_view["body"]["progressFill"] = {"source": "actual"}
    view_path = tmp_path / "actual-view.yaml"
    view_path.write_text(yaml.safe_dump(actual_view, sort_keys=False), encoding="utf-8")

    svg = render_review(_draft_request(view_path=view_path)).artifact.content.decode()
    assert 'data-scene-id="progress-fill:actual:firmware:firmware"' in svg
    assert 'data-purpose="progress-fill"' in svg

    actual = yaml.safe_load((root / "examples/controller-z/actual.yaml").read_text(encoding="utf-8"))
    actual["body"]["observations"][0]["actual"] = {"progress": 0.5}
    missing_host_path = tmp_path / "missing-host.yaml"
    missing_host_path.write_text(yaml.safe_dump(actual, sort_keys=False), encoding="utf-8")
    without_host = render_review(_draft_request(view_path=view_path, actual_path=missing_host_path)).artifact.content.decode()
    assert 'data-scene-id="progress-fill:actual:firmware:firmware"' not in without_host


def test_open_actual_is_a_layout_completed_continuation_host_with_progress(tmp_path):
    root = _root()
    view = yaml.safe_load((root / "examples/controller-z/views/executive.yaml").read_text(encoding="utf-8"))
    view["body"]["progressFill"] = {"source": "actual"}
    view_path = tmp_path / "actual-open-view.yaml"
    view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")

    result = render_review(_draft_request(view_path=view_path))
    by_id = {primitive.scene_id: primitive for primitive in result.surface.primitives}
    actual = by_id["actual:performance:performance"]
    progress = by_id["progress-fill:actual:performance:performance"]
    assert actual.kind == "Symbol" and actual.end_treatment == "open" and actual.symbol is not None
    assert actual.symbol.outline[0].points[0] == actual.symbol.outline[-1].points[-1]
    assert progress.clip_source_id == actual.scene_id
    assert "missing-actual:performance:performance" not in by_id
    svg = result.artifact.content.decode()
    assert 'data-scene-id="actual:performance:performance"' in svg
    assert 'clip-path="url(#clip-actual:performance:performance)"' in svg


def test_open_actual_without_set_as_of_warns_without_fabricating_a_missing_stub(tmp_path):
    root = _root()
    actual = yaml.safe_load((root / "examples/controller-z/actual.yaml").read_text(encoding="utf-8"))
    actual["body"].pop("asOf")
    actual_path = tmp_path / "without-as-of.yaml"
    actual_path.write_text(yaml.safe_dump(actual, sort_keys=False), encoding="utf-8")
    result = render_review(_draft_request(actual_path=actual_path))
    ids = {primitive.scene_id for primitive in result.surface.primitives}
    assert "actual:performance:performance" not in ids
    assert "missing-actual:performance:performance" not in ids
    assert "W_LAYOUT_OPEN_ACTUAL_AS_OF_REQUIRED:performance" in result.scene.diagnostics
    assert "W_LAYOUT_OPEN_ACTUAL_AS_OF_REQUIRED:performance" in json.loads(serialize_scene(result.scene))["diagnostics"]


def test_progress_fill_omits_absent_and_zero_planned_progress(tmp_path):
    root = _root()
    project = yaml.safe_load((root / "examples/controller-z/project.yaml").read_text(encoding="utf-8"))
    for item in project["objects"].values():
        item.pop("plannedProgress", None)
    project_path = tmp_path / "without-progress.yaml"
    project_path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
    view = yaml.safe_load((root / "examples/controller-z/views/executive.yaml").read_text(encoding="utf-8"))
    view["body"]["progressFill"] = {"source": "planned"}
    view_path = tmp_path / "planned-view.yaml"
    view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")

    svg = render_review(_draft_request(project_path=project_path, view_path=view_path)).artifact.content.decode()
    assert 'data-purpose="progress-fill"' not in svg

    project["objects"]["firmware"]["plannedProgress"] = 0
    project_path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
    zero = render_review(_draft_request(project_path=project_path, view_path=view_path)).artifact.content.decode()
    assert 'data-scene-id="progress-fill:planned:firmware:firmware"' not in zero
