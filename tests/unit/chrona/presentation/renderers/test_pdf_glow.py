"""Private PDF glow serialization stays inside completed Scene/asset facts."""
from __future__ import annotations

from base64 import b64decode
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from lxml import etree

from PIL import Image
import resvg_py
import pytest

from chrona.presentation.model.font_metrics import FontFile
from chrona.presentation.renderers.pdf_glow import PDF_GLOW_GRAMMAR, lower_pdf_glows
from chrona.presentation.layout.surface_quality import StrokeClip
from chrona.presentation.scene.model import Glow, ScenePaint, ScenePrimitive, SceneSurface, TextLayout
from chrona.presentation.renderers.v05_svg import render_v05_svg


ROOT = Path(__file__).resolve().parents[5]
SVG_NS = "http://www.w3.org/2000/svg"
NS = {"s": SVG_NS}


def _font(path: Path, family: str) -> FontFile:
    return FontFile(path, "sha256:" + sha256(path.read_bytes()).hexdigest(), family, 400)


def _primitive(scene_id: str, region: tuple[float, float, float, float], text_layout=None):
    return SimpleNamespace(scene_id=scene_id, paint=SimpleNamespace(glow=SimpleNamespace(region=region)),
                           text_layout=text_layout)


def _raster(svg: bytes, paths=()) -> Image.Image:
    payload = bytes(resvg_py.svg_to_bytes(svg_string=svg.decode("utf-8"), dpi=96,
                                          font_files=[str(path) for path in paths], skip_system_fonts=True))
    return Image.open(BytesIO(payload)).convert("RGBA")


def _rect_svg() -> bytes:
    return f'''<svg xmlns="{SVG_NS}" width="120" height="100" viewBox="0 0 120 100">
      <defs>
        <clipPath id="outer-clip"><rect x="5" y="5" width="105" height="88"/></clipPath>
        <clipPath id="owner-clip"><rect x="20" y="15" width="52" height="45"/></clipPath>
        <pattern id="source-pattern" patternUnits="userSpaceOnUse" width="8" height="8">
          <rect width="8" height="8" fill="#ee3344"/><path d="M0 0L8 8" stroke="#111111" stroke-width="2"/>
        </pattern>
        <filter id="halo" filterUnits="userSpaceOnUse" x="15.25" y="10.5" width="65.1" height="60.25">
          <feGaussianBlur in="SourceAlpha" stdDeviation="4" result="blur"/>
          <feFlood flood-color="#00aaff" flood-opacity="0.8" result="color"/>
          <feComposite in="color" in2="blur" operator="in" result="halo"/>
          <feMerge><feMergeNode in="halo"/><feMergeNode in="halo"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>
      <g opacity="0.7" clip-path="url(#outer-clip)" transform="rotate(7 60 50)">
        <rect data-scene-id="glowing-rect" x="28" y="23" width="44" height="34" rx="3"
              fill="url(#source-pattern)" opacity="0.5" clip-path="url(#owner-clip)" filter="url(#halo)"/>
      </g>
    </svg>'''.encode()


def test_pdf_glow_preserves_fractional_clip_grid_nested_alpha_and_vector_source():
    source = _rect_svg()
    primitive = _primitive("glowing-rect", (15.25, 10.5, 65.1, 60.25))
    surface = SimpleNamespace(primitives=(primitive,))
    lowered = lower_pdf_glows(surface, source, (), {})
    assert PDF_GLOW_GRAMMAR == "pdf-resvg-completed-glow-v1"

    root = etree.fromstring(lowered)
    image = root.find(".//s:image", NS)
    rect = root.find(".//*[@data-scene-id='glowing-rect']", NS)
    assert image is not None and rect is not None
    assert (image.attrib["x"], image.attrib["y"], image.attrib["width"], image.attrib["height"]) == (
        "15", "10", "66", "61")
    assert "opacity" not in rect.attrib and "clip-path" not in rect.attrib and "filter" not in rect.attrib
    wrapper = rect.getparent()
    assert wrapper is not None and wrapper.tag == f"{{{SVG_NS}}}g"
    assert wrapper.attrib == {"opacity": "0.5", "clip-path": "url(#owner-clip)"}
    assert image.getparent() is wrapper and list(wrapper).index(image) < list(wrapper).index(rect)
    assert root.find(".//s:pattern[@id='source-pattern']", NS) is not None
    assert root.find(".//s:clipPath[@id='outer-clip']", NS) is not None
    assert root.find(".//s:clipPath[@id='owner-clip']", NS) is not None
    assert root.find(".//s:filter[@id='halo']", NS) is not None

    # The private halo contains no SourceGraphic repaint, but the final SVG
    # keeps the original patterned vector primitive and composes it once.
    halo = Image.open(BytesIO(b64decode(image.attrib["href"].split(",", 1)[1]))).convert("RGBA")
    assert halo.size == (66, 61)
    assert halo.getpixel((35 - 15, 40 - 10))[0] < 238
    actual = _raster(lowered)
    expected = _raster(source)
    assert actual.size == expected.size
    # The private 8-bit PNG can differ in RGB from direct SVG filter
    # compositing. Structural invariants stay exact: clipping and composed
    # source alpha are unchanged at control points.
    assert actual.getpixel((18, 35)) == expected.getpixel((18, 35)) == (0, 0, 0, 0)
    assert actual.getpixel((85, 80)) == expected.getpixel((85, 80)) == (0, 0, 0, 0)
    assert actual.getpixel((50, 40))[3] == expected.getpixel((50, 40))[3]


