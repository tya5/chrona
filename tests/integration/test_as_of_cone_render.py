"""A Theme-declared as-of cone paints a fading light from the marker under the marks and follows the #478 ladder (#890).

A small synthetic Project through the packaged `executive-light` bundle; no test reads `examples/`.
"""
from __future__ import annotations

import io
import json
import re
from copy import deepcopy
from html import escape
from datetime import date, timedelta
from pathlib import Path

import pytest
import resvg_py
import yaml
from PIL import Image

from chrona.presentation.color_scheme import ColorSchemeError
from chrona.presentation.model.closure import ClosureError, resolve_draft_render
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.presentation.renderers.v05_typeset import render_v05_tikz, render_v05_typst
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document, validate_scene_document
from chrona.presentation.scene.visual_capabilities import (
    VisualCapabilityError, resolve_visual_profile, validate_surface_visual_profile,
)
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderFailed, RenderRequest, render_review
from tests.support import synthetic_review as sr

RICH = "chrona-output/visual/v0.6-svg"
BASELINE = "chrona-output/visual/v0.5-baseline"
ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
          "body": {"asOf": "2026-03-20", "observations": []}}


def _source() -> dict:
    objects = {}
    for index, owner in enumerate("abc"):
        key = f"{owner}0"
        objects[key] = sr.span(key, date(2026, 3, 2) + timedelta(days=index * 9), 40, owner=owner, title=f"Synthetic task {key}")
    return sr.project(objects)


def _presentation(cone: bool = True, *, fidelity: str | None = None, spread: float = 1.0, extent: float = 1.0,
                  strength: float = 0.7, role: dict | None = None, bindings: dict | None = None) -> dict:
    parts = sr.bundle("executive-light")
    if cone:
        body = parts["theme"]["body"]
        body["values"].update({"cone.spread": {"type": "number", "value": spread},
                               "cone.extent": {"type": "number", "value": extent},
                               "cone.strength": {"type": "number", "value": strength}})
        declared = {"coneSpread": "cone.spread", "coneExtent": "cone.extent", "opacity": "cone.strength"}
        if fidelity is not None:
            body["values"]["cone.fidelity"] = {"type": "fidelity", "value": fidelity}
            declared["gradientFidelity"] = "cone.fidelity"
        body["roles"]["as-of-cone"] = role if role is not None else declared
        body["colorBindings"].update({"as-of-cone.fill": "warning"} if bindings is None else bindings)
    return parts


def _render(directory: Path, presentation: dict, profile: str):
    paths = {}
    for kind, value in presentation.items():
        paths[kind] = directory / f"{kind}.yaml"
        paths[kind].write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding="utf-8")
    (directory / "project.yaml").write_text(yaml.safe_dump(_source(), sort_keys=False), encoding="utf-8")
    (directory / "actual.yaml").write_text(yaml.safe_dump(ACTUAL, sort_keys=False), encoding="utf-8")
    draft = resolve_draft_render(project_path=directory / "project.yaml", view_path=paths["view"],
                                 theme_path=paths["theme"], scheme_path=paths["scheme"], layout_path=paths["layout"],
                                 actual_path=directory / "actual.yaml", viewport=(1600, 900), visual_profile=profile)
    return render_review(RenderRequest(closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
                                       scheduler=ReferenceScheduler(), renderer=V05SvgRenderer(),
                                       draft_auto_block=draft.auto_block))


def _png(svg: bytes, directory: Path) -> Image.Image:
    path = directory / "board.svg"
    path.write_bytes(svg)
    return Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(svg_path=str(path), zoom=1, font_dirs=[],
                                                              skip_system_fonts=False)))).convert("RGB")


def _cone(review):
    return next(item for item in review.surface.primitives if item.visual_role == "as-of-cone")


def _line(review):
    return next(item for item in review.surface.primitives if item.scene_id == "as-of")


def _delta(first: Image.Image, second: Image.Image, point: tuple[int, int]) -> int:
    return sum(abs(a - b) for a, b in zip(first.getpixel(point), second.getpixel(point)))


def _position(svg: str, scene_id: str) -> int:
    return svg.index(f'data-scene-id="{escape(scene_id, quote=True)}"')


def test_the_cone_falls_from_the_top_of_the_marker_to_the_last_row(tmp_path) -> None:
    review = _render(tmp_path, _presentation(), RICH)
    cone, line = _cone(review), _line(review)
    x, top = line.points[0]
    bottom = line.points[1][1]

    assert cone.kind == "Symbol" and cone.purpose == "as-of-cone"
    assert (cone.bounds[1], cone.bounds[1] + cone.bounds[3]) == (top, bottom)
    assert cone.bounds[0] == pytest.approx(x - (bottom - top)) and cone.bounds[2] == pytest.approx(2 * (bottom - top))
    gradient = cone.paint.gradient
    assert (gradient.start[1], gradient.end[1]) == (top, bottom) and gradient.stop_opacities == (1.0, 0.0)


