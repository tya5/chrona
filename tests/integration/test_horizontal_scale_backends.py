"""Measure compressed text after the native Typst and PDF output routes."""
from __future__ import annotations

import os
import json
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
from importlib.metadata import version
from pathlib import Path
import re
import shutil
import subprocess

import pypdfium2 as pdfium
from fontTools.ttLib import TTFont
from PIL import Image, ImageChops
from pypdf import PdfReader
import pytest
import resvg_py

from chrona.presentation.contracts import TypesetterIdentity
from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.model.font_metrics import FontFile
from chrona.presentation.renderers.registry import ReportLabPdfRenderer
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review
from tests.support import synthetic_review as sr
from tests.support import text_treatments as tt


ROOT = Path(__file__).resolve().parents[2]
FONTS = ROOT / "src/chrona/resources/fonts"
SCALE = 0.5
VIEWPORT = (640, 360)
EVIDENCE = os.environ.get("CHRONA_SCALE_EVIDENCE")


def _render_surface(directory: Path, target: str, scale: float):
    directory.mkdir()
    parts = sr.bundle()
    tt.with_scale(parts, roles=("heading",), value=scale)
    source = sr.bunched_project(groups=1, per_group=1)
    paths = {kind: sr._write(directory / f"{kind}.yaml", value) for kind, value in parts.items()}
    project = sr._write(directory / "project.yaml", source)
    typesetter = TypesetterIdentity("typst", "0.15.1", "chrona-typst/v0.1") if target == "typst" else None
    draft = resolve_draft_render(
        project_path=project, view_path=paths["view"], theme_path=paths["theme"],
        scheme_path=paths["scheme"], layout_path=paths["layout"], viewport=VIEWPORT,
        target_kind=target, typesetter=typesetter,
    )
    return render_review(RenderRequest(
        draft.closure, draft.asset_root, ReferenceScheduler(), asset_root=draft.asset_root,
        draft_auto_block=draft.auto_block, draft_font_resolution=draft.font_resolution,
    ))


def _ink_box(image: Image.Image, text, canvas_size: tuple[float, float]):
    """Return a full-row ink box relative to the completed baseline pivot.

    The horizontal window is the full canvas: an unclosed adapter font can be wider
    than Layout's bundled-font measure, and must not be silently clipped by it.
    """
    _x, y, _width, height = text.bounds
    sx, sy = image.width / canvas_size[0], image.height / canvas_size[1]
    pad = 3.0
    top = max(0, round((y - pad) * sy))
    bottom = min(image.height, round((y + height + pad) * sy))
    crop = image.convert("RGB").crop((0, top, image.width, bottom))
    background = Image.new("RGB", crop.size, crop.getpixel((0, 0)))
    mask = ImageChops.difference(crop, background).convert("L").point(
        lambda value: 255 if value > 35 else 0)
    bounds = mask.getbbox()
    assert bounds is not None, "the selected text must produce visible raster ink"
    anchor = round(text.baseline[0] * sx)
    return (bounds[0] - anchor, bounds[1], bounds[2] - anchor, bounds[3])


def _measure_compressed_ink(base_image: Image.Image, scaled_image: Image.Image,
                            base_review, scaled_review):
    texts_base = tt.texts(base_review)
    texts_scaled = tt.texts(scaled_review)
    text_id = "title"
    assert text_id in texts_base and text_id in texts_scaled
    canvas = (base_review.surface.canvas_bounds[2], base_review.surface.canvas_bounds[3])
    assert canvas == (scaled_review.surface.canvas_bounds[2], scaled_review.surface.canvas_bounds[3])
    natural = texts_base[text_id]
    squeezed = texts_scaled[text_id]
    base_box = _ink_box(base_image, natural, canvas)
    scaled_box = _ink_box(scaled_image, squeezed, canvas)
    base_width, scaled_width = base_box[2] - base_box[0], scaled_box[2] - scaled_box[0]
    ratio = scaled_width / base_width
    ratio_interval = ((scaled_width - 1) / (base_width + 1),
                      (scaled_width + 1) / (base_width - 1))
    origin_delta = abs(scaled_box[0] - base_box[0])
    return {
        "canvas_scene_units": list(canvas), "scale": SCALE,
        "base_ink_width_px": base_width, "scaled_ink_width_px": scaled_width,
        "measured_width_ratio": ratio,
        "ratio_interval_from_plus_minus_one_pixel_edges": list(ratio_interval),
        "base_origin_offset_px": base_box[0], "scaled_origin_offset_px": scaled_box[0],
        "origin_delta_px": origin_delta, "origin_tolerance_px": 2,
    }


