"""Isolated PDF paint opacity, including overlapping compound primitives."""
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
import pypdfium2
import pytest

from chrona.presentation.renderers.pdf_opacity import render_pdf_vector
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.scene.model import ScenePaint, ScenePrimitive
from tests.unit.chrona.presentation.renderers.test_pdf_scene_paints import _surface


def _image(pdf):
    document = pypdfium2.PdfDocument(pdf)
    return document[0].render(scale=4 / 3).to_pil().convert("RGB")


def _svg(body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">'
            '<rect width="100" height="100" fill="white"/>' + body + '</svg>').encode()


def test_scene_rect_opacity_has_pdf_alpha_and_does_not_change_public_svg():
    surface = _surface(ScenePrimitive("shade", "Rect", "shade", "background", "calendar", "calendar-closed",
                                     (10, 10, 70, 70), paint=ScenePaint("#000000", None, None, (), 0.1)))
    svg = render_v05_svg(surface, viewer_fit=False).encode()
    pdf = render_pdf_vector(svg, font_map=None)
    reader = PdfReader(BytesIO(pdf))
    states = reader.pages[0]["/Resources"]["/ExtGState"]
    # ReportLab emits fill and stroke alpha as separate graphics-state updates.
    for channel in ("/ca", "/CA"):
        assert any(float(state.get(channel, 1)) == 0.1 for state in states.values())
    forms = reader.pages[0]["/Resources"]["/XObject"]
    assert any(form.get_object()["/Group"]["/S"] == "/Transparency"
               and form.get_object()["/Group"]["/I"] for form in forms.values())
    assert _image(pdf).getpixel((30, 30)) == pytest.approx((229, 229, 229), abs=2)
    assert render_v05_svg(surface, viewer_fit=False).encode() == svg


def test_group_opacity_is_applied_once_at_overlapping_children_and_fill_stroke():
    svg = _svg('<g opacity="0.1"><rect x="10" y="10" width="50" height="50" fill="black" stroke="black" stroke-width="8"/>'
               '<rect x="30" y="10" width="50" height="50" fill="black"/></g>')
    image = _image(render_pdf_vector(svg, font_map=None))
    # Overlap and fill/stroke junctions are not separately alpha-painted.
    for point in ((20, 30), (40, 30), (70, 30), (12, 30)):
        assert image.getpixel(point) == pytest.approx((229, 229, 229), abs=2)


def test_nested_groups_preserve_combined_alpha_clip_transform_and_painter_order():
    svg = _svg('<defs><clipPath id="clip"><rect x="10" y="10" width="30" height="40"/></clipPath></defs>'
               '<g transform="translate(10 0)" clip-path="url(#clip)" opacity="0.5">'
               '<g opacity="0.5"><rect x="0" y="0" width="70" height="70" fill="black"/></g></g>'
               '<rect x="20" y="30" width="5" height="5" fill="red"/>')
    image = _image(render_pdf_vector(svg, font_map=None))
    assert image.getpixel((30, 20)) == pytest.approx((191, 191, 191), abs=2)
    assert image.getpixel((60, 20)) == (255, 255, 255)
    assert image.getpixel((22, 32)) == (255, 0, 0)


@pytest.mark.parametrize("opacity,expected", [(0, 255), (1, 0)])
def test_extreme_opacity_is_exact(opacity, expected):
    image = _image(render_pdf_vector(_svg(f'<rect width="100" height="100" fill="black" opacity="{opacity}"/>'), font_map=None))
    assert image.getpixel((30, 30)) == (expected, expected, expected)


def test_transparency_form_preserves_closed_embedded_font_and_text():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from chrona.presentation.renderers.registry import _ClosedPdfFontMap

    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    pdfmetrics.registerFont(TTFont("opacity-proof-noto", root / "src/chrona/resources/fonts/noto-sans-regular-v1.ttf"))
    svg = _svg('<g opacity="0.5"><text x="10" y="40" font-family="Closed Proof" '
               'font-weight="400" font-size="20">Exact face</text></g>')
    pdf = render_pdf_vector(svg, font_map=_ClosedPdfFontMap({("closed proof", 400): "opacity-proof-noto"}))
    reader = PdfReader(BytesIO(pdf))
    form = next(iter(reader.pages[0]["/Resources"]["/XObject"].values())).get_object()
    fonts = [item.get_object() for item in form["/Resources"]["/Font"].values()]
    embedded = next(font for font in fonts if "NotoSans" in font["/BaseFont"])
    assert embedded["/FontDescriptor"]["/FontFile2"].get_data()
    assert "Exact face" in reader.pages[0].extract_text()
