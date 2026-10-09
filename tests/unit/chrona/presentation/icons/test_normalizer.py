import math

import pytest

from chrona.presentation.icons import IconNormalizationError, normalize_glyph_entry, normalize_icon, normalize_pattern_entry


def test_normalizes_closed_svg_cubic_and_close():
    icon = normalize_icon("vector", b'<svg viewBox="0 0 24 24"><path d="M0 0 C 1 2 3 4 5 6 Z"/></svg>', (24, 24))
    assert [command.kind for command in icon.paths[0].commands] == ["move", "cubic", "close"]


@pytest.mark.parametrize("payload", (
    b'<svg viewBox="0 0 24 24"><script/></svg>',
    b'<svg viewBox="0 0 24 24"><path style="fill:red" d="M0 0"/></svg>',
    b'<svg viewBox="0 0 24 24"><path d="A 1 1 0 0 1 2 2"/></svg>',
))
def test_rejects_unsafe_svg(payload):
    with pytest.raises(IconNormalizationError):
        normalize_icon("vector", payload, (24, 24))


def test_rejects_png_with_wrong_intrinsic_dimensions():
    payload = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + (23).to_bytes(4, "big") + (24).to_bytes(4, "big")
    with pytest.raises(IconNormalizationError, match="E_ICON_PNG_INVALID"):
        normalize_icon("raster", payload, (24, 24))


def test_normalizes_catalog_glyph_to_canonical_shared_path_form():
    glyph = normalize_glyph_entry({
        "viewport": {"inlineSize": 24, "blockSize": 24},
        "parts": [{"paint": "fill", "d": "m 0,0 h 24 v 24 h -24 z"}],
    })
    assert glyph == {
        "viewport": {"inlineSize": 24, "blockSize": 24},
        "parts": [{"paint": "fill", "data": "M 0 0 L 24 0 L 24 24 L 0 24 Z"}],
    }


@pytest.mark.parametrize("size,declared", [(1, 1250), (2, 2500), (4, 5000)])
def test_pattern_density_uses_exact_basis_points(size, declared):
    pattern = normalize_pattern_entry({
        "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
        "densityBasisPoints": declared,
        "primitives": [{"kind": "rect", "x": 0, "y": 0,
                        "inlineSize": 8, "blockSize": size}],
    })
    assert pattern["densityBasisPoints"] == declared


def test_pattern_tile_allows_finite_fractional_dimensions():
    pattern = normalize_pattern_entry({
        "tile": {"inlineSize": 4.5, "blockSize": 8}, "angle": 0,
        "densityBasisPoints": 1250,
        "primitives": [{"kind": "rect", "x": 0, "y": 0,
                        "inlineSize": 4.5, "blockSize": 1}],
    })
    assert pattern["tile"]["inlineSize"] == 4.5


def test_pattern_arc_lowers_to_quadratic_path_and_checks_derived_density():
    pattern = normalize_pattern_entry({
        "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 15,
        "densityBasisPoints": 189,
        "primitives": [{"kind": "arc", "cx": 4, "cy": 4, "radius": 3,
                        "startAngle": 0, "endAngle": 90, "strokeWidth": 0.25}],
    })
    arc = pattern["primitives"][0]
    assert arc["kind"] == "path"
    assert all(command["kind"] != "arc" for command in arc["commands"])
    assert any(command["kind"] == "quadratic" for command in arc["commands"])


def test_pattern_full_span_max_radius_arc_uses_bounded_density_index():
    pattern = normalize_pattern_entry({
        "tile": {"inlineSize": 256, "blockSize": 256}, "angle": 0,
        "densityBasisPoints": 442,
        "primitives": [{"kind": "arc", "cx": 128, "cy": 128, "radius": 120,
                        "startAngle": 0, "endAngle": 360, "strokeWidth": 4}],
    })
    assert len(pattern["primitives"][0]["commands"]) > 700


def test_pattern_stroke_grid_ties_are_inclusive():
    pattern = normalize_pattern_entry({
        "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
        "densityBasisPoints": 156,
        "primitives": [{"kind": "line", "x1": 0, "y1": 4,
                        "x2": 8, "y2": 4, "strokeWidth": 0.0625}],
    })
    assert pattern["densityBasisPoints"] == 156


