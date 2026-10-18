"""Finite legend keys borrow Theme ink; Layout owns all geometry (#1562)."""
from copy import deepcopy
from datetime import date
from decimal import Decimal

import pytest

from tests.support import synthetic_review as sr
from chrona.presentation.layout.surface_legend import LegendArrangement, legend_source_input, swatch_extent
from chrona.presentation.model.surface_content import SurfaceLegendEntry
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.color_scheme import resolve_theme
from chrona.presentation.layout.mark_geometry import symbol_parts


def _parts():
    parts = sr.bundle("executive-light")
    body = parts["theme"]["body"]
    body["roles"]["calendar-closed"]["strokeWidth"] = "stroke-width"
    body["colorBindings"]["calendar-closed.stroke"] = "text"
    return parts


def _render(path, *, shape=None, role="planned", parts=None):
    path.mkdir()
    dependency = role == "dependency"
    relations = ([{"id": "dependency-a-b", "type": "dependency", "lag": "0d",
                   "from": {"object": "a", "endpoint": "end"},
                   "to": {"object": "b", "endpoint": "start"}}]
                 if dependency else [])
    objects = {"a": sr.span("a", date(2026, 2, 2), 20)}
    objects["b" if dependency else "g"] = (sr.span("b", date(2026, 2, 25), 10)
                                              if dependency else sr.point("g", date(2026, 2, 25)))
    source = sr.with_calendar(sr.project(objects, relations))
    entry = {"role": role, "label": role}
    if shape is not None:
        entry["swatchShape"] = shape
    detail = {"version": "chrona/review-detail-profile/v0.1", "id": "shape-detail",
              "body": {"legend": [entry]}}
    actual = ({"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "shape-actual",
               "body": {"asOf": "2026-02-20", "observations": []}}
              if role == "asOf" else None)
    return sr.render(path, source, presentation=parts or _parts(), detail=detail, actual=actual)


@pytest.mark.parametrize("role", ["planned", "milestone", "dependency", "asOf", "calendar-closed"])
def test_circle_borrows_keyed_fill_or_stroke_ink_and_has_completed_geometry(tmp_path, role):
    before = _render(tmp_path / "before", role=role)
    after = _render(tmp_path / "after", shape="circle", role=role)
    old = next(item for item in before.surface.primitives if item.scene_id == f"legend-swatch:{role}")
    circle = next(item for item in after.surface.primitives if item.scene_id == old.scene_id)
    assert circle.kind == "Symbol"
    assert circle.symbol.outline[-1].points[-1] == circle.symbol.outline[0].points[0]
    assert sum(command.kind == "quadratic" for command in circle.symbol.outline) == 4
    assert circle.bounds[2] == circle.bounds[3]
    assert circle.paint.fill == (old.paint.fill or old.paint.stroke)
    assert circle.paint.stroke is None
    assert circle.legend_swatch_shape is None
    assert circle.paint.opacity == old.paint.opacity


def test_rule_pair_has_two_vertical_completed_strokes_with_keyed_ink(tmp_path):
    result = _render(tmp_path / "pair", shape="rule-pair", role="calendar-closed")
    pair = next(item for item in result.surface.primitives if item.scene_id == "legend-swatch:calendar-closed")
    assert pair.kind == "Path" and pair.paint.fill is None
    assert [command.kind for command in pair.path_commands] == ["move", "line", "move", "line"]
    for move, line in zip(pair.path_commands[::2], pair.path_commands[1::2]):
        assert move.points[0][0] == line.points[0][0]
        assert move.points[0][1] < line.points[0][1]
    assert pair.legend_swatch_shape is None


def test_absent_shape_preserves_legacy_primitives_and_svg_bytes(tmp_path):
    first = _render(tmp_path / "first")
    second = _render(tmp_path / "second", shape=None)
    assert first.artifact.content == second.artifact.content
    assert first.surface == second.surface


def test_theme_default_applies_to_detail_without_shape_and_detail_override_wins(tmp_path):
    parts = _parts()
    parts["theme"]["body"]["roles"]["legend-swatch"] = {"swatchShape": "rule-pair"}
    (tmp_path / "inherited").mkdir()
    inherited = sr.render(
        tmp_path / "inherited",
        sr.with_calendar(sr.project({"a": sr.span("a", date(2026, 2, 2), 20)})),
        presentation=parts,
        detail={"version": "chrona/review-detail-profile/v0.1", "id": "shape-detail",
                "body": {"legend": [{"role": "planned", "label": "Planned"}]}},
    )
    pair = next(item for item in inherited.surface.primitives if item.scene_id == "legend-swatch:planned")
    assert pair.kind == "Path"
    assert pair.legend_swatch_shape is None  # Scene remains shape-neutral after Layout completion.

    overridden = _render(tmp_path / "overridden", parts=parts, shape="circle")
    circle = next(item for item in overridden.surface.primitives if item.scene_id == "legend-swatch:planned")
    assert circle.kind == "Symbol" and circle.bounds[2] == circle.bounds[3]


