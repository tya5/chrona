"""`--locale ja-JP` leaves no English built-in wording in a rendered scene (#1724 P4c, acceptance 2).

The scan covers wording the code and the locale table own. A literal label in the synthetic View or Layout is
authored content, so it is removed from the scanned text, as are the Project's own titles. The shipped yuya and
target-b designs reference the table for every legend and as-of label (#1783), so their Detail Profiles are
scanned, not treated as authored; their lower case comes from the legend and as-of role `textTransform`.
"""
from __future__ import annotations

from pathlib import Path
import re

import pytest
import yaml

from chrona.presentation.model.wording_tables import wording_catalog
from chrona.resources import safe_load
from tests.integration import test_realized_legends as legends
from tests.support import synthetic_review as sr
from tests.support.text_treatments import CJK_DESCRIPTOR


ROOT = Path(__file__).resolve().parents[2]
DESIGNS = ROOT / "src/chrona/resources/designs"
ICONS = tuple((ROOT / "src/chrona/resources/icons").glob("chrona-*-v2026-10-09.yaml"))
# The English words of the built-in tables, plus the lane/qualifier words, as the scan's vocabulary.
BUILT_IN_ENGLISH = tuple(sorted(set(wording_catalog()["en-US"].values()) | {"Lane", "Items"}, key=len, reverse=True))


def _scene_texts(review) -> list[str]:
    content = review.artifact.content
    svg = content.decode("utf-8") if isinstance(content, bytes) else content
    return [re.sub(r"<[^>]+>", "", body).strip() for body in re.findall(r"<text\b[^>]*>(.*?)</text>", svg, flags=re.S)]


def _authored_labels(*documents) -> set[str]:
    found: set[str] = set()

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"label", "header"} and isinstance(item, str):
                    found.add(item)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
    for document in documents:
        walk(document)
    return found


def _english_built_ins(texts, authored) -> list[str]:
    hits = []
    for text in texts:
        for label in sorted(authored, key=len, reverse=True):
            text = re.sub(re.escape(label), "", text, flags=re.I)
        for word in BUILT_IN_ENGLISH:
            if re.search(rf"(?<![A-Za-z]){re.escape(word)}(?![A-Za-z])", text, flags=re.I):
                hits.append(text)
                break
    return hits


def _source():
    source = legends._source()
    for key, title in {"ahead": "設計", "track": "試験", "behind": "製造", "gate": "出荷"}.items():
        source["objects"][key]["title"] = title
    source["entities"] = {"a": {"type": "team", "title": "チームA"}}
    source["relations"] = [{"id": "r1", "type": "dependency", "lag": "0d", "from": {"object": "ahead", "endpoint": "end"},
                            "to": {"object": "gate", "endpoint": "at"}}]
    return source


def _default_preset():
    parts = legends._parts(progress=True)
    return parts, legends._detail(), ()


def _design_preset(design):
    def preset():
        parts = legends._parts(progress=True)
        for kind in ("theme", "scheme", "layout"):
            parts[kind] = safe_load((DESIGNS / design / f"{kind}.yaml").read_bytes())
        return parts, safe_load((DESIGNS / design / "detail.yaml").read_bytes()), ICONS
    preset.lowercase = True  # the design's legend role lower-cases every entry, the code-owned one included
    return preset


_yuya_preset = _design_preset("yuya")
_target_b_preset = _design_preset("target-b")


def _font_descriptor(directory):
    """The bundled faces plus the Noto CJK provider's, so no run depends on the faces the operating system has."""
    descriptor = safe_load((ROOT / "src/chrona/resources/fonts/default-font-metrics.yaml").read_bytes())
    descriptor["assets"] = [*descriptor["assets"], *safe_load(CJK_DESCRIPTOR.read_bytes())["assets"]]
    path = directory / "font-metrics.yaml"
    path.write_text(yaml.safe_dump(descriptor, sort_keys=False), encoding="utf-8")
    return path


def _render(tmp_path, preset, locale, *, lanes):
    parts, detail, icons = preset()
    if lanes:
        parts["view"] = sr.lane_view(parts["view"])
    else:  # the Task column header is the built-in wording, not the column id
        parts["view"]["body"]["tableColumns"][0]["header"] = {"wording": "column.task"}
        parts["view"]["body"]["tableColumns"][1]["header"] = "変化"
    review = sr.render(tmp_path, _source(), presentation=parts, actual=legends.ACTUAL, detail=detail,
                       viewport=(1800, 1000), icon_catalogs=icons, locale=locale,
                       font_metrics_path=_font_descriptor(tmp_path))
    return _scene_texts(review), _authored_labels(parts["view"], parts["layout"])


@pytest.mark.parametrize("preset", [_default_preset, _yuya_preset, _target_b_preset], ids=["default", "yuya", "target-b"])
@pytest.mark.parametrize("lanes", [False, True], ids=["table", "lane-table"])
def test_ja_jp_has_no_english_built_in_wording_and_en_us_still_does(tmp_path, preset, lanes):
    (tmp_path / "ja").mkdir()
    ja_texts, authored = _render(tmp_path / "ja", preset, "ja-JP", lanes=lanes)
    assert _english_built_ins(ja_texts, authored) == [], ja_texts
    expected = ("レーン", "件数") if lanes else ("タスク",)
    if preset is _default_preset and not lanes:  # the Actual qualifier keys are admitted by this view only
        expected += ("前倒し", "予定どおり", "遅れ")
    for word in (*expected, "進捗"):
        assert word in ja_texts, (word, ja_texts)
    (tmp_path / "en").mkdir()
    en_texts, _ = _render(tmp_path / "en", preset, "en-US", lanes=lanes)
    found = {word for word in ("Lane", "Items", "Progress", "Ahead", "On track", "Behind", "Task")
             if any(re.search(rf"(?<![A-Za-z]){word}(?![A-Za-z])", text) for text in en_texts)}
    if getattr(preset, "lowercase", False):
        assert "progress" in en_texts and "Progress" not in found, en_texts
        found.add("Progress")
    assert {"Progress"} <= found and ({"Lane", "Items"} <= found if lanes else {"Task"} <= found), en_texts
