"""Axis cell corners (#491): the Theme declaration through a packaged bundle, the adapters and the Scene gates.

A synthetic Project is rendered through the packaged `executive-light` bundle (two band tiers: quarter and month), so no
corpus edit can change what these tests prove. The committed slide that shows corners is evidence, not a gate.
"""
from __future__ import annotations

import io
from copy import deepcopy
from datetime import date

import pytest
import resvg_py
from PIL import Image

from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.presentation.scene.serialization import scene_document
from chrona.resources import schema_validator
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr
from tests.support.legacy_axis import use_legacy_six_tier_axis

WINDOW = {"mode": "explicit", "start": "2026-01-01", "end": "2026-07-01"}
QUARTER, MONTH = "axis-band-decoration", "axis-band-decoration2"
BANDS = (0, 3)  # the View indexes of the quarter and month band tiers of the bundle


def _parts(*, quarter=None, month=None, gap=None) -> dict:
    """The bundle with corner properties on the quarter (first) and month (second) band roles."""
    parts = use_legacy_six_tier_axis(sr.bundle("executive-light"))
    parts["view"]["body"]["window"] = dict(WINDOW)
    body = parts["theme"]["body"]
    for role, declared in ((QUARTER, quarter), (MONTH, month)):
        for name, value in (declared or {}).items():
            body["values"][f"{role}-{name}"] = {"type": "number", "value": value}
            body["roles"][role][name] = f"{role}-{name}"
    if gap is not None:
        body["values"]["axis-cell-gap"] = {"type": "number", "value": gap}
    return parts


def _render(tmp_path, parts):
    source = sr.project({"a": sr.span("a", date(2026, 1, 5), 40), "b": sr.span("b", date(2026, 2, 10), 30, owner="b")})
    return sr.render(tmp_path, source, presentation=parts)


def _cells(rendered, tier):
    return sorted((item for item in rendered.surface.primitives if item.scene_id.startswith(f"axis-band-rect:{tier}:")),
                  key=lambda item: int(item.scene_id.rsplit(":", 1)[1]))


def _png(rendered, directory) -> Image.Image:
    path = directory / "board.svg"
    path.write_bytes(rendered.artifact.content)
    data = resvg_py.svg_to_bytes(svg_path=str(path), zoom=1, font_dirs=[], skip_system_fonts=False)
    return Image.open(io.BytesIO(bytes(data))).convert("RGB")


# --- SVG and PNG ----------------------------------------------------------------------------------------


def test_the_svg_draws_a_radius_as_rx_and_a_chamfer_as_a_filled_path(tmp_path):
    rendered = _render(tmp_path, _parts(quarter={"cellCornerChamfer": 0.25}, month={"cellCornerRadius": 0.25}))
    svg = rendered.artifact.content.decode()

    quarter, month = _cells(rendered, 0)[0], _cells(rendered, 3)[0]
    assert quarter.kind == "Symbol" and month.kind == "Rect"
    assert f'<path data-scene-id="{quarter.scene_id}"' in svg
    radius = f"{month.corner_radius:.3f}".rstrip("0").rstrip(".")
    assert f'data-scene-id="{month.scene_id}"' in svg and f'rx="{radius}" ry="{radius}"' in svg
    assert radius != "0"


def test_the_png_shows_the_cut_and_the_round_at_the_corner_and_the_ground_at_the_centre(tmp_path):
    plain_dir, cut_dir = _directory(tmp_path, "plain"), _directory(tmp_path, "cut")
    plain = _render(plain_dir, _parts())
    cut = _render(cut_dir, _parts(quarter={"cellCornerChamfer": 0.4}, month={"cellCornerRadius": 0.4}))
    plain_png, cut_png = _png(plain, plain_dir), _png(cut, cut_dir)

    for tier in BANDS:
        before, after = _cells(plain, tier)[1], _cells(cut, tier)[1]
        x, y, width, height = after.bounds
        corner, centre = (int(x) + 1, int(y) + 1), (int(x + width / 2), int(y + height / 2))
        assert plain_png.getpixel(corner) != cut_png.getpixel(corner), f"tier {tier}: the corner pixel is unchanged"
        assert plain_png.getpixel(centre) == cut_png.getpixel(centre), f"tier {tier}: the centre changed"
        assert before.bounds == after.bounds


def _directory(root, name):
    path = root / name
    path.mkdir()
    return path


