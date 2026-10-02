"""#585 I585-1: a declared, measured horizontal compression, rendered end to end.

A Theme role `horizontalScale` compresses the role's text along its own inline axis. Layout measures the compressed
width (so fit, wrap and column decisions see it), Scene carries the factor, SVG/PNG serialise it. Synthetic Projects
through the packaged `executive-light` bundle; no `examples/` input.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import pytest
import resvg_py
from PIL import Image, ImageChops

from chrona.presentation.color_scheme import ColorSchemeError
from chrona.presentation.renderers.v05_typeset import render_v05_tikz, render_v05_typst
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.presentation.scene.serialization import scene_document, serialize_scene
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr
from tests.support import text_treatments as tt

FONTS = Path(__file__).resolve().parents[2] / "src/chrona/resources/fonts"
SCALE = 0.6


def _sub(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    return path


def _render(tmp_path, *, scale=None, roles=None, source=None, notes=False, mutate=None, viewport=(1600, 900)):
    source = source or sr.bunched_project(groups=2, per_group=3)
    parts = sr.bundle()
    if notes:
        ak.with_view_notes(parts, source)
    if scale is not None:
        tt.with_scale(parts, roles, scale)
    if mutate is not None:
        mutate(parts)
    return sr.render(tmp_path, source, presentation=parts, viewport=viewport)


def test_a_scale_of_one_or_none_is_the_default_output(tmp_path):
    base = _render(_sub(tmp_path, "base"))
    one = _render(_sub(tmp_path, "one"), scale=1)
    assert one.artifact.content == base.artifact.content
    assert list(one.surface.primitives) == list(base.surface.primitives)
    assert scene_document(base.scene)["version"] == "chrona/scene/v0.6"
    assert scene_document(one.scene)["version"] == "chrona/scene/v0.6"
    assert b"matrix(" not in base.artifact.content


def test_every_text_of_a_scaled_role_is_exactly_the_scale_times_its_natural_width(tmp_path):
    """The honesty sweep: any measuring site that ignored the factor would break this ratio."""
    base = _render(_sub(tmp_path, "base"))
    scaled = _render(_sub(tmp_path, "scaled"), scale=SCALE)
    before, after = tt.texts(base), tt.texts(scaled)
    assert before.keys() <= after.keys()
    assert {key.split(':')[0] for key in after.keys() - before.keys()} == {'member-label'}  # see the next test
    purposes = {item.purpose for item in after.values()}
    assert {"table-cell", "group-header", "title-text", "axis-label", "table-column-label"} <= purposes
    for scene_id, item in ((key, value) for key, value in after.items() if key in before):
        natural = before[scene_id]
        assert item.text == natural.text and item.text_layout.lines == natural.text_layout.lines, scene_id
        assert item.text_layout.horizontal_scale == SCALE, scene_id
        assert item.bounds[2] == pytest.approx(natural.bounds[2] * SCALE, rel=1e-4), scene_id
        assert item.bounds[3] == natural.bounds[3], scene_id  # the em height is untouched


def test_a_fit_decision_flips_because_the_measured_width_changed(tmp_path):
    """Plot labels that do not fit at their natural width are suppressed; compressed, they fit and are placed."""
    base = _render(_sub(tmp_path, "base"))
    scaled = _render(_sub(tmp_path, "scaled"), scale=SCALE)
    shown = {key for key in tt.texts(scaled) if key.startswith("member-label:")}
    assert shown and not {key for key in tt.texts(base) if key.startswith("member-label:")}
    for key in shown:
        item = tt.texts(scaled)[key]
        assert item.text_layout.horizontal_scale == SCALE
        slot_inline = next(slot for slot in scaled.scene.surfaces[0].slots if slot.slot_id == item.slot_id).bounds
        assert item.bounds[0] >= slot_inline[0] - 1e-6  # placed inside its slot on the compressed width


def test_only_the_declared_roles_are_scaled(tmp_path):
    base = _render(_sub(tmp_path, "base"))
    scaled = _render(_sub(tmp_path, "scaled"), scale=SCALE, roles=("groupHeader",))
    for scene_id, item in tt.texts(scaled).items():
        natural = tt.texts(base)[scene_id]
        if item.purpose == "group-header":
            assert item.text_layout.horizontal_scale == SCALE
            assert item.bounds[2] == pytest.approx(natural.bounds[2] * SCALE, rel=1e-4)
        else:
            assert item.text_layout.horizontal_scale == 1 and item.bounds[2] == natural.bounds[2], scene_id


def test_the_scale_applies_to_letter_spacing_too(tmp_path):
    def spaced(parts):
        theme = parts["theme"]["body"]
        theme["values"]["wide"] = {"type": "number", "value": 0.2}
        theme["roles"]["heading"]["letterSpacing"] = "wide"

    base = _render(_sub(tmp_path, "base"), mutate=spaced)
    scaled = _render(_sub(tmp_path, "scaled"), scale=SCALE, roles=("heading",), mutate=spaced)
    title, natural = tt.texts(scaled)["title"], tt.texts(base)["title"]
    assert natural.text_layout.letter_spacing > 0
    assert title.bounds[2] == pytest.approx(natural.bounds[2] * SCALE, rel=1e-4)
    assert title.text_layout.letter_spacing == natural.text_layout.letter_spacing  # the painted spacing, scaled by the transform


def test_a_note_wraps_to_fewer_lines_and_gets_a_shorter_box_because_the_width_changed(tmp_path):
    source = ak.project(text="A longer note that needs several lines of text to say what it has to say about the task.")
    base = _render(_sub(tmp_path, "base"), source=source, notes=True)
    scaled = _render(_sub(tmp_path, "scaled"), source=source, notes=True, scale=SCALE, roles=("annotation-note-text",))
    note = "annotation-text:view-n0"
    natural, squeezed = tt.texts(base)[note], tt.texts(scaled)[note]
    assert squeezed.text_layout.horizontal_scale == SCALE
    assert len(natural.text_layout.lines) > 1
    assert len(squeezed.text_layout.lines) < len(natural.text_layout.lines)  # 4 lines at natural width, 3 compressed
    assert squeezed.bounds[3] < natural.bounds[3]
    box_before = next(item for item in base.surface.primitives if item.scene_id == "annotation-box:view-n0")
    box_after = next(item for item in scaled.surface.primitives if item.scene_id == "annotation-box:view-n0")
    assert box_after.bounds[3] < box_before.bounds[3]  # the note box was sized from the compressed measure


def test_the_scene_document_names_the_factor_only_where_it_applies(tmp_path):
    scaled = _render(_sub(tmp_path, "scaled"), scale=SCALE, roles=("heading",))
    document = scene_document(scaled.scene)
    assert document["version"] == "chrona/scene/v0.7"
    serialize_scene(scaled.scene)  # validates against scene-v0.7
    layouts = {item["id"]: item["textLayout"] for item in document["surfaces"][0]["primitives"] if "textLayout" in item}
    assert layouts["title"]["horizontalScale"] == SCALE
    assert all("horizontalScale" not in value for key, value in layouts.items() if key != "title")


def _ink_width(rendered, wider_than, scene_id="title"):
    """Width in pixels of the ink of one text, rasterised by resvg with the bundled fonts only."""
    files = [str(FONTS / name) for name in ("noto-sans-regular-v1.ttf", "noto-sans-bold-v1.ttf")]
    image = Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(
        svg_string=rendered.artifact.content.decode(), font_files=files, skip_system_fonts=True)))).convert("RGB")
    x, y, w, h = tt.texts(rendered)[scene_id].bounds
    crop = image.crop((int(x) - 4, int(y) - 4, int(x + max(w, wider_than)) + 4, int(y + h) + 4))
    difference = ImageChops.difference(crop, Image.new("RGB", crop.size, crop.getpixel((0, 0)))).convert("L")
    box = difference.point(lambda value: 255 if value > 40 else 0).getbbox()
    return box[2] - box[0]


def test_svg_writes_the_scale_about_the_baseline_start_and_png_shows_the_compression(tmp_path):
    base = _render(_sub(tmp_path, "base"))
    scaled = _render(_sub(tmp_path, "scaled"), scale=SCALE, roles=("heading",))
    node = re.search(r'<text [^>]*data-scene-id="title"[^>]*>', scaled.artifact.content.decode()).group(0)
    pivot = re.search(r'transform="matrix\(0\.6 0 0 1 ([-0-9.]+) 0\)"', node)
    assert pivot and float(pivot.group(1)) == pytest.approx(tt.texts(scaled)["title"].baseline[0] * 0.4, abs=1e-2)
    assert "transform" not in re.search(r'<text [^>]*data-scene-id="title"[^>]*>', base.artifact.content.decode()).group(0)
    natural_width = tt.texts(base)["title"].bounds[2]
    natural_ink, squeezed_ink = _ink_width(base, natural_width), _ink_width(scaled, natural_width)
    assert natural_ink > 20
    assert squeezed_ink / natural_ink == pytest.approx(SCALE, abs=0.04)


def test_the_gates_cover_compressed_text(tmp_path):
    source = ak.project()
    rendered = _render(_sub(tmp_path, "scaled"), source=source, notes=True, scale=SCALE, roles=("annotation-note-text",))
    document = scene_document(rendered.scene)
    assert not [item for item in evaluate_scene_perceptibility(document) if item.severity == "error"]
    findings = {item.primitive_id: item for item in evaluate_scene_contrast(document)
                if item.visual_role == "annotation-note-text"}
    assert set(findings) == {"annotation-text:view-n0", "annotation-text:view-n1"}
    assert all(item.severity == "info" and item.ground_id.startswith("annotation-box:") for item in findings.values())
    # The compressed text is judged on its real ground, like any other: a note box as dark as the ink fails.
    for primitive in document["surfaces"][0]["primitives"]:
        if primitive["id"] == "annotation-box:view-n0":
            primitive["paint"]["fill"] = "#1B2536"
    errors = [item for item in evaluate_scene_contrast(document)
              if item.visual_role == "annotation-note-text" and item.severity == "error"]
    assert [item.primitive_id for item in errors] == ["annotation-text:view-n0"]
    # Perceptibility rests on the compressed bounds the Scene carries.
    text = next(item for item in document["surfaces"][0]["primitives"] if item["id"] == "annotation-text:view-n0")
    assert text["textLayout"]["horizontalScale"] == SCALE
    assert text["bounds"]["inlineSize"] == pytest.approx(tt.texts(rendered)["annotation-text:view-n0"].bounds[2])


def test_tikz_has_no_verified_scale_and_typst_writes_a_scale_fragment(tmp_path):
    surface = _render(tmp_path, scale=SCALE, roles=("heading",)).surface
    with pytest.raises(ValueError, match="E_VISUAL_CAPABILITY_UNSUPPORTED"):
        render_v05_tikz(surface)
    typst = render_v05_typst(surface)
    assert "#scale(x: 60%, y: 100%, origin: left + top, reflow: false)[#text(" in typst
    plain = render_v05_typst(_render(_sub(tmp_path, "plain")).surface)
    assert "#scale(" not in plain


@pytest.mark.parametrize("role", ["heading", "annotation-arrow-text"])  # a role the render uses, and one it never does
@pytest.mark.parametrize("value", [0.4, 1.2, 0])
def test_a_scale_outside_the_range_is_a_typed_theme_diagnostic(tmp_path, value, role):
    with pytest.raises(Exception) as failure:
        _render(tmp_path, scale=value, roles=(role,))
    text = str(failure.value) + repr(getattr(failure.value, "__cause__", ""))
    assert "E_THEME_TEXT_SCALE_RANGE" in text


def test_the_bounds_of_the_range_are_accepted(tmp_path):
    assert _render(_sub(tmp_path, "floor"), scale=0.5, roles=("heading",)).surface is not None


def test_a_scale_bound_to_a_non_number_token_is_a_token_type_error(tmp_path):
    def wrong(parts):
        parts["theme"]["body"]["values"]["not-a-number"] = {"type": "textTransform", "value": "none"}
        parts["theme"]["body"]["roles"]["heading"]["horizontalScale"] = "not-a-number"

    with pytest.raises(Exception) as failure:
        _render(tmp_path, mutate=wrong)
    assert "E_THEME_TOKEN_TYPE" in str(failure.value) + repr(getattr(failure.value, "__cause__", ""))


def test_rendering_twice_gives_the_same_bytes(tmp_path):
    first = _render(_sub(tmp_path, "a"), scale=SCALE)
    second = _render(_sub(tmp_path, "b"), scale=SCALE)
    assert first.artifact.content == second.artifact.content


MATERIAL = Path(__file__).resolve().parents[2] / "src/chrona/resources/icons/material-symbols-outline-rounded-v2026-09-22.yaml"


def test_a_label_visual_reservation_measures_the_compressed_text(tmp_path):
    """The label-visual path re-measures a placed text from its own record; it must carry the factor."""
    source = sr.bunched_project(groups=2, per_group=3)

    def render(name, scale):
        parts = sr.bundle()
        parts["view"]["body"]["visuals"] = [{"target": {"kind": "group-header", "id": "team-0"},
                                             "ref": "material:10k-outline-rounded", "decorative": True}]
        if scale is not None:
            tt.with_scale(parts, ("groupHeader",), scale)
        return ak.render(_sub(tmp_path, name), source, parts, catalogs=(MATERIAL,),
                         visual_profile="chrona-output/visual/v0.7-svg")

    natural, squeezed = render("natural", None), render("squeezed", SCALE)
    assert any(item.scene_id.startswith("visual:group-header:team-0") for item in squeezed.surface.primitives)
    before, after = tt.texts(natural)["group-header:team-0"], tt.texts(squeezed)["group-header:team-0"]
    assert before.text_layout.lines == after.text_layout.lines
    assert after.bounds[2] == pytest.approx(before.bounds[2] * SCALE, rel=1e-4)
