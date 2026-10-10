"""The optional #1286 chip-shape token has a closed authoring grammar."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from chrona.resources import schema_document, validator_for_schema


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
THEME = "theme-v0.15.schema.yaml"
GEOMETRY_REF = "urn:chrona:graphics-v0.1#/$defs/catalogNineSliceGeometry"
_THEME_VALIDATOR = validator_for_schema(schema_document(THEME))


def _theme(shape: Any | None = None, *, role_value: str = "chip") -> dict[str, Any]:
    values: dict[str, Any] = {}
    roles: dict[str, Any] = {"as-of-chip": {"chipShape": role_value}}
    if shape is not None:
        values[role_value] = {"type": "chipShape", "value": shape}
    return {
        "version": "chrona/theme/v0.15",
        "kind": "theme",
        "id": "chip-shape-schema-test",
        "body": {"values": values, "roles": roles, "colorBindings": {"text.fill": "text"}},
    }


def test_chip_shape_token_accepts_rectangle_burst_and_shared_catalogue_geometry():
    assert _THEME_VALIDATOR.is_valid(_theme({"kind": "rectangle"}))
    assert _THEME_VALIDATOR.is_valid(_theme({"kind": "burst", "points": 2, "innerRatio": 0.01}))
    assert _THEME_VALIDATOR.is_valid(_theme({"kind": "burst", "points": 12, "innerRatio": 1}))
    assert _THEME_VALIDATOR.is_valid(_theme({
        "kind": "catalog",
        "glyph": "chrona-parts:burst",
        "sliceInsets": {"top": 1, "right": 2, "bottom": 3, "left": 4},
        "unitEm": 0.5,
    }))


def test_chip_shape_role_is_optional_and_absent_keeps_the_legacy_input_shape():
    theme = _theme()
    theme["body"]["values"].clear()
    theme["body"]["roles"]["as-of-chip"].clear()
    assert _THEME_VALIDATOR.is_valid(theme)


def test_chip_shape_union_rejects_unknown_kinds_extra_fields_and_invalid_burst_values():
    invalid = (
        {"kind": "ellipse"},
        {"kind": "rectangle", "points": 8},
        {"kind": "burst", "points": 1, "innerRatio": 0.5},
        {"kind": "burst", "points": 8.5, "innerRatio": 0.5},
        {"kind": "burst", "points": 8, "innerRatio": 0},
        {"kind": "burst", "points": 8, "innerRatio": 1.01},
        {"kind": "burst", "points": 8, "innerRatio": 0.5, "extra": True},
        {"kind": "catalog", "glyph": "bad", "sliceInsets": {"top": 1, "right": 1, "bottom": 1, "left": 1}, "unitEm": 1},
        {"kind": "catalog", "glyph": "parts:burst", "sliceInsets": {"top": 1, "right": 1, "bottom": 1, "left": 1}, "unitEm": 0},
        {"kind": "catalog", "glyph": "parts:burst", "sliceInsets": {"top": 1, "right": 1, "bottom": 1}, "unitEm": 1},
        {"kind": "catalog", "glyph": "parts:burst", "sliceInsets": {"top": 1, "right": 1, "bottom": 1, "left": 1}, "unitEm": 1, "extra": 1},
    )
    for value in invalid:
        assert not _THEME_VALIDATOR.is_valid(_theme(value)), value


def test_chip_shape_binding_must_name_a_nonempty_value_token():
    assert not _THEME_VALIDATOR.is_valid(_theme(role_value=""))


def test_annotation_artwork_still_uses_the_same_shared_geometry_definition():
    theme_schema = schema_document(THEME)
    graphics_schema = schema_document("graphics-v0.1.schema.yaml")
    assert theme_schema["$defs"]["artworkGeometry"]["$ref"] == GEOMETRY_REF
    assert theme_schema["$defs"]["artworkObject"]["$ref"] == "#/$defs/artworkGeometry"
    assert theme_schema["$defs"]["artworkLayer"]["allOf"][0]["$ref"] == "#/$defs/artworkGeometry"
    assert "catalogNineSliceGeometry" in graphics_schema["$defs"]
