from pathlib import Path

import pytest

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.model.design_summary import DesignSummaryError, summarize_presentation


ROOT = Path(__file__).parents[5]


def _draft(view: str = "executive"):
    base = ROOT / "examples/controller-z"
    return resolve_draft_render(
        project_path=base / "project.yaml", view_path=base / "views" / f"{view}.yaml",
        theme_path=base / "themes/executive-light.yaml", scheme_path=base / "schemes/executive-light.yaml",
        layout_path=base / "layouts/executive-review.yaml", actual_path=base / "actual.yaml",
    ).closure


def test_summary_is_read_only_finite_projection_with_resource_sources():
    summary = summarize_presentation(_draft())
    value = summary.as_data()

    assert value["format"] == "chrona/presentation-design-summary/v0.1"
    assert value["provenance"]["view"]["kind"] == "view"
    assert value["dimensions"]["content"]["surface"]["value"] == "table-timeline"
    assert value["dimensions"]["composition"]["slots"]["source"]["kind"] == "layout-profile"
    assert "start" not in value["dimensions"]["content"]["window"]["value"]
    assert "coordinates" not in str(value)
    with pytest.raises(TypeError):
        summary.dimensions["content"]["window"].value["mode"] = "derived"  # type: ignore[index]


def test_summary_distinguishes_effective_presentation_resources_without_rendering():
    executive = summarize_presentation(_draft("executive")).as_data()
    plan_only = summarize_presentation(_draft("plan-only")).as_data()

    assert executive["dimensions"]["content"]["comparison"]["value"] != plan_only["dimensions"]["content"]["comparison"]["value"]
    assert executive["dimensions"]["content"]["comparison"]["source"]["contentIdentity"] != plan_only["dimensions"]["content"]["comparison"]["source"]["contentIdentity"]


def test_summary_rejects_missing_effective_resource():
    closure = _draft()
    incomplete = type(closure)(closure.context, tuple(item for item in closure.resources if item.kind != "theme"), closure.resolved_theme)
    with pytest.raises(DesignSummaryError, match="E_DESIGN_SUMMARY_INPUT"):
        summarize_presentation(incomplete)
