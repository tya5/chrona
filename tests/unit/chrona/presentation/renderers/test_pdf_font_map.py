import pytest

from chrona.presentation.renderers.registry import _ClosedPdfFontMap, _svg_font_characters


def test_font_map_uses_only_completed_face_aliases():
    mapping = _ClosedPdfFontMap({("cff proof", 400): "exact-regular", ("cff proof", 700): "exact-bold"})
    assert mapping
    assert mapping.find_font("CFF Proof", "400", "normal") == ("exact-regular", True)
    assert mapping.find_font("cff proof", "normal", "normal") == ("exact-regular", True)
    assert mapping.find_font("CFF Proof", "bold", "normal") == ("exact-bold", True)


def test_font_map_routes_registered_truetype_faces_without_default_lookup():
    mapping = _ClosedPdfFontMap({("noto sans", 400): "Noto Sans",
                                 ("noto sans", 700): "Noto Sans-700"})
    assert mapping.find_font("Noto Sans", "400", "normal") == ("Noto Sans", True)
    assert mapping.find_font("Noto Sans", "700", "normal") == ("Noto Sans-700", True)


@pytest.mark.parametrize("family,weight,style", [
    ("unknown", "400", "normal"), ("CFF Proof", "700", "normal"),
    ("CFF Proof", "400", "italic"), ("CFF Proof", "invalid", "normal"),
])
def test_font_map_refuses_discovery_substitution_or_unselected_style(family, weight, style):
    with pytest.raises(ValueError, match="E_RENDER_FONT_CLOSURE"):
        _ClosedPdfFontMap({("cff proof", 400): "exact"}).find_font(family, weight, style)


def test_svg_characters_follow_completed_face_and_multiline_runs():
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><text font-family="CFF Proof" font-weight="400">A<tspan>H&amp;</tspan></text><text font-family="Other" font-weight="700">B</text></svg>'
    assert _svg_font_characters(svg) == {
        ("CFF Proof", 400): frozenset(map(ord, "AH&")),
        ("Other", 700): frozenset({ord("B")}),
    }
