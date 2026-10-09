"""Group header line boxes use the same band-centred baseline as table cells."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date

import pytest

from tests.support import synthetic_review as sr


GROUPS = ("team-0", "team-1", "team-2")


def _parts(*, marked: bool):
    parts = sr.bundle("control-room-dark")
    parts["theme"]["version"] = "chrona/theme/v0.15"
    body = parts["theme"]["body"]
    body["values"].update({
        "header.size": {"type": "number", "value": 20},
        "header.leading": {"type": "number", "value": 1.6},
        "ordinal.size": {"type": "number", "value": 9},
        "ordinal.leading": {"type": "number", "value": 1.1},
    })
    body["roles"]["groupHeader"]["fontSize"] = "header.size"
    body["roles"]["groupHeader"]["lineHeight"] = "header.leading"
    if marked:
        body["roles"]["group-ordinal"] = {
            **{key: body["roles"]["groupHeader"][key]
               for key in ("fontFamily", "fontWeight", "letterSpacing", "textTransform", "numericSpacing")},
            "fontSize": "ordinal.size", "lineHeight": "ordinal.leading",
        }
        body["colorBindings"]["group-ordinal.fill"] = "accent"
        parts["view"]["body"]["grouping"]["header"] = {
            "text": "{ordinal|group-ordinal} {title}", "ordinal": "zero-padded",
        }
    return parts


@pytest.mark.parametrize("marked", [False, True], ids=["plain", "role-marked"])
@pytest.mark.parametrize("folded", [False, True], ids=["ordinary", "folded-points-expand-band"])
def test_each_group_header_line_box_is_centred_in_its_final_band_in_scene_and_svg(tmp_path, marked, folded):
    source = sr.bunched_project(groups=len(GROUPS), per_group=3)
    for index, group in enumerate(GROUPS):
        source["entities"][group]["title"] = f"Team {index}"
    parts = _parts(marked=marked)
    if folded:
        source["objects"].update({
            f"point-{index}": sr.point(f"point-{index}", date(2026, 2, 2 + index), owner="team-0")
            for index in range(4)
        })
        parts["view"]["body"]["rows"] = {"mode": "automatic", "points": "group-header"}
    rendered = sr.render(tmp_path, source, presentation=parts)

    groups = {item.group_id: item for item in rendered.surface.groups}
    text = {item.scene_id: item for item in rendered.surface.primitives if item.kind.value == "Text"}
    svg = ET.fromstring(rendered.artifact.content)
    svg_text = {item.attrib.get("data-scene-id"): item for item in svg.iter()
                if item.tag.rsplit("}", 1)[-1] == "text" and item.attrib.get("data-scene-id")}
    for group_id in GROUPS:
        band = groups[group_id].header_bounds
        expected_baseline = float(band[1]) + (float(band[3]) - 20 * 1.6) / 2 + 20
        ids = ([f"group-header:{group_id}#run0", f"group-header:{group_id}#run1"] if marked
               else [f"group-header:{group_id}"])
        assert all(scene_id in text for scene_id in ids)
        for scene_id in ids:
            assert text[scene_id].baseline[1] == pytest.approx(expected_baseline, abs=0.01)
            assert float(svg_text[scene_id].attrib["y"]) == pytest.approx(expected_baseline, abs=0.01)

    if marked:
        # The marker's smaller font/leading cannot move the line box owned by groupHeader.
        assert text["group-header:team-0#run0"].text_layout.font_size == 9

    if folded:
        header = groups["team-0"].header_bounds
        assert header[3] > 20 * 1.6
        folded_marks = [item for item in rendered.surface.primitives
                        if item.kind.value == "Symbol" and item.source_ref.startswith("point-")]
        assert len(folded_marks) == 4
        centers = sorted(item.bounds[1] + item.bounds[3] / 2 for item in folded_marks)
        assert [right - left for left, right in zip(centers, centers[1:])] == pytest.approx([10, 10, 10])
        assert (centers[0] + centers[-1]) / 2 == pytest.approx(header[1] + header[3] / 2, abs=0.01)