def test_the_svg_draws_the_gradient_with_stop_opacity_above_the_bands_and_below_every_mark_and_text(tmp_path) -> None:
    review = _render(tmp_path, _presentation(), RICH)
    svg = review.artifact.content.decode()
    cone = _position(svg, "as-of-cone")
    cone_box = _cone(review).bounds

    definition = re.search(r'<linearGradient id="(gradient-[0-9a-f]+)"[^>]*>(.*?)</linearGradient>', svg)
    assert 'stop-opacity="1"' in definition.group(2) and 'stop-opacity="0"' in definition.group(2)
    assert f'fill="url(#{definition.group(1)})"' in svg[cone:cone + 400]
    for item in review.surface.primitives:
        if item.purpose in {"row-decoration", "group-decoration", "calendar-closed"}:
            assert _position(svg, item.scene_id) < cone
        inside = (item.bounds[0] < cone_box[0] + cone_box[2] and item.bounds[0] + item.bounds[2] > cone_box[0]
                  and item.bounds[1] < cone_box[1] + cone_box[3] and item.bounds[1] + item.bounds[3] > cone_box[1])
        if item.visual_role in {"planned", "actual", "as-of"} or (item.kind == "Text" and inside and item.purpose != "title"):
            assert _position(svg, item.scene_id) > cone, item.scene_id


