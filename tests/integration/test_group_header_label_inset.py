"""The Theme groupHeader labelInset is an absolute band-relative Layout offset (#1284)."""
from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr
from tests.support import text_treatments as tt


def _source():
    source = sr.bunched_project(groups=2, per_group=2)
    for index in range(2):
        source["entities"][f"team-{index}"]["title"] = f"Group {index}"
    return source


def _parts(*, inset: float | None = None, marked: bool = False, vertical: bool = False,
           tab: tuple[float, str] | None = None):
    parts = sr.bundle("control-room-dark")
    theme_body = parts["theme"]["body"]
    if inset is not None:
        theme_body["values"]["group-header.inset"] = {"type": "number", "value": inset}
        theme_body["roles"]["groupHeader"]["labelInset"] = "group-header.inset"
    if marked:
        theme_body["values"]["group-ordinal.size"] = {"type": "number", "value": 22}
        header_role = theme_body["roles"]["groupHeader"]
        theme_body["roles"]["group-ordinal"] = {
            key: header_role[key]
            for key in ("fontFamily", "fontWeight", "lineHeight", "letterSpacing", "textTransform", "numericSpacing")
        }
        theme_body["roles"]["group-ordinal"].update({"fontSize": "group-ordinal.size"})
        theme_body["colorBindings"]["group-ordinal.fill"] = "warning"
        parts["view"]["body"]["grouping"]["header"] = {"text": "{ordinal|group-ordinal} {title}"}
    if vertical:
        tt.with_vertical_groups(parts)
    if tab is not None:
        width, position = tab
        theme_body["values"]["group-tab.inline"] = {"type": "number", "value": width}
        theme_body["values"]["group-tab.opacity"] = {"type": "number", "value": 1}
        theme_body["roles"]["group-tab"] = {
            "backgroundTreatment": "fill", "backgroundPaintOrder": 13,
            "tabInlineSize": "group-tab.inline", "opacity": "group-tab.opacity",
        }
        theme_body["colorBindings"]["group-tab.fill"] = "warning"
        if position == "end":
            theme_body["roles"]["group-tab"]["tabPosition"] = "end"
    parts["view"]["body"]["backgroundDecoration"] = {"rows": "none", "groups": "none"}
    return parts


def _render(tmp_path, parts, name="render"):
    output = tmp_path / name
    output.mkdir(parents=True, exist_ok=True)
    return sr.render(output, _source(), presentation=parts)


def _by_id(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives}


def _group_header_font_size(parts):
    body = parts["theme"]["body"]
    token = body["roles"]["groupHeader"]["fontSize"]
    return body["values"][token]["value"]


@pytest.mark.parametrize("marked", [False, True])
def test_absent_and_explicit_zero_keep_legacy_scene_and_svg_bytes(tmp_path, marked):
    absent_parts = _parts(marked=marked)
    zero_parts = _parts(inset=0, marked=marked)
    absent = _render(tmp_path, absent_parts, "absent")
    zero = _render(tmp_path, zero_parts, "zero")

    assert absent.artifact.content == zero.artifact.content
    assert absent.surface.primitives == zero.surface.primitives


@pytest.mark.parametrize("marked", [False, True])
def test_text_starts_at_band_edge_plus_group_header_font_size_ratio(tmp_path, marked):
    ratio = 0.4
    parts = _parts(inset=ratio, marked=marked)
    rendered = _render(tmp_path, parts)
    primitives = _by_id(rendered)
    group_header_size = _group_header_font_size(parts)
    svg = ET.fromstring(rendered.artifact.content)
    elements = {item.attrib.get("data-scene-id"): item for item in svg.iter()
                if item.attrib.get("data-scene-id")}
    for group_index in range(2):
        header = primitives[f"group-header-band:team-{group_index}"]
        text = primitives[f"group-header:team-{group_index}#run0" if marked else f"group-header:team-{group_index}"]
        assert text.baseline[0] == pytest.approx(header.bounds[0] + ratio * group_header_size)
        assert text.bounds[0] >= header.bounds[0]
        assert text.bounds[0] + text.bounds[2] <= header.bounds[0] + header.bounds[2]
        if marked:
            assert text.text_layout.font_size != pytest.approx(group_header_size)
        svg_text = elements[text.scene_id]
        assert float(svg_text.attrib["x"]) == pytest.approx(text.baseline[0])


@pytest.mark.parametrize("marked", [False, True])
def test_layout_retains_immutable_content_extent_from_band_start_through_shown_runs(tmp_path, monkeypatch, marked):
    import chrona.presentation.layout.surface_composer as composer

    original = composer.compose_group_presentation
    completed = []

    def capture(**kwargs):
        value = original(**kwargs)
        completed.append(value)
        return value

    monkeypatch.setattr(composer, "compose_group_presentation", capture)
    rendered = _render(tmp_path, _parts(inset=0.4, marked=marked))
    primitives = _by_id(rendered)
    groups = {item.group_id: item.header_bounds for item in rendered.surface.groups}
    content_bounds = dict(completed[-1].header_content_bounds)

    assert set(content_bounds) == set(groups)
    for group_id, extent in content_bounds.items():
        prefix = f"group-header:{group_id}#run" if marked else f"group-header:{group_id}"
        runs = [item for item in rendered.surface.primitives if item.scene_id.startswith(prefix)]
        assert extent.inline == pytest.approx(groups[group_id][0])
        assert float(extent.inline_size) == pytest.approx(
            max(item.bounds[0] + item.bounds[2] for item in runs) - groups[group_id][0])