def test_pdf_glow_uses_closed_native_aliases_for_distinct_same_family_weight_faces(tmp_path):
    regular = _font(ROOT / "src/chrona/resources/fonts/noto-sans-regular-v1.ttf", "Shared Face")
    mono = _font(ROOT / "src/chrona/resources/fonts/noto-sans-mono-regular-v1.ttf", "Shared Face")
    aliases = {
        (regular.content_identity, "shared face", 400): "ChronaClosedFace-primary",
        (mono.content_identity, "shared face", 400): "ChronaClosedFace-override",
    }
    layout = SimpleNamespace(
        asset_identity=regular.content_identity, family="Shared Face", weight=400,
        runs=((SimpleNamespace(text="WWWW", family="Shared Face", weight=400,
                               asset_identity=regular.content_identity),
               SimpleNamespace(text="WWWW", family="Shared Face", weight=400,
                               asset_identity=mono.content_identity)),),
    )
    primitive = _primitive("glowing-text", (0, 0, 250, 70), layout)
    surface = SimpleNamespace(primitives=(primitive,))
    svg = f'''<svg xmlns="{SVG_NS}" width="250" height="70" viewBox="0 0 250 70">
      <defs><filter id="glow" filterUnits="userSpaceOnUse" x="0" y="0" width="250" height="70">
        <feGaussianBlur in="SourceAlpha" stdDeviation="3" result="blur"/>
        <feFlood flood-color="#ff8800" flood-opacity="0.8" result="color"/>
        <feComposite in="color" in2="blur" operator="in" result="halo"/>
        <feMerge><feMergeNode in="halo"/><feMergeNode in="halo"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter></defs>
      <text data-scene-id="glowing-text" x="8" y="48" font-size="30" filter="url(#glow)" font-family="ChronaClosedFace-primary">
        <tspan>WWWW</tspan><tspan x="130" font-family="ChronaClosedFace-override">WWWW</tspan>
      </text>
    </svg>'''.encode()
    reference = etree.fromstring(svg.replace(b"ChronaClosedFace-primary", b"Noto Sans").replace(
        b"ChronaClosedFace-override", b"Noto Sans Mono"))
    reference_filter = reference.xpath(".//s:filter[@id='glow']", namespaces=NS)[0]
    reference_source = reference_filter.xpath(".//s:feMergeNode[@in='SourceGraphic']", namespaces=NS)[0]
    reference_source.getparent().remove(reference_source)
    reference_root = etree.Element(f"{{{SVG_NS}}}svg", nsmap={None: SVG_NS}, width="250", height="70",
                                   viewBox="0 0 250 70")
    reference_root.append(reference.find(f"{{{SVG_NS}}}defs"))
    reference_root.append(reference.find(f"{{{SVG_NS}}}text"))
    expected = _raster(etree.tostring(reference_root), [regular.path, mono.path])
    lowered = lower_pdf_glows(surface, svg, (regular, mono), aliases)
    lowered_root = etree.fromstring(lowered)
    image = lowered_root.find(".//s:image", NS)
    assert image is not None
    actual_halo = Image.open(BytesIO(b64decode(image.attrib["href"].split(",", 1)[1]))).convert("RGBA")
    assert actual_halo.tobytes() == expected.tobytes()
    assert b'font-family="ChronaClosedFace-primary"' in lowered
    assert b'font-family="ChronaClosedFace-override"' in lowered


