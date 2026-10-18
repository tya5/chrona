from types import MappingProxyType

from chrona.presentation.layout.surface_marks import MARK_GEOMETRY_ROLES, resolve_mark_geometries
from chrona.presentation.model.theme_tokens import ThemeTokenView


def _theme_tokens():
    values = {
        "height": {"type": "number", "value": "0.25"},
        "order": {"type": "number", "value": 10},
        "radius": {"type": "number", "value": 0},
        "gap": {"type": "number", "value": 4},
        "padding": {"type": "number", "value": 2},
    }
    roles = {
        role: {"markHeight": "height", "markPaintOrder": "order", "markCornerRadius": "radius"}
        for role in MARK_GEOMETRY_ROLES
    }
    return ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
                          "body": {"values": values, "roles": roles}})


def _add_mark_role(theme, role, *, height, offset, order, radius, symbol_height=None, symbol_offset=None):
    values = theme["body"]["values"]
    bindings = theme["body"]["roles"].setdefault(role, {})
    for prop, value, token_type in (
        ("markHeight", height, "number"), ("markOffset", offset, "number"),
        ("markPaintOrder", order, "number"), ("markCornerRadius", radius, "number"),
        ("symbolHeight", symbol_height, "number"), ("symbolOffset", symbol_offset, "number"),
    ):
        if value is None:
            continue
        token = f"{role}-{prop}"
        values[token] = {"type": token_type, "value": value}
        bindings[prop] = token


def test_default_role_selection_preserves_the_existing_canonical_geometry():
    tokens = _theme_tokens()

    default = resolve_mark_geometries(tokens)
    explicit_empty = resolve_mark_geometries(tokens, theme_role_by_geometry_role=MappingProxyType({}))

    assert tuple(default) == MARK_GEOMETRY_ROLES
    assert explicit_empty == default
    assert default["planned"].height == 0.25
    assert default["planned"].offset == 0.375
    assert default["planned"].paint_order == 10
    assert default["actual"].symbol_extent == (0.375, 0.25)


def test_custom_theme_roles_override_geometry_and_actual_fallback_uses_resolved_planned():
    theme = {"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
             "body": {"values": dict(_theme_tokens().resolved_theme["body"]["values"]),
                      "roles": dict(_theme_tokens().resolved_theme["body"]["roles"])} }
    _add_mark_role(theme, "custom-planned", height="0.4", offset="0.1", order=20,
                   radius="0.05", symbol_height="0.6", symbol_offset="0.2")
    _add_mark_role(theme, "custom-actual", height="0.2", offset="0.1", order=30, radius="0.1")
    tokens = ThemeTokenView(theme)
    selection = MappingProxyType({"planned": "custom-planned", "actual": "custom-actual"})

    geometries = resolve_mark_geometries(tokens, theme_role_by_geometry_role=selection)

    assert tuple(geometries) == MARK_GEOMETRY_ROLES
    assert (geometries["planned"].height, geometries["planned"].offset,
            geometries["planned"].paint_order, geometries["planned"].corner_radius,
            geometries["planned"].symbol_extent) == (0.4, 0.1, 20, 0.05, (0.2, 0.6))
    assert (geometries["actual"].height, geometries["actual"].offset,
            geometries["actual"].paint_order, geometries["actual"].corner_radius,
            geometries["actual"].symbol_extent) == (0.2, 0.1, 30, 0.1, (0.2, 0.6))
    assert geometries["snapshot"].height == 0.25