def _assert_compressed_measurement(measurements: dict[str, object]) -> None:
    base_width = measurements["base_ink_width_px"]
    scaled_width = measurements["scaled_ink_width_px"]
    ratio_interval = measurements["ratio_interval_from_plus_minus_one_pixel_edges"]
    assert base_width > 30
    assert ratio_interval[0] <= SCALE <= ratio_interval[1], measurements
    # Independent integer rounding of the anchor and ink edge accounts for at most 2 px.
    assert measurements["origin_delta_px"] <= 2, measurements
    assert measurements["scale"] == SCALE


def _title_font_proof(rendered, page, reader) -> dict[str, object]:
    title = tt.texts(rendered)["title"]
    current_font = None
    title_font = None
    for operands, operator in page.get_contents().operations:
        if operator == b"Tf":
            current_font = str(operands[0])
        elif operator in {b"Tj", b"TJ"} and any(str(value) == title.text for value in operands):
            title_font = current_font
            break
    assert title_font is not None, "the title text must select a PDF font resource"
    face = page["/Resources"]["/Font"][title_font].get_object()
    descriptor = face.get("/FontDescriptor")
    embedded_key = next((key for key in ("/FontFile", "/FontFile2", "/FontFile3")
                         if descriptor is not None and key in descriptor), None)
    embedded = embedded_key is not None
    family = title.text_layout.family.split(",", 1)[0].strip()
    base_font = str(face.get("/BaseFont", "")).lstrip("/").split("+", 1)[-1]
    normalize = lambda value: re.sub(r"[^a-z0-9]", "", value.casefold())
    embedded_family = None
    weight = None
    if embedded_key in {"/FontFile2", "/FontFile3"}:
        embedded_font = TTFont(BytesIO(descriptor[embedded_key].get_object().get_data()))
        embedded_family = embedded_font["name"].getDebugName(1)
        if "OS/2" in embedded_font:
            weight = embedded_font["OS/2"].usWeightClass
    return {
        "resource": title_font,
        "base_font": base_font,
        "embedded_family": embedded_family,
        "scene_family": family,
        "family_matches_scene": normalize(embedded_family or "") == normalize(family),
        "pdf_font_weight": weight,
        "scene_font_weight": title.text_layout.weight,
        "weight_matches_scene": weight == title.text_layout.weight,
        "embedded_font_program": embedded,
    }


