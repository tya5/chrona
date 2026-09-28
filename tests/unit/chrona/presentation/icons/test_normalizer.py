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


def test_pattern_wraps_strokes_across_all_relevant_tile_edges():
    pattern = normalize_pattern_entry({
        "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
        "densityBasisPoints": 1250,
        "primitives": [{"kind": "line", "x1": 0, "y1": 0,
                        "x2": 0, "y2": 8, "strokeWidth": 1}],
    })
    assert pattern["densityBasisPoints"] == 1250


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
