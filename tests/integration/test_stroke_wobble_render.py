"""A Theme-declared hand-wobble perturbs a stroke deterministically and changes no bound (#588).

A small synthetic Project through the packaged `executive-light` bundle; no test reads `examples/`.
"""
from __future__ import annotations

import io
from html import escape
import json
import re
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest
import resvg_py
import yaml
from PIL import Image, ImageChops

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.presentation.renderers.v05_typeset import render_v05_tikz, render_v05_typst
from chrona.presentation.scene.serialization import scene_document, validate_scene_document
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderFailed, RenderRequest, render_review
from tests.support import synthetic_review as sr

RICH = "chrona-output/visual/v0.6-svg"
BASELINE = "chrona-output/visual/v0.5-baseline"


def _source() -> dict:
    objects = {}
    for index, owner in enumerate("abc"):
        key = f"{owner}0"
        objects[key] = sr.span(key, date(2026, 3, 2) + timedelta(days=index * 9), 40, owner=owner, title=f"Synthetic task {key}")
    return sr.project(objects)


def _presentation(wobble: bool = True, *, fidelity: str | None = None, roles=("planned", "axis-rule")) -> dict:
    parts = sr.bundle("executive-light")
    if wobble:
        body = parts["theme"]["body"]
        body["values"].update({"wobble.amp": {"type": "number", "value": 1.6},
                               "wobble.wave": {"type": "number", "value": 22},
                               "wobble.seed": {"type": "number", "value": 7}})
        declared = {"wobbleAmplitude": "wobble.amp", "wobbleWavelength": "wobble.wave", "wobbleSeed": "wobble.seed"}
        if fidelity is not None:
            body["values"]["wobble.fidelity"] = {"type": "fidelity", "value": fidelity}
            declared["wobbleFidelity"] = "wobble.fidelity"
        for role in roles:
            body["roles"][role].update(declared)
    return parts


def _render(directory: Path, presentation: dict, profile: str):
    paths = {}
    for kind, value in presentation.items():
        paths[kind] = directory / f"{kind}.yaml"
        paths[kind].write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding="utf-8")
    project = directory / "project.yaml"
    project.write_text(yaml.safe_dump(_source(), sort_keys=False), encoding="utf-8")
    draft = resolve_draft_render(project_path=project, view_path=paths["view"], theme_path=paths["theme"],
                                 scheme_path=paths["scheme"], layout_path=paths["layout"],
                                 viewport=(1600, 900), visual_profile=profile)
    return render_review(RenderRequest(closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
                                       scheduler=ReferenceScheduler(), renderer=V05SvgRenderer(),
                                       draft_auto_block=draft.auto_block))


def _png(svg: bytes, directory: Path) -> Image.Image:
    path = directory / "board.svg"
    path.write_bytes(svg)
    return Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(svg_path=str(path), zoom=1, font_dirs=[],
                                                              skip_system_fonts=False)))).convert("RGB")


def _by_role(review, role):
    return [item for item in review.surface.primitives if item.visual_role == role]


def _pair(tmp_path, **kwargs):
    (tmp_path / "plain").mkdir()
    return _render(tmp_path, _presentation(**kwargs), RICH), _render(tmp_path / "plain", _presentation(wobble=False), RICH)


def test_a_wobbled_bar_is_one_closed_path_and_a_wobbled_line_keeps_its_end_points(tmp_path) -> None:
    review, plain = _pair(tmp_path)
    svg = review.artifact.content.decode()
    bars, rules = _by_role(review, "planned"), _by_role(review, "axis-rule")

    assert len(bars) == 3 and all(item.paint.wobble is not None and item.paint.wobble.closed for item in bars)
    for item in bars:
        shape = re.search(rf'<path data-scene-id="{re.escape(escape(item.scene_id))}"[^>]* d="(M[^"]*Z)"', svg)
        assert shape is not None and shape.group(1).count("L") + 1 == len(item.paint.wobble.outline[0])
        assert f'<rect data-scene-id="{escape(item.scene_id)}"' not in svg
    assert len({item.paint.wobble.outline[0] for item in bars}) == 3      # each bar has its own line
    plain_rules = _by_role(plain, "axis-rule")
    for item, straight in zip(rules, plain_rules, strict=True):
        polyline = item.paint.wobble.outline[0]
        assert polyline[0] == straight.points[0] and polyline[-1] == straight.points[-1]
        assert len(polyline) >= 2 and not item.paint.wobble.closed
        drawn = re.search(rf'<path data-scene-id="{re.escape(escape(item.scene_id))}"[^>]* d="([^"]*)"', svg).group(1)
        number = lambda value: f"{value:.3f}".rstrip("0").rstrip(".")
        assert drawn == "M" + "L".join(f"{number(px)} {number(py)}" for px, py in polyline)   # drawn verbatim
        assert max(abs(py - straight.points[0][1]) for _, py in polyline) > 0.3                  # and really displaced


def test_no_bound_id_or_placement_changes_and_only_the_wobble_differs(tmp_path) -> None:
    review, plain = _pair(tmp_path)

    assert [item.scene_id for item in review.surface.primitives] == [item.scene_id for item in plain.surface.primitives]
    assert any(item.paint.wobble is not None for item in review.surface.primitives)
    for wobbled, straight in zip(review.surface.primitives, plain.surface.primitives, strict=True):
        stripped = replace(wobbled, paint=replace(wobbled.paint, wobble=None))
        assert stripped == straight                      # bounds, points, commands, slot, order: all equal
    assert review.surface.slots == plain.surface.slots and review.surface.rows == plain.surface.rows
    assert review.surface.canvas_bounds == plain.surface.canvas_bounds
    assert review.surface.info_diagnostics == plain.surface.info_diagnostics
    assert review.scene.diagnostics == plain.scene.diagnostics


