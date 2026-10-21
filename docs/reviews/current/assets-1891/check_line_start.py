"""Wrap synthetic Japanese text at every width and list any line that starts with a prohibited character (#1891 row 2).

Run: python docs/reviews/current/assets-1891/check_line_start.py   (PYTHONPATH=<worktree>/src:<worktree>)
Every character of the test's JIS X 4051 line-start-prohibited set is placed after a plain kanji run, once as the
probe in the middle of the text and once directly after the first character.
"""
from types import SimpleNamespace

from chrona.presentation.layout.text import wrap_text
from tests.unit.chrona.presentation.layout.test_line_start_prohibition import PROHIBITED

METRICS = SimpleNamespace(width=lambda text, size: len(text) * size)
bad = checked = 0
for probe in sorted(PROHIBITED):
    for text in (f"設計確認{probe}完了報告", f"設{probe}計確認完了"):
        for characters in range(1, len(text) + 1):
            lines = wrap_text(text, available_inline=characters * 10, font_size=10, font_metrics=METRICS)
            assert "".join(lines) == text
            checked += 1
            if any(line[0] in PROHIBITED for line in lines[1:]):
                bad += 1
                print("STARTS WITH PROHIBITED:", probe, characters, lines)
print(f"prohibited characters: {len(PROHIBITED)}; wraps checked: {checked}; lines starting with a prohibited character: {bad}")
print("the reported note:", wrap_text("設計レビュー", available_inline=40, font_size=10, font_metrics=METRICS))