def test_the_png_shows_ink_at_the_apex_fading_to_nothing_and_nothing_outside(tmp_path) -> None:
    (tmp_path / "plain").mkdir()
    lit = _render(tmp_path, _presentation(), RICH)
    plain = _render(tmp_path / "plain", _presentation(False), RICH)
    first, second = _png(lit.artifact.content, tmp_path), _png(plain.artifact.content, tmp_path / "plain")
    line, cone = _line(lit), _cone(lit)
    x, top = int(line.points[0][0]), int(line.points[0][1])
    bottom = int(line.points[1][1])
    column = x + 6

    near_apex, middle, near_foot = (_delta(first, second, (column, y)) for y in (top + 10, (top + bottom) // 2, bottom - 3))
    assert near_apex > middle > near_foot >= 0 and near_apex > 20
    assert _delta(first, second, (x + 250, top + 10)) == 0           # outside the polygon
    assert _delta(first, second, (column, bottom + 12)) == 0         # below the last row
    assert _delta(first, second, (int(cone.bounds[0]) - 5, top + 10)) == 0
    bar = next(item for item in lit.surface.primitives if item.visual_role == "planned" and item.scene_id.endswith("a0"))
    bx, by, bw, bh = (int(value) for value in bar.bounds)
    assert bx < column < bx + bw
    assert _delta(first, second, (column, by + bh // 2)) == 0        # the mark is above the cone: its own colour


def test_without_the_role_nothing_is_drawn_and_the_cone_removed_from_a_render_is_the_plain_render(tmp_path) -> None:
    (tmp_path / "plain").mkdir()
    lit = _render(tmp_path, _presentation(), RICH)
    plain = _render(tmp_path / "plain", _presentation(False), RICH)
    svg = lit.artifact.content.decode()
    stripped = re.sub(r'<path data-scene-id="as-of-cone"[^>]*/>\n', "", svg)
    stripped = re.sub(r'<linearGradient id="gradient-[0-9a-f]+".*?</linearGradient>', "", stripped).replace("<defs></defs>\n", "")

    assert b"as-of-cone" not in plain.artifact.content and b"stop-opacity" not in plain.artifact.content
    assert all(item.visual_role != "as-of-cone" for item in plain.surface.primitives)
    assert stripped == plain.artifact.content.decode()  # the cone moved no label, route or bar: it is a ground only
    assert scene_document(plain.scene)["version"] == "chrona/scene/v0.6"


def test_gradients_that_differ_only_in_stop_opacity_get_distinct_definitions(tmp_path) -> None:
    from dataclasses import replace

    review = _render(tmp_path, _presentation(), RICH)
    cone = _cone(review)
    opaque = replace(cone, scene_id="as-of-cone-opaque",
                     paint=replace(cone.paint, gradient=replace(cone.paint.gradient, stop_opacities=None)))
    svg = V05SvgRenderer().render(replace(review.surface, primitives=(*review.surface.primitives, opaque))).content.decode()

    assert len(set(re.findall(r'<linearGradient id="(gradient-[0-9a-f]+)"', svg))) == 2


def test_two_renders_are_byte_identical(tmp_path) -> None:
    (tmp_path / "again").mkdir()

    assert _render(tmp_path, _presentation(), RICH).artifact.content == _render(
        tmp_path / "again", _presentation(), RICH).artifact.content


def test_the_serialized_scene_is_v07_carries_the_stop_opacity_and_validates(tmp_path) -> None:
    review = _render(tmp_path, _presentation(), RICH)
    document = scene_document(review.scene)
    validate_scene_document(document)
    primitive = next(item for surface in document["surfaces"] for item in surface["primitives"]
                     if item.get("visualRole") == "as-of-cone")

    assert document["version"] == "chrona/scene/v0.7"
    assert [stop["opacity"] for stop in primitive["paint"]["gradient"]["stops"]] == [1.0, 0.0]
    assert json.dumps(primitive["symbol"]["outline"])


def test_a_decorative_optional_cone_is_omitted_whole_under_the_baseline_with_the_painting_profile(tmp_path) -> None:
    review = _render(tmp_path, _presentation(fidelity="decorative-optional"), BASELINE)
    omissions = [item for item in review.info_diagnostics if item.code == "I_VISUAL_TREATMENT_OMITTED"]
    svg = review.artifact.content

    assert [(item.role, item.treatment, item.paintable_profile) for item in omissions] == [("as-of-cone", "as-of-cone", RICH)]
    assert all(item.visual_role != "as-of-cone" for item in review.surface.primitives)  # no flat ink polygon either
    assert b"as-of-cone" not in svg and b"linearGradient" not in svg
    assert sum(text.startswith("I_VISUAL_TREATMENT_OMITTED:") for text in review.scene.diagnostics) == 1
    for render in (render_v05_typst, render_v05_tikz):
        render(review.surface)  # the typeset routes receive no gradient


@pytest.mark.parametrize("fidelity", ["required", None])
def test_a_required_cone_fails_before_serialization_under_the_baseline(tmp_path, fidelity) -> None:
    with pytest.raises(RenderFailed) as error:
        _render(tmp_path, _presentation(fidelity=fidelity), BASELINE)

    assert error.value.code == "E_VISUAL_CAPABILITY_UNSUPPORTED"


def test_a_cone_surface_is_refused_by_the_baseline_profile_gate(tmp_path) -> None:
    review = _render(tmp_path, _presentation(fidelity="required"), RICH)

    with pytest.raises(VisualCapabilityError) as error:
        validate_surface_visual_profile(review.surface, resolve_visual_profile(BASELINE, "typst"))

    assert error.value.diagnostic_id == "E_VISUAL_CAPABILITY_UNSUPPORTED"


@pytest.mark.parametrize(("spread", "extent", "pointer"), [
    (0, 1, "coneSpread"), (5, 1, "coneSpread"), (0.5, 0, "coneExtent"), (0.5, 1.2, "coneExtent")])
def test_a_spread_or_extent_out_of_range_fails_at_its_exact_pointer(tmp_path, spread, extent, pointer) -> None:
    with pytest.raises(RenderFailed) as error:
        _render(tmp_path, _presentation(spread=spread, extent=extent), RICH)

    assert error.value.code == "E_VISUAL_CAPABILITY_LIMIT"
    assert error.value.source_ref == f"/body/roles/as-of-cone/{pointer}"


SHAPE = {"coneSpread": "cone.spread", "coneExtent": "cone.extent"}


@pytest.mark.parametrize(("role", "bindings", "code", "pointer"), [
    (SHAPE, {}, "E_THEME_ROLE_REQUIRED", "/body/roles/as-of-cone/fill"),
    ({"coneExtent": "cone.extent"}, None, "E_THEME_ROLE_REQUIRED", "/body/roles/as-of-cone/coneSpread"),
    ({"coneSpread": "cone.spread"}, None, "E_THEME_ROLE_REQUIRED", "/body/roles/as-of-cone/coneExtent"),
    (SHAPE, {"as-of-cone.fill": "warning", "as-of-cone.stroke": "warning"},
     "E_THEME_ROLE_PROPERTY_UNSUPPORTED", "/body/colorBindings/as-of-cone.stroke"),
    ({**SHAPE, "backgroundPaintOrder": 5}, None, "E_THEME_ROLE_PROPERTY_UNSUPPORTED", "/body/roles/as-of-cone/backgroundPaintOrder"),
])
def test_a_malformed_cone_role_fails_before_layout_at_its_exact_pointer(tmp_path, role, bindings, code, pointer) -> None:
    with pytest.raises((ColorSchemeError, ClosureError)) as error:
        _render(tmp_path, _presentation(role=role, bindings=bindings), RICH)

    assert getattr(error.value, "diagnostic_id", None) == code
    assert getattr(error.value, "source_ref", getattr(error.value, "pointer", None)) == pointer


def test_the_gate_judges_a_bar_in_the_cone_on_the_composited_ground(tmp_path) -> None:
    review = _render(tmp_path, _presentation(strength=0.9), RICH)
    findings = [item for item in evaluate_scene_contrast(scene_document(review.scene))
                if item.ground_id == "as-of-cone"]

    assert findings and {item.ground_kind for item in findings} == {"cone-blend"}
    assert all(item.code == "E_SCENE_MARK_CONTRAST" for item in findings)


def test_the_presentation_helper_does_not_alias_the_packaged_bundle() -> None:
    first, second = _presentation(), _presentation(False)

    assert "as-of-cone" in first["theme"]["body"]["roles"] and "as-of-cone" not in second["theme"]["body"]["roles"]
    assert deepcopy(second) == second
