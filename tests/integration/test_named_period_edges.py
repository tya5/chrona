"""Named-period single/double edge rules and nominal fit contract (#871)."""
from __future__ import annotations

from datetime import date

import pytest
from xml.etree import ElementTree

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_backgrounds import validate_background_shapes
from chrona.presentation.layout.surface_quality import ShapePlacement
from chrona.presentation.model.closure import ClosureError
from chrona.presentation.color_scheme import resolve_theme
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.layout.surface_periods import compose_period_decoration
from chrona.resources import schema_validator
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr


def _parts(*, rules: dict[str, str] | None = None, treatment: str = "fill",
           width: int = 4, gap: int | None = None) -> dict:
    parts = sr.bundle("executive-light")
    theme = parts["theme"]["body"]
    for target in ("period-band.fill", "period-band.stroke"):
        theme["colorBindings"].pop(target, None)
    role = {"backgroundTreatment": treatment, "backgroundPaintOrder": 11,
            "opacity": "opacity.axis-band"}
    if rules is not None:
        role["edgeRules"] = dict(rules)
        role["strokeWidth"] = "period-edge-width"
        theme["values"]["period-edge-width"] = {"type": "number", "value": width}
        theme["colorBindings"]["period-band.stroke"] = "text"
        if gap is not None:
            role["doubleRuleGap"] = "period-edge-gap"
            theme["values"]["period-edge-gap"] = {"type": "number", "value": gap}
    if treatment == "fill":
        theme["colorBindings"]["period-band.fill"] = "accent"
    theme["roles"]["period-band"] = role
    parts["view"]["body"]["window"] = {
        "mode": "explicit", "start": "2026-01-01", "end": "2026-04-01"}
    parts["view"]["body"]["periods"] = [{"id": "window"}]
    return parts


def _source(*, outside: bool = False) -> dict:
    source = sr.project({"a": sr.span("a", date(2026, 1, 5), 40)})
    source["periods"] = {
        "window": {"start": "2025-01-01", "end": "2025-02-01"}
        if outside else {"start": "2026-02-01", "end": "2026-03-01"}}
    return source


def _render(tmp_path, *, parts: dict, source: dict | None = None):
    directory = tmp_path / "render"
    directory.mkdir(parents=True)
    return sr.render(directory, source or _source(), presentation=parts)


def _period_shapes(rendered):
    return [item for item in rendered.surface.primitives if item.purpose == "period-band"]


def _tokens(parts: dict) -> ThemeTokenView:
    resolved = resolve_theme(parts["theme"], parts["scheme"],
                             scheme_content_identity="sha256:" + "0" * 64)
    return ThemeTokenView(resolved)


def test_theme_schema_accepts_only_nonempty_closed_edge_rule_maps():
    parts = _parts(rules={"top": "single"})
    schema_validator("theme-v0.15.schema.yaml").validate(parts["theme"])
    for invalid in ({}, {"left": "single"}, {"top": "triple"}, {"top": "single", "extra": "double"}):
        parts["theme"]["body"]["roles"]["period-band"]["edgeRules"] = invalid
        assert not schema_validator("theme-v0.15.schema.yaml").is_valid(parts["theme"]), invalid


def test_layout_completes_exact_edge_offsets_and_host_channel_masks():
    bounds = Rect(10, 20, 80, 50)
    parts = _parts(rules={"top": "single", "bottom": "double"}, gap=3)
    completed = compose_period_decoration(
        bounds=bounds, placement_id="period-band:window", source_ref="window",
        visual_role="period-band", slot_id="timeline", paint_order=11,
        theme_tokens=_tokens(parts))
    host, *paths = completed
    assert host.kind == "Rect" and host.paint_channels == "fill"
    assert [item.kind for item in paths] == ["Path", "Path", "Path"]
    assert all(item.paint_channels == "stroke" for item in paths)
    edges = {":".join(item.placement_id.rsplit(":", 2)[-2:]): item for item in paths}
    assert all(item.placement_id.startswith("period-edge:") for item in paths)
    assert all(item.placement_id ==
               f"period-edge:{len('period-band:window')}:period-band:window:{side}:{line}"
               for side, line in (("top", 0), ("bottom", 0), ("bottom", 1))
               for item in (edges[f"{side}:{line}"],))
    assert edges["top:0"].points == ((12.0, 22.0), (88.0, 22.0))
    assert edges["bottom:0"].points == ((12.0, 68.0), (88.0, 68.0))
    assert edges["bottom:1"].points == ((12.0, 61.0), (88.0, 61.0))


