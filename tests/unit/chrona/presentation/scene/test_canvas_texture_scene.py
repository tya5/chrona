"""The canvas texture is ground on both surfaces, admitted narrowly, and gated as ground (#587).

Synthetic Themes and Scenes only: nothing here reads `examples/`.
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.model import LayoutDecision, LayoutManifest, Rect
from chrona.presentation.layout.sources import MeasuredSources, MeasuredTextRun
from chrona.presentation.model.surface_content import AxisTier
from chrona.presentation.scene.capabilities import (
    theme_catalog_pattern_consumer,
    theme_role_contract,
    theme_role_property_consumer,
)
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.presentation.scene.v05_builder import (
    build_scene_input,
    compose_review_surface,
)
from tests.unit.chrona.presentation.scene.test_v05_builder import (
    BACKGROUND_EXTENTS,
    _axis_tiers_scene,
    _theme,
    surface_content,
)

ENTRY = {"tile": {"inlineSize": 12, "blockSize": 21}, "angle": 0, "densityBasisPoints": 1455,
         "primitives": [{"kind": "path", "paint": "stroke", "strokeWidth": 0.9, "lineCap": "round",
                         "lineJoin": "round",
                         "commands": [{"kind": "move", "points": [0, 0]}, {"kind": "line", "points": [6, 3.5]}]}]}
GROUND, INK = "#101820", "#243447"


def _texture_theme() -> dict:
    theme = _theme()
    body = theme["body"]
    body["values"]["texture"] = {"type": "pattern", "value": {"kind": "catalog", "ref": "local:lattice"}}
    body["values"]["ground"] = {"type": "color", "value": GROUND}
    body["values"]["lines"] = {"type": "color", "value": INK}
    body["roles"]["canvas-texture"] = {"pattern": "texture", "fill": "ground", "stroke": "lines"}
    body["catalogAssets"] = {"glyphs": {}, "patterns": {"local:lattice": ENTRY}}
    return theme


def _table_timeline(theme: dict):
    return _axis_tiers_scene((AxisTier("month", 1, "grid-major"),), theme=theme)


def _network(theme: dict):
    node = SimpleNamespace(object_id="a", title="A", order_key=("a",), critical=True, source_kind="primary")
    projection = SimpleNamespace(surface="dependency-network", network=SimpleNamespace(nodes=(node,), edges=()))
    title_bounds = Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(40))
    network_bounds = Rect(Decimal(0), Decimal(50), Decimal(400), Decimal(200))
    manifest = LayoutManifest("network", "sha256:test", "horizontal", "horizontal",
                              Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(250)), (
        LayoutDecision("title", "slot", title_bounds, "title", priority="required"),
        LayoutDecision("network", "slot", network_bounds, "network", priority="required"),
    ), row_distribution="fill", background_extents=BACKGROUND_EXTENTS)
    run = lambda source, content, role, width, block, base: MeasuredTextRun(
        source, content, role, Decimal(width), Decimal(block), Decimal(base), "Test Sans", 400, float(block), 1.0, "sha256:test")
    measured = MeasuredSources({}, {}, {
        "network.node.minInlineSize": Decimal(60), "network.node.minBlockSize": Decimal(30), "network.rank.gap": Decimal(12),
    }, {"title": (run(None, "Network", "heading", 80, 24, 20),), "network": (run("a", "A", "text", 20, 14, 11),)})
    value = build_scene_input(projection=projection, surface_content=surface_content(), layout_manifest=manifest,
                              resolved_theme=theme, font_metrics=object(), measured_sources=measured,
                              capabilities={"svg": True})
    return compose_review_surface(value)


@pytest.mark.parametrize("surface_of", [_table_timeline, _network], ids=["table-timeline", "dependency-network"])
def test_the_texture_is_the_first_primitive_over_the_whole_canvas_in_its_own_slot(surface_of) -> None:
    surface = surface_of(_texture_theme())
    first = surface.primitives[0]

    assert (first.scene_id, first.kind, first.purpose, first.visual_role) == (
        "canvas-texture", "Rect", "canvas-texture", "canvas-texture")
    assert first.bounds == surface.canvas_bounds
    assert first.paint_order == 0 and first.slot_id == "canvas"
    assert [slot.bounds for slot in surface.slots if slot.slot_id == "canvas"] == [surface.canvas_bounds]
    assert all(item.paint_order >= first.paint_order for item in surface.primitives)
    assert [item.scene_id for item in surface.primitives].count("canvas-texture") == 1


@pytest.mark.parametrize("surface_of", [_table_timeline, _network], ids=["table-timeline", "dependency-network"])
def test_the_texture_carries_the_catalogue_tile_with_substrate_and_ink(surface_of) -> None:
    first = surface_of(_texture_theme()).primitives[0]

    assert (first.paint.fill, first.paint.stroke, first.paint.opacity) == (GROUND, INK, 1.0)
    assert first.paint.gradient is None and first.paint.shadow is None
    assert (first.pattern.tile_inline_size, first.pattern.tile_block_size) == (12.0, 21.0)
    assert first.pattern.density_basis_points == 1455
    assert first.pattern.origin == (first.bounds[0], first.bounds[1])
    assert first.pattern.region_bounds == first.pattern.clip_bounds == first.bounds


@pytest.mark.parametrize("surface_of", [_table_timeline, _network], ids=["table-timeline", "dependency-network"])
def test_a_theme_without_a_texture_has_no_texture_primitive_and_no_canvas_slot(surface_of) -> None:
    surface = surface_of(_theme())

    assert "canvas-texture" not in {item.scene_id for item in surface.primitives}
    assert "canvas" not in {slot.slot_id for slot in surface.slots}
    assert all(item.pattern is None for item in surface.primitives if item.visual_role == "network-node")


def test_a_band_of_any_paint_order_stays_above_the_texture() -> None:
    surface = _axis_tiers_scene((AxisTier("quarter", 1, "band"), AxisTier("month", 1, "band")),
                                theme=_texture_theme())
    bands = [item for item in surface.primitives if item.visual_role.endswith("band-decoration")]
    texture = surface.primitives[0]

    assert len(bands) > 2
    assert all((item.paint_order, surface.primitives.index(item)) > (texture.paint_order, 0) for item in bands)


def test_the_role_admits_only_declared_surface_pattern_controls() -> None:
    contract = theme_role_contract("canvas-texture")

    assert contract is not None and contract.properties == {
        "fill", "stroke", "pattern", "patternMode", "opacity", "textureFidelity"}
    for admitted in contract.properties:
        assert theme_role_property_consumer("canvas-texture", admitted) is not None, admitted
    for refused in ("backgroundPaintOrder", "backgroundTreatment", "strokeWidth", "dash",
                    "gradientAngle", "shadowBlur", "fontSize"):
        assert theme_role_property_consumer("canvas-texture", refused) is None, refused
    assert theme_catalog_pattern_consumer("canvas-texture", "pattern") is not None


def _bounds(inline=10, block=10, inline_size=20, block_size=10):
    return {"inline": inline, "block": block, "inlineSize": inline_size, "blockSize": block_size}


def _texture_primitive(*, fill=GROUND, ink=INK):
    return {"id": "canvas-texture", "kind": "Rect", "slotId": "canvas", "paintOrder": 0,
            "visualRole": "canvas-texture", "purpose": "canvas-texture",
            "bounds": _bounds(0, 0, 400, 300), "paint": {"fill": fill, "stroke": ink, "opacity": 1}}


def _mark(identifier, fill, *, order=100, role="planned"):
    return {"id": identifier, "kind": "Rect", "slotId": "timeline", "paintOrder": order, "visualRole": role,
            "purpose": role, "bounds": _bounds(), "paint": {"fill": fill, "opacity": 1}}


def _scene(*primitives, canvas="#FFFFFF"):
    return {"version": "chrona/scene/v0.7", "kind": "scene", "surfaces": [{
        "id": "review", "canvasPaint": {"fill": canvas, "opacity": 1},
        "slots": [{"id": "timeline", "bounds": _bounds(0, 0, 400, 300), "overflow": "fit"},
                  {"id": "canvas", "bounds": _bounds(0, 0, 400, 300), "overflow": "visible-overflow"}],
        "primitives": list(primitives), "decorationDispositions": []}]}


def _finding(document, identifier):
    return next(item for item in evaluate_scene_contrast(document) if item.primitive_id == identifier)


def test_a_mark_on_the_texture_is_gated_against_the_worse_of_substrate_and_ink() -> None:
    finding = _finding(_scene(_texture_primitive(), _mark("bar", "#5FA8FF")), "bar")

    assert (finding.ground_id, finding.ground_color, finding.ground_kind) == ("canvas-texture", INK, "texture-ink")
    assert finding.floor == 3.0


def test_the_substrate_is_the_ground_when_it_is_the_worse_of_the_two() -> None:
    finding = _finding(_scene(_texture_primitive(fill="#5FA8FF", ink="#101820"), _mark("bar", "#5FA8FF")), "bar")

    assert (finding.ground_color, finding.ground_kind) == ("#5FA8FF", "texture-substrate")
    assert finding.severity == "error"


def test_a_mark_that_clears_the_floor_on_substrate_but_not_on_ink_fails_the_gate() -> None:
    finding = _finding(_scene(_texture_primitive(ink="#5FA8FF"), _mark("bar", "#5FA8FF")), "bar")

    assert finding.severity == "error" and finding.ground_kind == "texture-ink"
    assert finding.contrast_ratio == pytest.approx(1.0)


def test_a_mark_on_a_later_band_is_gated_against_the_band_not_the_texture() -> None:
    band = {"id": "band", "kind": "Rect", "slotId": "timeline", "paintOrder": 10, "visualRole": "row-band",
            "purpose": "row-decoration", "bounds": _bounds(0, 0, 100, 100), "paint": {"fill": "#FFFFFF", "opacity": 1}}
    finding = _finding(_scene(_texture_primitive(), band, _mark("bar", "#102030")), "bar")

    assert (finding.ground_id, finding.ground_color, finding.ground_kind) == ("band", "#FFFFFF", "flat")


def test_a_decoration_on_the_texture_is_judged_against_the_substrate_not_the_ink_lines() -> None:
    tint = {"id": "tint", "kind": "Rect", "slotId": "timeline", "paintOrder": 10, "visualRole": "row-band",
            "purpose": "row-decoration", "bounds": _bounds(), "paint": {"fill": "#1B2733", "opacity": 1}}
    finding = _finding(_scene(_texture_primitive(ink="#1C2834"), tint), "tint")

    assert (finding.ground_id, finding.ground_kind, finding.severity) == ("canvas-texture", "flat", "info")
    assert finding.ground_color == GROUND


def test_the_texture_has_no_contrast_floor_of_its_own() -> None:
    document = _scene(_texture_primitive(fill="#101820", ink="#101821"))

    assert [item for item in evaluate_scene_contrast(document) if item.primitive_id == "canvas-texture"] == []


def test_a_patterned_mark_on_the_texture_also_checks_the_texture_ink_pairs() -> None:
    pattern = {"densityBasisPoints": 1000, "tileInlineSize": 4, "tileBlockSize": 4, "angleDegrees": 0,
               "primitives": [], "origin": [0, 0]}
    mark = {**_mark("hatched", "#335577"), "pattern": pattern, "paint": {"fill": "#335577", "stroke": "#99BBDD", "opacity": 1}}
    findings = [item for item in evaluate_scene_contrast(_scene(_texture_primitive(), mark))
                if item.primitive_id == "hatched"]

    assert {item.ground_kind for item in findings} >= {"texture-substrate", "texture-ink", "pattern-substrate"}


def _paint_contrast(document, identifier):
    finding = next(item for item in evaluate_scene_perceptibility(document)
                   if item.code == "I_SCENE_PAINT_CONTRAST" and item.primitive_ids == (identifier,))
    return dict(finding.measured_facts)["contrastRatio"]


def test_paint_contrast_is_measured_against_the_worse_ground_when_a_texture_covers_the_canvas() -> None:
    from chrona.presentation.scene.paint_analysis import composited_contrast

    without = _paint_contrast(_scene(_mark("bar", "#5FA8FF")), "bar")
    with_texture = _paint_contrast(_scene(_texture_primitive(), _mark("bar", "#5FA8FF")), "bar")

    assert without == pytest.approx(composited_contrast(fill="#5FA8FF", opacity=1, ground="#FFFFFF"))
    assert with_texture == pytest.approx(min(
        composited_contrast(fill="#5FA8FF", opacity=1, ground=GROUND),
        composited_contrast(fill="#5FA8FF", opacity=1, ground=INK)))


def test_the_texture_itself_is_measured_against_the_canvas_fill() -> None:
    from chrona.presentation.scene.paint_analysis import composited_contrast

    value = _paint_contrast(_scene(_texture_primitive(), _mark("bar", "#5FA8FF")), "canvas-texture")

    assert value == pytest.approx(composited_contrast(fill=GROUND, opacity=1, ground="#FFFFFF"))


def test_a_texture_never_occludes_text_because_it_is_never_later() -> None:
    text = {"id": "title", "kind": "Text", "slotId": "timeline", "paintOrder": 0, "bounds": _bounds()}
    codes = [item.code for item in evaluate_scene_perceptibility(_scene(_texture_primitive(), text))]

    assert "E_SCENE_TEXT_OCCLUDED" not in codes
