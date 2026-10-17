"""Private raster/PDF positioning follows Layout's completed fallback runs."""
from lxml import etree
from types import SimpleNamespace
import pytest

from chrona.presentation.renderers.svg_text_runs import (
    RASTER_TEXT_RUN_GRAMMAR,
    lower_png_text_runs,
    position_completed_text_runs,
)
from chrona.presentation.renderers.pdf_svg import lower_pdf_svg
from chrona.presentation.renderers import registry
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.scene.model import TextLayout, TextRun
from tests.unit.chrona.presentation.renderers.test_pdf_text_run_advances import _surface


NS = "{http://www.w3.org/2000/svg}"


def _mixed_layout(*, runs=True):
    completed = (
        (TextRun("UX ", 14, 18.4, "Noto Sans", 400, "sha256:primary"),
         TextRun("リサーチ", 14, 42, "Hiragino Sans", 400, "sha256:fallback")),
        (TextRun("API / ", 14, 22, "Noto Sans", 400, "sha256:primary"),
         TextRun("決済", 14, 28, "Hiragino Sans", 400, "sha256:fallback")),
    ) if runs else ()
    return TextLayout(
        bounds=(24, 90, 80, 36), baseline=(24, 100), lines=("UX リサーチ", "API / 決済"),
        family="Noto Sans, sans-serif", weight=400, font_size=14, line_height=1.2,
        asset_identity="sha256:primary", letter_spacing=0.4, orientation="rotate-cw",
        rotation_degrees=90, horizontal_scale=0.8, runs=completed,
    )


def test_png_projection_places_mixed_faces_from_completed_advances_only_in_private_copy():
    layout = _mixed_layout()
    surface = _surface(layout)
    original = render_v05_svg(surface, viewer_fit=False).encode()

    lowered = lower_png_text_runs(surface, original)

    assert RASTER_TEXT_RUN_GRAMMAR == "resvg-completed-text-runs-v1"
    assert lowered != original
    assert b'xmlns="http://www.w3.org/2000/svg"' in lowered
    root = etree.fromstring(lowered)
    text = next(item for item in root.iter(NS + "text") if item.get("data-scene-id") == "small-caps")
    assert text.get("transform") == "rotate(90 20 30) matrix(0.8 0 0 1 4 0)"
    lines = list(text)
    assert [line.get("x") for line in lines] == ["20", "20"]
    assert [line.get("dy") for line in lines] == ["0", "16.8"]
    spans = [[child for child in line if child.tag == NS + "tspan"] for line in lines]
    assert [[child.text for child in line] for line in spans] == [
        ["UX ", "リサーチ"], ["API / ", "決済"],
    ]
    assert [[child.get("x") for child in line] for line in spans] == [
        ["20", "43.5"], ["20", "48"],
    ]
    assert [[child.get("font-family") for child in line] for line in spans] == [
        ["Noto Sans", "Hiragino Sans"], ["Noto Sans", "Hiragino Sans"],
    ]
    assert [[child.get("font-weight") for child in line] for line in spans] == [
        ["400", "400"], ["400", "400"],
    ]
    assert [[child.get("data-asset-identity") for child in line] for line in spans] == [
        ["sha256:primary", "sha256:fallback"], ["sha256:primary", "sha256:fallback"],
    ]
    assert all(child.get("{http://www.w3.org/XML/1998/namespace}space") == "preserve"
               for line in spans for child in line)
    # Public serialization is not the private raster projection.
    assert render_v05_svg(surface, viewer_fit=False).encode() == original


def test_latin_only_png_returns_the_original_bytes_even_for_small_caps_runs():
    from dataclasses import replace

    layout = replace(_mixed_layout(runs=False), lines=("UX RESEARCH",), text_transform="small-caps",
                     runs=((TextRun("UX ", 14, 18.4), TextRun("RESEARCH", 14, 42)),))
    surface = _surface(layout)
    original = render_v05_svg(surface, viewer_fit=False).encode()

    assert lower_png_text_runs(surface, original) is original


def test_fallback_face_run_projection_matches_pdf_geometry_without_double_projection():
    layout = _mixed_layout()
    surface = _surface(layout)
    original = render_v05_svg(surface, viewer_fit=False).encode()

    png_private = etree.fromstring(lower_png_text_runs(surface, original))
    pdf_private = etree.fromstring(lower_pdf_svg(surface, original))
    png_text = next(item for item in png_private.iter(NS + "text"))
    pdf_text = next(item for item in pdf_private.iter(NS + "text"))
    extract = lambda node: [[(span.text, span.get("x"), span.get("font-family"),
                             span.get("font-weight"), span.get("data-asset-identity"))
                            for span in line.iter(NS + "tspan") if span is not line]
                           for line in node.iter(NS + "tspan") if list(line)]
    assert extract(png_text) == extract(pdf_text)


