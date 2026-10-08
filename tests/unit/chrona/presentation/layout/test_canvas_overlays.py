from __future__ import annotations

from decimal import Decimal

import pytest

from chrona.presentation.layout.canvas_overlays import complete_canvas_overlays
from chrona.presentation.layout.model import LayoutError, Rect

CANVAS = Rect(Decimal("10"), Decimal("20"), Decimal("100"), Decimal("80"))
RADIAL = {
    "radialCenterInline": Decimal("0.5"),
    "radialCenterBlock": Decimal("0.25"),
    "radialRadiusInline": Decimal("0.25"),
    "radialRadiusBlock": Decimal("0.5"),
    "radialInnerStop": Decimal("0"),
}
GRAIN = {
    "kind": "seeded", "algorithm": "splitmix64-v1", "motif": "grain",
    "seed": 7, "tile": {"inlineSize": 12, "blockSize": 10}, "count": 2, "radius": 1,
}


class Tokens:
    def __init__(self, roles=None, patterns=None):
        self.roles = roles or {}
        self.patterns = patterns or {}

    def has_role(self, role):
        return role in self.roles

    def optional_pattern(self, role):
        return self.patterns.get(role)

    def optional_number(self, role, prop):
        return self.roles.get(role, {}).get(prop)


def test_absent_roles_produce_an_empty_canvas_overlay_batch():
    overlays = complete_canvas_overlays(Tokens(), CANVAS)
    assert overlays.pattern is None and overlays.radial is None


def test_seeded_pattern_overlay_uses_completed_canvas_and_role_slot_identity():
    overlays = complete_canvas_overlays(
        Tokens({"canvas-overlay": {}}, {"canvas-overlay": GRAIN}), CANVAS)

    assert overlays.radial is None
    assert overlays.pattern.placement_id == "canvas-overlay"
    assert overlays.pattern.slot.slot_id == overlays.pattern.slot.source_ref == "canvas-overlay"
    assert overlays.pattern.slot.bounds is CANVAS
    assert overlays.pattern.pattern.region is CANVAS
    assert overlays.pattern.pattern.clip is CANVAS
    assert overlays.pattern.pattern.origin == (10.0, 20.0)
    assert overlays.pattern.pattern.density_basis_points > 0


def test_radial_only_uses_canvas_origin_and_size_with_zero_inner_stop():
    overlays = complete_canvas_overlays(
        Tokens({"canvas-overlay-gradient": RADIAL}), CANVAS)

    assert overlays.pattern is None
    assert overlays.radial.placement_id == "canvas-overlay-gradient"
    assert overlays.radial.slot.slot_id == overlays.radial.slot.source_ref == "canvas-overlay-gradient"
    assert overlays.radial.slot.bounds is CANVAS
    assert overlays.radial.center == (Decimal("60.0"), Decimal("40.00"))
    assert overlays.radial.radii == (Decimal("25.00"), Decimal("40.0"))
    assert overlays.radial.stop_offsets == (Decimal(0), Decimal(1))


def test_pattern_and_radial_roles_complete_independently_together():
    overlays = complete_canvas_overlays(Tokens({
        "canvas-overlay": {}, "canvas-overlay-gradient": RADIAL,
    }, {"canvas-overlay": GRAIN}), CANVAS)
    assert overlays.pattern is not None and overlays.radial is not None


def test_radial_inner_stop_adds_declared_offset_without_owning_stop_paint():
    radial = {**RADIAL, "radialInnerStop": Decimal("0.4")}
    overlays = complete_canvas_overlays(Tokens({"canvas-overlay-gradient": radial}), CANVAS)
    assert overlays.radial.stop_offsets == (Decimal(0), Decimal("0.4"), Decimal(1))


def test_missing_radial_geometry_is_required_at_its_role_property_pointer():
    with pytest.raises(LayoutError) as error:
        complete_canvas_overlays(Tokens({"canvas-overlay-gradient": {
            key: value for key, value in RADIAL.items() if key != "radialRadiusBlock"
        }}), CANVAS)
    assert (error.value.diagnostic_id, error.value.path) == (
        "E_THEME_ROLE_REQUIRED", "/body/roles/canvas-overlay-gradient/radialRadiusBlock")


