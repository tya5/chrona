"""PDF-only small-caps positioning consumes Layout's completed advances."""
from datetime import date
from io import BytesIO
from xml.etree import ElementTree

from pypdf import PdfReader
from pypdf.generic import ContentStream
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg

from chrona.presentation.renderers.pdf_svg import lower_pdf_svg
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.scene.model import (
    ScenePaint,
    ScenePrimitive,
    SceneSurface,
    SurfaceScaleManifest,
    TextLayout,
    TextRun,
)


NS = "{http://www.w3.org/2000/svg}"


def _surface(layout):
    text = " ".join(layout.lines)
    primitive = ScenePrimitive(
        "small-caps", "Text", "small-caps-source", "label", "label",
        "label", (20, 20, 20, 24), text=text, baseline=(20, 30),
        text_layout=layout, paint=ScenePaint("#000000", None, None, (), 1),
    )
    scale = SurfaceScaleManifest("surface", "primary", date(2026, 1, 1), date(2026, 1, 2),
                                 0, 100, 0, 100)
    return SceneSurface("surface", (), (), (), scale, (primitive,),
                        ScenePaint("#FFFFFF", None, None, (), 1), canvas_bounds=(0, 0, 100, 100))


def test_pdf_lowering_places_runs_from_measured_advances_and_preserves_text_geometry():
    layout = TextLayout(
        bounds=(20, 20, 20, 24), baseline=(20, 30), lines=("A B", "CD"),
        family="CFF Proof", weight=400, font_size=10, line_height=1.2,
        asset_identity="sha256:face", letter_spacing=0.5, text_transform="small-caps",
        orientation="rotate-cw", rotation_degrees=90, horizontal_scale=0.8,
        runs=((TextRun("A ", 10, 4), TextRun("B", 8, 3)),
              (TextRun("C", 8, 2), TextRun("D", 8, 2))),
    )
    surface = _surface(layout)
    public_svg = render_v05_svg(surface, viewer_fit=False).encode()

    lowered = lower_pdf_svg(surface, public_svg)

    assert lowered != public_svg
    assert b'xmlns="http://www.w3.org/2000/svg"' in lowered
    root = ElementTree.fromstring(lowered)
    text = next(node for node in root.iter(NS + "text") if node.get("data-scene-id") == "small-caps")
    assert text.get("transform") == "rotate(90 20 30) matrix(0.8 0 0 1 4 0)"
    lines = [node for node in text if node.tag == NS + "tspan"]
    assert [line.get("dy") for line in lines] == ["0", "12"]
    runs = [[span for span in line if span.tag == NS + "tspan"] for line in lines]
    assert [[span.text for span in line] for line in runs] == [["A ", "B"], ["C", "D"]]
    assert [[span.get("x") for span in line] for line in runs] == [
        ["20", "25.625"], ["20", "23.125"],
    ]
    assert [[span.get("font-size") for span in line] for line in runs] == [
        ["10", "8"], ["8", "8"],
    ]
    assert all(span.get("{http://www.w3.org/XML/1998/namespace}space") == "preserve"
               for line in runs for span in line)

    pdf = renderPDF.drawToString(svg2rlg(BytesIO(lowered)))
    reader = PdfReader(BytesIO(pdf))
    positions = [operands[4] for operands, operator in ContentStream(
        reader.pages[0].get_contents(), reader).operations if operator == b"Tm"]
    assert [position for position in positions if position in {20, 25.625, 23.125}] == [
        20, 25.625, 20, 23.125,
    ]


def test_pdf_lowering_keeps_non_run_surface_svg_byte_identical():
    layout = TextLayout(
        bounds=(20, 20, 20, 24), baseline=(20, 30), lines=("plain",),
        family="CFF Proof", weight=400, font_size=10, line_height=1.2,
        asset_identity="sha256:face",
    )
    surface = _surface(layout)
    public_svg = render_v05_svg(surface, viewer_fit=False).encode()

    assert lower_pdf_svg(surface, public_svg) is public_svg


def test_pdf_run_positioning_retains_private_exact_face_aliases():
    layout = TextLayout(
        bounds=(20, 20, 20, 24), baseline=(20, 30), lines=("AB",),
        family="Proof", weight=400, font_size=10, line_height=1.2,
        asset_identity="sha256:face", runs=((TextRun("A", 8, 4), TextRun("B", 8, 3)),),
    )
    surface = _surface(layout)
    svg = render_v05_svg(surface, viewer_fit=False).encode()
    from lxml import etree
    root = etree.fromstring(svg)
    text = next(root.iter(NS + "text"))
    spans = list(text.iter(NS + "tspan"))
    for index, span in enumerate(spans):
        span.set("font-family", f"pdf-private-{index}")
        span.set("font-weight", "700")
        span.set("data-font-asset", f"sha256:face{index}")
    lowered = etree.fromstring(lower_pdf_svg(surface, etree.tostring(root)))
    retained = list(next(lowered.iter(NS + "text")).iter(NS + "tspan"))
    assert [span.get("font-family") for span in retained] == ["pdf-private-0", "pdf-private-1"]
    assert [span.get("font-weight") for span in retained] == ["700", "700"]
    assert [span.get("data-font-asset") for span in retained] == ["sha256:face0", "sha256:face1"]
