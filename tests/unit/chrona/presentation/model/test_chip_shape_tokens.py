from decimal import Decimal

import pytest

from chrona.presentation.model.theme_tokens import (
    BurstChipShape, CatalogChipShape, RectangleChipShape, ThemeTokenError, ThemeTokenView,
)


ROLES = ("as-of-label-chip", "member-label-chip", "finish-delta-chip", "period-label-chip")


def _theme(value=None, *, role=ROLES[0], properties=None, tokens=None):
    values = dict(tokens or {})
    binding = dict(properties or {})
    if value is not None:
        values["shape"] = {"type": "chipShape", "value": value}
        binding["chipShape"] = "shape"
    return {"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": {
        "values": values, "roles": {role: binding}, "metrics": {},
    }}


@pytest.mark.parametrize("role", ROLES)
def test_absent_and_explicit_rectangle_resolve_identically_without_activating_chip(role):
    absent = ThemeTokenView(_theme(role=role))
    explicit = ThemeTokenView(_theme({"kind": "rectangle"}, role=role))
    assert absent.label_chip_shape(role) == explicit.label_chip_shape(role) == RectangleChipShape()
    assert explicit.label_chip(role) is None


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("points,ratio", [(2, 1), (5, .4), (5.0, .4), (49, 1e-12)])
def test_burst_normalization_is_policy_only_and_keeps_text_follows_box(role, points, ratio):
    tokens = ThemeTokenView(_theme({"kind": "burst", "points": points, "innerRatio": ratio},
                                  role=role, properties={"viewerFit": "text-follows-box"}))
    assert tokens.label_chip_shape(role) == BurstChipShape(points, Decimal(str(ratio)))


@pytest.mark.parametrize("value,suffix", [
    ({"kind": "rectangle", "points": 2}, ""),
    ({"kind": "unknown"}, ""),
    ({"kind": "burst", "points": True, "innerRatio": .5}, "/points"),
    ({"kind": "burst", "points": 1, "innerRatio": .5}, "/points"),
    ({"kind": "burst", "points": 2.5, "innerRatio": .5}, "/points"),
    *[({"kind": "burst", "points": 5, "innerRatio": ratio}, "/innerRatio")
      for ratio in (True, "0.5", 0, -1, 1.1, float("nan"), float("inf"))],
])
def test_malformed_shape_has_selected_property_pointer(value, suffix):
    with pytest.raises(ThemeTokenError) as error:
        ThemeTokenView(_theme(value)).label_chip_shape(ROLES[0])
    assert error.value.diagnostic_id == "E_THEME_TOKEN_TYPE"
    assert error.value.path == f"/body/roles/{ROLES[0]}/chipShape{suffix}"


@pytest.mark.parametrize("property_name,value,token_type", [
    ("viewerFit", "box-follows-text", None),
    ("cornerRadius", "capsule", "radius"),
    ("cornerRadius", 1, "radius"),
    ("markCornerRadius", .2, "number"),
    ("pattern", "anything", "pattern"),
])
def test_nonrect_shape_refuses_declared_incompatibility_at_its_property(property_name, value, token_type):
    properties = {property_name: "conflict" if token_type else value}
    tokens = {"conflict": {"type": token_type, "value": value}} if token_type else {}
    with pytest.raises(ThemeTokenError) as error:
        ThemeTokenView(_theme({"kind": "burst", "points": 5, "innerRatio": .5},
                             properties=properties, tokens=tokens)).label_chip_shape(ROLES[0])
    assert error.value.path == f"/body/roles/{ROLES[0]}/{property_name}"


def test_rectangle_does_not_restrict_existing_corner_and_viewer_policy():
    tokens = ThemeTokenView(_theme({"kind": "rectangle"},
                                  properties={"cornerRadius": "round", "pattern": "pattern"},
                                  tokens={"round": {"type": "radius", "value": "capsule"}}))
    assert tokens.label_chip_shape(ROLES[0]) == RectangleChipShape()


def test_catalog_uses_shared_nine_slice_normalization_and_viewport_validation():
    value = {"kind": "catalog", "glyph": "test:box", "sliceInsets": {
        "top": 1, "right": 2, "bottom": 3, "left": 4}, "unitEm": .25}
    glyphs = {"test:box": {"viewport": {"inlineSize": 8, "blockSize": 8}}}
    tokens = ThemeTokenView(_theme(value), catalog_glyphs=glyphs)
    assert tokens.label_chip_shape(ROLES[0]) == CatalogChipShape(
        "test:box", (Decimal(1), Decimal(2), Decimal(3), Decimal(4)), Decimal(".25"))
    value["sliceInsets"]["left"] = 7
    with pytest.raises(ThemeTokenError) as error:
        tokens.label_chip_shape(ROLES[0])
    assert error.value.path == f"/body/roles/{ROLES[0]}/chipShape/sliceInsets"


@pytest.mark.parametrize("unit", [False, 0, -1, float("inf"), "0.25"])
def test_catalog_invalid_unit_is_theme_owned(unit):
    value = {"kind": "catalog", "glyph": "test:box", "sliceInsets": dict.fromkeys(
        ("top", "right", "bottom", "left"), 0), "unitEm": unit}
    with pytest.raises(ThemeTokenError) as error:
        ThemeTokenView(_theme(value)).label_chip_shape(ROLES[0])
    assert error.value.path == f"/body/roles/{ROLES[0]}/chipShape/unitEm"
