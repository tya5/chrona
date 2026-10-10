"""Full-pipeline shape chips for period labels and finish-delta labels (#1286)."""
from __future__ import annotations

from datetime import date
from pathlib import Path
import re

import pytest
import yaml

from tests.support import synthetic_review as sr


ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = ROOT / "src/chrona/resources/icons/chrona-target-parts-v2026-10-09.yaml"
ACTUAL = {
    "version": "chrona/actual-set/v0.3",
    "kind": "actual-set",
    "id": "observed",
    "body": {
        "asOf": "2026-04-30",
        "observations": [{
            "id": "alpha-observed", "sequence": 1, "projectObjectId": "alpha",
            "actual": {"start": "2026-02-02", "finish": "2026-03-10", "progress": 1.0},
        }],
    },
}


def _chip_shape(kind: str) -> dict:
    if kind == "burst":
        return {"kind": "burst", "points": 7, "innerRatio": .7}
    return {
        "kind": "catalog", "glyph": "chrona-target-parts:synthetic-chip",
        "sliceInsets": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "unitEm": .4,
    }


def _catalogue(path: Path) -> Path:
    data = yaml.safe_load(CATALOGUE.read_text(encoding="utf-8"))
    data["body"]["glyphs"]["synthetic-chip"] = {
        "viewport": {"inlineSize": 100, "blockSize": 100},
        "parts": [
            {"paint": "fill", "data": "M0 0L100 0L100 100L0 100Z"},
            {"paint": "fill", "data": "M10 10L90 10L90 90L10 90Z"},
        ],
    }
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _finish_fixture(kind: str) -> tuple[dict, dict]:
    parts = sr.bundle("executive-light")
    theme = parts["theme"]["body"]
    theme["roles"]["finish-delta-chip"] = {
        "backgroundTreatment": "fill", "chipPadding": "chip-padding", "chipShape": "test-chip-shape",
    }
    theme["values"]["test-chip-shape"] = {"type": "chipShape", "value": _chip_shape(kind)}
    theme["colorBindings"]["finish-delta-chip.fill"] = "surfaceRaised"
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["view"]["body"]["visibility"]["labels"]["content"] = ["title"]
    source = sr.project({"alpha": sr.span("alpha", date(2026, 2, 2), 30, title="Alpha", owner="a")})
    return parts, source


def _render_finish(tmp_path: Path, kind: str, catalog: Path | None):
    parts, source = _finish_fixture(kind)
    output = tmp_path / f"finish-{kind}"
    output.mkdir()
    return sr.render(output, source, presentation=parts, actual=ACTUAL,
                     icon_catalogs=(catalog,) if catalog else ())


def _render_period(tmp_path: Path, kind: str, catalog: Path | None):
    from tests.integration.test_named_periods import (
        FEBRUARY, _labelled, _parts, _render, _source,
    )

    parts = _labelled(_parts(), "top", chip=True)
    theme = parts["theme"]["body"]
    theme["values"]["test-chip-shape"] = {"type": "chipShape", "value": _chip_shape(kind)}
    theme["roles"]["period-label-chip"]["chipShape"] = "test-chip-shape"
    return _render(tmp_path, _source(window=FEBRUARY), parts, name=f"period-{kind}",
                   catalogs=(catalog,) if catalog else ())


def _assert_chip_pair(rendered, label_purpose: str, role: str, catalog: bool):
    label, = [item for item in rendered.surface.primitives
              if item.kind == "Text" and item.purpose == label_purpose]
    chip_id = f"chip:{label.scene_id}"
    chips = [item for item in rendered.surface.primitives
             if item.scene_id == chip_id or item.scene_id.startswith(chip_id + ":part")]
    assert chips
    assert chips[0].scene_id == chip_id
    assert chips[0].kind == "Symbol" and chips[0].symbol is not None
    assert chips[0].purpose == "label-chip"
    assert chips[0].visual_role == role
    assert chips[0].source_ref == label.source_ref
    assert chips[0].bounds[0] <= label.bounds[0]
    assert chips[0].bounds[1] <= label.bounds[1]
    assert chips[0].bounds[0] + chips[0].bounds[2] >= label.bounds[0] + label.bounds[2]
    assert chips[0].bounds[1] + chips[0].bounds[3] >= label.bounds[1] + label.bounds[3]
    if label_purpose == "finish-delta":
        assert chips[0].slot_id == label.slot_id
        assert chips[0].lane_row_id == label.lane_row_id
        assert chips[0].lane_member_id == label.lane_member_id
    if catalog:
        assert len(chips) == 2
        assert chips[1].scene_id == chip_id + ":part1"
        assert all(item.symbol is not None for item in chips)
        assert all(item.paint.fill is not None and item.paint.stroke is None for item in chips)
    else:
        assert len(chips) == 1
        assert len(chips[0].symbol.outline) >= 8
    svg = rendered.artifact.content.decode("utf-8")
    for chip in chips:
        match = re.search(rf'<path\b(?=[^>]*data-scene-id="{re.escape(chip.scene_id)}")[^>]*\bd="([^"]+)"', svg)
        assert match and match.group(1)
    return label, chips


@pytest.mark.parametrize("kind", ["burst", "catalog"])
def test_period_label_chip_shape_reaches_scene_and_svg(tmp_path, kind):
    catalog = _catalogue(tmp_path / "period-catalog.yaml") if kind == "catalog" else None
    rendered = _render_period(tmp_path, kind, catalog)
    _assert_chip_pair(rendered, "period-label", "period-label-chip", kind == "catalog")


@pytest.mark.parametrize("kind", ["burst", "catalog"])
def test_finish_delta_chip_shape_reaches_scene_and_svg_with_lane_ownership(tmp_path, kind):
    catalog = _catalogue(tmp_path / "finish-catalog.yaml") if kind == "catalog" else None
    rendered = _render_finish(tmp_path, kind, catalog)
    _assert_chip_pair(rendered, "finish-delta", "finish-delta-chip", kind == "catalog")
