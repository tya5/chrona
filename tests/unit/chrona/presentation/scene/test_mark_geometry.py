import pytest

from chrona.presentation.scene.mark_geometry import glyph_parts, symbol_geometry


def _glyph(*parts):
    return {"shape": "glyph", "viewBox": [10, 10], "parts": list(parts)}


def test_glyph_parts_fits_the_view_box_contain_and_centred_into_wider_bounds():
    parts = glyph_parts(_glyph({"d": "M0 0L10 0L10 10L0 10Z", "paint": "fill"}), (0, 0, 40, 20))
    assert len(parts) == 1
    points = [command.points[0] for command in parts[0].outline]
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    # 10x10 viewBox scaled to fit 40x20 bounds: scale=2, centred inline (offset 10).
    assert min(xs) == pytest.approx(10.0)
    assert max(xs) == pytest.approx(30.0)
    assert min(ys) == pytest.approx(0.0)
    assert max(ys) == pytest.approx(20.0)


def test_glyph_parts_omits_a_part_declaring_no_paint():
    parts = glyph_parts(_glyph({"d": "M0 0L10 0L10 10L0 10Z", "paint": "fill"},
                               {"d": "M2 2L8 2L8 8L2 8Z", "paint": "none"}),
                        (0, 0, 10, 10))
    assert len(parts) == 1


def test_glyph_parts_carries_each_part_paint_mode_and_optional_literal_color():
    parts = glyph_parts(_glyph({"d": "M0 0L10 0L10 10L0 10Z", "paint": "fill"},
                               {"d": "M2 2L8 2L8 8L2 8Z", "paint": "stroke", "color": "#1B1B1B"}),
                        (0, 0, 10, 10))
    assert [part.paint for part in parts] == ["fill", "stroke"]
    assert parts[0].color is None
    assert parts[1].color == "#1B1B1B"


def test_glyph_parts_rejects_a_curved_part_not_yet_supported():
    with pytest.raises(ValueError, match="E_THEME_TOKEN_TYPE"):
        glyph_parts(_glyph({"d": "M0 0C1 1 2 2 3 3", "paint": "fill"}), (0, 0, 10, 10))


def test_glyph_parts_rejects_a_missing_view_box():
    with pytest.raises(ValueError, match="E_THEME_TOKEN_TYPE"):
        glyph_parts({"shape": "glyph", "parts": [{"d": "M0 0L1 1Z", "paint": "fill"}]}, (0, 0, 10, 10))


def test_glyph_parts_rejects_empty_parts():
    with pytest.raises(ValueError, match="E_THEME_TOKEN_TYPE"):
        glyph_parts({"shape": "glyph", "viewBox": [10, 10], "parts": []}, (0, 0, 10, 10))


def test_symbol_geometry_still_resolves_built_in_shapes_from_the_full_value_mapping():
    geometry = symbol_geometry({"shape": "diamond"}, (0, 0, 10, 10))
    assert geometry.outline


def test_symbol_geometry_rejects_a_glyph_shape_reaching_it_directly():
    with pytest.raises(ValueError, match="E_THEME_TOKEN_TYPE"):
        symbol_geometry(_glyph({"d": "M0 0L1 1Z", "paint": "fill"}), (0, 0, 10, 10))
