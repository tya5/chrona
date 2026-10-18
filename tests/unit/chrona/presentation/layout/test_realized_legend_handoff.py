from __future__ import annotations

from decimal import Decimal

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.mark_geometry import SymbolPartPlacement
from chrona.presentation.layout.surface_quality import MarkPlacement, PathCommand, ShapePlacement, completed_symbol_primitive_ids
from chrona.presentation.layout.realized_legend import visible_placement
from chrona.presentation.model.legend_paint import RealizedLegendKey
from chrona.presentation.model.surface_content import SurfaceLegendEntry
from chrona.presentation.model.theme_paint import PaintFamily, resolve_theme_paint_witness
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.model import ScenePrimitive, SceneSurface
from chrona.presentation.scene.v05_builder import (
    _completed_legend_paints, _completed_shape_primitive, _complete_surface_paint,
    _legend_mark_role, _symbol_primitives,
)


def _tokens() -> ThemeTokenView:
    return ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2",
        "kind": "resolved-theme",
        "body": {
            "values": {
                "canvas": {"type": "color", "value": "#FFFFFF"},
                "ink": {"type": "color", "value": "#AA2233"},
                "edge": {"type": "color", "value": "#123456"},
                "width": {"type": "number", "value": 2},
            },
            "roles": {
                "background": {"fill": "canvas"},
                "actual": {"fill": "ink", "stroke": "edge", "strokeWidth": "width"},
                "progressFill": {"fill": "ink", "stroke": "edge", "strokeWidth": "width"},
            },
            "metrics": {},
        },
    })


def _key(tokens: ThemeTokenView, family: str, role: str = "actual") -> RealizedLegendKey:
    witness = resolve_theme_paint_witness(tokens, role, PaintFamily.SOLID)
    return RealizedLegendKey(family, role, witness)


def _project(entry: SurfaceLegendEntry, shape: str = "Rect") -> tuple[ShapePlacement, ScenePrimitive]:
    key = entry.realized_key
    assert key is not None
    placement = ShapePlacement(
        entry.swatch_placement_id, entry.source_identity, shape,
        Rect(Decimal(1), Decimal(2), Decimal(8), Decimal(6)),
        visual_role=key.paint_role,
        legend_swatch_shape=entry.swatch_shape,
        legend_paint=key.paint,
    )
    primitive = _completed_shape_primitive(placement, "legend", "legendEntry", key.paint_role)
    return placement, primitive


def _complete(primitive: ScenePrimitive, tokens: ThemeTokenView, witness) -> ScenePrimitive:
    completed = _complete_surface_paint(
        SceneSurface("surface", (), (), (), None, (primitive,)), tokens,
        legend_paints={primitive.scene_id: witness},
    )
    return completed.primitives[0]


def test_realized_entry_identity_is_not_its_period_source_and_scene_uses_witness():
    tokens = _tokens()
    key = _key(tokens, "actual")
    entry = SurfaceLegendEntry("actual", "Actual", source_ref="period:actual",
                               realized_key=key)

    placement, primitive = _project(entry)
    completed = _complete(primitive, tokens, placement.legend_paint)

    assert entry.source_identity == key.key_id
    assert entry.swatch_placement_id == f"legend-swatch:{key.key_id}"
    assert placement.source_ref == key.key_id
    assert entry.source_ref == "period:actual"
    assert completed.paint.fill == key.paint.effective_channels.fill == "#AA2233"
    assert completed.paint.stroke == key.paint.effective_channels.stroke == "#123456"


def test_actual_and_progress_keys_keep_distinct_meaning_with_equal_completed_ink():
    tokens = _tokens()
    actual = _key(tokens, "actual", "actual")
    progress = _key(tokens, "progress", "progressFill")
    actual_entry = SurfaceLegendEntry("actual", "Actual", realized_key=actual)
    progress_entry = SurfaceLegendEntry("progressFill", "Progress", realized_key=progress)

    actual_placement, actual_primitive = _project(actual_entry)
    progress_placement, progress_primitive = _project(progress_entry)
    actual_scene = _complete(actual_primitive, tokens, actual_placement.legend_paint)
    progress_scene = _complete(progress_primitive, tokens, progress_placement.legend_paint)

    assert actual.key_id != progress.key_id
    assert actual_scene.paint == progress_scene.paint
    assert actual_scene.paint.fill == "#AA2233"


