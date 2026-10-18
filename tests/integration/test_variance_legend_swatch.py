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
ACTUAL = {
    "version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "variance-swatches",
    "body": {"asOf": "2026-02-20", "observations": [
        {"id": "ahead-observed", "sequence": 1, "projectObjectId": "ahead",
         "actual": {"start": "2026-02-02", "finish": "2026-02-07"}},
        {"id": "track-observed", "sequence": 1, "projectObjectId": "track",
         "actual": {"start": "2026-02-02", "finish": "2026-02-11"}},
        {"id": "behind-observed", "sequence": 1, "projectObjectId": "behind",
         "actual": {"start": "2026-02-02", "finish": "2026-02-14"}},
    ]},
}


def test_technical_print_variance_legend_rects_use_bound_inks_under_strict_contrast(tmp_path):
    parts = sr.bundle("technical-print")
    parts["theme"]["body"]["contrastPolicy"] = {member: "error" for member in POLICY_MEMBERS}
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["view"]["body"]["comparison"]["facets"] = ["planned", "actual", "finishDelta"]
    parts["view"]["body"]["tableColumns"] = [
        {"id": "Task", "source": "title", "missing": "em-dash", "align": "start",
         "width": "content", "headerOrientation": "horizontal"},
        {"id": "Finish delta", "source": {"comparisonFacet": "finishDelta"},
         "format": "signedNumber", "missing": "blank", "align": "end",
         "width": "content", "headerOrientation": "horizontal"},
    ]
    source = sr.project({
        "ahead": sr.span("ahead", date(2026, 2, 2), 10),
        "track": sr.span("track", date(2026, 2, 2), 9),
        "behind": sr.span("behind", date(2026, 2, 2), 7),
    })
    detail = {
        "version": "chrona/review-detail-profile/v0.1",
        "id": "variance-legend",
        "body": {"legend": [
            {"role": role, "label": label}
            for role, (label, _color) in ENTRIES.items()
        ]},
    }

    rendered = sr.render(tmp_path, source, presentation=parts, actual=ACTUAL, detail=detail,
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

    # Each variance key is backed by a realized, bound-ink finish-delta cell.
    actuals = {item.source_ref: item for item in rendered.surface.primitives if item.purpose == "actual"}
    assert {item.source_ref for item in actuals.values()} == {"ahead", "track", "behind"}
    assert {item.visual_role for item in actuals.values()} == {"actual"}
    variance_cells = [item for item in rendered.surface.primitives
                      if item.purpose == "table-cell" and item.visual_role.startswith("variance-")]
    assert {item.visual_role for item in variance_cells} == set(ENTRIES)
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