def test_radial_domain_and_completed_overflow_report_the_offending_property():
    invalid = {**RADIAL, "radialInnerStop": Decimal(1)}
    with pytest.raises(LayoutError) as error:
        complete_canvas_overlays(Tokens({"canvas-overlay-gradient": invalid}), CANVAS)
    assert (error.value.diagnostic_id, error.value.path) == (
        "E_VISUAL_CAPABILITY_LIMIT", "/body/roles/canvas-overlay-gradient/radialInnerStop")

    huge_canvas = Rect(Decimal(0), Decimal(0), Decimal("1e999999"), Decimal(80))
    overflowing = {**RADIAL, "radialRadiusInline": Decimal("1e999999")}
    with pytest.raises(LayoutError) as error:
        complete_canvas_overlays(Tokens({"canvas-overlay-gradient": overflowing}), huge_canvas)
    assert (error.value.diagnostic_id, error.value.path) == (
        "E_VISUAL_CAPABILITY_LIMIT", "/body/roles/canvas-overlay-gradient/radialRadiusInline")


@pytest.mark.parametrize("raw", [True, "0.5", 0.5, 1])
def test_radial_tokens_require_theme_decimal_values(raw):
    malformed = {**RADIAL, "radialCenterInline": raw}
    with pytest.raises(LayoutError) as error:
        complete_canvas_overlays(Tokens({"canvas-overlay-gradient": malformed}), CANVAS)
    assert (error.value.diagnostic_id, error.value.path) == (
        "E_VISUAL_CAPABILITY_LIMIT", "/body/roles/canvas-overlay-gradient/radialCenterInline")


def test_radial_completed_geometry_must_fit_binary64_but_large_finite_values_are_kept():
    large_canvas = Rect(Decimal(0), Decimal(0), Decimal(1600), Decimal(80))
    valid = {**RADIAL, "radialRadiusInline": Decimal("1e300")}
    result = complete_canvas_overlays(
        Tokens({"canvas-overlay-gradient": valid}), large_canvas).radial
    assert result.radii[0] == Decimal("1.6E+303")

    too_large = {**RADIAL, "radialRadiusInline": Decimal("1e308")}
    with pytest.raises(LayoutError) as error:
        complete_canvas_overlays(Tokens({"canvas-overlay-gradient": too_large}), large_canvas)
    assert (error.value.diagnostic_id, error.value.path) == (
        "E_VISUAL_CAPABILITY_LIMIT", "/body/roles/canvas-overlay-gradient/radialRadiusInline")


def test_pattern_role_without_a_pattern_binding_is_absent():
    with pytest.raises(LayoutError) as error:
        complete_canvas_overlays(Tokens({"canvas-overlay": {}}), CANVAS)
    assert (error.value.diagnostic_id, error.value.path) == (
        "E_THEME_ROLE_REQUIRED", "/body/roles/canvas-overlay/pattern")


def test_pattern_binding_with_unsupported_value_fails_closed():
    with pytest.raises(LayoutError) as error:
        complete_canvas_overlays(Tokens({"canvas-overlay": {}}, {"canvas-overlay": {"kind": "other"}}), CANVAS)
    assert (error.value.diagnostic_id, error.value.path) == (
        "E_THEME_ROLE_PROPERTY_UNSUPPORTED", "/body/roles/canvas-overlay/pattern")


def test_positive_radial_radius_cannot_collapse_to_zero_in_binary64():
    tiny = {**RADIAL, "radialRadiusInline": Decimal("1e-999")}
    with pytest.raises(LayoutError) as error:
        complete_canvas_overlays(Tokens({"canvas-overlay-gradient": tiny}), CANVAS)
    assert (error.value.diagnostic_id, error.value.path) == (
        "E_VISUAL_CAPABILITY_LIMIT", "/body/roles/canvas-overlay-gradient/radialRadiusInline")
