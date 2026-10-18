from __future__ import annotations

from decimal import Decimal

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_quality import ShapePlacement
from chrona.presentation.layout.realized_legend import visible_placement
from chrona.presentation.model.legend_paint import RealizedLegendKey
from chrona.presentation.model.surface_content import SurfaceLegendEntry
from chrona.presentation.model.theme_paint import PaintFamily, resolve_theme_paint_witness
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.model import ScenePrimitive, SceneSurface
from chrona.presentation.scene.v05_builder import _completed_shape_primitive, _complete_surface_paint


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
