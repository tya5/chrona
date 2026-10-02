"""A Theme-declared glow paints a halo around marks under a rich profile and follows the #478 ladder (#587).

A small synthetic Project through the packaged `executive-light` bundle; no test reads `examples/`.
"""
from __future__ import annotations

import io
from html import escape
import json
import re
from datetime import date, timedelta
from pathlib import Path

import pytest
import resvg_py
import yaml
from PIL import Image, ImageChops

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
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


def _presentation(glow: bool = True, *, fidelity: str | None = None, shadow: bool = False) -> dict:
    parts = sr.bundle("executive-light")
    if glow:
        body = parts["theme"]["body"]
        body["values"].update({"glow.blur": {"type": "number", "value": 7}, "glow.strength": {"type": "number", "value": 0.9}})
        role = {"glowBlur": "glow.blur", "glowOpacity": "glow.strength"}
        if fidelity is not None:
            body["values"]["glow.fidelity"] = {"type": "fidelity", "value": fidelity}
            role["glowFidelity"] = "glow.fidelity"
        if shadow:
            body["values"]["shadow.offset"] = {"type": "number", "value": 2}
            role.update({"shadowOffsetX": "shadow.offset", "shadowOffsetY": "shadow.offset",
                         "shadowBlur": "glow.blur", "shadowOpacity": "glow.strength"})
            body["colorBindings"]["planned.shadowColor"] = "warning"
        body["roles"]["planned"].update(role)
        body["colorBindings"]["planned.glowColor"] = "warning"
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


def _planned(review):
    return [item for item in review.surface.primitives if item.visual_role == "planned"]


def test_the_rich_svg_gives_each_glowing_mark_its_own_filter_over_its_region(tmp_path) -> None:
    review = _render(tmp_path, _presentation(), RICH)
    svg = review.artifact.content.decode()
    marks = _planned(review)

    assert len(marks) == 3 and all(item.paint.glow is not None for item in marks)
    assert len(set(item.paint.glow.region for item in marks)) == 3
    assert svg.count("<filter ") == 3 and "feDropShadow" not in svg
    for item in marks:
        x, y, w, h = item.paint.glow.region
        filter_id = re.search(rf'data-scene-id="{re.escape(escape(item.scene_id))}"[^>]*filter="url\(#(glow-[0-9a-f]+)\)"', svg).group(1)
        definition = re.search(rf'<filter id="{filter_id}"[^>]*>', svg).group(0)
        assert 'filterUnits="userSpaceOnUse"' in definition
        body = re.search(rf'<filter id="{filter_id}"[^>]*>(.*?)</filter>', svg).group(1)
        assert 'stdDeviation="7"' in body and 'flood-opacity="0.9"' in body
        assert f'flood-color="{item.paint.glow.color}"' in body
        assert body.count('<feMergeNode in="halo"/>') == 2 and body.endswith('<feMergeNode in="SourceGraphic"/></feMerge>')
        for name, value in (("x", x), ("y", y), ("width", w), ("height", h)):
            assert f' {name}="{f"{value:.3f}".rstrip("0").rstrip(".")}"' in definition


def test_the_halo_is_inside_the_region_and_inside_the_canvas(tmp_path) -> None:
    review = _render(tmp_path, _presentation(), RICH)
    for item in _planned(review):
        x, y, w, h = item.paint.glow.region
        bx, by, bw, bh = item.bounds
        assert x >= 0 and y >= 0 and x + w <= review.surface.canvas_bounds[2] and y + h <= review.surface.canvas_bounds[3]
        assert x <= bx and y <= by and x + w >= bx + bw and y + h >= by + bh
        assert item.bounds == next(p for p in review.surface.primitives if p.scene_id == item.scene_id).bounds


