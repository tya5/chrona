"""A legend key is a miniature of its mark: a catalogue pattern bound to a role paints the key too (#991, #718).

A Theme role that binds a catalogue pattern (`hatch-wide`) used to crash the legend swatch in Scene
(`_paint_family` knew only the outline and diagonal-hatch forms). Synthetic Project and the packaged
`executive-light` bundle with the packaged `chrona-target-parts` catalogue; no test reads `examples/`.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from tests.support import synthetic_review as sr

ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = ROOT / "src/chrona/resources/icons/chrona-target-parts-v2026-10-09.yaml"
ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
          "body": {"asOf": "2026-07-01", "observations": []}}
DETAIL = {"version": "chrona/review-detail-profile/v0.1", "id": "legend-detail", "body": {"legend": [
    {"role": "planned", "label": "Planned"}, {"role": "missing-actual", "label": "No actual"}]}}


def _parts(ref: str) -> dict:
    parts = sr.bundle("executive-light")
    parts["theme"]["version"] = "chrona/theme/v0.15"
    comparison = parts["view"]["body"]["comparison"]
    comparison["actual"] = "required"
    comparison["facets"].append("missingActual")
    body = parts["theme"]["body"]
    body["values"]["missing.pattern"] = {"type": "pattern", "value": {"kind": "catalog", "ref": ref}}
    role = body["roles"]["missing-actual"]
    role.pop("strokeWidth")  # a pattern role takes its ink from fill and stroke
    role["pattern"] = "missing.pattern"
    return parts


def _render(tmp_path: Path, ref: str):
    source = sr.project({key: sr.span(key, date(2026, 3, 2) + timedelta(days=index * 20), 30)
                         for index, key in enumerate(("a0", "a1"))})
    return sr.render(tmp_path, source, presentation=_parts(ref), actual=ACTUAL, icon_catalogs=(CATALOGUE,), detail=DETAIL)


@pytest.mark.parametrize("name", ["hatch-wide", "hazard-stripes"])
def test_a_catalogue_pattern_on_a_role_paints_the_legend_key_like_the_mark(tmp_path, name):
    rendered = _render(tmp_path, f"chrona-target-parts:{name}")
    by_id = {item.scene_id: item for item in rendered.surface.primitives}
    swatch = by_id["legend-swatch:missing-actual"]
    mark = next(item for item in rendered.surface.primitives if item.scene_id.startswith("missing-actual:"))

    assert swatch.pattern is not None and swatch.pattern.primitives
    assert swatch.pattern.primitives == mark.pattern.primitives
    assert (swatch.pattern.tile_inline_size, swatch.pattern.angle_degrees) == (
        mark.pattern.tile_inline_size, mark.pattern.angle_degrees)
    assert swatch.paint.fill == mark.paint.fill and swatch.paint.stroke == mark.paint.stroke
    svg = rendered.artifact.content.decode()
    assert 'data-scene-id="legend-swatch:missing-actual"' in svg
    # One tile placement per patterned rectangle: two marks and the key.
    assert svg.count("<pattern ") == 3


def test_a_role_without_a_pattern_leaves_the_legend_key_plain(tmp_path):
    parts = _parts("chrona-target-parts:hatch-wide")
    role = parts["theme"]["body"]["roles"]["missing-actual"]
    role.pop("pattern")
    role["strokeWidth"] = "stroke-width"
    source = sr.project({"a0": sr.span("a0", date(2026, 3, 2), 30)})
    rendered = sr.render(tmp_path, source, presentation=parts, actual=ACTUAL, icon_catalogs=(CATALOGUE,), detail=DETAIL)
    swatch = next(item for item in rendered.surface.primitives if item.scene_id == "legend-swatch:missing-actual")
    assert swatch.pattern is None
