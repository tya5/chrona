"""#1148: renderer-neutral physical radius completion, independent of token syntax."""
from __future__ import annotations

import pytest

from chrona.presentation.layout.rounded_outline import resolve_corner_radius


@pytest.mark.parametrize("height", [8.0, 16.0, 32.0])
def test_physical_radius_does_not_scale_with_box_height(height):
    assert resolve_corner_radius(3.0, width=120.0, height=height, legacy_radius=height * 0.2) == 3.0


@pytest.mark.parametrize("width,height", [(40.0, 10.0), (10.0, 40.0), (10.0, 10.0), (0.0, 10.0)])
def test_capsule_is_exactly_half_the_shorter_side(width, height):
    assert resolve_corner_radius("capsule", width=width, height=height, legacy_radius=1.0) == min(width, height) / 2


def test_oversize_physical_radius_is_limited_by_actual_box():
    assert resolve_corner_radius(20.0, width=12.0, height=40.0, legacy_radius=0.0) == 6.0


def test_zero_physical_radius_and_degenerate_box_are_explicit():
    assert resolve_corner_radius(0.0, width=12.0, height=40.0, legacy_radius=3.0) == 0.0
    assert resolve_corner_radius(3.0, width=12.0, height=0.0, legacy_radius=3.0) == 0.0


def test_absence_preserves_the_existing_result_without_new_clamping():
    legacy = 3.1899999999999995
    assert resolve_corner_radius(None, width=1.0, height=2.0, legacy_radius=legacy) is legacy


@pytest.mark.parametrize("value", [-1.0, float("nan"), float("inf"), True, "3px", "round"])
def test_invalid_physical_declaration_is_rejected(value):
    with pytest.raises(ValueError):
        resolve_corner_radius(value, width=40.0, height=10.0, legacy_radius=0.0)


@pytest.mark.parametrize("width,height", [(-1.0, 10.0), (10.0, -1.0), (float("nan"), 10.0), (10.0, float("inf"))])
def test_invalid_opt_in_box_is_rejected(width, height):
    with pytest.raises(ValueError):
        resolve_corner_radius("capsule", width=width, height=height, legacy_radius=0.0)