def test_every_vertex_is_within_the_amplitude_of_its_nominal_position_and_inside_the_grown_bounds(tmp_path) -> None:
    review, _ = _pair(tmp_path)
    for item in _by_role(review, "planned"):
        x, y, w, h = item.bounds
        reach = 1.6 + 0.002
        for px, py in item.paint.wobble.outline[0]:
            assert x - reach <= px <= x + w + reach and y - reach <= py <= y + h + reach


def test_the_png_draws_the_wobble_where_the_svg_does_and_moves_nothing_else(tmp_path) -> None:
    review, plain = _pair(tmp_path)
    first, second = _png(review.artifact.content, tmp_path), _png(plain.artifact.content, tmp_path / "plain")
    difference = ImageChops.difference(first, second)
    box = difference.getbbox()

    assert box is not None
    changed = [(px, py) for px in range(0, first.width) for py in range(0, first.height)
               if difference.getpixel((px, py)) != (0, 0, 0)]
    allowed = [item.bounds for item in (*_by_role(review, "planned"), *_by_role(review, "axis-rule"))]
    reach = 1.6 + 3.0

    def covered(point):
        px, py = point
        for x, y, w, h in allowed:
            if x - reach <= px <= x + w + reach and y - reach <= py <= y + h + reach:
                return True
        return False

    assert changed and all(covered(point) for point in changed)
    bar = _by_role(review, "planned")[0]
    # a vertex displaced by at least one pixel paints ink in the wobbled raster and none in the straight one
    moved = max(bar.paint.wobble.outline[0], key=lambda point: abs(point[1] - bar.bounds[1]) if abs(point[1] - bar.bounds[1]) < 3 else 0)
    px, py = round(moved[0]), round(moved[1])
    assert first.getpixel((px, py)) != second.getpixel((px, py))


def test_two_renders_are_byte_identical_and_a_theme_without_wobble_has_no_trace(tmp_path) -> None:
    (tmp_path / "again").mkdir()
    (tmp_path / "plain").mkdir()
    first = _render(tmp_path, _presentation(), RICH).artifact.content
    again = _render(tmp_path / "again", _presentation(), RICH).artifact.content
    plain = _render(tmp_path / "plain", _presentation(wobble=False), RICH)

    assert first == again
    assert all(item.paint.wobble is None for item in plain.surface.primitives)
    assert b'Z" ' not in b"".join(re.findall(rb'<path data-scene-id="[^"]*planned[^"]*"[^>]*>', plain.artifact.content))
    assert "wobble" not in json.dumps(scene_document(plain.scene))


def test_the_serialized_scene_is_v07_valid_and_carries_the_completed_outline(tmp_path) -> None:
    review, _ = _pair(tmp_path)
    document = scene_document(review.scene)
    validate_scene_document(document)
    paints = [item["paint"] for surface in document["surfaces"] for item in surface["primitives"]
              if item.get("visualRole") == "planned"]

    assert document["version"] == "chrona/scene/v0.7"
    assert all(set(paint["wobble"]) == {"amplitude", "wavelength", "seed", "fidelity", "closed", "outline"} for paint in paints)
    assert paints[0]["wobble"]["amplitude"] == 1.6 and paints[0]["wobble"]["seed"] == 7 and paints[0]["wobble"]["closed"] is True
    assert len(paints[0]["wobble"]["outline"]) == 1 and len(paints[0]["wobble"]["outline"][0]) > 4


def test_a_decorative_optional_wobble_is_omitted_under_the_baseline_with_the_painting_profile(tmp_path) -> None:
    review = _render(tmp_path, _presentation(fidelity="decorative-optional"), BASELINE)
    omissions = [item for item in review.info_diagnostics if item.code == "I_VISUAL_TREATMENT_OMITTED"]

    assert sorted((item.role, item.treatment, item.paintable_profile) for item in omissions) == [
        ("axis-rule", "wobble", RICH), ("planned", "wobble", RICH)]
    assert all(item.paint.wobble is None for item in review.surface.primitives)
    assert b'<rect data-scene-id="' in review.artifact.content
    assert sum(text.startswith("I_VISUAL_TREATMENT_OMITTED:") and "treatment=wobble" in text for text in review.scene.diagnostics) == 2


def test_a_required_wobble_fails_before_serialization_under_the_baseline(tmp_path) -> None:
    with pytest.raises(RenderFailed) as error:
        _render(tmp_path, _presentation(), BASELINE)

    assert error.value.code == "E_VISUAL_CAPABILITY_UNSUPPORTED"


def test_the_typeset_adapters_refuse_a_required_wobble_and_draw_an_optional_one_straight(tmp_path) -> None:
    (tmp_path / "soft").mkdir()
    required = _render(tmp_path, _presentation(), RICH)
    optional = _render(tmp_path / "soft", _presentation(fidelity="decorative-optional"), RICH)

    for render in (render_v05_typst, render_v05_tikz):
        with pytest.raises(ValueError, match="E_VISUAL_CAPABILITY_UNSUPPORTED"):
            render(required.surface)
        assert render(optional.surface)


def test_a_role_without_a_stroke_is_drawn_exactly_as_before(tmp_path) -> None:
    review = _render(tmp_path, _presentation(roles=("group-band",)), RICH)
    bands = _by_role(review, "group-band")

    assert bands and all(item.paint.stroke is None and item.paint.wobble is None for item in bands)
    assert all(item.paint.wobble is None for item in review.surface.primitives)
    assert all(f'<rect data-scene-id="{escape(item.scene_id)}"' in review.artifact.content.decode() for item in bands)