def test_layout_outline_rule_helper_omits_a_full_rect_host():
    parts = _parts(rules={"start": "single"}, treatment="outline")
    completed = compose_period_decoration(
        bounds=Rect(10, 20, 80, 50), placement_id="period-band:window",
        source_ref="window", visual_role="period-band", slot_id="timeline",
        paint_order=11, theme_tokens=_tokens(parts))
    assert len(completed) == 1 and completed[0].kind == "Path"
    assert completed[0].paint_channels == "stroke"


def test_single_and_double_edges_are_separate_paths_with_stroke_only_paint(tmp_path):
    rendered = _render(tmp_path, parts=_parts(rules={
        "top": "single", "bottom": "double", "start": "single", "end": "double"}, gap=3))
    shapes = _period_shapes(rendered)
    (host,) = [item for item in shapes if item.kind == "Rect"]
    edges = [item for item in shapes if item.kind == "Path"]
    assert host.scene_id == "period-band:window"
    assert host.paint.fill and host.paint.stroke is None
    assert len(edges) == 6
    assert all(item.source_ref == "window" and item.visual_role == "period-band" for item in edges)
    assert all(item.paint.fill is None and item.paint.stroke and item.paint.stroke_width == 4 for item in edges)
    bounds = host.bounds
    by_id = {":".join(item.scene_id.rsplit(":", 2)[-2:]): item for item in edges}
    top = by_id["top:0"]
    assert top.points[0] == pytest.approx((bounds[0] + 2, bounds[1] + 2))
    assert top.points[1] == pytest.approx((bounds[0] + bounds[2] - 2, bounds[1] + 2))
    bottom_lines = sorted((item.points[0][1] for item in edges
                           if item.scene_id.endswith((":bottom:0", ":bottom:1"))), reverse=True)
    assert bottom_lines == pytest.approx((bounds[1] + bounds[3] - 2,
                                         bounds[1] + bounds[3] - 9))
    start = by_id["start:0"]
    assert start.points[0][0] == pytest.approx(bounds[0] + 2)
    assert start.points[0][1] == pytest.approx(bounds[1] + 2)
    assert start.points[1][1] == pytest.approx(bounds[1] + bounds[3] - 2)


def test_edge_ids_are_length_framed_and_cannot_alias_colon_bearing_host_ids():
    parts = _parts(rules={"top": "single"})
    tokens = _tokens(parts)
    bounds = Rect(0, 0, 80, 50)
    edges = compose_period_decoration(
        bounds=bounds, placement_id="period-band:x", source_ref="x",
        visual_role="period-band", slot_id="timeline", paint_order=11,
        theme_tokens=tokens)
    edge_id = edges[-1].placement_id
    colon_bearing_host_id = "period-band:x:edge:top:0"
    assert edge_id == f"period-edge:{len('period-band:x')}:period-band:x:top:0"
    assert edge_id != colon_bearing_host_id
    assert len({edge_id, colon_bearing_host_id}) == 2


def test_catalogue_pattern_pigment_survives_fill_only_period_host_with_edges(tmp_path):
    from tests.integration.test_named_periods import (
        STARTER_CATALOG,
        _bands,
        _parts as period_parts,
        _render as render_period,
    )

    parts = period_parts(preset="technical-print", pattern="starter-halftone")
    role = parts["theme"]["body"]["roles"]["period-band"]
    role["edgeRules"] = {"top": "single"}
    role["strokeWidth"] = "period-edge-width"
    parts["theme"]["body"]["values"]["period-edge-width"] = {"type": "number", "value": 2}
    rendered = render_period(tmp_path, parts=parts, catalogs=(STARTER_CATALOG,))

    (host,) = [item for item in _bands(rendered) if item.kind == "Rect"]
    edges = [item for item in _bands(rendered) if item.kind == "Path"]
    assert host.pattern is not None and host.pattern.primitives
    assert host.paint.fill is not None and host.paint.stroke is not None
    assert len(edges) == 1 and edges[0].paint.fill is None and edges[0].paint.stroke

    svg = ElementTree.fromstring(rendered.artifact.content)
    host_element = next(node for node in svg.iter()
                        if node.attrib.get("data-scene-id") == host.scene_id)
    assert host_element.tag.endswith("rect")
    assert host_element.attrib.get("stroke") is None
    assert host_element.attrib["fill"].startswith("url(#pattern-")
    assert any(node.tag.endswith("circle") and node.attrib.get("fill") == host.paint.stroke
               for node in svg.iter())


def test_catalogue_pattern_stroke_geometry_stays_forbidden_without_period_edges(tmp_path):
    from tests.integration.test_named_periods import (
        STARTER_CATALOG,
        _parts as period_parts,
        _render as render_period,
    )

    parts = period_parts(preset="technical-print", pattern="starter-halftone")
    parts["theme"]["body"]["roles"]["period-band"]["strokeWidth"] = "stroke-width"
    with pytest.raises(ClosureError) as raised:
        render_period(tmp_path, parts=parts, catalogs=(STARTER_CATALOG,))
    assert (raised.value.diagnostic_id, raised.value.source_ref) == (
        "E_THEME_ROLE_PROPERTY_UNSUPPORTED", "/body/roles/period-band/strokeWidth")