def _retain_measurements(backend: str, measurements: dict[str, object]) -> Path | None:
    if EVIDENCE is None:
        return None
    destination = Path(EVIDENCE) / backend
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "measurements.json").write_text(
        json.dumps(measurements, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination


def test_typst_compiled_svg_preserves_compressed_text_ink_and_origin(tmp_path):
    executable = os.environ.get("CHRONA_TYPST")
    if not executable:
        pytest.skip("native Typst path absent; the typesetter-compile workflow supplies pinned Typst 0.15.1")
    reviews = []
    images = []
    for name, scale in (("natural", 1.0), ("compressed", SCALE)):
        rendered = _render_surface(tmp_path / name, "typst", scale)
        source = tmp_path / name / f"{name}.typ"
        svg = tmp_path / name / f"{name}.svg"
        source.write_bytes(rendered.artifact.content)
        result = subprocess.run(
            [executable, "compile", "--format", "svg", "--ignore-system-fonts", "--ignore-embedded-fonts",
             "--font-path", str(FONTS), str(source), str(svg)],
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert svg.is_file() and svg.stat().st_size > 0
        raster = resvg_py.svg_to_bytes(
            svg_path=str(svg), font_files=[str(path) for path in FONTS.glob("*.ttf")],
            skip_system_fonts=True, width=VIEWPORT[0], height=VIEWPORT[1], dpi=96,
        )
        image = Image.open(BytesIO(raster)).convert("RGB")
        reviews.append(rendered)
        images.append(image)
        if EVIDENCE is not None:
            destination = Path(EVIDENCE) / "typst"
            destination.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination / source.name)
            shutil.copy2(svg, destination / svg.name)
            image.save(destination / f"{name}.png")
    measurements = _measure_compressed_ink(images[0], images[1], reviews[0], reviews[1])
    _retain_measurements("typst", {"backend": "typst-0.15.1", "natural_scale": 1.0,
                                    "compressed": measurements})
    _assert_compressed_measurement(measurements)


def test_reportlab_pdf_raster_preserves_compressed_text_ink_and_origin(tmp_path):
    reviews = []
    images = []
    font_proofs: dict[str, dict[str, object]] = {}
    for name, scale in (("natural", 1.0), ("compressed", SCALE)):
        rendered = _render_surface(tmp_path / name, "pdf", scale)
        assert rendered.artifact.target_kind == "pdf"
        assert (f"pdf-closed-face-v1-fonttools-{version('fonttools')}"
                in rendered.artifact.adapter_identity)
        reader = PdfReader(BytesIO(rendered.artifact.content))
        page_reader = reader.pages[0]
        font_proofs[name] = _title_font_proof(rendered, page_reader, reader)
        if EVIDENCE is not None:
            destination = Path(EVIDENCE) / "pdf"
            destination.mkdir(parents=True, exist_ok=True)
            (destination / f"{name}.pdf").write_bytes(rendered.artifact.content)
            (destination / f"{name}.content-stream.txt").write_bytes(page_reader.get_contents().get_data())
        # ReportLab's deterministic output is the actual route artifact; rasterize those exact bytes.
        pdf = pdfium.PdfDocument(rendered.artifact.content)
        page = pdf[0]
        bitmap = page.render(scale=4)
        image = bitmap.to_pil().convert("RGB").copy()
        bitmap.close()
        page.close()
        pdf.close()
        reviews.append(rendered)
        images.append(image)
        if EVIDENCE is not None:
            destination = Path(EVIDENCE) / "pdf"
            destination.mkdir(parents=True, exist_ok=True)
            image.save(destination / f"{name}.png")
    measurements = _measure_compressed_ink(images[0], images[1], reviews[0], reviews[1])
    _retain_measurements("pdf", {"backend": "reportlab-pypdfium2-5.14.0",
                                  "pdf_raster_scale_px_per_point": 4,
                                  "natural_scale": 1.0, "compressed": measurements,
                                  "title_fonts": font_proofs})
    _assert_compressed_measurement(measurements)
    assert all(proof["embedded_font_program"] for proof in font_proofs.values()), font_proofs
    assert all(proof["family_matches_scene"] for proof in font_proofs.values()), font_proofs
    assert all(proof["weight_matches_scene"] for proof in font_proofs.values()), font_proofs


def test_sequential_pdf_faces_with_same_family_weight_embed_their_own_glyphs(tmp_path):
    rendered = _render_surface(tmp_path / "base", "pdf", 1.0)
    title = tt.texts(rendered)["title"]
    codepoint = ord(title.text[0])
    source_path = FONTS / "noto-sans-regular-v1.ttf"
    variants: list[tuple[FontFile, tuple[tuple[int, int], ...]]] = []
    for index, shift in enumerate((37, 91)):
        font = TTFont(str(source_path), recalcTimestamp=False)
        glyph_name = font.getBestCmap()[codepoint]
        glyph = font["glyf"][glyph_name]
        assert not glyph.isComposite()
        glyph.coordinates.translate((shift, 0))
        glyph.recalcBounds(font["glyf"])
        expected_coordinates = tuple((int(x), int(y)) for x, y in glyph.coordinates)
        variant_path = tmp_path / f"noto-variant-{index}.ttf"
        font.save(variant_path)
        font.close()
        variants.append((FontFile(variant_path, "sha256:" + sha256(variant_path.read_bytes()).hexdigest(),
                                "Noto Sans", 400), expected_coordinates))

    assert variants[0][0].content_identity != variants[1][0].content_identity
    assert variants[0][1] != variants[1][1]
    descriptor = {"svglibVersion": version("svglib"), "reportlabVersion": version("reportlab"),
                  "engine": "reportlab", "invariant": True}
    base_names = []
    for item, expected_coordinates in variants:
        artifact = ReportLabPdfRenderer(descriptor, None, None, font_files=(item,)).render(rendered.surface)
        reader = PdfReader(BytesIO(artifact.content))
        proof = _title_font_proof(rendered, reader.pages[0], reader)
        assert proof["embedded_font_program"] and proof["family_matches_scene"]
        assert proof["weight_matches_scene"]
        face = reader.pages[0]["/Resources"]["/Font"][proof["resource"]].get_object()
        base_names.append(str(face["/BaseFont"]))
        descriptor_obj = face["/FontDescriptor"]
        embedded = TTFont(BytesIO(descriptor_obj["/FontFile2"].get_object().get_data()))
        try:
            embedded_outlines = set()
            for glyph in embedded["glyf"].glyphs.values():
                glyph.expand(embedded["glyf"])
                embedded_outlines.add(tuple((int(x), int(y))
                                            for x, y in glyph.getCoordinates(embedded["glyf"])[0]))
            assert expected_coordinates in embedded_outlines
        finally:
            embedded.close()
    assert base_names[0] != base_names[1], "ReportLab must not reuse a prior same-family/weight face"


def test_pdf_registration_keeps_regular_and_bold_faces_distinct(tmp_path):
    rendered = _render_surface(tmp_path / "surface", "pdf", 1.0)
    primitives = list(rendered.surface.primitives)
    title_index = next(index for index, item in enumerate(primitives) if item.scene_id == "title")
    title = primitives[title_index]
    primitives[title_index] = replace(
        title, text_layout=replace(title.text_layout, weight=700),
    )
    surface = replace(rendered.surface, primitives=tuple(primitives))
    regular_path = FONTS / "noto-sans-regular-v1.ttf"
    bold_path = FONTS / "noto-sans-bold-v1.ttf"
    faces = tuple(
        FontFile(path, "sha256:" + sha256(path.read_bytes()).hexdigest(), "Noto Sans", weight)
        for path, weight in ((regular_path, 400), (bold_path, 700))
    )
    descriptor = {"svglibVersion": version("svglib"), "reportlabVersion": version("reportlab"),
                  "engine": "reportlab", "invariant": True}
    artifact = ReportLabPdfRenderer(descriptor, None, None, font_files=faces).render(surface)
    page = PdfReader(BytesIO(artifact.content)).pages[0]
    weights_and_names = set()
    for reference in page["/Resources"]["/Font"].values():
        face = reference.get_object()
        font_descriptor = face.get("/FontDescriptor")
        if font_descriptor is None or "/FontFile2" not in font_descriptor:
            continue
        embedded = TTFont(BytesIO(font_descriptor["/FontFile2"].get_object().get_data()))
        try:
            weights_and_names.add((embedded["OS/2"].usWeightClass, str(face["/BaseFont"])))
        finally:
            embedded.close()
    assert {weight for weight, _name in weights_and_names} == {400, 700}
    assert len({name for _weight, name in weights_and_names}) == 2
