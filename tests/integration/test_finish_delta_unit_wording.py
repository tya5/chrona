"""The unit after a signed finish delta is a wording key per `comparison.deltaUnit` (#1790 row 1).

en-US keeps `d` for both units (byte-identical to the former literal); ja-JP reads `日` for calendar days and
`営業日` for working days; a View `wording.keys` entry overrides either. The ja-JP cases declare the Noto CJK
provider through a font-metrics descriptor, so no run depends on the operating system's faces.
"""
from __future__ import annotations

import re

import pytest

from tests.integration import test_ja_jp_builtin_wording as ja
from tests.integration import test_realized_legends as legends
from tests.support import synthetic_review as sr


def _delta_texts(tmp_path, locale, unit, keys=None):
    parts = legends._parts(progress=True)
    parts["view"]["body"]["comparison"]["deltaUnit"] = unit
    if keys:
        parts["view"]["body"]["wording"] = {"keys": keys}
    review = sr.render(tmp_path, ja._source(), presentation=parts, actual=legends.ACTUAL, detail=legends._detail(),
                       viewport=(1800, 1000), locale=locale, font_metrics_path=ja._font_descriptor(tmp_path))
    return {match for text in ja._scene_texts(review) for match in re.findall(r"[+-]\d+\S*", text)}


@pytest.mark.parametrize(("locale", "unit", "keys", "suffix"), [
    ("en-US", "calendar-days", None, "d"),
    ("en-US", "working-days", None, "d"),
    ("ja-JP", "calendar-days", None, "日"),
    ("ja-JP", "working-days", None, "営業日"),
    ("ja-JP", "working-days", {"delta.unit.workingDay": "営"}, "営"),
    ("en-US", "calendar-days", {"delta.unit.calendarDay": "dy"}, "dy"),
], ids=["en-calendar", "en-working", "ja-calendar", "ja-working", "ja-override", "en-override"])
def test_label_unit_follows_delta_unit_locale_and_override(tmp_path, locale, unit, keys, suffix):
    texts = _delta_texts(tmp_path, locale, unit, keys)
    labelled = {text for text in texts if not text[1:].isdigit()}  # the bare table cells carry no unit
    assert labelled, texts
    assert all(text.endswith(suffix) for text in labelled), labelled
