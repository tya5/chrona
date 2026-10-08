"""Role-marked runs of a group header, end to end through a synthetic Project and a packaged preset bundle (#1192).

Nothing here reads `examples/`.
"""
from __future__ import annotations

from copy import deepcopy
import xml.etree.ElementTree as ET

import pytest

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr
from tests.support import text_treatments as tt

GROUPS = ("team-0", "team-1", "team-2")
TEMPLATE = "{ordinal|group-ordinal} {title}  {secondary|group-gloss}"


def _source():
    source = sr.bunched_project(groups=len(GROUPS), per_group=3)
    for group, gloss in zip(GROUPS, ("SPACECRAFT BUS", "PAYLOAD", "GROUND"), strict=True):
        source["entities"][group]["title"] = f"Team {group[-1]}"
        source["entities"][group]["fields"] = {"gloss": gloss}
    return source


def _role(body, name, *, size, weight=400, spacing=0, transform="none", fill="accent"):
    body["values"][f"{name}.size"] = {"type": "number", "value": size}
    body["values"][f"{name}.weight"] = {"type": "fontWeight", "value": weight}
    body["values"][f"{name}.spacing"] = {"type": "number", "value": spacing}
    body["values"][f"{name}.transform"] = {"type": "textTransform", "value": transform}
    base = {key: value for key, value in body["roles"]["groupHeader"].items()
            if key in {"fontFamily", "lineHeight", "numericSpacing"}}
    body["roles"][name] = {**base, "fontSize": f"{name}.size", "fontWeight": f"{name}.weight",
                           "letterSpacing": f"{name}.spacing", "textTransform": f"{name}.transform"}
    if fill is not None:
        body["colorBindings"][f"{name}.fill"] = fill


def _parts(template=TEMPLATE, *, secondary=True, first=None, vertical=False, tab=None, ordinal_fill="accent",
           group_roles=True):
    parts = sr.bundle("control-room-dark")
    parts["theme"]["version"] = "chrona/theme/v0.15"
    body = parts["theme"]["body"]
    if group_roles:
        _role(body, "group-ordinal", size=22, weight=700, fill=ordinal_fill)
        _role(body, "group-gloss", size=11, spacing=0.1, transform="uppercase", fill="textMuted")
    header = {"text": template, "ordinal": "zero-padded"}
    if first is not None:
        header["first"] = first
    if secondary:
        header["secondary"] = {"entityField": "gloss"}
    parts["view"]["body"]["grouping"]["header"] = header
    if vertical:
        tt.with_vertical_groups(parts)
        parts["view"]["body"]["grouping"]["header"] = header
    if tab is not None:
        body["values"]["tab.inline"] = {"type": "number", "value": tab}
        body["values"]["tab.opacity"] = {"type": "number", "value": 1}
        body["roles"]["group-tab"] = {"backgroundTreatment": "fill", "backgroundPaintOrder": 13,
                                      "opacity": "tab.opacity", "tabInlineSize": "tab.inline"}
        body["colorBindings"]["group-tab.fill"] = "warning"
    return parts


def _render(tmp_path, parts, name="r"):
    directory = tmp_path / name
    directory.mkdir(parents=True, exist_ok=True)
    return sr.render(directory, _source(), presentation=parts)


def _texts(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives if item.kind.value == "Text"}


def _runs(rendered, group):
    texts = _texts(rendered)
    found = []
    while f"group-header:{group}#run{len(found)}" in texts:
        found.append(texts[f"group-header:{group}#run{len(found)}"])
    return found


def test_a_marked_template_emits_one_text_run_per_span_on_one_baseline_in_order(tmp_path):
    rendered = _render(tmp_path, _parts())

    for group, gloss in zip(GROUPS, ("SPACECRAFT BUS", "PAYLOAD", "GROUND"), strict=True):
        runs = _runs(rendered, group)
        assert [run.text for run in runs] == [f"0{GROUPS.index(group) + 1}", f"Team {group[-1]}", gloss]
        assert f"group-header:{group}" not in _texts(rendered)
        assert len({run.baseline[1] for run in runs}) == 1
        assert [run.visual_role for run in runs] == ["group-ordinal", "text", "group-gloss"]
        assert [run.text_layout.font_size for run in runs] == [22, runs[1].text_layout.font_size, 11]
        assert [run.text_layout.weight for run in runs] == [700, 700, 400]
        starts = [run.baseline[0] for run in runs]
        assert starts == sorted(starts) and len(set(starts)) == 3


def test_the_block_width_is_the_sum_of_the_runs_and_the_gaps(tmp_path):
    rendered = _render(tmp_path, _parts())
    for group in GROUPS:
        runs = _runs(rendered, group)
        gaps = [later.baseline[0] - (earlier.baseline[0] + earlier.bounds[2])
                for earlier, later in zip(runs, runs[1:], strict=False)]
        # The literal whitespace between two spans, measured in the face of the text it belongs to, is the gap.
        assert all(gap > 0 for gap in gaps)
        assert gaps[1] > gaps[0]  # two spaces of the title role against one
        block = runs[-1].baseline[0] + runs[-1].bounds[2] - runs[0].baseline[0]
        assert block == pytest.approx(sum(run.bounds[2] for run in runs) + sum(gaps))