def test_negative_ratio_is_rejected_at_the_theme_property_pointer(tmp_path):
    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, _parts(inset=-0.1))

    assert (raised.value.code, raised.value.source_ref) == (
        "E_THEME_TOKEN_TYPE", "/body/roles/groupHeader/labelInset")


def test_start_tab_requires_a_compatible_absolute_inset(tmp_path):
    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, _parts(inset=0.1, tab=(30, "start")))

    assert (raised.value.code, raised.value.source_ref) == (
        "E_LAYOUT_GROUP_TAB_SIZE", "/body/roles/groupHeader/labelInset")
    assert "required reservation" in raised.value.message


def test_start_tab_is_not_added_a_second_time_when_explicit_inset_covers_it(tmp_path):
    ratio = 3.0
    parts = _parts(inset=ratio, tab=(30, "start"))
    rendered = _render(tmp_path, parts)
    primitives = _by_id(rendered)
    header, text = primitives["group-header-band:team-0"], primitives["group-header:team-0"]

    assert text.baseline[0] == pytest.approx(
        header.bounds[0] + ratio * _group_header_font_size(parts))


def test_end_tab_preserves_absolute_inset_and_leaves_its_trailing_reservation(tmp_path):
    ratio = 0.25
    parts = _parts(inset=ratio, tab=(30, "end"))
    rendered = _render(tmp_path, parts)
    primitives = _by_id(rendered)
    header, text = primitives["group-header-band:team-0"], primitives["group-header:team-0"]
    tab = primitives["group-tab:team-0"]

    assert text.baseline[0] == pytest.approx(header.bounds[0] + ratio * _group_header_font_size(parts))
    assert text.bounds[0] + text.bounds[2] <= tab.bounds[0]


def test_untabbed_large_inset_keeps_visible_overflow_instead_of_ellipsizing(tmp_path):
    parts = _parts(inset=120)
    rendered = _render(tmp_path, parts)
    primitives = _by_id(rendered)
    header, text = primitives["group-header-band:team-0"], primitives["group-header:team-0"]

    assert text.baseline[0] > header.bounds[0] + header.bounds[2]
    assert text.text == "Group 0"


@pytest.mark.parametrize("marked", [False, True], ids=["plain", "role-marked"])
def test_folded_header_centering_and_label_inset_preserve_band_and_mark_geometry(tmp_path, marked):
    from datetime import date

    source = _source()
    source["objects"].update({
        f"point-{index}": sr.point(f"point-{index}", date(2026, 2, 2 + index), owner="team-0")
        for index in range(4)
    })

    def render_with_inset(name, inset):
        parts = _parts(inset=inset, marked=marked)
        theme_body = parts["theme"]["body"]
        theme_body["values"].update({
            "header.size": {"type": "number", "value": 20},
            "header.leading": {"type": "number", "value": 1.6},
        })
        theme_body["roles"]["groupHeader"].update({
            "fontSize": "header.size", "lineHeight": "header.leading",
        })
        parts["view"]["body"]["rows"] = {"mode": "automatic", "points": "group-header"}
        output = tmp_path / name
        output.mkdir(parents=True, exist_ok=True)
        return sr.render(output, source, presentation=parts)

    zero = render_with_inset("zero", 0)
    inset = render_with_inset("inset", 0.4)
    zero_primitives, inset_primitives = _by_id(zero), _by_id(inset)
    group_ids = ("team-0", "team-1")

    assert zero.surface.groups == inset.surface.groups
    zero_marks = {item.scene_id: item for item in zero.surface.primitives
                  if item.kind.value == "Symbol" and item.source_ref.startswith("point-")}
    inset_marks = {item.scene_id: item for item in inset.surface.primitives
                   if item.kind.value == "Symbol" and item.source_ref.startswith("point-")}
    assert len(zero_marks) == len(inset_marks) == 4
    assert zero_marks == inset_marks

    for rendered, primitives, ratio in ((zero, zero_primitives, 0), (inset, inset_primitives, 0.4)):
        svg = ET.fromstring(rendered.artifact.content)
        svg_text = {item.attrib.get("data-scene-id"): item for item in svg.iter()
                    if item.tag.rsplit("}", 1)[-1] == "text" and item.attrib.get("data-scene-id")}
        for group_id in group_ids:
            band = primitives[f"group-header-band:{group_id}"]
            if group_id == "team-0":
                assert band.bounds[3] > 20 * 1.6
            text_ids = ([f"group-header:{group_id}#run0", f"group-header:{group_id}#run1"] if marked
                        else [f"group-header:{group_id}"])
            for text_id in text_ids:
                text = primitives[text_id]
                expected_baseline = band.bounds[1] + (band.bounds[3] - 20 * 1.6) / 2 + 20
                assert text.baseline[1] == pytest.approx(expected_baseline, abs=0.01)
                assert float(svg_text[text_id].attrib["y"]) == pytest.approx(expected_baseline, abs=0.01)
            leading = primitives[text_ids[0]]
            assert leading.baseline[0] == pytest.approx(band.bounds[0] + ratio * 20)
            if marked:
                assert leading.text_layout.font_size == 22


def test_end_tab_must_leave_nonnegative_inline_capacity(tmp_path):
    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, _parts(inset=1000, tab=(30, "end")))

    assert (raised.value.code, raised.value.source_ref) == (
        "E_LAYOUT_GROUP_TAB_SIZE", "/body/roles/groupHeader/labelInset")
    assert "available=" in raised.value.message


def test_vertical_group_tags_refuse_horizontal_inset_and_keep_tab_gap_contract(tmp_path):
    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, _parts(inset=0.2, vertical=True))

    assert (raised.value.code, raised.value.source_ref) == (
        "E_THEME_ROLE_PROPERTY_UNSUPPORTED", "/body/roles/groupHeader/labelInset")