@pytest.mark.parametrize("swatch_shape,scene_kind", [("circle", "Symbol"), ("rule-pair", "Path")])
def test_finite_key_shapes_borrow_selected_source_ink(swatch_shape, scene_kind):
    tokens = _tokens()
    key = _key(tokens, "actual")
    entry = SurfaceLegendEntry("actual", "Actual", swatch_shape=swatch_shape, realized_key=key)
    placement, primitive = _project(entry, scene_kind)

    completed = _complete(primitive, tokens, placement.legend_paint)

    assert completed.paint.fill == "#AA2233" if swatch_shape == "circle" else completed.paint.fill is None
    if swatch_shape == "circle":
        assert completed.paint.stroke is None
    else:
        assert completed.paint.stroke == "#AA2233"
        assert completed.paint.stroke_width == 2


def test_legacy_period_entry_retains_its_original_identity():
    entry = SurfaceLegendEntry("actual", "Actual", source_ref="period:actual")

    assert entry.source_identity == "period:actual"
    assert entry.text_placement_id == "legend-period:period:actual"
    assert entry.swatch_placement_id == "legend-period-swatch:period:actual"


def test_completed_period_edge_is_visible_without_a_rectangular_area():
    edge = ShapePlacement("edge", "period", "Path",
        Rect(Decimal(1), Decimal(2), Decimal(8), Decimal(0)),
        ((1.0, 2.0), (9.0, 2.0)))
    assert visible_placement(edge)
    empty = ShapePlacement("empty", "period", "Path",
        Rect(Decimal(1), Decimal(2), Decimal(0), Decimal(0)))
    assert not visible_placement(empty)


def test_composite_glyph_legend_mark_consumes_exact_ordered_part_witnesses():
    tokens = _tokens()
    fill_witness = resolve_theme_paint_witness(
        tokens, "actual", PaintFamily.SOLID, part_mode="fill", part_color="#AABBCC")
    stroke_witness = resolve_theme_paint_witness(
        tokens, "actual", PaintFamily.SOLID, part_mode="stroke", part_color="#112233")
    parts = (
        SymbolPartPlacement((PathCommand("move", ((1.0, 2.0),)),
                             PathCommand("line", ((9.0, 2.0),)),
                             PathCommand("line", ((9.0, 8.0),)),
                             PathCommand("line", ((1.0, 2.0),))), "fill", "#AABBCC"),
        SymbolPartPlacement((PathCommand("move", ((2.0, 3.0),)),
                             PathCommand("line", ((8.0, 7.0),))), "stroke", "#112233"),
    )
    mark = MarkPlacement(
        "legend-swatch:actual:composite", "actual:composite", Rect(Decimal(1), Decimal(2), Decimal(8), Decimal(6)),
        None, None, mark_shape="point", slot_id="legend", semantic_id="actual", theme_role="actual",
        symbol_parts=parts, legend_paints=(fill_witness, stroke_witness),
    )

    assert _legend_mark_role(mark, tokens) == "actual"
    primitive_ids = completed_symbol_primitive_ids(mark.placement_id, parts)
    assert primitive_ids == (f"{mark.placement_id}:part0", f"{mark.placement_id}:part1")
    paints = _completed_legend_paints((), (mark,))
    assert tuple(paints[primitive_id] for primitive_id in primitive_ids) == mark.legend_paints

    primitives = _symbol_primitives(mark.placement_id, mark.source_ref, "legend", "legend-swatch",
        _legend_mark_role(mark, tokens), (1.0, 2.0, 8.0, 6.0), mark.symbol_parts,
        slot_id=mark.slot_id, paint_order=mark.paint_order)
    completed = _complete_surface_paint(
        SceneSurface("surface", (), (), (), None, tuple(primitives)), tokens, legend_paints=paints)

    assert tuple(item.scene_id for item in completed.primitives) == primitive_ids
    assert tuple(item.source_ref for item in completed.primitives) == (mark.source_ref, mark.source_ref)
    assert tuple(item.visual_role for item in completed.primitives) == ("actual", "actual")
    assert tuple(item.paint.fill for item in completed.primitives) == ("#AABBCC", None)
    assert tuple(item.paint.stroke for item in completed.primitives) == (None, "#112233")
