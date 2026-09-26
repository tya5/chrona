"""Current render-product integration evidence.

The former minimal schedule-SVG adapter is intentionally absent: this proves
authoring inputs enter the same review pipeline as immutable evidence renders.
"""
from pathlib import Path
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
import re

import pytest
import yaml

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.model.info_diagnostics import PaintOmission
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.presentation.review.detail import ReviewDetailError
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderFailed, RenderRequest, render_review
from chrona.presentation.scene.serialization import serialize_scene
from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.app.cli import _emit_render_warnings
from chrona.resources import default_preset_resource, default_preset_root


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


def test_suppressed_plot_labels_have_one_completed_info_count(capsys):
    # #487 corrected the table's `minmax`/content-minimum and its flex-allocation
    # basis (ADR-0032), which changes which member label this `elevated-light`
    # draft suppresses (`structure:structure` before #487, `launch:launch`
    # after) because the table's corrected width gives the plot different room.
    # The mechanism under test here -- exactly one completed info count and its
    # JSON emission -- is unaffected; only the specific suppressed label id is.
    root = _root()
    example = root / "examples/halcyon-1"
    preset = root / "src/chrona/resources/presets/bundles/elevated-light"
    rendered = render_review(_draft_request(
        project_path=example / "project.yaml", actual_path=example / "actual.yaml",
        scheme_path=root / "examples/controller-z/schemes/executive-light.yaml",
        view_path=preset / "view.yaml", theme_path=preset / "theme.yaml", layout_path=preset / "layout.yaml"))
    visible_labels = {item.scene_id for item in rendered.surface.primitives if item.kind == "Text"}
    per_id = {item.removeprefix("W_LAYOUT_LABEL_SUPPRESSED:") for item in rendered.scene.diagnostics
              if item.startswith("W_LAYOUT_LABEL_SUPPRESSED:")}
    assert len(per_id) == 1
    assert not per_id & visible_labels
    assert rendered.scene.diagnostics.count(
        "I_LAYOUT_PLOT_LABELS_SUPPRESSED:surface=table-timeline;count=1") == 1
    _emit_render_warnings(rendered)
    info = [json.loads(line) for line in capsys.readouterr().err.splitlines()
            if '"I_LAYOUT_PLOT_LABELS_SUPPRESSED"' in line]
    assert info == [{"code": "I_LAYOUT_PLOT_LABELS_SUPPRESSED", "count": 1,
                     "severity": "info", "surfaceId": "table-timeline"}]


def test_controller_executive_draft_no_longer_suppresses_its_member_label_after_487():
    # Direct evidence of the #487 attribution above: the same draft request that
    # used to suppress `member-label:ga:ga` (and report
    # `I_LAYOUT_PLOT_LABELS_SUPPRESSED:surface=table-timeline;count=1`) now fits
    # it, because the corrected table minimum is narrower than the old
    # widest-row-label basis for this view under the CSS-Grid flex allocation
    # (ADR-0032). Two relation labels are suppressed instead, because the
    # narrower table gives the plot/relation surface different, not more, room
    # to route through.
    rendered = render_review(_draft_request())
    assert not any(item.startswith("W_LAYOUT_LABEL_SUPPRESSED:member-label:") for item in rendered.scene.diagnostics)
    assert not any(item.startswith("I_LAYOUT_PLOT_LABELS_SUPPRESSED:") for item in rendered.scene.diagnostics)
    assert {item for item in rendered.scene.diagnostics if item.startswith("W_LAYOUT_RELATION_LABEL_SUPPRESSED:")} == {
        "W_LAYOUT_RELATION_LABEL_SUPPRESSED:relation:evb-to-bringup:evb-arrival:evb-arrival:silicon-bringup:silicon-bringup",
        "W_LAYOUT_RELATION_LABEL_SUPPRESSED:relation:bringup-to-performance:silicon-bringup:silicon-bringup:performance:performance",
    }
    assert not any(item.startswith("W_LAYOUT_VISIBLE_OVERFLOW") for item in rendered.scene.diagnostics)


