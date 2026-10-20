from dataclasses import replace
from decimal import Decimal, ROUND_UP, localcontext
from math import copysign

import pytest

from chrona.presentation.layout.chip_geometry import ChipGeometryError
from chrona.presentation.layout.label_chip_measurement import (
    complete_label_chip_placement,
    measure_label_chip,
    _quantize_coordinate,
)
from chrona.presentation.model.theme_tokens import ThemeTokenView


def _theme(shape):
    role = "member-label-chip"
    return ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2",
        "kind": "resolved-theme",
        "body": {
            "values": {"shape": {"type": "chipShape", "value": shape}},
            "roles": {role: {"backgroundTreatment": "fill", "chipShape": "shape"}},
            "metrics": {},
        },
    }, catalog_glyphs={"test:chip": {
        "viewport": {"inlineSize": 10, "blockSize": 10},
        "parts": [{"paint": "fill", "data": "M0 0L10 0L10 10L0 10Z"}],
    }})


def _burst(precision):
    measured = measure_label_chip(
        _theme({"kind": "burst", "points": 7, "innerRatio": 0.45}),
        "memberLabel", text_inline=31.17, text_block=11.13, font_size=10,
        padding=(4.2, 2.1), scene_precision=precision,
    )
    assert measured is not None
    return measured


@pytest.mark.parametrize("precision", [0, 3, 6])
def test_burst_outline_quantizes_absolute_points_and_bounds_enclose_ink(precision):
    measured = _burst(precision)
    origin = (103.1234567, 27.7654321)
    bounds, parts = complete_label_chip_placement(measured, origin_x=origin[0], origin_y=origin[1])
    nominal_inline = Decimal(str(origin[0])) + measured.geometry.outer_bounds.inline
    nominal_block = Decimal(str(origin[1])) + measured.geometry.outer_bounds.block
    assert bounds.inline <= nominal_inline and bounds.block <= nominal_block
    assert bounds.inline + bounds.inline_size >= nominal_inline + measured.geometry.outer_bounds.inline_size
    assert bounds.block + bounds.block_size >= nominal_block + measured.geometry.outer_bounds.block_size
    quantum = Decimal(1).scaleb(-precision)
    for part in parts:
        for command in part.commands:
            for x, y in command.points:
                assert Decimal(str(x)) == Decimal(str(x)).quantize(quantum)
                assert Decimal(str(y)) == Decimal(str(y)).quantize(quantum)
                assert float(bounds.inline) <= x <= float(bounds.inline + bounds.inline_size)
                assert float(bounds.block) <= y <= float(bounds.block + bounds.block_size)

    extra = Decimal("0.5").scaleb(-precision)
    assert measured.footprint.inline <= Decimal(0) - extra
    assert measured.footprint.block <= Decimal(0) - extra
    assert measured.footprint.inline_size >= measured.geometry.outer_bounds.inline_size + 2 * extra


def test_subquantum_local_vertex_perturbation_canonicalizes_after_nonzero_translation():
    measured = _burst(3)
    part = measured.geometry.symbol_parts[0]
    command = part.commands[1]
    x, y = command.points[0]
    perturbed_command = replace(command, points=((x + 0.0000001, y - 0.0000001),))
    perturbed_part = replace(part, commands=(part.commands[0], perturbed_command, *part.commands[2:]))
    perturbed = replace(measured, geometry=replace(
        measured.geometry, symbol_parts=(perturbed_part,)))

    origin = (238.123456, 46.987654)
    assert complete_label_chip_placement(measured, origin_x=origin[0], origin_y=origin[1]) == \
        complete_label_chip_placement(perturbed, origin_x=origin[0], origin_y=origin[1])


def test_catalog_geometry_is_not_scene_precision_quantized():
    theme = _theme({"kind": "catalog", "glyph": "test:chip", "unitEm": 0.1,
                    "sliceInsets": {"top": 1, "right": 1, "bottom": 1, "left": 1}})
    low = measure_label_chip(theme, "memberLabel", text_inline=21.25, text_block=11.5,
        font_size=10, padding=(3, 2), scene_precision=0)
    high = measure_label_chip(theme, "memberLabel", text_inline=21.25, text_block=11.5,
        font_size=10, padding=(3, 2), scene_precision=6)
    assert low is not None and high is not None
    assert low.outline_precision is None and high.outline_precision is None
    assert low.geometry == high.geometry
    assert complete_label_chip_placement(low, origin_x=0.123456, origin_y=4.654321) == \
        complete_label_chip_placement(high, origin_x=0.123456, origin_y=4.654321)


def test_zero_precision_fails_closed_if_quantized_outline_loses_text_ground():
    # The fitter admits a tiny positive ground before Scene precision is
    # applied; whole-point rounding collapses its diamond and cannot retain it.
    measured = measure_label_chip(
        _theme({"kind": "burst", "points": 2, "innerRatio": 0.1}),
        "memberLabel", text_inline=0.01, text_block=0.01, font_size=10,
        padding=(0.01, 0.01), scene_precision=0,
    )
    assert measured is not None
    with pytest.raises(ChipGeometryError, match="precision-geometry"):
        complete_label_chip_placement(measured, origin_x=0.27, origin_y=0.61)


def test_quantization_uses_declared_half_even_independently_of_decimal_context():
    with localcontext() as context:
        context.rounding = ROUND_UP
        assert _quantize_coordinate(1.2345, 3) == 1.234
        assert _quantize_coordinate(1.2355, 3) == 1.236
    assert copysign(1, _quantize_coordinate(-0.0001, 3)) == 1
    assert copysign(1, _quantize_coordinate(-0.0, 3)) == 1


def test_precision_beyond_float_resolution_does_not_add_an_arbitrary_limit():
    measured = _burst(10**50)
    assert measured.footprint.inline == Decimal(0)
    _bounds, parts = complete_label_chip_placement(measured, origin_x=103.1, origin_y=27.7)
    assert parts[0].commands[1].points[0] == tuple(
        value + origin for value, origin in zip(
            measured.geometry.symbol_parts[0].commands[1].points[0], (103.1, 27.7)))
