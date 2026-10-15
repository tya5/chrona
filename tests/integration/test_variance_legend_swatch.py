"""Variance-role legend swatches use their bound fills, not state-text treatment (#1515)."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from xml.etree import ElementTree

from chrona.presentation.scene.contrast_policy import POLICY_MEMBERS
from tests.support import synthetic_review as sr


ROOT = Path(__file__).resolve().parents[2]
STARTER_CATALOG = ROOT / "src/chrona/resources/icons/chrona-theme-starter-v2026-10-09.yaml"

ENTRIES = {
    "variance-ahead": ("Early", "#2E6B3E"),
    "variance-on-track": ("On schedule", "#444444"),
    "variance-behind": ("Overrun", "#B3241C"),
}


def test_technical_print_variance_legend_rects_use_bound_inks_under_strict_contrast(tmp_path):
    parts = sr.bundle("technical-print")
    parts["theme"]["body"]["contrastPolicy"] = {member: "error" for member in POLICY_MEMBERS}
    source = sr.project({"task": sr.span("task", date(2026, 2, 2), 10)})
    detail = {
        "version": "chrona/review-detail-profile/v0.1",
        "id": "variance-legend",
        "body": {"legend": [
            {"role": role, "label": label}
            for role, (label, _color) in ENTRIES.items()
        ]},
    }

    rendered = sr.render(tmp_path, source, presentation=parts, detail=detail,
                         icon_catalogs=(STARTER_CATALOG,), viewport=(1800, 1000))
    svg = ElementTree.fromstring(rendered.artifact.content)
    svg_rects = {
        node.attrib.get("data-scene-id"): node.attrib.get("fill")
        for node in svg.iter()
        if node.tag.endswith("rect") and node.attrib.get("data-scene-id")
    }
    swatches = {
        item.visual_role: item for item in rendered.surface.primitives
        if item.scene_id.startswith("legend-swatch:variance-")
    }

    # These Detail entries are explicit and are retained despite there being no Actual Set or variance data.
    assert not [item for item in rendered.surface.primitives if item.purpose == "actual"]
    assert set(swatches) == set(ENTRIES)
    for role, (_label, color) in ENTRIES.items():
        swatch = swatches[role]
        assert swatch.kind == "Rect"
        assert swatch.purpose == "legend-swatch"
        assert swatch.contrast_treatment is None
        assert swatch.paint.fill == color
        assert svg_rects[swatch.scene_id] == color

    # Strict policy would raise on any mark/text floor miss; no lenient warnings are expected either.
    assert rendered.contrast_warnings == ()
