"""Padding-only leading calendar buckets are absent from realized SVG axes (#1855)."""
from datetime import date

import pytest

from chrona.resources import builtin_preset_source_root, safe_load
from tests.integration.test_ja_jp_builtin_wording import _font_descriptor
from tests.support.synthetic_review import bundle, project, render, span


def test_october_plan_does_not_emit_a_thinned_padding_only_q3_axis_label(tmp_path):
    parts = bundle()
    parts["view"]["body"]["axis"]["tiers"] = [
        {"unit": "quarter", "every": 1, "role": "band"},
        {"unit": "quarter", "every": 1, "role": "grid-major"},
        {"unit": "quarter", "every": 1, "role": "labels", "typographyRole": "axisQuarter",
         "label": {"form": "year-quarter", "align": "center", "overflow": "thin-with-record",
                   "orientation": "horizontal"}},
        {"unit": "month", "every": 1, "role": "grid-minor"},
    ]
    rendered = render(
        tmp_path,
        project({"task": span("task", date(2026, 10, 5), 220)}),
        presentation=parts, locale="ja-JP", font_metrics_path=_font_descriptor(tmp_path),
    )
    svg = rendered.artifact.content.decode("utf-8")
    diagnostics = rendered.scene.diagnostics

    surface = rendered.scene.surfaces[0]
    assert surface.scale_manifest.domain_start == date(2026, 9, 13)
    assert not any(diagnostic.startswith("W_LAYOUT_AXIS_LABEL_THINNED:axis-label:2:0")
                   for diagnostic in diagnostics)
    scene_ids = {primitive.scene_id for primitive in surface.primitives}
    assert "axis-label:2:0" not in scene_ids
    assert "axis-label:2:1" in scene_ids
    assert 'data-scene-id="axis-label:2:1"' in svg
    assert 'data-scene-id="axis-label:2:0"' not in svg
    assert "2026" in svg and "2027" in svg


@pytest.mark.parametrize("design", ["marquee", "titlecard", "yuya"])
def test_target_design_axis_keeps_padding_only_period_out_of_actual_svg(tmp_path, design):
    preset_root = builtin_preset_source_root("presets/bundles/design-default")
    design_root = builtin_preset_source_root(f"designs/{design}")
    view = safe_load(preset_root.joinpath("view.yaml").read_bytes())
    view["body"]["window"] = {"mode": "selected-planned"}
    parts = {
        "view": view,
        "theme": safe_load(design_root.joinpath("theme.yaml").read_bytes()),
        "scheme": safe_load(design_root.joinpath("scheme.yaml").read_bytes()),
        "layout": safe_load(design_root.joinpath("layout.yaml").read_bytes()),
    }
    layout_tiers = parts["layout"]["viewDefaults"]["axis"]["tiers"]
    quarter_label_index = next(
        index for index, tier in enumerate(layout_tiers)
        if tier.get("unit") == "quarter" and tier.get("role") == "labels"
    )
    summary_path = design_root.joinpath("summary.yaml")
    summary = (safe_load(summary_path.read_bytes()) if summary_path.is_file() else None)
    icon_root = builtin_preset_source_root("icons")
    catalogs = tuple(icon_root.joinpath(name) for name in (
        "chrona-target-parts-v2026-10-09.yaml",
        "chrona-annotation-parts-v2026-10-09.yaml",
    ))
    design_tmp = tmp_path / design
    design_tmp.mkdir()

    rendered = render(
        design_tmp,
        project({"task": span("task", date(2026, 10, 5), 220)}),
        presentation=parts, summary=summary, icon_catalogs=catalogs,
        visual_profile="chrona-output/visual/v0.7-svg", locale="ja-JP",
        font_metrics_path=_font_descriptor(design_tmp),
    )
    svg = rendered.artifact.content.decode("utf-8")
    surface = rendered.scene.surfaces[0]

    assert surface.scale_manifest.domain_start == date(2026, 9, 13)
    assert not any(diagnostic.startswith(
        f"W_LAYOUT_AXIS_LABEL_THINNED:axis-label:{quarter_label_index}:0")
        for diagnostic in rendered.scene.diagnostics)
    scene_ids = {primitive.scene_id for primitive in surface.primitives}
    assert f"axis-label:{quarter_label_index}:0" not in scene_ids
    assert f"axis-label:{quarter_label_index}:1" in scene_ids
    assert f'data-scene-id="axis-label:{quarter_label_index}:0"' not in svg
    assert f'data-scene-id="axis-label:{quarter_label_index}:1"' in svg