def test_each_run_takes_its_own_ink_in_the_svg(tmp_path):
    rendered = _render(tmp_path, _parts())
    svg = ET.fromstring(rendered.artifact.content)
    elements = {item.attrib.get("data-scene-id"): item for item in svg.iter() if item.attrib.get("data-scene-id")}
    fills = [elements[f"group-header:team-0#run{index}"].attrib.get("fill") for index in range(3)]

    assert fills[0] == "#5FA8FF" and fills[2] == "#8EA0BA" and fills[1] not in {fills[0], fills[2]}


def test_an_unknown_role_is_an_error_at_its_pointer(tmp_path):
    parts = _parts("{ordinal|no-such-role} {title}", secondary=False)

    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, parts)

    assert (raised.value.code, raised.value.source_ref) == ("E_THEME_ROLE_REQUIRED", "/body/grouping/header/text")
    assert "no-such-role" in raised.value.message


def test_an_unknown_role_in_the_first_variant_names_its_own_pointer(tmp_path):
    parts = _parts("{ordinal} {title}", secondary=False, first="{ordinal|nope} {title}")

    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, parts)

    assert raised.value.source_ref == "/body/grouping/header/first"


def test_a_role_without_ink_is_an_error_at_the_template_pointer(tmp_path):
    parts = _parts()
    del parts["theme"]["body"]["colorBindings"]["group-gloss.fill"]

    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, parts)

    assert (raised.value.code, raised.value.source_ref) == ("E_THEME_ROLE_REQUIRED", "/body/grouping/header/text")
    assert "/body/roles/group-gloss/fill" in raised.value.message


def test_an_unmarked_template_has_no_runs_and_is_the_single_header_text(tmp_path):
    rendered = _render(tmp_path, _parts("{ordinal} {title}", secondary=False, group_roles=False))
    texts = _texts(rendered)

    assert all(f"group-header:{group}" in texts for group in GROUPS)
    assert not [key for key in texts if "#run" in key]
    assert texts["group-header:team-0"].text == "01 Team 0"
    assert texts["group-header:team-0"].visual_role == "text"


def test_the_first_group_variant_alone_may_be_marked(tmp_path):
    rendered = _render(tmp_path, _parts("{ordinal} {title}", secondary=False, first="{ordinal|group-ordinal} {title}"))
    texts = _texts(rendered)

    assert "group-header:team-0#run0" in texts and "group-header:team-0" not in texts
    assert "group-header:team-1" in texts and "group-header:team-1#run0" not in texts


def test_a_marked_template_on_a_vertical_group_tag_is_refused(tmp_path):
    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, _parts(vertical=True))

    assert (raised.value.code, raised.value.source_ref) == (
        "E_LAYOUT_GROUP_HEADER_RUNS_VERTICAL", "/body/grouping/header")


def test_beside_a_tab_the_last_run_gives_way_first_with_its_source_kept(tmp_path):
    wide = _render(tmp_path, _parts(tab=20), "wide")
    runs = _runs(wide, "team-0")
    natural_right = runs[-1].baseline[0] + runs[-1].bounds[2]
    header = next(item for item in wide.surface.groups if item.group_id == "team-0").header_bounds
    inline_end = header[0] + header[2]
    # leave room for the first two runs and half of the gloss
    tab = 20 + (inline_end - natural_right) + runs[-1].bounds[2] / 2
    rendered = _render(tmp_path, _parts(tab=tab), "narrow")
    narrow = _runs(rendered, "team-0")

    assert [run.text for run in narrow[:2]] == [run.text for run in runs[:2]]
    assert narrow[2].text.endswith("…") and len(narrow[2].text) < len(runs[2].text)
    assert narrow[2].baseline[0] + narrow[2].bounds[2] <= inline_end + 1e-6
    warnings = [item for item in rendered.warning_records if "group-header:team-0#run2" in str(item)]
    assert warnings


def test_a_run_that_cannot_keep_an_ellipsis_is_dropped_and_the_one_before_gives_way(tmp_path):
    wide = _render(tmp_path, _parts(tab=20), "wide")
    runs = _runs(wide, "team-0")
    header = next(item for item in wide.surface.groups if item.group_id == "team-0").header_bounds
    inline_end = header[0] + header[2]
    # room for the ordinal and a sliver of the title: the gloss is dropped, the title shortened
    tab = 20 + (inline_end - runs[0].baseline[0]) - runs[0].bounds[2] - runs[1].bounds[2] / 2
    rendered = _render(tmp_path, _parts(tab=tab), "tight")
    surviving = _runs(rendered, "team-0")

    assert [run.text for run in surviving][:1] == [runs[0].text]
    assert all(run.text_layout is not None for run in surviving)
    assert not any(run.scene_id.endswith("#run2") for run in rendered.surface.primitives)
    assert surviving[1].text.endswith("…")


