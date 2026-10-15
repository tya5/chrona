"""Packaged quarter/month axis tiers render their own short labels (#1518)."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from xml.etree import ElementTree

import pytest

from chrona.presentation.layout.surface_geometry import GEOMETRY_TOLERANCE
from tests.support import synthetic_review as sr


ROOT = Path(__file__).resolve().parents[2]
STARTER_CATALOG = ROOT / "src/chrona/resources/icons/chrona-theme-starter-v2026-10-09.yaml"
PRESETS = ("technical-print", "muted-executive", "wallboard-dark")
MONTHS = {"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"}


def _tier_index(view, unit: str, role: str) -> int:
    return next(index for index, tier in enumerate(view["body"]["axis"]["tiers"])
                if tier["unit"] == unit and tier["role"] == role)


@pytest.mark.parametrize("preset", PRESETS)
def test_packaged_quarter_and_month_bands_have_visible_short_labels_in_svg(tmp_path, preset):
    parts = sr.bundle(preset)
    view = parts["view"]
    quarter_band_index = _tier_index(view, "quarter", "band")
    quarter_label_index = _tier_index(view, "quarter", "labels")
    month_band_index = _tier_index(view, "month", "band")
    month_label_index = _tier_index(view, "month", "labels")
    view["body"]["window"] = {
        "mode": "explicit", "start": "2026-01-01", "end": "2027-01-01",
    }
    source = sr.project({"year": sr.span("year", date(2026, 1, 1), 365, title="Year")})
    icon_catalogs = (STARTER_CATALOG,) if preset == "technical-print" else ()
    rendered = sr.render(tmp_path, source, presentation=parts, viewport=(1800, 1000),
                         icon_catalogs=icon_catalogs)

    labels = [item for item in rendered.surface.primitives
              if item.scene_id.startswith("axis-label:")]
    quarter_labels = [item for item in labels
                      if item.scene_id.startswith(f"axis-label:{quarter_label_index}:")]
    month_labels = [item for item in labels
                    if item.scene_id.startswith(f"axis-label:{month_label_index}:")]
    bands = {item.scene_id: item for item in rendered.surface.primitives
             if item.scene_id.startswith("axis-band-rect:")}
    quarter_bands = {key: item for key, item in bands.items()
                     if key.startswith(f"axis-band-rect:{quarter_band_index}:")}
    month_bands = {key: item for key, item in bands.items()
                   if key.startswith(f"axis-band-rect:{month_band_index}:")}

    assert [item.text for item in quarter_labels] == ["Q1", "Q2", "Q3", "Q4"]
    assert {item.text for item in month_labels} == MONTHS
    assert len(month_labels) == 12
    assert len(quarter_bands) == 4 and len(month_bands) == 12
    assert len(bands) == 16

    # Each label lane shares its corresponding band lane; the two tiers occupy distinct rows.
    quarter_label_y, quarter_label_h = quarter_labels[0].bounds[1], quarter_labels[0].bounds[3]
    month_label_y, month_label_h = month_labels[0].bounds[1], month_labels[0].bounds[3]
    quarter_band_y, quarter_band_h = next(iter(quarter_bands.values())).bounds[1], next(iter(quarter_bands.values())).bounds[3]
    month_band_y, month_band_h = next(iter(month_bands.values())).bounds[1], next(iter(month_bands.values())).bounds[3]
    assert quarter_band_y <= quarter_label_y
    assert quarter_label_y + quarter_label_h <= quarter_band_y + quarter_band_h
    assert month_band_y <= month_label_y
    assert month_label_y + month_label_h <= month_band_y + month_band_h
    assert quarter_label_y + quarter_label_h / 2 == pytest.approx(quarter_band_y + quarter_band_h / 2)
    assert month_label_y + month_label_h / 2 == pytest.approx(month_band_y + month_band_h / 2)
    assert quarter_band_y + quarter_band_h <= month_band_y + float(GEOMETRY_TOLERANCE)

    svg = ElementTree.fromstring(rendered.artifact.content)
    svg_text = [node for node in svg.iter()
                if node.tag.endswith("text") and node.attrib.get("data-purpose") == "axis-label"]
    svg_by_id = {node.attrib["data-scene-id"]: (node.text or "") for node in svg_text}
    assert {svg_by_id[item.scene_id] for item in quarter_labels} == {"Q1", "Q2", "Q3", "Q4"}
    assert {svg_by_id[item.scene_id] for item in month_labels} == MONTHS
    assert len(svg_text) == len(labels)
    assert not any(item.startswith("W_LAYOUT_AXIS") for item in rendered.surface.diagnostics)
    assert not rendered.contrast_warnings
