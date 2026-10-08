from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.pattern_placement import PatternPlacement
from chrona.presentation.layout.seeded_pattern import complete_seeded_pattern

BOUNDS = Rect(Decimal(10), Decimal(20), Decimal(100), Decimal(80))


def grain(seed: int = 7) -> dict[str, object]:
    return {"kind": "seeded", "algorithm": "splitmix64-v1", "motif": "grain", "seed": seed,
            "tile": {"inlineSize": 20, "blockSize": 12}, "count": 3, "radius": 1.25}


def rain(seed: int = 7) -> dict[str, object]:
    return {"kind": "seeded", "algorithm": "splitmix64-v1", "motif": "rain", "seed": seed,
            "tile": {"inlineSize": 20, "blockSize": 12}, "count": 2,
            "length": 4, "strokeWidth": 1, "slant": 0.5}


def test_grain_has_golden_seeded_positions_and_is_stable_on_nonzero_origin() -> None:
    first = complete_seeded_pattern(grain(), BOUNDS)
    second = complete_seeded_pattern(grain(), BOUNDS)
    assert first == second
    assert isinstance(first, PatternPlacement)
    assert first.angle_degrees == 0
    assert first.origin == (10, 20)
    assert first.region is BOUNDS and first.clip is BOUNDS
    assert first.density_basis_points == 614
    assert [(item.cx, item.cy, item.radius) for item in first.primitives] == [
        (8.072, 1.409, 1.25), (17.013, 6.788, 1.25), (9.168, 3.62, 1.25)]
    assert complete_seeded_pattern(grain(seed=8), BOUNDS) != first


def test_rain_has_golden_endpoints_and_uses_butt_capped_stroke() -> None:
    pattern = complete_seeded_pattern(rain(), BOUNDS)
    assert pattern.density_basis_points == 373
    first = pattern.primitives[0]
    assert first.kind == "path" and first.paint == "stroke"
    assert (first.stroke_width, first.line_cap, first.line_join) == (1.0, "butt", "round")
    assert [command.points for command in first.commands] == [((7.127, 0.618),), ((9.127, 4.618),)]
    for item in pattern.primitives:
        for command in item.commands:
            for x, y in command.points:
                assert 0.5 <= x <= pattern.tile_inline_size - 0.5
                assert 0.5 <= y <= pattern.tile_block_size - 0.5


def test_rain_rejects_endpoints_collapsed_by_position_quantization() -> None:
    value = {"kind": "seeded", "algorithm": "splitmix64-v1", "motif": "rain", "seed": 1,
             "tile": {"inlineSize": 1, "blockSize": 1}, "count": 1,
             "length": 0.001, "strokeWidth": 0.001, "slant": 0}
    with pytest.raises(LayoutError) as error:
        complete_seeded_pattern(value, BOUNDS, pointer="/body/roles/canvas-overlay/pattern")
    assert (error.value.diagnostic_id, error.value.path) == (
        "E_THEME_TOKEN_TYPE", "/body/roles/canvas-overlay/pattern")


@pytest.mark.parametrize("seed", [0, 0xFFFFFFFF])
def test_seed_domain_includes_both_uint32_endpoints(seed: int) -> None:
    assert len(complete_seeded_pattern(grain(seed), BOUNDS).primitives) == 3


def test_different_rain_seed_changes_completed_geometry() -> None:
    assert complete_seeded_pattern(rain(seed=7), BOUNDS) != complete_seeded_pattern(rain(seed=8), BOUNDS)


@pytest.mark.parametrize("mutate", [
    lambda value: value.update(seed=True),
    lambda value: value.update(seed=-1),
    lambda value: value.update(count=65),
    lambda value: value.update(algorithm="other"),
    lambda value: value.update(extra=1),
    lambda value: value.update(radius=0),
    lambda value: value.update(radius=0.0004),
    lambda value: value.update(tile={"inlineSize": 0.0004, "blockSize": 12}),
    lambda value: value.update(tile={"inlineSize": 1e308, "blockSize": 1e308}),
])
def test_invalid_grain_declarations_fail_at_caller_pointer(mutate) -> None:
    value = grain()
    mutate(value)
    with pytest.raises(LayoutError) as error:
        complete_seeded_pattern(value, BOUNDS, pointer="/body/roles/canvas-overlay/pattern")
    assert (error.value.diagnostic_id, error.value.path) == (
        "E_THEME_TOKEN_TYPE", "/body/roles/canvas-overlay/pattern")


@pytest.mark.parametrize("mutate", [
    lambda value: value.update(slant=float("inf")),
    lambda value: value.update(length=0.0004),
    lambda value: value.update(strokeWidth=0),
    lambda value: value.update(tile={"inlineSize": 20, "blockSize": 5}),
    lambda value: value.update(radius=1),
    lambda value: value.update(unused=1),
])
def test_invalid_rain_declarations_and_fits_fail_at_caller_pointer(mutate) -> None:
    value = rain()
    mutate(value)
    with pytest.raises(LayoutError) as error:
        complete_seeded_pattern(value, BOUNDS, pointer="/body/roles/canvas-texture/pattern")
    assert (error.value.diagnostic_id, error.value.path) == (
        "E_THEME_TOKEN_TYPE", "/body/roles/canvas-texture/pattern")


def test_quantize_before_fit_and_reject_collapsed_completed_bounds() -> None:
    value = grain()
    value["tile"] = {"inlineSize": 20.0004, "blockSize": 12.0004}
    assert (complete_seeded_pattern(value, BOUNDS).tile_inline_size,
            complete_seeded_pattern(value, BOUNDS).tile_block_size) == (20, 12)
    with pytest.raises(LayoutError, match="E_THEME_TOKEN_TYPE"):
        complete_seeded_pattern(grain(), Rect(Decimal(0), Decimal(0), Decimal(0), Decimal(8)))


def test_nonfinite_bounds_are_rejected_without_mutating_the_completed_region() -> None:
    with pytest.raises(LayoutError, match="E_THEME_TOKEN_TYPE"):
        complete_seeded_pattern(grain(), Rect(Decimal("NaN"), Decimal(0), Decimal(10), Decimal(8)))
    source = deepcopy(BOUNDS)
    completed = complete_seeded_pattern(grain(), source)
    assert completed.region == source and completed.clip == source
