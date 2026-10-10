"""Full-pipeline shape chips for period labels and finish-delta labels (#1286)."""
from __future__ import annotations

from datetime import date
from html import escape
from math import cos, pi, sin, sqrt
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
    if kind in {"burst", "ellipse"}:
        fit = {"fit": "ellipse"} if kind == "ellipse" else {}
        return {"kind": "burst", "points": 7, "innerRatio": .7, **fit}
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


def _assert_chip_pair(rendered, label_purpose: str, role: str, kind: str):
    catalog = kind == "catalog"
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
    if kind == "ellipse":
        points, ratio = 7, .7
        factor = _inradius_factor(points, ratio)
        vertices = tuple(command.points[0] for command in chips[0].symbol.outline[:-1])
        center = (sum(x for x, _y in vertices) / len(vertices),
                  sum(y for _x, y in vertices) / len(vertices))
        axis_x = max(abs(x - center[0]) for x, _y in vertices)
        axis_y = max(abs(y - center[1]) for _x, y in vertices)
        x, y, width, height = label.bounds
        for corner_x in (x, x + width):
            for corner_y in (y, y + height):
                normalized = ((corner_x - center[0]) / axis_x) ** 2 + (
                    (corner_y - center[1]) / axis_y) ** 2
                assert normalized <= factor * factor + 1e-6
                assert _inside_polygon((corner_x, corner_y), vertices)
    svg = rendered.artifact.content.decode("utf-8")
    for chip in chips:
        escaped_id = re.escape(escape(chip.scene_id, quote=True))
        match = re.search(rf'<path\b(?=[^>]*data-scene-id="{escaped_id}")[^>]*\bd="([^"]+)"', svg)
        assert match and match.group(1)
        commands = re.findall(r"([ML])\s*([-+]?(?:\d+\.?\d*|\.\d+))\s+([-+]?(?:\d+\.?\d*|\.\d+))",
                              match.group(1))
        if chip.symbol is not None:
            expected = tuple(("M" if item.kind == "move" else "L", *item.points[0])
                             for item in chip.symbol.outline)
            assert len(commands) == len(expected)
            for actual, wanted in zip(commands, expected):
                assert actual[0] == wanted[0]
                assert float(actual[1]) == pytest.approx(wanted[1], abs=.00051)
                assert float(actual[2]) == pytest.approx(wanted[2], abs=.00051)
    return label, chips


def _inradius_factor(points, ratio):
    theta = pi / points
    if ratio <= cos(theta):
        return ratio
    return ratio * sin(theta) / sqrt(1 + ratio * ratio - 2 * ratio * cos(theta))


def _inside_polygon(point, vertices):
    inside = False
    for start, end in zip(vertices, (*vertices[1:], vertices[0])):
        if (start[1] > point[1]) != (end[1] > point[1]):
            crossing = start[0] + ((point[1] - start[1]) * (end[0] - start[0]) /
                                   (end[1] - start[1]))
            if point[0] < crossing:
                inside = not inside
    return inside


@pytest.mark.parametrize("kind", ["burst", "ellipse", "catalog"])
def test_period_label_chip_shape_reaches_scene_and_svg(tmp_path, kind):
    catalog = _catalogue(tmp_path / "period-catalog.yaml") if kind == "catalog" else None
    rendered = _render_period(tmp_path, kind, catalog)
    _assert_chip_pair(rendered, "period-label", "period-label-chip", kind)


@pytest.mark.parametrize("kind", ["burst", "ellipse", "catalog"])
def test_finish_delta_chip_shape_reaches_scene_and_svg_with_lane_ownership(tmp_path, kind):
    catalog = _catalogue(tmp_path / "finish-catalog.yaml") if kind == "catalog" else None
    rendered = _render_finish(tmp_path, kind, catalog)
    _assert_chip_pair(rendered, "finish-delta", "finish-delta-chip", kind)