def test_pattern_clips_edge_strokes_to_the_fundamental_tile():
    # Tile clipping happens before repetition: only the right half of this
    # edge-centered stroke contributes to the fundamental cell.
    pattern = normalize_pattern_entry({
        "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
        "densityBasisPoints": 625,
        "primitives": [{"kind": "line", "x1": 0, "y1": 0,
                        "x2": 0, "y2": 8, "strokeWidth": 1}],
    })
    assert pattern["densityBasisPoints"] == 625


def _reference_circle_density(circles, *, tile=(8, 8)):
    """Independent 128² sample-grid oracle for ordered circle paint operations."""
    width, height = tile
    visible = 0
    for row in range(128):
        y = (row + 0.5) * height / 128
        for column in range(128):
            x = (column + 0.5) * width / 128
            ink = False
            for cx, cy, radius, channel, stroke_width in circles:
                distance = math.hypot(x - cx, y - cy)
                if distance <= radius:
                    if channel == "ink":
                        ink = True
                    elif channel == "substrate":
                        ink = False
                if stroke_width is not None and max(0, radius - stroke_width / 2) <= distance <= radius + stroke_width / 2:
                    ink = True
            visible += ink
    # Explicit positive half-up rounding, matching the declared basis-point unit.
    return visible, math.floor(visible * 10_000 / (128 * 128) + 0.5)


def test_pattern_circle_defaults_to_ink_without_changing_normalized_bytes():
    pattern = normalize_pattern_entry({
        "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
        "densityBasisPoints": 10000,
        "primitives": [{"kind": "circle", "cx": 4, "cy": 4, "radius": 16}],
    })
    assert pattern["primitives"] == [{"kind": "circle", "cx": 4.0, "cy": 4.0, "radius": 16.0}]


def test_pattern_substrate_fill_erases_earlier_ink_in_painter_order():
    circles = [
        (4, 4, 3, "ink", None),
        (4, 4, 2, "substrate", None),
        (4.5, 4, 1, "substrate", None),
        (4, 4, 0.5, "ink", None),
    ]
    primitives = [
        {"kind": "circle", "cx": cx, "cy": cy, "radius": radius,
         **({"fillChannel": channel} if channel != "ink" else {})}
        for cx, cy, radius, channel, _stroke in circles
    ]
    _visible_samples, expected = _reference_circle_density(circles)
    _full_samples, full_ink = _reference_circle_density([circles[0]])
    assert 0 < expected < full_ink
    normalized = normalize_pattern_entry({
        "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
        "densityBasisPoints": expected, "primitives": primitives,
    })
    assert normalized["densityBasisPoints"] == expected


def test_pattern_circle_stroke_paints_after_fill_and_can_be_ink_only():
    stroke_only = [{"kind": "circle", "cx": 4, "cy": 4, "radius": 2,
                    "fillChannel": "none", "strokeWidth": 0.125}]
    # The 128×128 grid has 0.0625-unit spacing here. Exactly 412 samples lie
    # in this thin annulus, yielding 251 bp after half-up rounding.
    samples, expected = _reference_circle_density([(4, 4, 2, "none", 0.125)])
    assert samples == 412
    assert expected == 251
    normalized = normalize_pattern_entry({
        "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
        "densityBasisPoints": expected, "primitives": stroke_only,
    })
    assert normalized["densityBasisPoints"] == expected

    substrate_then_ring = [{"kind": "circle", "cx": 4, "cy": 4, "radius": 4,
                            "fillChannel": "substrate", "strokeWidth": 1}]
    _ring_samples, expected_ring = _reference_circle_density([(4, 4, 4, "substrate", 1)])
    assert expected_ring > 0
    assert normalize_pattern_entry({
        "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
        "densityBasisPoints": expected_ring, "primitives": substrate_then_ring,
    })["densityBasisPoints"] == expected_ring


