import pytest

from chrona.presentation.layout.mark_geometry import glyph_parts, symbol_parts


def test_catalog_glyph_quadratics_use_existing_contain_and_center_fit():
    glyph = {
        "viewport": {"inlineSize": 20, "blockSize": 10},
        "parts": [{"paint": "fill", "data": "M 0 0 Q 10 10 20 0 L 20 10 L 0 10 Z"}],
    }

    parts = symbol_parts({"shape": "glyph", **glyph}, (5, 10, 20, 20))

    commands = parts[0].commands
    assert [command.kind for command in commands] == ["move", "quadratic", "line", "line", "line"]
    assert commands[0].points == ((5.0, 15.0),)
    assert commands[1].points == ((15.0, 25.0), (25.0, 15.0))
    assert parts[0].paint_mode == "fill"


def test_catalog_glyph_viewport_must_be_positive_and_parts_nonempty():
    with pytest.raises(ValueError, match="E_THEME_TOKEN_TYPE"):
        glyph_parts({"viewport": {"inlineSize": 0, "blockSize": 10}, "parts": [{"paint": "fill", "data": "M 0 0"}]},
                    (0, 0, 10, 10))
    with pytest.raises(ValueError, match="E_THEME_TOKEN_TYPE"):
        glyph_parts({"viewport": {"inlineSize": 10, "blockSize": 10}, "parts": []}, (0, 0, 10, 10))


def test_resolved_catalog_stroke_uses_uniform_fit_width_and_exact_finish():
    glyph = {
        "shape": "catalog-glyph",
        "ref": "starter:gate",
        "viewport": {"inlineSize": 10, "blockSize": 10},
        "parts": [{"paint": "stroke", "data": "M 0 0 Q 5 10 10 0",
                   "strokeWidth": 1.5, "lineCap": "round", "lineJoin": "bevel"}],
    }

    part = symbol_parts(glyph, (0, 0, 40, 20))[0]

    assert part.commands[1].kind == "quadratic"
    assert part.stroke_width == pytest.approx(3.0)
    assert (part.line_cap, part.line_join) == ("round", "bevel")
