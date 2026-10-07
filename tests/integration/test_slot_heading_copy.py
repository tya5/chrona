"""View selects caption copy; completed slot allocation and other primitives stay Layout-owned."""
import pytest

from chrona.usecases.render_review import RenderFailed
from tests.integration.test_slot_heading import HEADING, _by_id, _render
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


@pytest.mark.parametrize("target", ["missing", "review", "title", "unknown/~slot"])
def test_invalid_caption_target_is_refused_at_the_view_entry(tmp_path, target):
    with pytest.raises(RenderFailed) as failure:
        _render(tmp_path, heading={"text": "Notes"}, configure=_copy({target: "Wrong"}))
    error = failure.value
    escaped = target.replace("~", "~0").replace("/", "~1")
    assert error.code == "E_VIEW_SLOT_HEADING_TARGET"
    assert error.source_ref == f"/body/slotHeadingText/{escaped}"
    assert target in error.message and "annotations" in error.message
