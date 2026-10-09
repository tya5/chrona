"""A Theme-declared canvas texture renders under every mark in SVG and PNG, and only when declared (#587).

The rules do not depend on the HALCYON board: a small synthetic Project is rendered through
the packaged `executive-light` bundle with the packaged `chrona-target-parts` catalogue.
No test reads `examples/`.
"""
from __future__ import annotations

import io
import re
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

import pytest
import resvg_py
from PIL import Image

from chrona.presentation.color_scheme import ColorSchemeError
from chrona.presentation.model.closure import ClosureError
from chrona.presentation.renderers.v05_typeset import render_v05_tikz, render_v05_typst
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from tests.support import synthetic_review as sr

ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = ROOT / "src/chrona/resources/icons/chrona-target-parts-v2026-10-09.yaml"
LATTICE = "chrona-target-parts:hexagon-lattice"


def _source() -> dict:
    objects = {}
    for index, owner in enumerate("abc"):
        for step in range(2):
            key = f"{owner}{step}"
            objects[key] = sr.span(key, date(2026, 3, 2) + timedelta(days=index * 9 + step * 50), 40, owner=owner,
                                   title=f"Synthetic task {key}")
    return sr.project(objects)


def _presentation(role: dict | None = None, *, extra_bindings: dict | None = None) -> dict:
    """The packaged flat-canvas bundle, with a `canvas-texture` role when `role` is given (Theme v0.13 admits catalogue patterns)."""
    parts = sr.bundle("executive-light")
    if role is not None:
        parts["theme"]["version"] = "chrona/theme/v0.15"
        body = parts["theme"]["body"]
        body["values"]["canvas-texture.lattice"] = {"type": "pattern", "value": {"kind": "catalog", "ref": LATTICE}}
        body["values"]["canvas-texture.hatch"] = {"type": "pattern", "value": {
            "kind": "diagonal-hatch", "tileInlineSize": 6, "tileBlockSize": 6, "angle": 45, "strokeWidth": 1}}
        body["values"]["canvas-texture.one"] = {"type": "number", "value": 1}
        body["values"]["canvas-texture.half"] = {"type": "number", "value": 0.5}
        body["roles"]["canvas-texture"] = role
        body["colorBindings"].update({"canvas-texture.fill": "surface", "canvas-texture.stroke": "surfaceRaised",
                                      **(extra_bindings or {})})
    return parts


def _render(directory: Path, presentation: dict):
    return sr.render(directory, _source(), presentation=presentation, icon_catalogs=(CATALOGUE,))


def _textured(directory: Path):
    return _render(directory, _presentation({"pattern": "canvas-texture.lattice"}))


def _png(svg: bytes, directory: Path) -> Image.Image:
    path = directory / "board.svg"
    path.write_bytes(svg)
    return Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(svg_path=str(path), zoom=1, font_dirs=[],
                                                              skip_system_fonts=False)))).convert("RGB")


def test_the_texture_is_the_first_drawn_shape_after_the_canvas_with_one_pattern_definition(tmp_path) -> None:
    svg = _textured(tmp_path).artifact.content.decode()

    assert svg.count("<pattern ") == 1
    shapes = re.findall(r'<rect [^>]*data-scene-id="([^"]+)"[^>]*>', svg)
    assert shapes[0] == "canvas-texture"
    texture = re.search(r'<rect [^>]*data-scene-id="canvas-texture"[^>]*>', svg).group(0)
    assert 'fill="url(#pattern-' in texture and 'data-purpose="canvas-texture"' in texture
    assert svg.index("canvas-texture") < svg.index('data-scene-id="title"')


def test_the_png_shows_the_lattice_ink_on_empty_canvas_and_none_without_a_texture(tmp_path) -> None:
    (tmp_path / "plain").mkdir()
    textured = _png(_textured(tmp_path).artifact.content, tmp_path)
    plain = _png(_render(tmp_path / "plain", _presentation()).artifact.content, tmp_path / "plain")

    empty = (30, 500, 470, 880)  # below the table's last row: nothing but canvas
    textured_colours = {colour for _count, colour in textured.crop(empty).getcolors(maxcolors=1 << 20)}
    plain_colours = {colour for _count, colour in plain.crop(empty).getcolors(maxcolors=1 << 20)}
    assert len(plain_colours) == 1
    assert plain_colours <= textured_colours and len(textured_colours) > 2
    assert textured.size == plain.size


def test_marks_and_labels_paint_above_the_texture(tmp_path) -> None:
    review = _textured(tmp_path)
    order = [item.scene_id for _index, item in sorted(enumerate(review.surface.primitives),
                                                      key=lambda pair: (pair[1].paint_order, pair[0]))]
    texture = next(index for index, item in enumerate(review.surface.primitives) if item.scene_id == "canvas-texture")
    painted = [item.scene_id for item in review.surface.primitives]

    assert order[0] == "canvas-texture" and texture == 0
    assert len(painted) > 20 and painted.count("canvas-texture") == 1