@pytest.mark.parametrize("channel", ["bad", None, [], 3])
def test_pattern_rejects_invalid_circle_fill_channel(channel):
    with pytest.raises(IconNormalizationError) as error:
        normalize_pattern_entry({
            "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
            "densityBasisPoints": 100,
            "primitives": [{"kind": "circle", "cx": 4, "cy": 4, "radius": 2,
                            "fillChannel": channel}],
        })
    assert error.value.diagnostic_id == "E_THEME_ASSET_SOURCE_PATTERN"
    assert "fillChannel must be 'ink', 'substrate', or 'none'" in str(error.value)
    assert "/entry/primitives/0/fillChannel" in str(error.value)
    assert (repr(channel) if isinstance(channel, (str, int, float, bool, type(None), list)) else "<list>") in str(error.value)


def test_pattern_circle_none_requires_stroke_and_zero_visible_ink_is_rejected():
    with pytest.raises(IconNormalizationError) as invalid_channel:
        normalize_pattern_entry({
            "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
            "densityBasisPoints": 1,
            "primitives": [{"kind": "circle", "cx": 4, "cy": 4, "radius": 2,
                            "fillChannel": "none"}],
        })
    assert invalid_channel.value.diagnostic_id == "E_THEME_ASSET_SOURCE_PATTERN"
    assert "/entry/primitives/0/strokeWidth" in str(invalid_channel.value)
    assert "fillChannel='none'" in str(invalid_channel.value)
    with pytest.raises(IconNormalizationError) as error:
        normalize_pattern_entry({
            "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
            "densityBasisPoints": 1,
            "primitives": [{"kind": "circle", "cx": 0, "cy": 0, "radius": 0.01}],
        })
    assert error.value.diagnostic_id == "E_THEME_ASSET_SOURCE_DENSITY"


@pytest.mark.parametrize("value,code,operand", [
    (None, "E_THEME_ASSET_SOURCE_GLYPH", "/entry requires object fields"),
    ({"viewport": {"inlineSize": 24, "blockSize": 24}, "parts": [{"paint": "fill", "d": "M0 0 A 1 1"}]},
     "E_THEME_ASSET_SOURCE_PATH", "/entry/parts/0/d"),
    ({"viewport": {"inlineSize": 24, "blockSize": 24}, "parts": [{"paint": "stroke", "d": "M0 0L2 2", "strokeWidth": "wide", "lineCap": "round", "lineJoin": "round"}]},
     "E_THEME_ASSET_SOURCE_VALUE", "/entry/parts/0/strokeWidth"),
])
def test_glyph_diagnostics_identify_invalid_operand(value, code, operand):
    with pytest.raises(IconNormalizationError) as error:
        normalize_glyph_entry(value)
    assert error.value.diagnostic_id == code
    assert operand in str(error.value)


def test_pattern_diagnostics_identify_numeric_operand_and_expected_range():
    with pytest.raises(IconNormalizationError) as error:
        normalize_pattern_entry({
            "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
            "densityBasisPoints": 1250,
            "primitives": [{"kind": "rect", "x": 0, "y": 0,
                            "inlineSize": 8, "blockSize": 257}],
        })
    assert error.value.diagnostic_id == "E_THEME_ASSET_SOURCE_LIMIT"
    assert "/entry/primitives/0/blockSize=257" in str(error.value)
    assert "<= 8" in str(error.value)


def test_path_diagnostic_identifies_path_reference_and_unsupported_command():
    with pytest.raises(IconNormalizationError) as error:
        normalize_icon("vector", b'<svg viewBox="0 0 24 24"><path d="M0 0 A 1 1"/></svg>', (24, 24))
    assert error.value.diagnostic_id == "E_ICON_SVG_UNSAFE"
    assert "/svg/path/@d" in str(error.value)
    assert "unexpected character='A'" in str(error.value)


def test_png_diagnostic_reports_actual_and_expected_viewport():
    payload = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + (23).to_bytes(4, "big") + (24).to_bytes(4, "big")
    with pytest.raises(IconNormalizationError) as error:
        normalize_icon("raster", payload, (24, 24))
    assert error.value.diagnostic_id == "E_ICON_PNG_INVALID"
    assert "23x24" in str(error.value) and "24x24" in str(error.value)