def test_the_png_shows_a_halo_around_a_mark_and_nothing_far_from_it(tmp_path) -> None:
    (tmp_path / "plain").mkdir()
    glowing = _render(tmp_path, _presentation(), RICH)
    plain = _render(tmp_path / "plain", _presentation(glow=False), RICH)
    first, second = _png(glowing.artifact.content, tmp_path), _png(plain.artifact.content, tmp_path / "plain")
    mark = _planned(glowing)[0]
    x, y, w, h = (int(value) for value in mark.bounds)
    above = (x + w // 2, max(0, y - 5), x + w // 2 + 1, max(0, y - 4))   # five px above the bar: inside the halo
    far = (x + w // 2, 880, x + w // 2 + 1, 881)
    assert first.crop(above).getpixel((0, 0)) != second.crop(above).getpixel((0, 0))
    assert first.crop(far).getpixel((0, 0)) == second.crop(far).getpixel((0, 0))
    assert ImageChops.difference(first, second).getbbox() is not None


def test_the_halo_is_not_clipped_to_the_marks_own_box(tmp_path) -> None:
    glowing = _render(tmp_path, _presentation(), RICH)
    (tmp_path / "plain").mkdir()
    plain = _render(tmp_path / "plain", _presentation(glow=False), RICH)
    first, second = _png(glowing.artifact.content, tmp_path), _png(plain.artifact.content, tmp_path / "plain")
    x, y, w, h = (int(value) for value in _planned(glowing)[0].bounds)
    differing = [(px, py) for px in range(x - 12, x + w + 12) for py in (y - 8, y + h + 8)
                 if first.getpixel((px, py)) != second.getpixel((px, py))]

    assert len(differing) > w // 2


def test_two_renders_are_byte_identical_and_a_theme_without_glow_has_no_filter(tmp_path) -> None:
    (tmp_path / "again").mkdir()
    (tmp_path / "plain").mkdir()
    first = _render(tmp_path, _presentation(), RICH).artifact.content
    again = _render(tmp_path / "again", _presentation(), RICH).artifact.content
    plain = _render(tmp_path / "plain", _presentation(glow=False), RICH)

    assert first == again
    assert b"<filter" not in plain.artifact.content and b"glow" not in plain.artifact.content
    assert all(item.paint.glow is None for item in plain.surface.primitives)


def test_the_serialized_scene_is_v07_and_carries_the_completed_glow(tmp_path) -> None:
    review = _render(tmp_path, _presentation(), RICH)
    document = scene_document(review.scene)
    validate_scene_document(document)
    paints = [item["paint"] for surface in document["surfaces"] for item in surface["primitives"]
              if item.get("visualRole") == "planned"]

    assert document["version"] == "chrona/scene/v0.7"
    assert all(set(paint["glow"]) == {"color", "blur", "opacity", "fidelity", "region"} for paint in paints)
    assert json.dumps(paints[0]["glow"]["region"]) and paints[0]["glow"]["blur"] == 7


def test_a_decorative_optional_glow_is_omitted_under_the_baseline_with_the_painting_profile(tmp_path) -> None:
    review = _render(tmp_path, _presentation(fidelity="decorative-optional"), BASELINE)
    omissions = [item for item in review.info_diagnostics if item.code == "I_VISUAL_TREATMENT_OMITTED"]

    assert [(item.role, item.treatment, item.paintable_profile) for item in omissions] == [("planned", "glow", RICH)]
    assert all(item.paint.glow is None for item in _planned(review))
    assert b"<filter" not in review.artifact.content
    assert sum(text.startswith("I_VISUAL_TREATMENT_OMITTED:") for text in review.scene.diagnostics) == 1


def test_a_required_glow_fails_before_serialization_under_the_baseline(tmp_path) -> None:
    with pytest.raises(RenderFailed) as error:
        _render(tmp_path, _presentation(), BASELINE)

    assert error.value.code == "E_VISUAL_CAPABILITY_UNSUPPORTED"


def test_a_shadow_and_a_glow_on_one_role_fail_at_the_glow_pointer(tmp_path) -> None:
    with pytest.raises(RenderFailed) as error:
        _render(tmp_path, _presentation(shadow=True), RICH)

    assert error.value.code == "E_VISUAL_CAPABILITY_VALUE"
