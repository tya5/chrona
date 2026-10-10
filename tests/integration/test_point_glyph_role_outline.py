"""A bound point role adds one Layout-completed edge around filled glyph ink (#1287)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document, serialize_scene
from chrona.presentation.model.closure import resolve_draft_render
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderFailed, RenderRequest, render_review
from tests.support import synthetic_review as sr

DETAIL = {"version": "chrona/review-detail-profile/v0.1", "id": "point-outline", "body": {"legend": [
    {"role": "planned", "label": "Plan"}, {"role": "milestone", "label": "Gate"}]}}

CATALOGUE = Path(__file__).resolve().parents[2] / "src/chrona/resources/icons/chrona-target-parts-v2026-10-09.yaml"
SVG_PROFILE = "chrona-output/visual/v0.6-svg"


def _parts(*, stroke: bool = True, width: bool = True, alignment: str | None = None,
           outline_pattern: bool = False, glyph: str = "diamond", row_mode: str = "lanes") -> dict:
    parts = sr.bundle("executive-light")
    body = parts["theme"]["body"]
    glyph_value = (
        {"shape": "glyph", "viewBox": [10, 10],
         "parts": [{"d": "M0 5L5 0L10 5L5 10Z", "paint": "fill"}]}
        if glyph == "inline" else
        {"shape": {"catalog": f"chrona-target-parts:{glyph}"}}
    )
    body["values"]["point-outline-glyph"] = {"type": "symbol", "value": glyph_value}
    body["roles"]["milestoneSymbol"]["symbol"] = "point-outline-glyph"
    body["colorBindings"]["milestone.fill"] = "surface"
    body["colorBindings"]["gate.fill"] = "surface"
    body["roles"]["gate"] = {}
    if row_mode != "lanes":
        parts["view"]["body"]["rows"] = {"mode": row_mode}
    role = body["roles"]["gate"]
    if width:
        body["values"]["point-outline-width"] = {"type": "number", "value": 2}
        role["strokeWidth"] = "point-outline-width"
    if alignment is not None:
        role["strokeAlign"] = alignment
    if outline_pattern:
        body["values"]["point-outline-pattern"] = {"type": "pattern", "value": {"kind": "outline"}}
        role["pattern"] = "point-outline-pattern"
    if stroke:
        body["colorBindings"]["gate.stroke"] = "text"
    return parts


def _render(directory, *, stroke: bool = True, width: bool = True,
            alignment: str | None = None, outline_pattern: bool = False,
            glyph: str = "diamond", row_mode: str = "lanes"):
    directory.mkdir(parents=True, exist_ok=True)
    source = sr.project({
        "work": sr.span("work", date(2026, 2, 2), 30),
        "gate": sr.point("gate", date(2026, 3, 9)),
    }, relations=[{"id": "work-to-gate", "type": "dependency",
                   "from": {"object": "work", "endpoint": "end"},
                   "to": {"object": "gate", "endpoint": "at"}, "lag": "0d"}])
    parts = _parts(stroke=stroke, width=width, alignment=alignment, outline_pattern=outline_pattern,
                   glyph=glyph, row_mode=row_mode)
    paths = {kind: sr._write(directory / f"{kind}.yaml", value) for kind, value in parts.items()}
    draft = resolve_draft_render(
        project_path=sr._write(directory / "project.yaml", source), view_path=paths["view"],
        theme_path=paths["theme"], scheme_path=paths["scheme"], layout_path=paths["layout"],
        detail_path=sr._write(directory / "detail.yaml", DETAIL), icon_catalog_paths=(CATALOGUE,),
        viewport=(1600, 900), target_kind="svg", visual_profile=SVG_PROFILE)
    return render_review(RenderRequest(
        closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
        scheduler=ReferenceScheduler(), renderer=None, draft_auto_block=draft.auto_block))


def _glyph_parts(rendered, *, source_kind: str, source_ref: str):
    return [item for item in rendered.surface.primitives
            if item.kind == "Symbol" and item.source_kind == source_kind and item.source_ref == source_ref]


def _local_symbol(item):
    x, y, width, height = item.bounds
    commands = tuple((command.kind, tuple((px - x, py - y) for px, py in command.points))
                     for command in item.symbol.outline)
    clip = item.stroke_clip
    local_clip = None if clip is None else (
        tuple((command.kind, tuple((px - x, py - y) for px, py in command.points))
              for command in clip.outline),
        clip.outside,
        (clip.region[0] - x, clip.region[1] - y, clip.region[2], clip.region[3]),
        clip.stroke_width,
    )
    return item.scene_id, item.paint, (width, height), commands, local_clip


@pytest.mark.parametrize(("row_mode", "glyph"), [
    ("lanes", "diamond"), ("automatic", "diamond"),
    ("lanes", "inline"), ("automatic", "inline"),
])
def test_bound_point_outline_reaches_mark_legend_svg_and_external_ground_contrast(
    tmp_path, monkeypatch, row_mode, glyph,
):
    rendered = _render(tmp_path / "rendered", row_mode=row_mode, glyph=glyph)
    mark = _glyph_parts(rendered, source_kind="object", source_ref="gate")
    swatch = _glyph_parts(rendered, source_kind="legend", source_ref="milestone")

    assert len(mark) == len(swatch) == 2
    contour_ink = mark[1].paint.stroke
    assert contour_ink is not None
    for parts in (mark, swatch):
        assert parts[0].paint.fill == "#FFFFFF"
        assert parts[0].paint.stroke is None
        assert parts[1].paint.fill is None
        assert parts[1].paint.stroke == contour_ink
        assert parts[1].paint.stroke_width == 2
        assert parts[1].symbol.outline
    assert mark[1].paint == swatch[1].paint

    findings = evaluate_scene_contrast(scene_document(rendered.scene))
    winner = next(item for item in findings if item.primitive_id == mark[1].scene_id)
    assert winner.paint_channel == "stroke"
    assert winner.ground_id is not None and winner.ground_id != mark[0].scene_id
    assert winner.contrast_ratio >= winner.floor == 3.0

    from chrona.presentation.layout import mark_geometry, surface_legend
    monkeypatch.setattr(mark_geometry, "complete_point_outline", lambda parts, **_kwargs: parts)
    monkeypatch.setattr(surface_legend, "complete_point_outline", lambda parts, **_kwargs: parts)
    plain = _render(tmp_path / "plain", row_mode=row_mode, glyph=glyph)
    plain_mark = _glyph_parts(plain, source_kind="object", source_ref="gate")
    (fill_finding,) = (item for item in evaluate_scene_contrast(scene_document(plain.scene))
                       if item.primitive_id == plain_mark[0].scene_id)
    assert fill_finding.paint_channel == "fill" and fill_finding.contrast_ratio < fill_finding.floor

    svg = rendered.artifact.content.decode("utf-8")
    from xml.etree import ElementTree as ET
    root = ET.fromstring(svg)
    edge = next(item for item in root.iter() if item.attrib.get("data-scene-id") == mark[1].scene_id)
    assert edge.attrib.get("stroke") == contour_ink
    assert edge.attrib.get("stroke-width") == "2"


@pytest.mark.parametrize(("alignment", "outside"), [("center", None), ("inside", False), ("outside", True)])
def test_completed_contour_obeys_point_role_alignment_without_changing_source_parts(
    tmp_path, monkeypatch, alignment, outside,
):
    from chrona.presentation.layout import mark_geometry, surface_legend

    rendered = _render(tmp_path / alignment, alignment=alignment, glyph="bulb")
    mark = _glyph_parts(rendered, source_kind="object", source_ref="gate")
    active_routes = [(item.scene_id, item.bounds, item.path_commands, item.points, item.marker_start, item.marker_end)
                     for item in rendered.surface.primitives if item.source_ref == "work-to-gate"
                     and item.source_kind == "relation"]
    active_ports = [(item.scene_id, item.from_instance_id, item.to_instance_id,
                     item.marker_start, item.marker_end)
                    for item in rendered.surface.primitives if item.source_ref == "work-to-gate"
                    and item.source_kind == "relation"]

    monkeypatch.setattr(mark_geometry, "complete_point_outline", lambda parts, **_kwargs: parts)
    monkeypatch.setattr(surface_legend, "complete_point_outline", lambda parts, **_kwargs: parts)
    legacy = _render(tmp_path / f"{alignment}-legacy", alignment=alignment, glyph="bulb")
    legacy_mark = _glyph_parts(legacy, source_kind="object", source_ref="gate")
    legacy_routes = [(item.scene_id, item.bounds, item.path_commands, item.points, item.marker_start, item.marker_end)
                     for item in legacy.surface.primitives if item.source_ref == "work-to-gate"
                     and item.source_kind == "relation"]
    legacy_ports = [(item.scene_id, item.from_instance_id, item.to_instance_id,
                     item.marker_start, item.marker_end)
                    for item in legacy.surface.primitives if item.source_ref == "work-to-gate"
                    and item.source_kind == "relation"]

    assert len(mark) == 3
    source_fill, source_stroke, contour = mark
    # Catalogue width/finish intents are consumed into completed Scene paint;
    # glyph_* metadata is deliberately cleared at that boundary.
    assert source_stroke.paint.stroke_finish is not None
    assert source_stroke.paint.stroke_finish.line_cap == "round"
    assert source_stroke.paint.stroke_finish.line_join == "round"
    source_width = min(source_stroke.bounds[2:]) / 16  # bulb: width 1 in a 16×16 viewport
    assert source_stroke.paint.stroke_width == pytest.approx(
        source_width if outside is None else 2 * source_width)
    assert len(legacy_mark) == 2
    for current, original in zip(mark[:2], legacy_mark):
        assert _local_symbol(current) == _local_symbol(original)
    assert [route[0] for route in active_routes] == [route[0] for route in legacy_routes]
    assert active_ports == legacy_ports
    assert contour.paint.stroke is not None
    if outside is None:
        assert contour.stroke_clip is None
    else:
        assert contour.stroke_clip is not None
        assert contour.stroke_clip.outside is outside
        assert contour.stroke_clip.outline == contour.symbol.outline
        assert contour.stroke_clip.stroke_width == contour.paint.stroke_width == 4
    assert source_fill.bounds == source_stroke.bounds == contour.bounds
    svg = rendered.artifact.content.decode("utf-8")
    from xml.etree import ElementTree as ET
    svg_root = ET.fromstring(svg)
    edge = next(item for item in svg_root.iter() if item.attrib.get("data-scene-id") == contour.scene_id)
    assert any(item.attrib.get("stroke") == contour.paint.stroke for item in edge.iter())
    if alignment != "center":
        assert 'mask-type="luminance"' in svg


def test_width_without_ink_keeps_the_existing_scene_paint_refusal(tmp_path, monkeypatch):
    from chrona.presentation.layout import mark_geometry, surface_legend

    with pytest.raises(RenderFailed) as active:
        _render(tmp_path / "active", stroke=False, width=True)
    monkeypatch.setattr(mark_geometry, "complete_point_outline", lambda parts, **_kwargs: parts)
    monkeypatch.setattr(surface_legend, "complete_point_outline", lambda parts, **_kwargs: parts)
    with pytest.raises(RenderFailed) as legacy:
        _render(tmp_path / "legacy", stroke=False, width=True)

    assert (active.value.code, active.value.source_ref) == (
        legacy.value.code, legacy.value.source_ref)
    assert (active.value.code, active.value.source_ref) == (
        "E_PRESENTATION_PAINT_INVALID", "/body/roles/gate")


def _install_legacy_point_projection(monkeypatch):
    """Freeze pre-#1287 projection from 8ba462d8, independent of the new builder."""
    import chrona.presentation.layout.mark_geometry as geometry
    import chrona.presentation.layout.surface_legend as legend
    import chrona.presentation.scene.v05_builder as builder

    def project(scene_id, source_ref, source_kind, purpose, visual_role,
                bounds, completed_parts, primitive_ids=None, **shared):
        base_paint_order = shared.pop("paint_order", 0)
        order_step = shared.pop("part_order_step", 1)
        if primitive_ids is not None and len(primitive_ids) != len(completed_parts):
            raise builder.SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", scene_id,
                                          "typed lane handoff part count differs from Layout geometry")
        return [builder.ScenePrimitive(
            primitive_ids[index] if primitive_ids is not None else
            f"{scene_id}:part{index}" if part.paint_mode is not None else scene_id,
            builder.PrimitiveKind.SYMBOL, source_ref, source_kind, purpose, visual_role,
            bounds, symbol=builder.SymbolGeometry(part.commands),
            paint_order=base_paint_order + index * order_step,
            glyph_paint_mode=part.paint_mode, glyph_paint_color=part.paint_color,
            glyph_stroke_width=part.stroke_width,
            glyph_line_cap=part.line_cap, glyph_line_join=part.line_join, **shared,
        ) for index, part in enumerate(completed_parts)]

    monkeypatch.setattr(geometry, "complete_point_outline", lambda parts, **_kwargs: parts)
    monkeypatch.setattr(legend, "complete_point_outline", lambda parts, **_kwargs: parts)
    monkeypatch.setattr(builder, "_symbol_primitives", project)


@pytest.mark.parametrize("case", ["absent", "stroke-only", "outline-pattern"])
@pytest.mark.parametrize("row_mode", ["lanes", "automatic"])
@pytest.mark.parametrize("glyph", ["diamond", "inline"])
def test_inactive_or_existing_outline_treatment_is_exactly_the_no_contour_path(
    tmp_path, monkeypatch, case, row_mode, glyph,
):
    if case == "absent":
        options = {"stroke": False, "width": False}
    elif case == "stroke-only":
        options = {"stroke": True, "width": False}
    else:
        options = {"stroke": True, "width": True, "outline_pattern": True}

    actual = _render(tmp_path / f"actual-{case}", row_mode=row_mode, glyph=glyph, **options)
    _install_legacy_point_projection(monkeypatch)
    legacy = _render(tmp_path / f"legacy-{case}", row_mode=row_mode, glyph=glyph, **options)

    assert actual.artifact.content == legacy.artifact.content
    assert serialize_scene(actual.scene) == serialize_scene(legacy.scene)
    assert all(len(_glyph_parts(actual, source_kind=kind, source_ref=ref)) == 1
               for kind, ref in (("object", "gate"), ("legend", "milestone")))
