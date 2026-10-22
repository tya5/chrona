"""The wording keys a design's heading, count nouns and slot captions need (#1880 row 4), in both locales."""
from __future__ import annotations

import re

import pytest

from chrona.presentation.model.wording_tables import wording_catalog, wording_resolver
from tests.integration import test_derived_figures as derived
from tests.integration import test_ja_jp_builtin_wording as ja
from tests.integration.test_slot_heading import HEADING, _by_id
from tests.support import synthetic_review as sr

DESIGN_TEXT_KEYS = {
    "heading.kicker": ("The plan", "計画"),
    "heading.schedule": ("Schedule", "計画表"),
    "count.workPackages": ("Work packages", "作業パッケージ"),
    "count.sections": ("Sections", "セクション"),
    "caption.statusReports": ("Status reports", "状況報告"),
    "caption.untilFinish": ("Until finish", "完了まで"),
}


@pytest.mark.parametrize("key", DESIGN_TEXT_KEYS)
def test_each_key_reads_neutral_sentence_case_in_en_us_and_japanese_in_ja_jp(key):
    english, japanese = DESIGN_TEXT_KEYS[key]
    assert wording_resolver("en-US", None).text(key) == english
    assert wording_resolver("ja-JP", None).text(key) == japanese
    assert english[:1].isupper() and english[1:] == english[1:].lower()
    assert not re.search("[A-Za-z]", japanese)
    assert wording_catalog()["en-US"][key] == english


def test_a_slot_caption_and_a_summary_label_reference_the_new_keys(tmp_path):
    from tests.integration import test_slot_heading as base
    for locale, index in (("en-US", 0), ("ja-JP", 1)):
        directory = tmp_path / locale
        directory.mkdir()
        parts = sr.bundle("executive-light")
        sr.with_note_rail(parts, base.RAIL)
        base._filled_notes(parts)
        base._beside_the_timeline(parts)
        base._with_heading_role(parts, colour="textMuted")
        sr.find_node(parts["layout"], "annotations")["heading"] = {
            "text": {"wording": "caption.statusReports"}, "block": "header-row"}
        source = sr.chain_project()
        sr.add_notes(source, parts["view"], base.TARGETS, base._rail_candidates(), words=3)
        rendered = sr.render(directory, source, presentation=parts, locale=locale,
                             font_metrics_path=ja._font_descriptor(directory))
        expected = DESIGN_TEXT_KEYS["caption.statusReports"][index]
        assert _by_id(rendered)[HEADING].text == (expected.upper() if locale == "en-US" else expected)

        summary = derived._summary(derived._metric(metric_id="countdown", label=None))
        summary["body"]["panels"][0]["metrics"][0]["label"] = {"wording": "caption.untilFinish"}
        rendered = sr.render(directory, derived._source(), presentation=derived._parts(derived.COUNTDOWN),
                             actual=derived.ACTUAL, summary=summary, locale=locale,
                             font_metrics_path=ja._font_descriptor(directory))
        assert derived._texts(rendered)["summary:key:countdown:caption"] == DESIGN_TEXT_KEYS["caption.untilFinish"][index]