@pytest.mark.parametrize("kind,payload,code,operand", [
    ("poster", b"unused", "E_ICON_CATALOG_SCHEMA", "'poster'"),
    ("raster", b"short-png", "E_ICON_PNG_INVALID", "byte_length=9"),
    ("vector", b"<svg>", "E_ICON_SVG_UNSAFE", "malformed at"),
    ("vector", b'<svg viewBox="0 0 24 24"/>', "E_ICON_SVG_LIMIT", "paths=0"),
])
def test_icon_diagnostics_name_bad_kind_or_payload_operand(kind, payload, code, operand):
    with pytest.raises(IconNormalizationError) as error:
        normalize_icon(kind, payload, (24, 24))
    assert error.value.diagnostic_id == code
    assert operand in str(error.value)


def test_png_limit_diagnostic_reports_actual_dimensions_and_allowed_range():
    payload = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + (4097).to_bytes(4, "big") + (24).to_bytes(4, "big")
    with pytest.raises(IconNormalizationError) as error:
        normalize_icon("raster", payload, (4097, 24))
    assert error.value.diagnostic_id == "E_ICON_PNG_LIMIT"
    assert "4097x24" in str(error.value) and "1..4096" in str(error.value)


def test_svg_unknown_attribute_diagnostic_bounds_key_sample():
    extras = " ".join(f'custom-{index:04d}="x"' for index in range(500))
    payload = f'<svg viewBox="0 0 24 24" {extras}/>'.encode()
    with pytest.raises(IconNormalizationError) as error:
        normalize_icon("vector", payload, (24, 24))
    message = str(error.value)
    assert "unexpected_attributes(count=500" in message
    assert "custom-0000" in message
    assert len(message) < 300


def test_glyph_extra_field_diagnostic_bounds_key_sample():
    parts = {f"extra-{index:04d}": index for index in range(500)}
    with pytest.raises(IconNormalizationError) as error:
        normalize_glyph_entry({"viewport": {"inlineSize": 24, "blockSize": 24},
                               "parts": [{"paint": "fill", "d": "M0 0 L1 1", **parts}]})
    message = str(error.value)
    assert "fields(count=502" in message
    assert "extra-0000" in message
    assert len(message) < 300


def test_svg_limit_diagnostic_reports_actual_path_count():
    payload = b'<svg viewBox="0 0 24 24">' + b'<path d="M0 0"/>' * 129 + b"</svg>"
    with pytest.raises(IconNormalizationError) as error:
        normalize_icon("vector", payload, (24, 24))
    assert error.value.diagnostic_id == "E_ICON_SVG_LIMIT"
    assert "paths=129" in str(error.value) and "1..128" in str(error.value)


def test_pattern_diagnostic_names_invalid_primitive_kind():
    with pytest.raises(IconNormalizationError) as error:
        normalize_pattern_entry({
            "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
            "densityBasisPoints": 1,
            "primitives": [{"kind": "hexagon", "seed": "r7"}],
        })
    assert error.value.diagnostic_id == "E_THEME_ASSET_SOURCE_PATTERN"
    assert "/entry/primitives/0" in str(error.value)
    assert "hexagon" in str(error.value) and "seed" in str(error.value)


def test_pattern_density_diagnostic_names_declared_and_derived_values():
    with pytest.raises(IconNormalizationError) as error:
        normalize_pattern_entry({
            "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
            "densityBasisPoints": 1251,
            "primitives": [{"kind": "rect", "x": 0, "y": 0,
                            "inlineSize": 8, "blockSize": 1}],
        })
    assert error.value.diagnostic_id == "E_THEME_ASSET_SOURCE_DENSITY"
    assert "densityBasisPoints=1251" in str(error.value) and "derived density=1250" in str(error.value)


def test_pattern_visible_density_is_invariant_under_tile_rotation():
    primitive = {"kind": "circle", "cx": 0, "cy": 4, "radius": 2,
                 "fillChannel": "none", "strokeWidth": 1}
    _samples, expected = _reference_circle_density([(0, 4, 2, "none", 1)])
    for angle in (0, 45):
        assert normalize_pattern_entry({
            "tile": {"inlineSize": 8, "blockSize": 8}, "angle": angle,
            "densityBasisPoints": expected, "primitives": [primitive],
        })["densityBasisPoints"] == expected