def test_suppression_count_excludes_other_plot_text_and_absent_count():
    root = _root()
    example = root / "examples/halcyon-1"
    preset = root / "src/chrona/resources/presets/bundles/mission-light"
    inputs = dict(project_path=example / "project.yaml", actual_path=example / "actual.yaml",
                  scheme_path=example / "schemes/mission-light.yaml")
    tuned = render_review(_draft_request(**inputs, view_path=preset / "view.yaml",
                                         theme_path=preset / "theme.yaml", layout_path=preset / "layout.yaml"))
    assert "W_LAYOUT_LABEL_SUPPRESSED:variance:detector:detector" in tuned.scene.diagnostics
    assert "I_LAYOUT_PLOT_LABELS_SUPPRESSED:surface=table-timeline;count=1" in tuned.scene.diagnostics
    ordinary = render_review(_draft_request(**inputs, view_path=example / "views/01-mission-brief.yaml",
                                            theme_path=example / "themes/briefing.yaml",
                                            layout_path=example / "layouts/briefing.yaml",
                                            summary_path=example / "profiles/summary.yaml"))
    assert not ordinary.info_diagnostics
    assert not any(item.startswith("I_LAYOUT_PLOT_LABELS_SUPPRESSED:") for item in ordinary.scene.diagnostics)


def test_elevated_preset_reports_default_profile_omissions_and_rich_svg_paints_them(capsys):
    root = _root()
    example = root / "examples/halcyon-1"
    preset = root / "src/chrona/resources/presets/bundles/elevated-light"
    inputs = dict(project_path=example / "project.yaml", actual_path=example / "actual.yaml",
                  view_path=preset / "view.yaml", theme_path=preset / "theme.yaml",
                  layout_path=preset / "layout.yaml",
                  scheme_path=root / "examples/controller-z/schemes/executive-light.yaml")
    baseline = render_review(_draft_request(**inputs))
    omissions = [item for item in baseline.info_diagnostics if item.code == "I_VISUAL_TREATMENT_OMITTED"]
    assert {(item.role, item.treatment, item.paintable_profile) for item in omissions} == {
        ("group-band", "linear-gradient", "chrona-output/visual/v0.6-svg"),
        ("group-band", "drop-shadow", "chrona-output/visual/v0.6-svg"),
    }
    assert all(item.source_ref.startswith("/body/roles/group-band/") for item in omissions)
    assert sum(item.startswith("I_VISUAL_TREATMENT_OMITTED:") for item in baseline.scene.diagnostics) == 2
    assert len([item for item in baseline.surface.primitives if item.visual_role == "group-band"]) == 6
    _emit_render_warnings(baseline)
    notices = [json.loads(line) for line in capsys.readouterr().err.splitlines()
               if '"I_VISUAL_TREATMENT_OMITTED"' in line]
    assert len(notices) == 2
    assert all(item["severity"] == "info" and item["paintableProfile"] == "chrona-output/visual/v0.6-svg"
               for item in notices)

    rich = render_review(_draft_request(**inputs, visual_profile="chrona-output/visual/v0.6-svg"))
    assert not any(item.startswith("I_VISUAL_TREATMENT_OMITTED:") for item in rich.scene.diagnostics)
    assert all(item.paint.gradient is not None and item.paint.shadow is not None
               for item in rich.surface.primitives if item.visual_role == "group-band")
    assert b"<linearGradient" in rich.artifact.content and b"<filter" in rich.artifact.content