def test_theme_default_applies_to_generated_scale_keys_and_uses_drawn_extent(tmp_path):
    parts = _parts()
    parts["theme"]["body"]["roles"]["legend-swatch"] = {"swatchShape": "circle"}
    parts["theme"]["body"]["colorScales"] = {
        "owners": {"slots": {"a": "default", "b": "capabilities-band"}},
    }
    parts["view"]["body"]["colorEncoding"] = {
        "scale": "owners", "target": "planned", "source": {"field": "owner"}, "domain": ["a", "b"],
    }
    source = sr.with_calendar(sr.project({
        "a": sr.span("a", date(2026, 2, 2), 20, owner="a"),
        "b": sr.span("b", date(2026, 2, 4), 18, owner="b"),
        "c": sr.span("c", date(2026, 2, 6), 16),
    }))
    result = sr.render(
        tmp_path,
        source,
        presentation=parts,
        detail={"version": "chrona/review-detail-profile/v0.1", "id": "scale-detail",
                "body": {"legend": [{"role": "planned", "label": "Planned", "swatchShape": "rule-pair"}]}},
    )
    keys = [item for item in result.surface.primitives if item.scene_id.startswith("legend-swatch:scale:owners:")]
    assert len(keys) == 2
    assert all(item.kind == "Symbol" and item.bounds[2] == item.bounds[3] for item in keys)
    assert not any(item.scene_id == "legend-swatch:planned" for item in result.surface.primitives)


def test_theme_circle_default_uses_the_same_extent_for_measurement_and_emission(tmp_path):
    parts = _parts()
    parts["theme"]["body"]["values"]["large-swatch-block"] = {"type": "number", "value": 22}
    parts["theme"]["body"]["roles"]["legend-swatch"] = {
        "swatchShape": "circle", "swatchBlockSize": "large-swatch-block",
    }
    resolved = resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="synthetic")
    tokens = ThemeTokenView(resolved)
    legend_size = float(tokens.text_treatment("legend").font_size)
    inline, block, bucket = swatch_extent("planned", tokens, 42.0, legend_size)
    content = legend_source_input(
        (SurfaceLegendEntry("planned", "Planned"),), tokens=tokens, mark_block_size=42.0,
        font_metrics=None, arrangement=LegendArrangement(),
    )
    assert (inline, block, bucket) == (22.0, 22.0, "circle")
    assert content.runs[0].inline_advance == Decimal(str(inline + legend_size * 0.4))

    result = _render(tmp_path / "circle", parts=parts)
    circle = next(item for item in result.surface.primitives if item.scene_id == "legend-swatch:planned")
    assert circle.kind == "Symbol" and circle.bounds[2:] == (22.0, 22.0)


def test_existing_symbol_size_token_is_track_relative_and_independent_of_bar_height(tmp_path):
    parts = _parts()
    parts["theme"]["body"]["values"]["bar-height"] = {"type": "number", "value": 0.5}
    parts["theme"]["body"]["values"]["bar-offset"] = {"type": "number", "value": 0.25}
    parts["theme"]["body"]["roles"]["planned"].update(markHeight="bar-height", markOffset="bar-offset")
    larger = deepcopy(parts)
    body = larger["theme"]["body"]
    body["values"]["gate-height"] = {"type": "number", "value": 0.9}
    body["values"]["gate-offset"] = {"type": "number", "value": 0.05}
    body["roles"]["planned"].update(symbolHeight="gate-height", symbolOffset="gate-offset")
    before = _render(tmp_path / "before", parts=parts)
    after = _render(tmp_path / "after", parts=larger)
    def marks(result, source):
        return next(item for item in result.surface.primitives if item.source_ref == source and item.purpose == "planned")
    assert marks(after, "a").bounds[3] == marks(before, "a").bounds[3]
    assert marks(after, "g").bounds[3] > marks(before, "g").bounds[3]
    assert marks(after, "g").bounds[3] > marks(after, "a").bounds[3]


@pytest.mark.parametrize("shape", ["circle", "square", "chevron"])
def test_positive_mark_radius_never_replaces_a_declared_native_point_shape(tmp_path, shape):
    parts = _parts()
    body = parts["theme"]["body"]
    symbol_token = body["roles"]["milestoneSymbol"]["symbol"]
    body["values"][symbol_token]["value"] = {"shape": shape}
    body["values"]["point-radius"] = {"type": "number", "value": 0.25}
    body["roles"]["planned"]["markCornerRadius"] = "point-radius"
    result = _render(tmp_path / shape, parts=parts)
    point = next(item for item in result.surface.primitives if item.source_ref == "g" and item.purpose == "planned")
    assert point.corner_radius > 0
    assert point.symbol.outline == symbol_parts({"shape": shape}, point.bounds)[0].commands