def test_shared_projector_keeps_inherited_face_attributes_when_the_source_has_no_explicit_tspan():
    from lxml import etree
    from dataclasses import replace

    layout = _mixed_layout()
    inherited_primary = tuple(replace(run, family=None, weight=None, asset_identity=None)
                              if run.family == "Noto Sans" else run for run in layout.runs[0])
    layout = replace(layout, lines=(layout.lines[0],), runs=(inherited_primary,))
    svg = (b'<svg xmlns="http://www.w3.org/2000/svg"><text data-scene-id="small-caps" '
           b'x="24" y="100" font-family="Noto Sans" font-weight="400">UX \n'
           b'<tspan font-family="Hiragino Sans" font-weight="400" '
           b'data-asset-identity="sha256:fallback">\xe3\x83\xaa\xe3\x82\xb5\xe3\x83\xbc\xe3\x83\x81</tspan>'
           b'</text></svg>')
    root = etree.fromstring(svg)
    text = next(item for item in root.iter(NS + "text"))

    position_completed_text_runs(text, layout)

    spans = [item for item in text.iter(NS + "tspan") if len(item) == 0]
    assert [(item.text, item.get("font-family"), item.get("font-weight"), item.get("x")) for item in spans] == [
        ("UX ", None, None, "24"), ("リサーチ", "Hiragino Sans", "400", "47.5"),
    ]


def test_shared_projector_preserves_inherited_private_family_alias_on_matched_run():
    layout = TextLayout(
        bounds=(20, 20, 40, 16), baseline=(20, 30), lines=("決済",),
        family="Shared Face", weight=400, font_size=14, line_height=1.2,
        asset_identity="sha256:closed-face",
        runs=((TextRun("決済", 14, 20, "Shared Face", 400, "sha256:closed-face"),),),
    )
    svg = (b'<svg xmlns="http://www.w3.org/2000/svg"><text data-scene-id="private-alias" '
           b'x="20" y="30" font-family="ChronaClosedFace-primary" font-weight="400">'
           b'<tspan data-asset-identity="sha256:closed-face">\xe6\xb1\xba\xe6\xb8\x88</tspan>'
           b'</text></svg>')
    root = etree.fromstring(svg)
    text = next(item for item in root.iter(NS + "text"))

    position_completed_text_runs(text, layout)

    span = next(item for item in text.iter(NS + "tspan"))
    assert span.get("font-family") is None
    assert text.get("font-family") == "ChronaClosedFace-primary"
    assert span.get("data-asset-identity") == "sha256:closed-face"


def test_png_projection_visits_every_fallback_text_after_rebuilding_earlier_nodes():
    from dataclasses import replace

    surface = _surface(_mixed_layout())
    second = replace(surface.primitives[0], scene_id="second-label", source_ref="second-source")
    surface = replace(surface, primitives=surface.primitives + (second,))
    original = render_v05_svg(surface, viewer_fit=False).encode()

    root = etree.fromstring(lower_png_text_runs(surface, original))
    positioned = {node.get("data-scene-id") for node in root.iter(NS + "text")
                  if any(span.get("data-asset-identity") == "sha256:fallback"
                         for span in node.iter(NS + "tspan"))}
    assert positioned == {"small-caps", "second-label"}


@pytest.mark.parametrize("has_fallback", [False, True], ids=["small-caps-no-fallback", "completed-fallback"])
def test_png_registry_identity_tracks_only_fallback_run_projection(monkeypatch, has_fallback):
    from dataclasses import replace
    import resvg_py

    no_fallback = replace(_mixed_layout(runs=False), lines=("UX RESEARCH",), text_transform="small-caps",
                          runs=((TextRun("UX ", 14, 18.4), TextRun("RESEARCH", 14, 42)),))
    surface = _surface(_mixed_layout() if has_fallback else no_fallback)
    descriptor = {"dpi": 96, "version": "test-resvg", "resvgVersion": "test-engine"}
    captured: list[str] = []

    monkeypatch.setattr(registry, "_verify_resvg", lambda _: None)
    monkeypatch.setattr(registry, "_font_files", lambda *args: ((), ("sha256:font",)))
    monkeypatch.setattr(registry, "V05SvgRenderer", lambda viewer_fit: SimpleNamespace(
        render=lambda surface: SimpleNamespace(content=render_v05_svg(surface, viewer_fit=False).encode())))
    monkeypatch.setattr(resvg_py, "svg_to_bytes", lambda **kwargs: captured.append(kwargs["svg_string"]) or b"PNG")

    original = render_v05_svg(surface, viewer_fit=False).encode()
    artifact = registry.ResvgPngRenderer("png", descriptor, None, None).render(surface)
    assert len(captured) == 1
    if has_fallback:
        assert captured[0].encode() == lower_png_text_runs(surface, original)
        assert captured[0].encode() != original
        assert f"-{RASTER_TEXT_RUN_GRAMMAR}-" in artifact.adapter_identity
    else:
        assert captured[0].encode() == original
        assert f"-{RASTER_TEXT_RUN_GRAMMAR}-" not in artifact.adapter_identity
    assert artifact.adapter_identity.endswith("-fonts-font")
