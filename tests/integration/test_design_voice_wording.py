"""Design-voice wording keys, the case rule and the code-owned `Other` legend entry (#1724 P4d)."""
from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

from chrona.presentation.model.wording_tables import wording_catalog, wording_resolver
from tests.integration import test_categorical_hues_not_cycled as folded
from tests.integration import test_derived_figures as derived
from tests.integration import test_ja_jp_builtin_wording as ja
from tests.integration import test_realized_legends as legends
from tests.support import synthetic_review as sr

NEW_LEGEND_KEYS = ("legend.plan", "legend.missing-actual", "legend.missing-actual-in-progress", "legend.in-the-wings",
                   "legend.calendar-exception", "legend.period", "legend.depends-on", "legend.other")


def _scene_texts(scene: Path) -> list[str]:
    primitives = json.loads(scene.read_text(encoding="utf-8"))["surfaces"][0]["primitives"]
    return [item["text"] for item in primitives if isinstance(item.get("text"), str)]


@pytest.mark.parametrize("locale", ["en-US", "ja-JP"])
def test_the_folded_other_legend_entry_is_a_table_key(tmp_path, monkeypatch, capsys, locale):
    owners = ["Ada", "Benoit", "Chika", "Diego", "Eleni", "Farah", "Gabe", "Hana"]
    project = folded._plan(tmp_path, monkeypatch, capsys, owners)
    scene = tmp_path / "scene.json"
    scheme = folded._mission_light_scheme_without_print_claim(tmp_path)
    result = folded._run(monkeypatch, capsys, "render", "--preset", "mission-light", str(project),
                         "--layout", str(folded._mission_light_layout_with_legend(tmp_path)),
                         "--scheme", str(scheme), "--locale", locale,
                         "-o", str(tmp_path / "out.svg"), "--emit-scene", str(scene))
    assert result["status"] == "ok"
    texts = _scene_texts(scene)
    expected = wording_catalog()[locale]["legend.other"]
    assert expected in {text.upper() if locale == "en-US" else text for text in texts} or expected in texts, texts
    if locale == "ja-JP":
        assert not any(text.lower() == "other" for text in texts)


def test_a_summary_metric_label_references_a_wording_key(tmp_path):
    summary = derived._summary(derived._metric(metric_id="countdown", label=None))
    summary["body"]["panels"][0]["metrics"][0]["label"] = {"wording": "summary.days"}
    for locale, expected in (("en-US", "DAYS"), ("ja-JP", "日")):
        directory = tmp_path / locale
        directory.mkdir()
        rendered = sr.render(directory, derived._source(), presentation=derived._parts(derived.COUNTDOWN),
                             actual=derived.ACTUAL, summary=summary, locale=locale,
                             font_metrics_path=ja._font_descriptor(directory))
        assert derived._texts(rendered)["summary:key:countdown:caption"] == expected
    # the View's wording.summary entry still wins over the reference
    parts = derived._parts(derived.COUNTDOWN)
    parts["view"]["body"]["wording"] = {"summary": {"key.countdown": "remaining"}}
    rendered = sr.render(tmp_path, derived._source(), presentation=parts, actual=derived.ACTUAL, summary=summary)
    assert derived._texts(rendered)["summary:key:countdown:caption"] == "remaining"


ROLE_KEYS = (("missing-actual", "legend.missing-actual"), ("calendar-exception", "legend.calendar-exception"),
             ("period-band", "legend.period"), ("dependency", "legend.depends-on"), ("milestone", "legend.in-the-wings"),
             ("snapshot", "legend.plan"), ("forecast", "legend.missing-actual-in-progress"))


def _legend_detail():
    return legends._detail(*((role, {"wording": key}) for role, key in ROLE_KEYS))


def _render_legend(tmp_path, locale, *, lowercase=False):
    parts = legends._parts(progress=True)
    if lowercase:  # the case rule: the role's Theme typography transform, not a second set of keys
        body = parts["theme"]["body"]
        body["values"]["design-lower"] = {"type": "textTransform", "value": "lowercase"}
        body["roles"]["legend"]["textTransform"] = "design-lower"
    columns = parts["view"]["body"]["tableColumns"]
    columns[0]["header"], columns[1]["header"] = {"wording": "column.task"}, {"wording": "column.no"}
    review = sr.render(tmp_path, ja._source(), presentation=parts, actual=legends.ACTUAL, detail=_legend_detail(),
                       viewport=(1800, 1000), locale=locale, font_metrics_path=ja._font_descriptor(tmp_path))
    return ja._scene_texts(review), parts


def test_every_new_legend_key_is_japanese_under_ja_jp_and_the_scan_knows_the_english(tmp_path):
    texts, parts = _render_legend(tmp_path, "ja-JP")
    table = wording_catalog()["ja-JP"]
    assert table["legend.depends-on"] in texts
    # The realized point figures differ, so the translated owner label has
    # translated state qualifiers rather than an unqualified duplicate key.
    assert {table["legend.in-the-wings"] + " · " + table[key]
            for key in ("legend.planned-plain", "legend.actual")} <= set(texts)
    resolver = wording_resolver("ja-JP", None)
    assert all(resolver.text(key) == table[key] and not re.search("[A-Za-z]", table[key])
               for key in (*NEW_LEGEND_KEYS, "column.no"))
    assert wording_catalog()["ja-JP"]["column.no"] in texts
    assert ja._english_built_ins(texts, ja._authored_labels(parts["view"], parts["layout"])) == [], texts
    vocabulary = {text.lower() for text in ja.BUILT_IN_ENGLISH}
    assert {wording_catalog()["en-US"][key].lower() for key in NEW_LEGEND_KEYS} <= vocabulary


def test_a_design_gets_lower_case_from_the_role_transform_without_its_own_keys(tmp_path):
    plain, _ = _render_legend(tmp_path / "plain" if (tmp_path / "plain").mkdir() is None else tmp_path, "en-US")
    lowered, _ = _render_legend(tmp_path / "lower" if (tmp_path / "lower").mkdir() is None else tmp_path, "en-US", lowercase=True)
    entry = wording_catalog()["en-US"]["legend.depends-on"]
    assert entry in plain
    assert entry.lower() in lowered and entry not in lowered
    assert wording_catalog()["en-US"]["legend.depends-on"] == "Depends on"  # the value stays case-neutral
