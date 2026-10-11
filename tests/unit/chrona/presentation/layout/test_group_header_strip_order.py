"""Completed same-group strip layers, without Scene or adapter policy."""
from dataclasses import replace
from decimal import Decimal
from itertools import permutations

import pytest

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_backgrounds import (
    validate_background_shapes, validate_group_header_strip_order,
)
from chrona.presentation.layout.surface_quality import ShapePlacement, TextPlacement


def _shape(semantic, order, group="g"):
    return ShapePlacement(semantic, group, "Rect", Rect(*(Decimal(v) for v in (0, 0, 100, 20))),
                          semantic_id=semantic, paint_order=order)


def _text(order=300):
    return TextPlacement("caption", "g", "Group", Rect(*(Decimal(v) for v in (2, 2, 40, 12))),
                         "groupHeader", semantic_id="groupHeader", paint_order=order)


@pytest.mark.parametrize("order", tuple(permutations(("groupBand", "groupHeaderStrip", "groupHeaderBand"))))
def test_layer_validation_is_independent_of_placement_emission_order(order):
    shapes = {semantic: _shape(semantic, value) for semantic, value in
              (("groupBand", 1), ("groupHeaderStrip", 2), ("groupHeaderBand", 3))}
    validate_group_header_strip_order([shapes[semantic] for semantic in order], [_text()])


@pytest.mark.parametrize("semantic,order", (("groupBand", 2), ("groupBand", 3),
                                          ("groupHeaderBand", 2), ("groupHeaderBand", 1)))
def test_equal_or_reversed_actual_group_layers_fail_with_exact_pointer(semantic, order):
    with pytest.raises(LayoutError) as raised:
        validate_group_header_strip_order([_shape("groupHeaderStrip", 2), _shape(semantic, order)], [])
    assert raised.value.diagnostic_id == "E_LAYOUT_GROUP_HEADER_STRIP_ORDER"
    assert raised.value.path == "/body/roles/group-header-strip/backgroundPaintOrder"
    assert "groupHeaderStrip" in raised.value.detail and semantic in raised.value.detail


@pytest.mark.parametrize("order", (300, 301))
def test_strip_must_precede_text_without_a_caption_band(order):
    with pytest.raises(LayoutError, match="E_LAYOUT_GROUP_HEADER_STRIP_ORDER"):
        validate_group_header_strip_order([_shape("groupHeaderStrip", order)], [_text()])


def test_unrelated_and_nonintersecting_placements_do_not_constrain_strip_order():
    strip = _shape("groupHeaderStrip", 2)
    other_group = _shape("groupHeaderBand", 1, "other")
    outside = replace(_shape("groupHeaderBand", 1), bounds=Rect(Decimal(200), Decimal(0), Decimal(10), Decimal(10)))
    validate_group_header_strip_order([strip, other_group, outside, _shape("groupTab", 1)], [])


class _TranslucentTheme:
    def background(self, role):
        return "fill", {"group-band": 1, "group-header-strip": 2, "group-header-band": 3}[role]

    def opacity(self, role):
        return 0.5


@pytest.mark.parametrize("other,order", (("groupBand", 1), ("groupHeaderBand", 3)))
@pytest.mark.parametrize("reverse", (False, True))
def test_explicit_translucent_strip_pair_composites_in_either_emission_order(other, order, reverse):
    pair = [_shape("groupHeaderStrip", 2), _shape(other, order)]
    validate_background_shapes(pair[::-1] if reverse else pair, _TranslucentTheme())


def test_translucent_strip_does_not_waive_unrelated_group_overlap():
    with pytest.raises(LayoutError, match="E_LAYOUT_BACKGROUND_OVERLAP"):
        validate_background_shapes([_shape("groupHeaderStrip", 2), _shape("groupHeaderBand", 3, "other")],
                                   _TranslucentTheme())
