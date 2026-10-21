"""Wrapped CJK text never starts a line with a line-start-prohibited character (JIS X 4051, #1891)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from chrona.presentation.layout.text import wrap_text

METRICS = SimpleNamespace(width=lambda text, size: len(text) * size)

# One synthetic note per JIS X 4051 line-start-prohibited class; the character after the first one is the probe.
CLASSES = {
    "small-kana": ("設計レビュー会議", "ュ"),
    "small-tsu": ("設計して下さいっ", "っ"),
    "small-katakana-tsu": ("最終チェックを実施", "ッ"),
    "long-sound-mark": ("設計レビュー結果を共有", "ー"),
    "closing-corner-bracket": ("確認事項「設計レビュー」完了", "」"),
    "closing-paren": ("設計レビュー（暫定）完了", "）"),
    "closing-lenticular": ("設計レビュー【暫定】完了", "】"),
    "ideographic-full-stop": ("設計をレビューする。次へ進む", "。"),
    "ideographic-comma": ("設計を確認、次へ進む", "、"),
    "middle-dot": ("設計・レビュー・完了", "・"),
    "colon": ("結果：合格です", "："),
    "question-mark": ("合格ですか？はい", "？"),
    "exclamation-mark": ("合格です！次へ", "！"),
    "iteration-mark": ("人々が設計する", "々"),
    "wave-dash": ("設計〜完了までの流れ", "〜"),
    "curly-quote": ("彼は”完了”と言った", "”"),
}

PROHIBITED = frozenset("、。，．・：；？！‼⁇⁈⁉ー〜゠）］｝」』】〉》〕〗〙〛｠’”"
                       "ぁぃぅぇぉっゃゅょゎゕゖァィゥェォッャュョヮヵヶㇰㇱㇲㇳㇴㇵㇶㇷㇸㇹㇺㇻㇼㇽㇾㇿ々〻ゝゞヽヾ")


@pytest.mark.parametrize("name", sorted(CLASSES))
def test_no_wrapped_line_starts_with_a_prohibited_character(name):
    text, probe = CLASSES[name]
    assert probe in text and probe in PROHIBITED
    for characters in range(1, len(text) + 1):
        lines = wrap_text(text, available_inline=characters * 10, font_size=10, font_metrics=METRICS)
        assert "".join(lines) == text
        for line in lines[1:]:
            assert line[0] not in PROHIBITED, (name, characters, lines)


def test_the_reported_small_kana_note_keeps_the_kana_with_its_syllable():
    lines = wrap_text("設計レビュー", available_inline=40, font_size=10, font_metrics=METRICS)
    assert lines == ("設計レ", "ビュー")


def test_text_without_prohibited_characters_wraps_as_before():
    assert wrap_text("設計確認完了", available_inline=30, font_size=10, font_metrics=METRICS) == ("設計確", "認完了")
    assert wrap_text("plan the next release", available_inline=100, font_size=10, font_metrics=METRICS) == (
        "plan the", "next", "release")
