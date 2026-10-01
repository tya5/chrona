"""Seeded mutation fuzz over the fixtures (design 13.5): positions, no partial Project, round trip, byte stability.

There is no `hypothesis` in the repository, so the fuzz is a deterministic `random.Random(148)` walk over
character and token mutations of every committed plan.
"""
from __future__ import annotations

import random

from chrona.core.validation import validate_project
from chrona.resources import safe_load
from chrona.terse.lexer import split_lines
from chrona.usecases.terse_compile import compile_plan
from tests.support.terse_plans import FIXTURES

CASES = 4000
POOL = ['"', ",", "#", ".", "..", " ", "  ", "\t", "\r", "\x00", "\x7f", "-", "+", "+1wd", "-2d", "5d", "wd", "0", "9", "after", "task",
        "gate", "group", "calendar", "from", "until", "except", "work", "start", ">=", "<=", "end", "at", "in", "terse", "project",
        "2026-10-01", "2026-02-30", "mon-fri", "é", " ", "あ", "\U0001f680", "\u0085", " ", "﻿", "\n", "\\", "\\\""]


def _sources() -> list[str]:
    valid = [path.read_bytes().decode("utf-8") for path in sorted(FIXTURES.glob("*.chrona"))]
    broken = [path.read_bytes().decode("utf-8") for path in sorted((FIXTURES / "errors").glob("*.chrona"))
              if path.name != "too-many-errors.chrona"]
    return valid * 4 + broken  # mostly valid plans, so that mutations reach the deeper rules


def _mutate(text: str, rng: random.Random) -> str:
    for _ in range(rng.choice((1, 1, 1, 2, 3))):
        operation = rng.randrange(12)
        if not text:
            return rng.choice(POOL)
        index = rng.randrange(len(text) + 1)
        if operation == 0:
            text = text[:index] + text[index + 1:]
        elif operation == 1:
            text = text[:index] + rng.choice(POOL) + text[index:]
        elif operation == 2 and index + 1 < len(text):
            text = text[:index] + text[index + 1] + text[index] + text[index + 2:]
        elif operation == 3:
            text = text[:index]
        elif operation == 4:
            tokens = text.split(" ")
            del tokens[rng.randrange(len(tokens))]
            text = " ".join(tokens)
        elif operation == 5:
            tokens = text.split(" ")
            a, b = rng.randrange(len(tokens)), rng.randrange(len(tokens))
            tokens[a], tokens[b] = tokens[b], tokens[a]
            text = " ".join(tokens)
        elif operation == 6:
            lines = text.split("\n")
            del lines[rng.randrange(len(lines))]
            text = "\n".join(lines)
        elif operation == 7:
            lines = text.split("\n")
            k = rng.randrange(len(lines))
            lines.insert(k, lines[k])
            text = "\n".join(lines)
        elif operation == 8:
            lines = text.split("\n")
            k = rng.randrange(len(lines))
            lines[k] = " " * rng.choice((1, 2, 3, 4, 6)) + lines[k]
            text = "\n".join(lines)
        elif operation == 9:
            tokens = text.split(" ")
            tokens[rng.randrange(len(tokens))] = rng.choice(POOL)
            text = " ".join(tokens)
        elif operation == 10:
            text = text[:index] + text[index:index + rng.randrange(1, 6)] * 2 + text[index + rng.randrange(1, 6):]
        else:
            lines = text.split("\n")
            a, b = rng.randrange(len(lines)), rng.randrange(len(lines))
            lines[a], lines[b] = lines[b], lines[a]
            text = "\n".join(lines)
    return text


def _check(text: str) -> bool:
    data = text.encode("utf-8")
    result = compile_plan(data, "fuzz.chrona")           # (a) never raises
    again = compile_plan(data, "fuzz.chrona")
    assert [item.as_dict() for item in again.diagnostics] == [item.as_dict() for item in result.diagnostics]
    assert again.yaml == result.yaml                       # (e) a second compile is byte-equal
    lines = split_lines(text)
    if result.diagnostics:                                 # (b) diagnostics imply no Project and no YAML
        assert result.project is None and result.yaml is None, text
        assert len(result.diagnostics) <= 51
        for item in result.diagnostics:                    # (c) every diagnostic is positioned inside the text
            assert item.id != "E_TERSE_COMPILER_DEFECT", (item.message, text)
            assert item.range is not None and item.message and item.source == "fuzz.chrona", (item, text)
            where = item.range
            assert where.end_line == where.line, (item, text)
            assert 1 <= where.line <= len(lines) + 1, (item, text)
            assert 1 <= where.column <= len(lines[where.line - 1] if where.line <= len(lines) else "") + 1, (item, text)
            assert where.end_column > where.column, (item, text)
        return False
    assert result.project is not None and result.yaml is not None
    assert validate_project(result.project) == []          # (d) accepted implies Core-valid
    assert safe_load(result.yaml) == result.project, text  # the emitter round-trip contract
    return True


def test_seeded_mutation_fuzz_holds_every_property():
    sources = _sources()
    rng = random.Random(148)
    accepted = 0
    for number in range(CASES):
        text = _mutate(rng.choice(sources), rng)
        accepted += _check(text)
    assert accepted > 100, "the fuzz must exercise accepted plans as well as rejected ones"


def test_the_unmutated_fixtures_pass_the_same_checks():
    for path in sorted(FIXTURES.glob("*.chrona")):
        assert _check(path.read_bytes().decode("utf-8")), path.name


def test_random_byte_soup_never_raises_and_never_emits_a_partial_project():
    rng = random.Random(1481)
    for _ in range(500):
        data = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 120)))
        result = compile_plan(data)
        assert (result.yaml is None) == bool(result.diagnostics) and (result.project is None) == (result.yaml is None)
        for item in result.diagnostics:
            assert item.range is not None and item.range.line >= 1 and item.range.column >= 1


def test_random_token_soup_is_rejected_or_valid():
    rng = random.Random(1482)
    words = [word for word in POOL if word not in ("\n",)] + ["a", "b", "calendar", "x1"]
    for _ in range(1500):
        lines = ["project p"] + [" ".join(rng.choice(words) for _ in range(rng.randrange(1, 9))) for _ in range(rng.randrange(1, 6))]
        _check("\n".join(lines) + "\n")
