"""View selects caption copy; completed slot allocation and other primitives stay Layout-owned."""
import xml.etree.ElementTree as ET

import pytest

from chrona.usecases.render_review import RenderFailed
from tests.integration.test_slot_heading import HEADING, _by_id, _render, _with_heading_role
from tests.support import synthetic_review as sr


def _copy(value):
    def configure(parts):
        parts["view"]["body"]["slotHeadingText"] = value
    return configure


def test_view_copy_changes_only_the_completed_caption(tmp_path):
    plain = _render(tmp_path, name="plain", heading={"text": "Notes", "block": "header-row"})
    selected = _render(tmp_path, name="selected", heading={"text": "Notes", "block": "header-row"},
                       configure=_copy({"annotations": "Remarks"}))
    before, after = _by_id(plain), _by_id(selected)
    assert after[HEADING].text == "REMARKS"
    assert after[HEADING].baseline == before[HEADING].baseline
    assert after[HEADING].bounds[1] == before[HEADING].bounds[1]
    assert after[HEADING].bounds[3] == before[HEADING].bounds[3]
    assert selected.surface.slots == plain.surface.slots
    assert {key: item for key, item in after.items() if key != HEADING} == {
        key: item for key, item in before.items() if key != HEADING}
    assert b">REMARKS<" in selected.artifact.content
    assert b">NOTES<" in plain.artifact.content


def test_empty_view_copy_map_is_byte_identical(tmp_path):
    plain = _render(tmp_path, name="plain", heading={"text": "Notes"})
    selected = _render(tmp_path, name="selected", heading={"text": "Notes"}, configure=_copy({}))
    assert selected.artifact.content == plain.artifact.content
    assert selected.surface.primitives == plain.surface.primitives


def test_use_case_hands_the_same_completed_preparation_to_scene_once(tmp_path, monkeypatch):
    import chrona.usecases.render_review as use_case
    from chrona.presentation.scene import v05_builder

    prepare = use_case.prepare_surface_content
    compose = v05_builder.compose_surface_layout
    prepared, forwarded = [], []

    def observe_prepare(request, *, natural=None):
        result = prepare(request, natural=natural)
        prepared.append(result)
        return result

    def observe_compose(request, *, prepared=None):
        forwarded.append((request, prepared))
        return compose(request, prepared=prepared)

    monkeypatch.setattr(use_case, "prepare_surface_content", observe_prepare)
    monkeypatch.setattr(v05_builder, "compose_surface_layout", observe_compose)
    rendered = _render(tmp_path, heading={"text": "Notes"})
    assert len(prepared) == len(forwarded) == 1
    assert forwarded[0][1] is prepared[0]
    assert forwarded[0][0] is prepared[0].inline.request
    assert b">NOTES<" in rendered.artifact.content


def test_copy_targets_node_identity_not_slot_source(tmp_path):
    def configure(parts):
        sr.find_node(parts["layout"], "annotations")["id"] = "note-rail"
        _copy({"note-rail": "Remarks"})(parts)
    selected = _render(tmp_path, heading={"text": "Notes"}, configure=configure)
    assert _by_id(selected)["slot-heading:note-rail"].text == "REMARKS"
    assert b">REMARKS<" in selected.artifact.content


def test_absent_optional_slot_accepts_its_copy_without_drawing_a_caption(tmp_path):
    selected = _render(tmp_path, heading={"text": "Notes"}, notes=False,
                       configure=_copy({"annotations": "Remarks"}))
    assert HEADING not in _by_id(selected)
    assert "annotations" not in {slot.slot_id for slot in selected.surface.slots}


def test_axis_tier_heading_matches_the_actual_upper_axis_label_baseline(tmp_path):
    def configure(parts):
        _with_heading_role(parts, size=8)
    selected = _render(tmp_path, heading={"text": "Notes", "block": "axis-tier"},
                       role=False, configure=configure)
    heading = _by_id(selected)[HEADING]
    labels = [item for item in selected.surface.primitives
              if item.scene_id.startswith("axis-label:") and not item.scene_id.endswith(":secondary")]
    upper = min(labels, key=lambda item: item.baseline[1])
    assert heading.baseline[1] == upper.baseline[1]
    assert not any("I_LAYOUT_SLOT_HEADING_NO_AXIS_TIER" in line for line in selected.surface.diagnostics)
    assert b">NOTES<" in selected.artifact.content
    texts = {element.get("data-scene-id"): element for element in ET.fromstring(selected.artifact.content).iter()
             if element.tag.endswith("}text")}
    assert texts[HEADING].get("y") == texts[upper.scene_id].get("y")


@pytest.mark.parametrize("case", ["rotated", "large-caption", "no-neighbor"])
def test_incompatible_axis_tier_fallback_is_visible_and_recorded(tmp_path, case):
    def configure(parts):
        _with_heading_role(parts, size=40 if case == "large-caption" else 8)
        if case == "rotated":
            for tier in parts["view"]["body"]["axis"]["tiers"]:
                if tier["role"] == "labels":
                    tier["label"]["orientation"] = "rotate-cw"
    selected = _render(tmp_path, heading={"text": "Notes", "block": "axis-tier"},
                       role=False, beside=case != "no-neighbor", configure=configure)
    assert HEADING in _by_id(selected) and b">NOTES<" in selected.artifact.content
    assert "I_LAYOUT_SLOT_HEADING_NO_AXIS_TIER:annotations" in selected.surface.diagnostics


@pytest.mark.parametrize("target", ["missing", "review", "title", "unknown/~slot"])
def test_invalid_caption_target_is_refused_at_the_view_entry(tmp_path, target):
    with pytest.raises(RenderFailed) as failure:
        _render(tmp_path, heading={"text": "Notes"}, configure=_copy({target: "Wrong"}))
    error = failure.value
    escaped = target.replace("~", "~0").replace("/", "~1")
    assert error.code == "E_VIEW_SLOT_HEADING_TARGET"
    assert error.source_ref == f"/body/slotHeadingText/{escaped}"
    assert target in error.message and "annotations" in error.message