def test_planned_mark_shadow_is_supported_but_optional_under_baseline(tmp_path):
    root = _root()
    example = root / "examples/halcyon-1"
    preset = root / "src/chrona/resources/presets/bundles/elevated-light"
    theme = yaml.safe_load((preset / "theme.yaml").read_text(encoding="utf-8"))
    shadow = {key: value for key, value in theme["body"]["roles"]["group-band"].items()
              if key.startswith("shadow")}
    theme["body"]["roles"]["planned"].update(shadow)
    theme["body"]["colorBindings"]["planned.shadowColor"] = "neutral"
    theme_path = tmp_path / "planned-shadow.yaml"
    theme_path.write_text(yaml.safe_dump(theme, sort_keys=False), encoding="utf-8")
    inputs = dict(project_path=example / "project.yaml", actual_path=example / "actual.yaml",
                  view_path=preset / "view.yaml", theme_path=theme_path,
                  layout_path=preset / "layout.yaml",
                  scheme_path=root / "examples/controller-z/schemes/executive-light.yaml")
    baseline = render_review(_draft_request(**inputs))
    rich = render_review(_draft_request(**inputs, visual_profile="chrona-output/visual/v0.6-svg"))
    assert any(isinstance(item, PaintOmission) and item.role == "planned" and item.treatment == "drop-shadow"
               for item in baseline.info_diagnostics)
    assert all(item.paint.shadow is None for item in baseline.surface.primitives
               if item.visual_role == "planned")
    assert all(item.paint.shadow is not None for item in rich.surface.primitives
               if item.visual_role == "planned")
    assert re.search(rb'<rect[^>]*data-purpose="planned"[^>]*filter="url\(#shadow-', rich.artifact.content)


def test_five_line_derived_theme_changes_visible_draft_and_closes_as_ordinary_theme():
    root = _root() / "examples/aster-ssd"
    inputs = {"project_path": root / "project.yaml", "view_path": root / "views/01-overview.yaml",
              "scheme_path": root / "schemes/executive-light.yaml", "layout_path": root / "layouts/executive-review.yaml",
              "actual_path": root / "actual.yaml"}
    base = resolve_draft_render(**inputs, theme_path=root / "themes/executive-light.yaml")
    derived = resolve_draft_render(**inputs, theme_path=root / "themes/onboarding-variation.yaml")
    assert derived.closure.resource("theme").contract.version == "chrona/theme/v0.11"
    assert base.closure.resource("theme").content_identity == (
        "sha256:" + sha256((root / "themes/executive-light.yaml").read_bytes()).hexdigest())
    assert derived.closure.resource("theme").content_identity != base.closure.resource("theme").content_identity

    def rendered(draft):
        return render_review(RenderRequest(draft.closure, draft.asset_root, ReferenceScheduler(),
                                           asset_root=draft.asset_root, draft_auto_block=draft.auto_block))

    base_result, derived_result = rendered(base), rendered(derived)
    assert base_result.artifact.content != derived_result.artifact.content
    base_scene, derived_scene = (json.loads(serialize_scene(result.scene)) for result in (base_result, derived_result))
    def font_sizes(scene):
        return {item["id"]: item["textLayout"]["fontSize"] for item in scene["surfaces"][0]["primitives"]
                if item["id"] in {"title", "column:Work package / gate"}}
    assert font_sizes(base_scene) == {"title": 24.0, "column:Work package / gate": 14.0}
    assert font_sizes(derived_scene) == {"title": 30.0, "column:Work package / gate": 16.0}


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
    assert not {"W_LAYOUT_ROW_DENSITY", "W_LAYOUT_MARK_OVERFLOW"} & {item.code for item in fixed.surface.fit_warnings}
    assert fixed.surface.canvas_bounds[3] > 900
    surface = json.loads(serialize_scene(fixed.scene))["surfaces"][0]
    timeline = next(slot["bounds"] for slot in surface["slots"] if slot["source"] == "timeline")
    assert all(row["bounds"]["block"] + row["bounds"]["blockSize"] <=
               timeline["block"] + timeline["blockSize"] + 0.001 for row in surface["rows"])
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
    assert not {"W_LAYOUT_ROW_DENSITY", "W_LAYOUT_MARK_OVERFLOW"} & {item.code for item in fixed.surface.fit_warnings}


