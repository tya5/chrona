"""Default axis readability over increasing windows, without corpus edits (#1294)."""
from datetime import date
from itertools import combinations
from xml.etree import ElementTree

import pytest

from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.presentation.scene.serialization import scene_document
from chrona.resources import safe_load
from chrona.usecases import preset_library
from tests.support import synthetic_review as sr


def _default_parts():
    entry = next(item for item in preset_library._library()
                 if item["id"] == preset_library.DEFAULT_PRESET_ID)
    return {kind: safe_load(preset_library._read_member(preset_library._member(entry, member)))
            for kind, member in (("view", "view"), ("theme", "theme"),
                                 ("scheme", "colorScheme"), ("layout", "layout"))}


def _assert_readable(rendered):
    labels = [primitive for primitive in rendered.surface.primitives
              if primitive.scene_id.startswith("axis-label:")]
    assert labels, "a fitting default tier must not disappear"
    for left, right in combinations(labels, 2):
        if left.scene_id.split(":")[1] != right.scene_id.split(":")[1]:
            continue
        x, y, w, h = left.bounds
        rx, ry, rw, rh = right.bounds
        assert min(x + w, rx + rw) <= max(x, rx) + 1e-6 or \
            min(y + h, ry + rh) <= max(y, ry) + 1e-6
    diagnostics = rendered.surface.diagnostics
    assert not any(item.startswith("W_LAYOUT_LABEL_OVERFLOW:axis-label:") for item in diagnostics)
    thinned = [item for item in diagnostics if item.startswith("W_LAYOUT_AXIS_LABEL_THINNED:")]
    for tier in {item.split(":")[2] for item in thinned}:
        assert any(item.startswith(f"W_LAYOUT_AXIS_DENSITY:axis-tier:{tier}:thinned=")
                   for item in diagnostics), tier
    findings = evaluate_scene_perceptibility(scene_document(rendered.scene))
    assert not any("TEXT_INTERSECTION" in item.code and
                   all(identifier.startswith("axis-label:") for identifier in item.primitive_ids)
                   for item in findings)
    svg = ElementTree.fromstring(rendered.artifact.content)
    namespace = "{http://www.w3.org/2000/svg}"
    assert len([node for node in svg.iter(namespace + "text")
                if node.attrib.get("data-scene-id", "").startswith("axis-label:")]) == len(labels)


@pytest.mark.parametrize("end", ["2027-02-01", "2027-04-01", "2028-01-01",
                                  "2032-01-01", "2037-01-01"])
def test_default_axis_is_readable_from_one_month_to_ten_years(tmp_path, end):
    start, finish = date(2027, 1, 1), date.fromisoformat(end)
    parts = _default_parts()
    parts["view"]["body"]["window"] = {"mode": "explicit", "start": start.isoformat(), "end": end}
    rendered = sr.render(tmp_path, sr.project({"work": sr.span("work", start, (finish - start).days)}),
                         presentation=parts)
    _assert_readable(rendered)


def test_reported_five_year_project_has_no_axis_label_intersections(tmp_path):
    source = sr.project({
        "p1": sr.span("p1", date(2027, 1, 4), (date(2028, 6, 30) - date(2027, 1, 4)).days,
                      title="Phase 1 research"),
        "p2": sr.span("p2", date(2028, 3, 1), (date(2030, 2, 28) - date(2028, 3, 1)).days,
                      title="Phase 2 platform build"),
        "p3": sr.span("p3", date(2029, 10, 1), (date(2031, 12, 31) - date(2029, 10, 1)).days,
                      title="Phase 3 rollout"),
        "m1": sr.point("m1", date(2028, 1, 15), title="Funding round"),
        "m2": sr.point("m2", date(2030, 3, 1), title="GA"),
    })
    _assert_readable(sr.render(tmp_path, source, presentation=_default_parts()))
