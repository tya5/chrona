"""Small-caps `textTransform` (#1285): synthetic, measured and emitted by Layout as runs at their own size.

Synthetic Project grouped by owner through the packaged `executive-light` bundle with the group header role set in
small caps; no test reads `examples/`.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import date, timedelta

import pytest

from chrona.presentation.renderers.v05_typeset import render_v05_tikz, render_v05_typst
from chrona.presentation.scene.serialization import scene_document, serialize_scene, validate_scene_document
from tests.support import synthetic_review as sr

OWNERS = ("imaging", "ground")
TITLES = {"imaging": "Imaging Team", "ground": "Ground"}
SCALE = 0.8


def _source() -> dict:
    objects = {}
    for index, owner in enumerate(OWNERS):
        key = f"t-{owner}"
        objects[key] = sr.span(key, date(2026, 1, 5) + timedelta(days=index * 20), 12, owner=owner)
    source = sr.project(objects)
    for owner in OWNERS:
        source["entities"][owner]["title"] = TITLES[owner]
    return source


def _parts(*, transform: str | None = "small-caps", scale: float | None = SCALE) -> dict:
    parts = sr.bundle("executive-light")
    body = parts["theme"]["body"]
    role = body["roles"]["groupHeader"]
    if transform is not None:
        body["values"]["caps.transform"] = {"type": "textTransform", "value": transform}
        role["textTransform"] = "caps.transform"
    if scale is not None:
        body["values"]["caps.scale"] = {"type": "number", "value": scale}
        role["smallCapsScale"] = "caps.scale"
    return parts


def _render(tmp_path, parts):
    return sr.render(tmp_path, _source(), presentation=parts)


def _header(rendered, owner):
    return next(item for item in rendered.surface.primitives if item.scene_id == f"group-header:{owner}")


def test_former_lowercase_letters_are_capitals_at_the_declared_scale_and_original_capitals_keep_the_size(tmp_path):
    layout = _header(_render(tmp_path, _parts()), "imaging").text_layout
    size = layout.font_size
    letters = [(character, run.font_size) for run in layout.runs[0] for character in run.text]

    assert layout.lines == ("IMAGING TEAM",) and layout.text_transform == "small-caps"
    assert [character for character, _ in letters] == list("IMAGING TEAM")
    assert [factor for _, factor in letters] == pytest.approx(
        [size, *[size * SCALE] * 6, size, size, *[size * SCALE] * 3])
    assert all(run.text == run.text.upper() for run in layout.runs[0])  # every run is capitals


def test_the_measured_inline_size_is_the_sum_of_the_run_measurements_plus_the_spacing_between_runs(tmp_path):
    rendered = _render(tmp_path, _parts())
    layout = _header(rendered, "imaging").text_layout
    runs = layout.runs[0]

    assert layout.bounds[2] == pytest.approx(sum(run.inline_size for run in runs) + layout.letter_spacing * (len(runs) - 1))
    assert len(runs) > 2 and [run.text for run in runs][0] == "I"


def test_without_the_transform_there_are_no_runs_and_the_output_is_unchanged(tmp_path):
    plain = _render(tmp_path / "a" if (tmp_path / "a").mkdir() is None else tmp_path, _parts(transform=None, scale=None))
    none = _render(tmp_path / "b" if (tmp_path / "b").mkdir() is None else tmp_path, _parts(transform="none", scale=None))

    assert plain.artifact.content == none.artifact.content
    assert not any(item.text_layout is not None and item.text_layout.runs for item in plain.surface.primitives)


def test_the_svg_sets_each_run_at_its_own_size_and_the_scene_validates(tmp_path):
    rendered = _render(tmp_path, _parts())
    document = json.loads(serialize_scene(rendered.scene))
    node = next(item for item in ET.fromstring(rendered.artifact.content).iter()
                if item.attrib.get("data-scene-id") == "group-header:imaging")
    sizes = [child.attrib["font-size"] for child in node if child.tag.endswith("tspan")]

    validate_scene_document(document)
    assert document["version"] == "chrona/scene/v0.7"
    assert "".join(node.itertext()) == "IMAGING TEAM"
    assert len(sizes) >= 2 and len(set(sizes)) == 1  # the small runs share one size; the capitals have no attribute


def test_typst_and_tikz_refuse_small_caps_runs_with_the_visual_capability_diagnostic(tmp_path):
    rendered = _render(tmp_path, _parts())

    for render in (render_v05_typst, render_v05_tikz):
        with pytest.raises(Exception) as caught:
            render(rendered.scene.surfaces[0])
        assert "E_VISUAL_CAPABILITY_UNSUPPORTED" in str(caught.value) + repr(getattr(caught.value, "code", ""))


@pytest.mark.parametrize("transform,scale,code", [
    ("small-caps", None, "E_THEME_ROLE_REQUIRED"),
    ("small-caps", 1.0, "E_THEME_TEXT_SCALE_RANGE"),
    ("small-caps", 0.5, "E_THEME_TEXT_SCALE_RANGE"),
    ("uppercase", 0.8, "E_THEME_TEXT_TREATMENT_CONFLICT"),
])
def test_the_scale_is_required_with_small_caps_inside_its_open_range_and_refused_beside_another_transform(
        tmp_path, transform, scale, code):
    with pytest.raises(Exception) as caught:
        _render(tmp_path, _parts(transform=transform, scale=scale))

    assert code in str(caught.value) + repr(getattr(caught.value, "diagnostic_id", ""))