# --- the Scene gates ------------------------------------------------------------------------------------


def test_the_gates_find_no_error_in_a_chamfered_axis_and_still_read_the_cell_paint(tmp_path):
    rendered = _render(tmp_path, _parts(quarter={"cellCornerChamfer": 0.25}, month={"cellCornerRadius": 0.25}))
    findings = evaluate_scene_perceptibility(scene_document(rendered.scene))

    assert [item for item in findings if item.severity == "error"] == []
    contrast = {ident for item in findings if item.code == "I_SCENE_PAINT_CONTRAST" for ident in item.primitive_ids}
    assert {cell.scene_id for tier in BANDS for cell in _cells(rendered, tier)} <= contrast


def _document_with_cell_over_text(tmp_path, *, role=None):
    """A Scene document in which the first chamfered quarter cell is painted over a month label, hosted elsewhere."""
    rendered = _render(tmp_path, _parts(quarter={"cellCornerChamfer": 0.25}))
    document = deepcopy(scene_document(rendered.scene))
    primitives = document["surfaces"][0]["primitives"]
    text = next(item for item in primitives if item["id"].startswith("axis-label:") and item.get("text") == "Feb")
    cell = next(item for item in primitives if item["id"] == "axis-band-rect:0:0")
    assert cell["kind"] == "Symbol"
    cell["bounds"] = dict(text["bounds"])
    cell["paintOrder"] = text["paintOrder"] + 1
    if role is not None:
        cell["visualRole"] = role
    return document, text["id"], cell["id"]


def test_the_occlusion_gate_treats_an_opaque_chamfered_cell_as_ground_that_can_cover_text(tmp_path):
    document, text_id, cell_id = _document_with_cell_over_text(tmp_path)

    codes = {(item.code, item.primitive_ids) for item in evaluate_scene_perceptibility(document)}
    assert ("E_SCENE_TEXT_OCCLUDED", (text_id, cell_id)) in codes


def test_the_occlusion_gate_does_not_treat_other_symbols_as_ground(tmp_path):
    document, _, _ = _document_with_cell_over_text(tmp_path, role="planned")

    assert "E_SCENE_TEXT_OCCLUDED" not in {item.code for item in evaluate_scene_perceptibility(document)}


def test_a_label_keeps_a_chamfered_cell_as_its_host(tmp_path):
    rendered = _render(tmp_path, _parts(quarter={"cellCornerChamfer": 0.25}, month={"cellCornerChamfer": 0.25}))

    hosts = {item.host_placement_id for item in rendered.surface.primitives
             if item.scene_id.startswith("axis-label:") and item.host_placement_id}
    cells = {cell.scene_id for tier in BANDS for cell in _cells(rendered, tier)}
    assert hosts and hosts <= cells


# --- the Theme schema and the diagnostics through a render -----------------------------------------------


@pytest.mark.parametrize("name", ["cellCornerRadius", "cellCornerChamfer"])
def test_the_theme_schemas_accept_a_named_number_and_reject_a_literal(name):
    for schema in ("theme-v0.15.schema.yaml", "theme-v0.15.schema.yaml"):
        validator = schema_validator(schema)
        theme = deepcopy(sr.bundle("executive-light")["theme"])
        theme["version"] = "chrona/theme/" + schema.split("-")[1].split(".schema")[0]
        theme["body"]["roles"][QUARTER][name] = "axis-cell-gap"
        assert not [error for error in validator.iter_errors(theme) if name in "/".join(map(str, error.absolute_path))]
        theme["body"]["roles"][QUARTER][name] = 0.25
        assert [error for error in validator.iter_errors(theme) if name in "/".join(map(str, error.absolute_path))]


def test_a_render_with_a_corner_above_half_the_cell_fails_with_the_axis_diagnostic(tmp_path):
    with pytest.raises(RenderFailed) as caught:
        _render(tmp_path, _parts(quarter={"cellCornerRadius": 0.6}))

    assert str(caught.value) == "E_PRESENTATION_AXIS_INVALID"


def test_a_bundle_that_declares_no_corner_renders_square_cells(tmp_path):
    rendered = _render(tmp_path, _parts())

    assert {item.kind for tier in BANDS for item in _cells(rendered, tier)} == {"Rect"}
    assert {item.corner_radius for tier in BANDS for item in _cells(rendered, tier)} == {None}
