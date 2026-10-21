"""`{wording:<key>}` placeholders in heading parts, slot caption templates and Summary titles (#1880 row 3)."""
from __future__ import annotations

from datetime import date

import pytest

from chrona.presentation.model.closure import ClosureError
from tests.integration.test_derived_figures import _metric, _parts as _summary_parts, _summary, _texts
from tests.integration.test_heading_counts import _parts as _heading_parts
from tests.integration.test_heading_omit_when_zero import _subtitle_role
from tests.integration.test_ja_jp_builtin_wording import _font_descriptor
from tests.integration.test_slot_heading import HEADING, _by_id, _render
from tests.support import synthetic_review as sr


def _source():
    return sr.project({"a": sr.span("a", date(2026, 2, 2), 5)})


def _heading_texts(tmp_path, heading, *, locale="en-US", wording=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    parts = _heading_parts()
    _subtitle_role(parts)
    parts["view"]["body"]["heading"] = heading
    if wording is not None:
        parts["view"]["body"]["wording"] = wording
    rendered = sr.render(tmp_path, _source(), presentation=parts, locale=locale,
                         font_metrics_path=_font_descriptor(tmp_path) if locale != "en-US" else None)
    return {item.scene_id: item.text for item in rendered.surface.primitives if item.scene_id in {"title", "subtitle", "kicker"}}


def test_heading_parts_and_shorthand_read_the_render_locale(tmp_path):
    heading = {"title": "{project}", "kicker": "{wording:column.plan}",
               "subtitle": [{"text": "{wording:column.task}"}, {"text": " / {figure:items} {wording:column.items}"}]}
    english = _heading_texts(tmp_path / "en", heading)
    assert (english["kicker"], english["subtitle"]) == ("Plan", "Task / 01 Items")
    japanese = _heading_texts(tmp_path / "ja", heading, locale="ja-JP")
    assert (japanese["kicker"], japanese["subtitle"]) == ("計画", "タスク / 01 件数")


def test_view_wording_keys_override_a_heading_placeholder(tmp_path):
    texts = _heading_texts(tmp_path, {"title": "{project}", "subtitle": "{wording:column.task}"},
                           wording={"keys": {"column.task": "Work package"}})
    assert texts["subtitle"] == "Work package"


def test_an_unknown_heading_key_is_refused_with_its_pointer(tmp_path):
    parts = _heading_parts()
    parts["view"]["body"]["heading"] = {"title": "{project}", "subtitle": [{"text": "x"}, {"text": "{wording:no.such}"}]}
    with pytest.raises(ClosureError) as caught:
        sr.render(tmp_path, _source(), presentation=parts)
    assert str(caught.value) == "E_WORDING_KEY_UNKNOWN"
    assert caught.value.source_ref == "/body/heading/subtitle/1/text"


def _template_counts(parts):
    parts["view"]["body"]["figures"] = [{"id": "n", "kind": "count", "source": "selected"}]


def test_a_slot_template_reads_the_render_locale_and_keeps_its_figures(tmp_path):
    rendered = _render(tmp_path, heading={"template": "{wording:slot.notes} {figure:n}", "block": "header-row"},
                       configure=_template_counts)
    literal = _render(tmp_path, name="literal", heading={"template": "Notes {figure:n}", "block": "header-row"},
                      configure=_template_counts)
    assert _by_id(rendered)[HEADING].text == _by_id(literal)[HEADING].text
    assert rendered.artifact.content == literal.artifact.content


def test_a_slot_template_follows_ja_jp(tmp_path):
    from tests.integration import test_slot_heading as base
    parts = sr.bundle("executive-light")
    sr.with_note_rail(parts, base.RAIL)
    base._filled_notes(parts)
    base._beside_the_timeline(parts)
    base._with_heading_role(parts, colour="textMuted")
    sr.find_node(parts["layout"], "annotations")["heading"] = {"template": "{wording:slot.notes} {figure:n}",
                                                                "block": "header-row"}
    _template_counts(parts)
    source = sr.chain_project()
    sr.add_notes(source, parts["view"], base.TARGETS, [base._rail_candidate()], words=3)
    rendered = sr.render(tmp_path, source, presentation=parts, locale="ja-JP",
                         font_metrics_path=_font_descriptor(tmp_path))
    assert _by_id(rendered)[HEADING].text.startswith("注記 ")


def test_a_slot_template_unknown_key_is_refused(tmp_path):
    with pytest.raises(Exception) as caught:
        _render(tmp_path, heading={"template": "{wording:no.such}"})
    assert type(caught.value).__name__ in {"LayoutError", "RenderFailed"}
    assert "E_WORDING_KEY_UNKNOWN" in str(caught.value) + str(getattr(caught.value, "code", ""))


def _summary_titles(tmp_path, title, *, locale="en-US"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    parts = _summary_parts({"id": "n", "kind": "count", "source": "selected"})
    summary = _summary(_metric("n", metric_id="n"))
    summary["body"]["panels"][0]["title"] = title
    rendered = sr.render(tmp_path, _source(), presentation=parts, summary=summary, locale=locale,
                         font_metrics_path=_font_descriptor(tmp_path) if locale != "en-US" else None)
    return {item.scene_id: item.text for item in rendered.surface.primitives if item.scene_id.startswith("summary:")}


def test_a_summary_title_reads_the_render_locale(tmp_path):
    english = _summary_titles(tmp_path / "en", "{wording:column.items}: {wording:column.task}")
    assert "Items: Task" in english.values()
    japanese = _summary_titles(tmp_path / "ja", "{wording:column.items}: {wording:column.task}", locale="ja-JP")
    assert "件数: タスク" in japanese.values()


def test_a_summary_title_without_a_marker_keeps_its_braces(tmp_path):
    assert "Key {figures}" in _summary_titles(tmp_path, "Key {figures}").values()


def test_a_summary_title_unknown_key_is_refused(tmp_path):
    with pytest.raises(ClosureError) as caught:
        _summary_titles(tmp_path, "{wording:no.such}")
    assert (caught.value.diagnostic_id, caught.value.source_ref) == ("E_WORDING_KEY_UNKNOWN", "/body/panels/0/title")
