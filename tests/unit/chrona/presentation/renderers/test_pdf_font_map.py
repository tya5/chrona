import pytest

from chrona.presentation.model.font_metrics import FontFile
from chrona.presentation.renderers.registry import _ClosedPdfFontMap, _pdf_private_svg, _svg_font_characters


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


def test_svg_viewer_alternatives_do_not_hide_selected_pdf_subset_characters():
    svg = b'<svg><text font-family="&quot;CFF Proof&quot;, Missing Face, sans-serif" font-weight="700">A<tspan>B</tspan></text></svg>'
    assert _svg_font_characters(svg) == {("CFF Proof", 700): frozenset(map(ord, "AB"))}


def test_svg_run_faces_override_inherited_pdf_font_face_for_text_and_tail():
    svg = (b'<svg><text font-family="Primary" font-weight="400">A'
           b'<tspan font-family="CJK" font-weight="700" data-asset-identity="sha256:cjk">\xe6\x97\xa5'
           b'<tspan>\xe6\x9c\xac</tspan></tspan>tail</text></svg>')
    assert _svg_font_characters(svg) == {
        ("Primary", 400): frozenset(map(ord, "Atail")),
        ("CJK", 700): frozenset(map(ord, "日本")),
    }


def test_pdf_private_svg_separates_same_name_faces_by_completed_asset_identity(tmp_path):
    from types import SimpleNamespace

    layout = SimpleNamespace(
        family="Noto Sans JP", weight=400, asset_identity="sha256:primary",
        runs=((SimpleNamespace(asset_identity="sha256:primary"),
               SimpleNamespace(asset_identity="sha256:fallback")),),
    )
    surface = SimpleNamespace(primitives=(SimpleNamespace(scene_id="mixed", kind="Text", text_layout=layout),))
    svg = (b'<svg><text data-scene-id="mixed" font-family="Noto Sans JP" font-weight="400">'
           b'<tspan font-family="Noto Sans JP" font-weight="400" data-asset-identity="sha256:primary">A</tspan>'
           b'<tspan font-family="Noto Sans JP" font-weight="400" data-asset-identity="sha256:fallback">\xe6\x97\xa5</tspan>'
           b'</text></svg>')
    files = (
        FontFile(tmp_path / "primary.ttf", "sha256:primary", "Noto Sans JP", 400),
        FontFile(tmp_path / "fallback.ttf", "sha256:fallback", "Noto Sans JP", 400),
    )
    private, aliases = _pdf_private_svg(surface, svg, files)
    assert svg.startswith(b'<svg><text data-scene-id="mixed" font-family="Noto Sans JP"')
    assert aliases is not None
    primary_alias = aliases[("sha256:primary", "noto sans jp", 400)]
    fallback_alias = aliases[("sha256:fallback", "noto sans jp", 400)]
    assert primary_alias != fallback_alias
    assert _svg_font_characters(private) == {
        (primary_alias, 400): frozenset({ord("A")}),
        (fallback_alias, 400): frozenset({ord("日")}),
    }


def test_pdf_private_svg_preserves_default_namespace_and_clipped_raster_with_face_runs(tmp_path):
    from io import BytesIO
    from types import SimpleNamespace

    Image = pytest.importorskip("PIL.Image")
    resvg_py = pytest.importorskip("resvg_py")
    layout = SimpleNamespace(
        family="Noto Sans JP", weight=400, asset_identity="sha256:primary",
        runs=((SimpleNamespace(asset_identity="sha256:primary"),),),
    )
    surface = SimpleNamespace(primitives=(SimpleNamespace(scene_id="mixed", kind="Text", text_layout=layout),))
    svg = (b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 10 10">'
           b'<defs><clipPath id="clip"><rect x="0" y="0" width="4" height="10"/></clipPath></defs>'
           b'<rect width="10" height="10" fill="red" clip-path="url(#clip)"/>'
           b'<text data-scene-id="mixed" font-family="Noto Sans JP" font-weight="400">'
           b'<tspan data-asset-identity="sha256:primary">A</tspan></text></svg>')
    files = (FontFile(tmp_path / "primary.ttf", "sha256:primary", "Noto Sans JP", 400),)

    private, aliases = _pdf_private_svg(surface, svg, files)

    assert aliases is not None
    assert b'xmlns="http://www.w3.org/2000/svg"' in private
    assert b"ns0:" not in private
    assert b"clipPath" in private and b'clip-path="url(#clip)"' in private
    raster = Image.open(BytesIO(resvg_py.svg_to_bytes(svg_string=private.decode(), dpi=96,
                                                       font_files=[], skip_system_fonts=True))).convert("RGB")
    assert raster.getpixel((2, 5)) == (255, 0, 0)
    assert raster.getpixel((7, 5)) != (255, 0, 0)