def test_two_renders_of_one_theme_are_byte_identical(tmp_path) -> None:
    (tmp_path / "again").mkdir()

    assert _textured(tmp_path).artifact.content == _textured(tmp_path / "again").artifact.content


def test_opaque_texture_opacity_one_preserves_scene_content_and_svg_bytes(tmp_path) -> None:
    plain_directory = tmp_path / "plain"
    explicit_directory = tmp_path / "explicit"
    plain_directory.mkdir()
    explicit_directory.mkdir()
    plain = _textured(plain_directory)
    explicit = _render(explicit_directory, _presentation({
        "pattern": "canvas-texture.lattice", "opacity": "canvas-texture.one",
    }))

    plain_document = scene_document(plain.scene)
    explicit_document = scene_document(explicit.scene)
    # The authored Theme differs, so its provenance identity must differ;
    # completed geometry and paint must remain exactly the same.
    assert plain_document.pop("provenance") != explicit_document.pop("provenance")
    assert plain_document == explicit_document
    assert plain.artifact.content == explicit.artifact.content


def test_a_theme_without_the_role_has_no_texture_slot_primitive_or_pattern(tmp_path) -> None:
    review = _render(tmp_path, _presentation())
    svg = review.artifact.content.decode()

    assert "canvas-texture" not in svg and "<pattern" not in svg
    assert "canvas" not in {slot.slot_id for slot in review.surface.slots}
    assert "canvas-texture" not in {item.scene_id for item in review.surface.primitives}


def test_the_serialized_scene_is_v07_and_passes_the_gates_with_the_texture_as_ground(tmp_path) -> None:
    review = _textured(tmp_path)
    document = scene_document(review.scene)

    assert document["version"] == "chrona/scene/v0.7"
    findings = evaluate_scene_contrast(document)
    grounded = [item for item in findings if item.ground_id == "canvas-texture"]
    marks = [item for item in grounded if item.code == "E_SCENE_MARK_CONTRAST"]
    assert marks and {item.ground_kind for item in marks} <= {"texture-substrate", "texture-ink"}
    # A decoration tint is judged against the substrate, not against the thin ink lines.
    assert {item.ground_kind for item in grounded if item.code == "E_SCENE_DECORATION_CONTRAST"} <= {"flat"}
    assert not [item for item in findings if item.severity == "error"]


def test_typst_and_tikz_never_receive_a_texture(tmp_path) -> None:
    review = _textured(tmp_path)

    for render in (render_v05_typst, render_v05_tikz):
        with pytest.raises(ValueError, match="E_VISUAL_CAPABILITY_UNSUPPORTED"):
            render(review.surface)


@pytest.mark.parametrize(("role", "code", "pointer"), [
    ({}, "E_THEME_ROLE_REQUIRED", "/body/roles/canvas-texture/pattern"),
    ({"pattern": "canvas-texture.hatch"}, "E_THEME_ROLE_PROPERTY_UNSUPPORTED", "/body/roles/canvas-texture/pattern"),
    ({"pattern": "canvas-texture.lattice", "opacity": "canvas-texture.half"},
     "E_THEME_ROLE_PROPERTY_UNSUPPORTED", "/body/roles/canvas-texture/opacity"),
    ({"pattern": "canvas-texture.lattice", "backgroundPaintOrder": 5},
     "E_THEME_ROLE_PROPERTY_UNSUPPORTED", "/body/roles/canvas-texture/backgroundPaintOrder"),
    ({"pattern": "canvas-texture.lattice", "strokeWidth": "canvas-texture.one"},
     "E_THEME_ROLE_PROPERTY_UNSUPPORTED", "/body/roles/canvas-texture/strokeWidth"),
])
def test_a_malformed_texture_role_fails_before_layout_at_its_exact_pointer(tmp_path, role, code, pointer) -> None:
    with pytest.raises((ColorSchemeError, ClosureError)) as error:
        _render(tmp_path, _presentation(role))

    assert getattr(error.value, "diagnostic_id", None) == code
    assert getattr(error.value, "source_ref", getattr(error.value, "pointer", None)) == pointer


def test_the_presentation_helper_does_not_alias_the_packaged_bundle() -> None:
    first, second = _presentation({"pattern": "canvas-texture.lattice"}), _presentation()

    assert "canvas-texture" in first["theme"]["body"]["roles"]
    assert "canvas-texture" not in second["theme"]["body"]["roles"]
    assert deepcopy(second) == second