def test_outline_edge_treatment_emits_only_selected_paths(tmp_path):
    outline = _period_shapes(_render(tmp_path, parts=_parts(
        rules={"top": "single", "bottom": "single"}, treatment="outline")))
    assert outline and all(item.kind == "Path" for item in outline)
    assert len(outline) == 2


def test_none_treatment_with_edge_rules_is_refused_at_the_rule_pointer(tmp_path):
    with pytest.raises(ClosureError) as raised:
        _render(tmp_path, parts=_parts(rules={"top": "single"}, treatment="none"))
    assert (raised.value.diagnostic_id, raised.value.source_ref) == (
        "E_THEME_ROLE_PROPERTY_UNSUPPORTED", "/body/roles/period-band/edgeRules")


@pytest.mark.parametrize("rules,gap,expected_code,expected_pointer", [
    ({"top": "double"}, None, "E_THEME_ROLE_REQUIRED", "/body/roles/period-band/doubleRuleGap"),
    ({"top": "single"}, 3, "E_THEME_ROLE_PROPERTY_UNSUPPORTED", "/body/roles/period-band/doubleRuleGap"),
])
def test_double_gap_is_conditional_and_metadata_fails_even_when_period_is_clipped(
        tmp_path, rules, gap, expected_code, expected_pointer):
    with pytest.raises(ClosureError) as raised:
        _render(tmp_path, parts=_parts(rules=rules, gap=gap), source=_source(outside=True))
    assert (raised.value.diagnostic_id, raised.value.source_ref) == (expected_code, expected_pointer)


def test_rule_paths_refuse_when_nominal_ink_cannot_fit_the_clipped_band(tmp_path):
    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, parts=_parts(rules={"start": "single"}, width=10000))
    assert raised.value.code == "E_LAYOUT_PERIOD_EDGE_SIZE"
    assert raised.value.source_ref == "/body/roles/period-band/edgeRules"
    assert "tangential extent" in raised.value.message


def test_stroke_only_paths_do_not_enter_translucent_background_overlap_checks():
    class Tokens:
        def background(self, _role):
            return "fill", 10

        def opacity(self, _role):
            return 0.5

    bounds = Rect(0, 0, 20, 20)
    edge = ShapePlacement("period:p:edge:top:0", "p", "Path", bounds,
                          ((0.0, 0.0), (20.0, 0.0)), paint_order=10,
                          semantic_id="periodBand", visual_role="period-band",
                          paint_channels="stroke")
    calendar = ShapePlacement("calendar-closed:d", "project-calendar", "Rect", bounds,
                              paint_order=10, semantic_id="calendarClosed")
    validate_background_shapes((edge, calendar), Tokens())

    host = ShapePlacement("period-band:p", "p", "Rect", bounds,
                          paint_order=10, semantic_id="periodBand", visual_role="period-band",
                          paint_channels="fill")
    with pytest.raises(LayoutError) as raised:
        validate_background_shapes((host, calendar), Tokens())
    assert raised.value.diagnostic_id == "E_LAYOUT_BACKGROUND_OVERLAP"


def test_theme_token_reader_validates_positive_width_and_gap(tmp_path):
    for field, value, pointer in (
            ("period-edge-width", 0, "/body/roles/period-band/strokeWidth"),
            ("period-edge-gap", 0, "/body/roles/period-band/doubleRuleGap")):
        parts = _parts(rules={"top": "double"}, gap=2)
        parts["theme"]["body"]["values"][field]["value"] = value
        with pytest.raises(ClosureError) as raised:
            _render(tmp_path / field, parts=parts)
        assert (raised.value.diagnostic_id, raised.value.source_ref) == ("E_THEME_TOKEN_TYPE", pointer)


@pytest.mark.parametrize("missing,pointer", [
    ("strokeWidth", "/body/roles/period-band/strokeWidth"),
    ("stroke", "/body/roles/period-band/stroke"),
])
def test_edge_rules_require_the_selected_role_stroke_and_width(tmp_path, missing, pointer):
    parts = _parts(rules={"top": "single"})
    if missing == "strokeWidth":
        del parts["theme"]["body"]["roles"]["period-band"][missing]
    else:
        del parts["theme"]["body"]["colorBindings"]["period-band.stroke"]
    with pytest.raises(ClosureError) as raised:
        _render(tmp_path, parts=parts)
    assert (raised.value.diagnostic_id, raised.value.source_ref) == ("E_THEME_ROLE_REQUIRED", pointer)