def test_pattern_seigaiha_circle_tile_uses_final_visible_ink_density():
    centres = [(0, 10), (20, 10), (10, 5)]
    radii = (10, 7, 4)
    primitives = [
        {"kind": "circle", "cx": cx, "cy": cy, "radius": radius,
         "fillChannel": "substrate" if radius == 10 else "none",
         "strokeWidth": 0.8}
        for cx, cy in centres for radius in radii
    ]
    _samples, expected = _reference_circle_density([
        (cx, cy, radius, "substrate" if radius == 10 else "none", 0.8)
        for cx, cy in centres for radius in radii
    ], tile=(20, 10))
    assert len(primitives) == 9
    assert expected == 2606
    normalized = normalize_pattern_entry({
        "tile": {"inlineSize": 20, "blockSize": 10}, "angle": 0,
        "densityBasisPoints": expected, "primitives": primitives,
    })
    assert normalized["densityBasisPoints"] == expected
    assert normalized["primitives"] == primitives


@pytest.mark.parametrize("primitive,declared", [
    ({"kind": "circle", "cx": 0.0625, "cy": 0.03125, "radius": 0.03125}, 1),
    ({"kind": "rect", "x": 0.03125, "y": 0.03125,
      "inlineSize": 0.0625, "blockSize": 0.0625}, 1),
])
def test_pattern_filled_shape_boundary_conventions(primitive, declared):
    pattern = normalize_pattern_entry({
        "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
        "densityBasisPoints": declared, "primitives": [primitive],
    })
    assert pattern["densityBasisPoints"] == declared


def test_pattern_rotates_non_square_repeat_lattice_before_sampling():
    pattern = normalize_pattern_entry({
        "tile": {"inlineSize": 8, "blockSize": 4}, "angle": 45,
        "densityBasisPoints": 1250,
        "primitives": [{"kind": "rect", "x": 0, "y": 0,
                        "inlineSize": 8, "blockSize": 0.5}],
    })
    assert pattern["densityBasisPoints"] == 1250


@pytest.mark.parametrize("primitive,declared", [
    ({"kind": "circle", "cx": 4, "cy": 4, "radius": 16}, 10000),
    ({"kind": "line", "x1": 0, "y1": 4, "x2": 8, "y2": 4, "strokeWidth": 1}, 1250),
])
def test_pattern_circle_and_line_primitives_are_closed_and_measured(primitive, declared):
    pattern = normalize_pattern_entry({
        "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
        "densityBasisPoints": declared, "primitives": [primitive],
    })
    assert pattern["densityBasisPoints"] == declared
    assert pattern["primitives"][0]["kind"] in {"circle", "path"}


def test_pattern_rejects_density_that_does_not_match_wrapped_grid():
    with pytest.raises(IconNormalizationError, match="E_THEME_ASSET_SOURCE_DENSITY"):
        normalize_pattern_entry({
            "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
            "densityBasisPoints": 1300,
            "primitives": [{"kind": "rect", "x": 0, "y": 0,
                            "inlineSize": 8, "blockSize": 1}],
        })


def test_pattern_rejects_arc_quadratic_points_outside_tile_instead_of_clipping():
    with pytest.raises(IconNormalizationError, match="E_THEME_ASSET_SOURCE_LIMIT"):
        normalize_pattern_entry({
            "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
            "densityBasisPoints": 100,
            "primitives": [{"kind": "arc", "cx": 1, "cy": 1, "radius": 2,
                            "startAngle": 180, "endAngle": 270, "strokeWidth": 0.5}],
        })


@pytest.mark.parametrize("pattern", [
    {"tile": {"inlineSize": 257, "blockSize": 8}, "angle": 0, "densityBasisPoints": 1250,
     "primitives": [{"kind": "rect", "x": 0, "y": 0, "inlineSize": 8, "blockSize": 1}]},
    {"tile": {"inlineSize": 8, "blockSize": 8}, "angle": 360, "densityBasisPoints": 1250,
     "primitives": [{"kind": "rect", "x": 0, "y": 0, "inlineSize": 8, "blockSize": 1}]},
    {"tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0, "densityBasisPoints": 1250,
     "primitives": [{"kind": "image", "data": "AA=="}]},
])
def test_pattern_rejects_out_of_profile_values(pattern):
    with pytest.raises(IconNormalizationError):
        normalize_pattern_entry(pattern)
