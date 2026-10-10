"""Truncated axis-band labels stay within their own painted cell (#1291)."""
from __future__ import annotations

from datetime import date
from xml.etree import ElementTree

import pytest

from tests.support import synthetic_review as sr


@pytest.mark.parametrize(
    ("window", "edge"),
    [
        (("2026-01-01", "2027-04-05"), "end"),
        (("2026-03-25", "2027-07-01"), "start"),
    ],
)
def test_truncated_quarter_labels_fit_their_band_and_plot_and_keep_svg_viewport(tmp_path, window, edge):
    parts = sr.bundle("executive-light")
    parts["view"]["body"]["window"] = {"mode": "explicit", "start": window[0], "end": window[1]}
    parts["view"]["body"]["axis"]["tiers"] = [
        {"unit": "quarter", "every": 1, "role": "band", "typographyRole": "axisQuarter"},
        {
            "unit": "quarter",
            "every": 1,
            "role": "labels",
            "typographyRole": "axisQuarter",
            "label": {
                "form": "year-quarter",
                "align": "center",
                "overflow": "visible-overflow",
                "orientation": "horizontal",
            },
        },
    ]
    start = date.fromisoformat(window[0])
    rendered = sr.render(
        tmp_path,
        sr.project({"task": sr.span("task", start, 14)}),
        presentation=parts,
        viewport=(1600, 900),
    )

    labels = {
        item.scene_id: item
        for item in rendered.surface.primitives
        if item.scene_id.startswith("axis-label:1:")
    }
    bands = {
        item.scene_id: item
        for item in rendered.surface.primitives
        if item.scene_id.startswith("axis-band-rect:0:")
    }
    assert len(labels) >= 3, "fixture needs fitting middle quarters as well as the truncated edge"
    assert bands
    timeline = next(slot for slot in rendered.surface.slots if slot.slot_id == "timeline")
    plot_inline, _, plot_width, _ = timeline.bounds

    # Every emitted label is fully inside its same-index quarter cell and the plot.
    for scene_id, label in labels.items():
        index = scene_id.rsplit(":", 1)[1]
        band = bands[f"axis-band-rect:0:{index}"]
        x, _, width, _ = label.bounds
        band_x, _, band_width, _ = band.bounds
        assert x >= band_x - 1e-6, scene_id
        assert x + width <= band_x + band_width + 1e-6, scene_id
        assert x >= plot_inline - 1e-6, scene_id
        assert x + width <= plot_inline + plot_width + 1e-6, scene_id

    indexes = sorted(int(scene_id.rsplit(":", 1)[1]) for scene_id in bands)
    edge_index = indexes[0] if edge == "start" else indexes[-1]
    assert f"axis-label:1:{edge_index}" not in labels
    assert any(
        diagnostic.startswith(f"W_LAYOUT_AXIS_LABEL_THINNED:axis-label:1:{edge_index}:")
        for diagnostic in rendered.surface.diagnostics
    )

    svg = ElementTree.fromstring(rendered.artifact.content)
    assert float(svg.attrib["width"]) == pytest.approx(1600)
