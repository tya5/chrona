from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from chrona.presentation.model.closure import ClosureError, _resolve_theme_catalog_assets
from chrona.resources import validator_for_schema
from chrona.presentation.color_scheme import _canvas_texture
from chrona.presentation.scene.capabilities import (
    RADIAL_GRADIENT,
    admitted_capability_ids,
    theme_catalog_pattern_consumer,
    theme_role_contract,
    theme_role_property_consumer,
)


SCHEMA_PATH = Path(__file__).resolve().parents[5] / "schemas/theme-v0.15.schema.yaml"
VALIDATOR = validator_for_schema(yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8")))


def _seeded(motif: str = "grain") -> dict[str, object]:
    value: dict[str, object] = {
        "kind": "seeded", "algorithm": "splitmix64-v1", "motif": motif,
        "seed": 7, "tile": {"inlineSize": 20, "blockSize": 12}, "count": 2,
    }
    value.update({"radius": 1} if motif == "grain" else {"length": 4, "strokeWidth": 1, "slant": 0.5})
    return value


def _theme(roles: dict, values: dict, color_bindings: dict | None = None) -> dict:
    return {"version": "chrona/theme/v0.15", "kind": "theme", "id": "surface",
            "body": {"values": values, "roles": roles,
                     "colorBindings": color_bindings or {"canvas-overlay.stroke": "accent"}}}


def _color(value: str = "#223344") -> dict:
    return {"type": "color", "value": value}


def test_theme_schema_accepts_closed_seeded_grain_rain_and_overlay_bindings() -> None:
    values = {
        "grain": {"type": "pattern", "value": _seeded()},
        "rain": {"type": "pattern", "value": _seeded("rain")},
        "fidelity": {"type": "fidelity", "value": "decorative-optional"},
        **{name: {"type": "number", "value": value} for name, value in {
            "cx": 0.5, "cy": 0.5, "rx": 0.25, "ry": 0.25, "inner": 0.2,
        }.items()},
    }
    roles = {
        "canvas-texture": {"pattern": "grain", "patternMode": "ink-only", "textureFidelity": "fidelity"},
        "canvas-overlay": {"pattern": "rain", "textureFidelity": "fidelity"},
        "canvas-overlay-gradient": {"radialCenterInline": "cx", "radialCenterBlock": "cy",
                                    "radialRadiusInline": "rx", "radialRadiusBlock": "ry",
                                    "radialInnerStop": "inner", "gradientFidelity": "fidelity"},
    }
    bindings = {"canvas-texture.stroke": "accent", "canvas-overlay.stroke": "accent",
                "canvas-overlay-gradient.fill": "accent", "canvas-texture.fill": "surface"}
    assert not tuple(VALIDATOR.iter_errors(_theme(roles, values, bindings)))


def test_color_scheme_guard_preserves_opaque_default_and_admits_seeded_ink_only() -> None:
    for pattern_mode in (None, "ink-only"):
        binding = {"pattern": "texture"}
        if pattern_mode:
            binding.update({"patternMode": pattern_mode, "textureFidelity": "fidelity"})
        _canvas_texture(roles={"canvas-texture": binding}, values={
            "texture": {"type": "pattern", "value": _seeded()},
        })


@pytest.mark.parametrize("mutate", [
    lambda value: value.update(algorithm="python-random"),
    lambda value: value.update(seed=True),
    lambda value: value.update(count=65),
    lambda value: value.update(tile={"inlineSize": 4}),
    lambda value: value.update(radius=1, length=2),
    lambda value: value.update(mystery=0),
])
def test_theme_schema_rejects_malformed_seeded_pattern_branches(mutate) -> None:
    declaration = _seeded()
    mutate(declaration)
    theme = _theme({"canvas-overlay": {"pattern": "grain", "stroke": "ink"}},
                   {"grain": {"type": "pattern", "value": declaration}, "ink": _color()})
    assert tuple(VALIDATOR.iter_errors(theme))


def test_consumer_registry_admits_only_declared_surface_role_properties() -> None:
    expected = {
        "canvas-texture": {"patternMode", "textureFidelity", "pattern", "fill", "stroke", "opacity"},
        "canvas-overlay": {"pattern", "stroke", "opacity", "textureFidelity"},
        "canvas-overlay-gradient": {"fill", "opacity", "gradientFidelity", "radialCenterInline",
                                    "radialCenterBlock", "radialRadiusInline", "radialRadiusBlock", "radialInnerStop"},
    }
    for role, properties in expected.items():
        contract = theme_role_contract(role)
        assert contract is not None
        assert properties == set(contract.properties)
        for property_name in properties:
            assert theme_role_property_consumer(role, property_name) is not None
    assert theme_role_property_consumer("planned", "radialRadiusInline") is None
    assert theme_role_property_consumer("group-band", "patternMode") is None
    assert theme_catalog_pattern_consumer("canvas-overlay", "pattern") is not None
    assert theme_catalog_pattern_consumer("canvas-overlay-gradient", "pattern") is None
    assert RADIAL_GRADIENT in admitted_capability_ids(RADIAL_GRADIENT)


def test_closure_allows_seeded_ink_only_overlay_without_fill_or_substrate() -> None:
    theme = _theme({"canvas-overlay": {"pattern": "grain", "stroke": "ink",
                                        "textureFidelity": "fidelity", "opacity": "opacity"}}, {
        "grain": {"type": "pattern", "value": _seeded()}, "ink": _color(),
        "fidelity": {"type": "fidelity", "value": "required"},
        "opacity": {"type": "number", "value": 0.45},
    })
    assert _resolve_theme_catalog_assets(theme, ()) == ({}, {})

    texture = _theme({"canvas-texture": {"pattern": "grain", "patternMode": "ink-only",
                                        "stroke": "ink", "opacity": "opacity",
                                        "textureFidelity": "fidelity"}}, {
        "grain": {"type": "pattern", "value": _seeded()}, "ink": _color(),
        "opacity": {"type": "number", "value": 0.5},
        "fidelity": {"type": "fidelity", "value": "required"},
    })
    assert _resolve_theme_catalog_assets(texture, ()) == ({}, {})


def test_closure_preserves_opaque_canvas_texture_contract_and_requires_opt_in_pattern() -> None:
    opaque = _theme({"canvas-texture": {"pattern": "grain", "fill": "ground", "stroke": "ink"}}, {
        "grain": {"type": "pattern", "value": _seeded()}, "ground": _color(), "ink": _color("#FFFFFF"),
    })
    assert _resolve_theme_catalog_assets(opaque, ()) == ({}, {})

    legacy_noop_bindings = _theme({"canvas-texture": {
        "pattern": "grain", "fill": "ground", "stroke": "ink",
        "opacity": "opacity", "backgroundTreatment": "fill",
    }}, {
        "grain": {"type": "pattern", "value": _seeded()}, "ground": _color(),
        "ink": _color("#FFFFFF"), "opacity": {"type": "number", "value": 1},
    })
    assert _resolve_theme_catalog_assets(legacy_noop_bindings, ()) == ({}, {})

    ink_only_missing_pattern = _theme({"canvas-texture": {"patternMode": "ink-only", "stroke": "ink"}},
                                      {"ink": _color()})
    with pytest.raises(ClosureError) as error:
        _resolve_theme_catalog_assets(ink_only_missing_pattern, ())
    assert (error.value.diagnostic_id, error.value.source_ref) == (
        "E_THEME_ROLE_REQUIRED", "/body/roles/canvas-texture/pattern")

    opacity_in_default_mode = _theme({"canvas-texture": {"pattern": "grain", "fill": "ground",
                                                        "stroke": "ink", "opacity": "opacity"}}, {
        "grain": {"type": "pattern", "value": _seeded()}, "ground": _color(), "ink": _color("#FFFFFF"),
        "opacity": {"type": "number", "value": 1},
    })
    assert _resolve_theme_catalog_assets(opacity_in_default_mode, ()) == ({}, {})

    opacity_not_one = _theme({"canvas-texture": {"pattern": "grain", "fill": "ground",
                                                  "stroke": "ink", "opacity": "opacity"}}, {
        "grain": {"type": "pattern", "value": _seeded()}, "ground": _color(), "ink": _color("#FFFFFF"),
        "opacity": {"type": "number", "value": 0.5},
    })
    with pytest.raises(ClosureError) as error:
        _resolve_theme_catalog_assets(opacity_not_one, ())
    assert (error.value.diagnostic_id, error.value.source_ref) == (
        "E_THEME_ROLE_PROPERTY_UNSUPPORTED", "/body/roles/canvas-texture/opacity")


@pytest.mark.parametrize("role, binding, values, expected", [
    ("canvas-overlay", {"pattern": "pattern", "stroke": "ink", "fill": "paper"},
     {"pattern": {"type": "pattern", "value": _seeded()}, "ink": _color(), "paper": _color()},
     ("E_THEME_ROLE_PROPERTY_UNSUPPORTED", "/body/roles/canvas-overlay/fill")),
    ("planned", {"pattern": "pattern", "fill": "paper", "stroke": "ink"},
     {"pattern": {"type": "pattern", "value": _seeded()}, "ink": _color(), "paper": _color()},
     ("E_THEME_ROLE_PROPERTY_UNSUPPORTED", "/body/roles/planned/pattern")),
])
def test_closure_keeps_seeded_patterns_scoped_to_canvas_roles(role, binding, values, expected) -> None:
    with pytest.raises(ClosureError) as error:
        _resolve_theme_catalog_assets(_theme({role: binding}, values), ())
    assert (error.value.diagnostic_id, error.value.source_ref) == expected


def test_closure_checks_required_radial_geometry_and_scheme_bound_ink() -> None:
    values = {"ink": _color(), **{name: {"type": "number", "value": value} for name, value in {
        "cx": 0.5, "cy": 0.5, "rx": 0.25, "ry": 0.25,
    }.items()}}
    role = {"fill": "ink", "radialCenterInline": "cx", "radialCenterBlock": "cy",
            "radialRadiusInline": "rx", "radialRadiusBlock": "ry"}
    with pytest.raises(ClosureError) as error:
        _resolve_theme_catalog_assets(_theme({"canvas-overlay-gradient": role}, values), ())
    assert (error.value.diagnostic_id, error.value.source_ref) == (
        "E_THEME_ROLE_REQUIRED", "/body/roles/canvas-overlay-gradient/radialInnerStop")