def test_immutable_context_uses_the_same_coherent_content_allocation(tmp_path):
    """Immutable viewport remains finite input; Layout grows its normal-flow hosts."""
    root = _root()
    request = _draft_request(project_path=root / "examples/controller-z/curriculum/scale-30.yaml",
                             viewport=(1600, 900))
    context = replace(request.closure.context,
                      identity=replace(request.closure.context.identity, revision="snapshot"))
    request = replace(request, closure=replace(request.closure, context=context))
    rendered = render_review(request)
    assert rendered.surface.canvas_bounds[3] > 900
    assert not {"W_LAYOUT_ROW_DENSITY", "W_LAYOUT_MARK_OVERFLOW"} & {item.code for item in rendered.surface.fit_warnings}


def test_fixed_draft_reallocates_table_timeline_and_notes_together():
    root = _root()
    draft = resolve_draft_render(
        project_path=root / "examples/halcyon-1/project.yaml",
        preset_path=Path(str(default_preset_resource())),
        preset_root=Path(str(default_preset_root())), viewport=(1600, 900),
    )
    rendered = render_review(RenderRequest(draft.closure, draft.asset_root, ReferenceScheduler(),
                                           renderer=V05SvgRenderer(), asset_root=draft.asset_root,
                                           draft_auto_block=draft.auto_block))
    assert not {"W_LAYOUT_ROW_DENSITY", "W_LAYOUT_MARK_OVERFLOW"} & {item.code for item in rendered.surface.fit_warnings}
    scene = json.loads(serialize_scene(rendered.scene))
    surface = scene["surfaces"][0]
    slots = {slot["source"]: slot["bounds"] for slot in surface["slots"]}
    timeline_end = slots["timeline"]["block"] + slots["timeline"]["blockSize"]
    table_end = slots["table"]["block"] + slots["table"]["blockSize"]
    assert abs(timeline_end - table_end) < 0.001
    assert slots["notes"]["block"] >= table_end
    assert all(row["bounds"]["block"] + row["bounds"]["blockSize"] <= timeline_end + 0.001
               for row in surface["rows"])
    assert all(item["bounds"]["block"] + item["bounds"]["blockSize"] <= table_end + 0.001
               for item in surface["primitives"] if item["id"].startswith("cell:"))
    assert not [item for item in evaluate_scene_perceptibility(scene)
                if item.code == "E_SCENE_TEXT_INTERSECTION"]
    svg_height = float(re.search(rb'<svg[^>]* height="([0-9.]+)"', rendered.artifact.content).group(1))
    assert svg_height >= surface["canvasBounds"]["blockSize"] - 0.001 > 900