def test_no_glow_is_byte_identical_and_owner_transform_fails_closed():
    source = _rect_svg()
    assert lower_pdf_glows(SimpleNamespace(primitives=()), source, (), {}) == source
    transformed = source.replace(b'<rect data-scene-id="glowing-rect"',
                                 b'<rect data-scene-id="glowing-rect" transform="rotate(2)"')
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID.*transformed filter owner"):
        lower_pdf_glows(SimpleNamespace(primitives=(_primitive("glowing-rect", (15, 10, 66, 61)),)),
                        transformed, (), {})


def test_actual_aligned_stroke_scene_keeps_scene_clip_and_opacity_on_halo_and_source():
    paint = ScenePaint("#ee3344", "#111111", 8, (), 0.5,
                       glow=Glow("#00aaff", 4, 0.8, "required", (12.25, 12.5, 75.5, 75.25)))
    node = ScenePrimitive("aligned-glow", "Rect", "synthetic", "object", "planned", "planned",
                          (25, 25, 50, 50), paint=paint,
                          stroke_clip=StrokeClip((), False, (0, 0, 100, 100), 8))
    surface = SceneSurface("surface", (), (), (), None, (node,),
                           ScenePaint("#ffffff", None, None, (), 1), canvas_bounds=(0, 0, 100, 100))
    source = render_v05_svg(surface, viewer_fit=False).encode()
    lowered = lower_pdf_glows(surface, source, (), {})
    root = etree.fromstring(lowered)
    scene_group = root.xpath(".//*[@data-scene-id='aligned-glow']", namespaces=NS)[0]
    wrapper = scene_group.getparent()
    image = wrapper.find("s:image", NS)
    filtered = scene_group.xpath(".//*[@filter]", namespaces=NS)
    assert wrapper.tag == f"{{{SVG_NS}}}g" and wrapper.get("opacity") == "0.5"
    assert image is not None and list(wrapper).index(image) < list(wrapper).index(scene_group)
    assert not filtered
    assert scene_group.xpath(".//*[@mask]", namespaces=NS)
    mask = root.find(".//s:mask", NS)
    assert mask is not None
    assert (mask.get("x"), mask.get("y"), mask.get("width"), mask.get("height")) == ("0", "0", "100", "100")
    stroke = scene_group.xpath(".//*[@mask]", namespaces=NS)[0]
    assert (stroke.get("x"), stroke.get("y"), stroke.get("width"), stroke.get("height")) == (
        "25", "25", "50", "50")
    rendered = _raster(lowered)
    assert rendered.size == (100, 100)
    assert rendered.getpixel((2, 2)) == (255, 255, 255, 255)
    assert rendered.getpixel((50, 50))[3] > 0


def test_actual_transformed_text_scene_rasterizes_in_its_untransformed_glow_owner():
    font = _font(ROOT / "src/chrona/resources/fonts/noto-sans-regular-v1.ttf", "Noto Sans")
    alias = "ChronaClosedFace-transformed-title"
    layout = TextLayout((10, 12, 62, 24), (10, 32), ("Halo",), "Noto Sans", 400, 20, 1.2,
                        font.content_identity, orientation="rotate-cw", rotation_degrees=90)
    node = ScenePrimitive("rotated-title", "Text", "synthetic", "heading", "heading", "heading",
                          layout.bounds, text="Halo", baseline=layout.baseline, text_layout=layout,
                          paint=ScenePaint("#112233", None, None, (), 1,
                                           glow=Glow("#00aaff", 3, 0.8, "required", (0, 0, 80, 80))))
    surface = SceneSurface("surface", (), (), (), None, (node,),
                           ScenePaint("#ffffff", None, None, (), 1), canvas_bounds=(0, 0, 80, 80))
    source = render_v05_svg(surface, viewer_fit=False).encode().replace(
        b'font-family="Noto Sans"', f'font-family="{alias}"'.encode())
    aliases = {(font.content_identity, "noto sans", 400): alias}
    lowered = lower_pdf_glows(surface, source, (font,), aliases)
    root = etree.fromstring(lowered)
    text = root.xpath(".//s:text[@data-scene-id='rotated-title']", namespaces=NS)[0]
    image = root.xpath(".//s:image[@data-pdf-glow='rotated-title']", namespaces=NS)[0]
    wrapper = text.getparent().getparent()
    assert text.get("transform") == "rotate(90 10 32)"
    assert image.getparent() is wrapper and list(wrapper).index(image) < list(wrapper).index(text.getparent())
    halo = Image.open(BytesIO(b64decode(image.get("href").split(",", 1)[1]))).convert("RGBA")
    assert halo.size == (80, 80) and halo.getchannel("A").getbbox() is not None
