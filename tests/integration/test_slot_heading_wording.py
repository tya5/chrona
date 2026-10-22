"""A slot heading's `text` accepts `{wording: key}` and follows the Render Context locale (#1827)."""
from __future__ import annotations

from copy import deepcopy

import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.profile import resolve_layout_profile
from chrona.resources import schema_validator
from tests.integration.test_ja_jp_builtin_wording import _font_descriptor
from tests.integration.test_slot_heading import HEADING, _by_id, _render
from tests.support import synthetic_review as sr

NOTES = {"wording": "slot.notes"}


def test_wording_reference_reads_the_table_entry_for_each_locale(tmp_path):
    from tests.integration import test_slot_heading as base
    literal = _render(tmp_path, name="literal", heading={"text": "Notes", "block": "header-row"})
    reference = _render(tmp_path, name="reference", heading={"text": NOTES, "block": "header-row"})
    assert _by_id(reference)[HEADING].text == _by_id(literal)[HEADING].text == "NOTES"
    assert reference.artifact.content == literal.artifact.content

    def render_ja(name, heading):
        directory = tmp_path / name
        directory.mkdir()
        parts = base.sr.bundle("executive-light")
        sr.with_note_rail(parts, base.RAIL)
        base._filled_notes(parts)
        base._beside_the_timeline(parts)
        base._with_heading_role(parts, colour="textMuted")
        sr.find_node(parts["layout"], "annotations")["heading"] = heading
        source = sr.chain_project()
        sr.add_notes(source, parts["view"], base.TARGETS, base._rail_candidates(), words=3)
        return sr.render(directory, source, presentation=parts, viewport=(1600, 900), locale="ja-JP",
                         font_metrics_path=_font_descriptor(directory))

    japanese = render_ja("ja", {"text": NOTES, "block": "header-row"})
    assert _by_id(japanese)[HEADING].text == "注記"
    # A literal stays as authored under ja-JP (level 2 of the wording precedence).
    assert _by_id(render_ja("ja-literal", {"text": "Notes", "block": "header-row"}))[HEADING].text == "NOTES"


def test_view_wording_keys_override_the_reference(tmp_path):
    rendered = _render(tmp_path, name="override", heading={"text": NOTES, "block": "header-row"},
                       configure=lambda parts: parts["view"]["body"].update({"wording": {"keys": {"slot.notes": "Remarks"}}}))
    assert _by_id(rendered)[HEADING].text == "REMARKS"


def test_the_layout_schema_and_profile_accept_a_known_key_and_name_an_unknown_one():
    layout = deepcopy(sr.bundle("executive-light")["layout"])
    validator = schema_validator("layout-profile-v0.10.schema.yaml")
    sr.find_node(layout, "annotations")["heading"] = {"text": NOTES}
    assert not list(validator.iter_errors(layout))
    sr.find_node(layout, "annotations")["heading"] = {"text": {"wording": "slot.nope"}}
    assert list(validator.iter_errors(layout))
    with pytest.raises(LayoutError) as raised:
        resolve_layout_profile(layout, available_sources={"annotations"}, theme={})
    assert raised.value.diagnostic_id == "E_LAYOUT_SCHEMA"
    assert raised.value.path.endswith("/heading/text")
    assert "slot.nope" in str(raised.value)