def test_the_contrast_gate_judges_each_run_over_the_header_band(tmp_path):
    # An ordinal inked like the canvas cannot be read on it; only that run is reported, each run on its own ink.
    rendered = _render(tmp_path, _parts(ordinal_fill="surface"))
    findings = {item.primitive_id: item for item in evaluate_scene_contrast(scene_document(rendered.scene))
                if item.primitive_id.startswith("group-header:team-0#run")}

    assert set(findings) == {f"group-header:team-0#run{index}" for index in range(3)}
    assert {item.purpose for item in findings.values()} == {"group-header"}
    assert [findings[f"group-header:team-0#run{index}"].visual_role for index in range(3)] == [
        "group-ordinal", "text", "group-gloss"]
    assert findings["group-header:team-0#run0"].severity == "error"
    assert findings["group-header:team-0#run1"].severity == "info" and findings["group-header:team-0#run2"].severity == "info"
    warned = {pid for item in rendered.contrast_warnings for pid in item.primitive_ids}
    assert warned == {f"group-header:{group}#run0" for group in GROUPS}


def test_unmarked_output_does_not_change_when_unused_roles_exist(tmp_path):
    plain = _render(tmp_path, _parts("{ordinal} {title}", secondary=False, group_roles=False), "plain")
    with_roles = _render(tmp_path, deepcopy(_parts("{ordinal} {title}", secondary=False, group_roles=True)), "roles")

    assert [item.scene_id for item in plain.surface.primitives] == [item.scene_id for item in with_roles.surface.primitives]
    assert {key: value.bounds for key, value in _texts(plain).items()} == {
        key: value.bounds for key, value in _texts(with_roles).items()}


def test_each_run_is_pinned_to_its_own_measured_width_by_its_own_role_when_the_roles_follow_the_box(tmp_path):
    raw = _render(tmp_path, _parts(), "raw")
    parts = _parts()
    for role in ("groupHeader", "group-ordinal", "group-gloss"):
        parts["theme"]["body"]["roles"][role]["viewerFit"] = "text-follows-box"
    pinned = _render(tmp_path, parts, "pinned")
    elements = {item.attrib.get("data-scene-id"): item for item in ET.fromstring(pinned.artifact.content).iter()
                if item.attrib.get("data-scene-id")}
    raw_elements = {item.attrib.get("data-scene-id"): item for item in ET.fromstring(raw.artifact.content).iter()
                    if item.attrib.get("data-scene-id")}

    for index, run in enumerate(_runs(pinned, "team-0")):
        node = elements[f"group-header:team-0#run{index}"]
        assert float(node.attrib["textLength"]) == pytest.approx(run.bounds[2])
        assert "textLength" not in raw_elements[f"group-header:team-0#run{index}"].attrib
    # Geometry is the same either way: only the viewer is asked to hold each run to its width.
    assert [run.bounds for run in _runs(raw, "team-0")] == [run.bounds for run in _runs(pinned, "team-0")]


def test_a_figure_id_may_not_contain_the_role_separator(tmp_path):
    parts = _parts("{ordinal} {title}", secondary=False, group_roles=False)
    parts["view"]["body"]["figures"] = [{"id": "a|b", "kind": "daysUntil", "to": "asOf"}]

    with pytest.raises(Exception) as raised:
        _render(tmp_path, parts)

    assert "E_VIEW_FIGURE_INVALID" in str(raised.value)


def test_the_unread_role_check_sees_the_template_as_the_consumer(tmp_path):
    marked = _render(tmp_path, _parts(), "marked")
    unmarked = _render(tmp_path, _parts("{ordinal} {title}", secondary=False), "unmarked")

    def unread(rendered):
        return {str(item) for item in rendered.warning_records if "W_THEME_ROLE_UNREAD" in str(item)}

    assert not [item for item in unread(marked) if "group-ordinal" in item or "group-gloss" in item]
    assert any("/body/roles/group-ordinal" in item for item in unread(unmarked))


def test_a_single_space_beside_a_marked_span_is_a_gap_with_the_letter_spacing_around_it(tmp_path):
    # #1238: "ACT {ordinal|r} - {title}" must not render as "ACTI-".
    parts = _parts("ACT {ordinal|group-ordinal} · {title}", secondary=False)
    parts["theme"]["body"]["values"]["group-ordinal.spacing"] = {"type": "number", "value": 0.2}
    runs = _runs(_render(tmp_path, parts), "team-0")

    assert [run.text for run in runs] == ["ACT", "01", "· Team 0"]
    gaps = [later.baseline[0] - (earlier.baseline[0] + earlier.bounds[2]) for earlier, later in zip(runs, runs[1:])]
    assert all(gap > 2 for gap in gaps)  # the space plus the spacing after the glyph before it