def test_halcyon_missing_actual_is_due_only_and_tvac_boundary_is_inclusive(tmp_path):
    example = _root() / "examples/halcyon-1"
    inputs = dict(project_path=example / "project.yaml", view_path=example / "views/01-mission-brief.yaml",
                  theme_path=example / "themes/briefing.yaml", scheme_path=example / "schemes/mission-light.yaml",
                  layout_path=example / "layouts/briefing.yaml", actual_path=example / "actual.yaml",
                  summary_path=example / "profiles/summary.yaml")
    shipped = render_review(_draft_request(**inputs))
    shipped_ids = {primitive.scene_id for primitive in shipped.surface.primitives}
    shipped_by_id = {primitive.scene_id: primitive for primitive in shipped.surface.primitives}
    future = {"psr", "campaign", "frr", "launch", "leop", "first-light"}
    assert not {f"missing-actual:{object_id}:{object_id}" for object_id in future} & shipped_ids
    assert "missing-actual:tvac:tvac" not in shipped_ids
    assert "W_LAYOUT_ACTUAL_INCOMPLETE:tvac" in shipped.scene.diagnostics
    assert shipped_by_id["cell:tvac:Obs"].text == "Recorded"
    assert all(shipped_by_id[f"cell:{object_id}:Obs"].text == "—" for object_id in future)
    assert 'data-scene-id="missing-actual:tvac:tvac"' not in shipped.artifact.content.decode()

    actual = yaml.safe_load((example / "actual.yaml").read_text(encoding="utf-8"))
    actual["body"]["observations"] = [entry for entry in actual["body"]["observations"]
                                        if entry.get("projectObjectId") != "tvac"]
    actual_path = tmp_path / "actual-without-tvac.yaml"
    actual_path.write_text(yaml.safe_dump(actual, sort_keys=False), encoding="utf-8")
    boundary = render_review(_draft_request(**{**inputs, "actual_path": actual_path}))
    boundary_ids = {primitive.scene_id for primitive in boundary.surface.primitives}
    boundary_by_id = {primitive.scene_id: primitive for primitive in boundary.surface.primitives}
    assert "missing-actual:tvac:tvac" in boundary_ids
    assert boundary_by_id["cell:tvac:Obs"].text == "Missing"
    assert 'data-scene-id="missing-actual:tvac:tvac"' in boundary.artifact.content.decode()
    assert "W_LAYOUT_ACTUAL_INCOMPLETE:tvac" not in boundary.scene.diagnostics

    board = render_review(_draft_request(**{**inputs,
        "view_path": example / "views/02-programme-board.yaml",
        "theme_path": example / "themes/wallboard.yaml",
        "scheme_path": example / "schemes/control-room-dark.yaml",
        "layout_path": example / "layouts/wallboard.yaml"}))
    board_ids = {primitive.scene_id for primitive in board.surface.primitives}
    all_future = {"shipment", "campaign", "frr", "launch", "rehearsals", "leop", "first-light", "emc", "psr"}
    assert not {f"missing-actual:{object_id}:{object_id}" for object_id in all_future} & board_ids


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


def test_row_stripes_paint_above_group_bands_across_the_whole_surface(tmp_path):
    """Issue #481 criterion 1: stripes and group bands combine across the whole surface."""
    root = _root()
    layout = yaml.safe_load((root / "conformance/layout-profile-intent-v0.2.yaml").read_text(encoding="utf-8"))
    layout["reviewSurface"]["backgroundExtents"]["rowBand"] = "both"
    layout["reviewSurface"]["backgroundExtents"]["groupBand"] = "both"
    layout_path = tmp_path / "layout.yaml"
    layout_path.write_text(yaml.safe_dump(layout, sort_keys=False), encoding="utf-8")

    # examples/controller-z/views/executive.yaml already declares rows: alternate, groups: all.
    rendered = render_review(_draft_request(layout_path=layout_path))
    primitives = rendered.surface.primitives
    index_by_id = {item.scene_id: index for index, item in enumerate(primitives)}
    groups = {item.scene_id: item for item in primitives if item.scene_id.startswith("group:")}
    rows = {item.scene_id: item for item in primitives if item.scene_id.startswith("row-band:")}
    assert groups and rows
    timeline_slot = next(item for item in rendered.surface.slots if item.slot_id == "timeline")
    timeline_end = timeline_slot.bounds[0] + timeline_slot.bounds[2]

    def block_contains(outer, inner) -> bool:
        return outer.bounds[1] <= inner.bounds[1] + 1e-6 and (
            inner.bounds[1] + inner.bounds[3] <= outer.bounds[1] + outer.bounds[3] + 1e-6)

    overlapping_pairs = 0
    for group in groups.values():
        for row in rows.values():
            if not block_contains(group, row):
                continue
            overlapping_pairs += 1
            # The stripe is a real Scene primitive reaching the timeline's far
            # edge (visible in the timeline region of a grouped row), not just
            # an SVG-serialization artifact.
            assert row.bounds[0] + row.bounds[2] >= timeline_end - 1e-6
            # The stripe paints on top of the group band it overlaps: either a
            # strictly higher Scene paint_order, or the same paint_order and a
            # later position in the Scene primitive list (the renderer's tie
            # break, `renderers/v05_svg.py`).
            assert (row.paint_order > group.paint_order
                    or (row.paint_order == group.paint_order
                        and index_by_id[row.scene_id] > index_by_id[group.scene_id]))
    assert overlapping_pairs > 0


