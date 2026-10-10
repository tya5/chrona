"""The nearest-name rule shared by the terse compiler and Project validation (#1303)."""
from __future__ import annotations

from collections.abc import Sequence


def distance(a: str, b: str) -> int:
    """Optimal string alignment distance (Levenshtein plus adjacent transposition); hand-written, no dependency."""
    rows = [list(range(len(b) + 1))]
    for i, ca in enumerate(a, 1):
        row = [i]
        for j, cb in enumerate(b, 1):
            cost = min(rows[i - 1][j] + 1, row[j - 1] + 1, rows[i - 1][j - 1] + (ca != cb))
            if i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                cost = min(cost, rows[i - 2][j - 2] + 1)
            row.append(cost)
        rows.append(row)
    return rows[-1][-1]


def nearest(word: str, candidates: Sequence[str]) -> str | None:
    """The closest candidate, ties broken by declaration order; None when nothing is close."""
    best: tuple[int, int, str] | None = None
    lowered = word.lower()
    for order, candidate in enumerate(candidates):
        d = distance(lowered, candidate.lower())
        if best is None or (d, order) < (best[0], best[1]):
            best = (d, order, candidate)
    if best is None or best[0] > max(1, len(word) // 3):
        return None
    return best[2]


def unknown_id_message(role: str, word: str, known: Sequence[str]) -> str:
    """`Unknown <role> 'word'`, with `; did you mean 'x'?` when a known id is near."""
    close = nearest(word, tuple(known))
    return f"Unknown {role} '{word}'" + (f"; did you mean '{close}'?" if close else "")