def test_group_band_includes_its_own_header_row_under_all_and_alternate(tmp_path):
    """Issue #481 criterion 2: a group's band includes its own header row."""
    root = _root()
    view = yaml.safe_load((root / "examples/controller-z/views/executive.yaml").read_text(encoding="utf-8"))
    for decoration in ("all", "alternate"):
        view["body"]["backgroundDecoration"]["groups"] = decoration
        view_path = tmp_path / f"view-{decoration}.yaml"
        view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")

        rendered = render_review(_draft_request(view_path=view_path))
        by_id = {item.scene_id: item for item in rendered.surface.primitives}
        groups = [group for group in rendered.surface.groups if group.header_bounds is not None]
        assert len(groups) >= 3, "the fixture needs at least one unselected alternate group"

        banded_count, unbanded_count = 0, 0
        for group in groups:
            band = by_id.get(f"group:{group.group_id}")
            header_band = by_id.get(f"group-header-band:{group.group_id}")
            if band is None:
                # No band is drawn for an unselected group's header: neither
                # its own body band nor a separate header accent.
                assert header_band is None
                unbanded_count += 1
                continue
            banded_count += 1
            # The drawn group band's bounds contain its own header row. A
            # banded group paints no separate header-band primitive (it would
            # only double-tint the header row its own band already covers,
            # see the design correction), so the containment is checked
            # against Layout's own recorded header_bounds geometry, which is
            # always present once a group has a header.
            assert header_band is None
            header_block, header_block_size = group.header_bounds[1], group.header_bounds[3]
            assert band.bounds[1] <= header_block + 1e-6
            assert header_block + header_block_size <= band.bounds[1] + band.bounds[3] + 1e-6
        assert banded_count > 0
        if decoration == "alternate":
            assert unbanded_count > 0


def test_group_header_text_uses_the_groupheader_theme_role(tmp_path):
    """Issue #481 criterion 3: group-header text uses the Theme's groupHeader role."""
    root = _root()
    theme = yaml.safe_load((root / "examples/controller-z/themes/executive-light.yaml").read_text(encoding="utf-8"))
    theme["body"]["values"]["group-header-test-weight"] = {"type": "fontWeight", "value": 700}
    theme["body"]["roles"]["groupHeader"] = {**theme["body"]["roles"]["groupHeader"],
                                             "fontWeight": "group-header-test-weight"}
    theme_path = tmp_path / "theme.yaml"
    theme_path.write_text(yaml.safe_dump(theme, sort_keys=False), encoding="utf-8")

    rendered = render_review(_draft_request(theme_path=theme_path))
    by_id = {item.scene_id: item for item in rendered.surface.primitives}
    header = by_id["group-header:fw-team"]
    body_text = by_id["cell:firmware:Workstream"]
    assert header.text_layout.weight == 700
    assert header.text_layout.weight != body_text.text_layout.weight


def test_group_header_text_requires_a_declared_groupheader_role(tmp_path):
    """A Theme missing the required groupHeader role fails closed, never a silent text-role fallback."""
    root = _root()
    theme = yaml.safe_load((root / "examples/controller-z/themes/executive-light.yaml").read_text(encoding="utf-8"))
    del theme["body"]["roles"]["groupHeader"]
    theme_path = tmp_path / "theme.yaml"
    theme_path.write_text(yaml.safe_dump(theme, sort_keys=False), encoding="utf-8")

    with pytest.raises(RenderFailed, match="E_THEME_ROLE_REQUIRED"):
        render_review(_draft_request(theme_path=theme_path))


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
