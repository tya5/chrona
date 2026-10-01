"""The hand-written emitter's contract: `safe_load(emitted)` equals the in-memory Project (#148, design 8)."""
from __future__ import annotations

import pytest

from chrona.resources import safe_load
from chrona.terse import compile_terse, emit_project
from chrona.terse.emitter import HEADER, _scalar
from tests.support.terse_plans import FIXTURES

YAML_WORDS = ["on", "no", "yes", "off", "true", "false", "null", "y", "n", "On", "NO", "Yes", "OFF", "True", "FALSE", "Null", "~"]


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.chrona")), ids=lambda path: path.stem)
def test_round_trip_on_every_fixture(path):
    project = compile_terse(path.read_bytes().decode("utf-8")).project
    assert project is not None
    assert safe_load(emit_project(project)) == project


@pytest.mark.parametrize("word", ["on", "no", "yes", "off", "true", "false", "null", "y", "n"])
def test_names_that_yaml_reads_as_booleans_or_none_stay_string_keys(word):
    project = compile_terse(f"project {word}\ncalendar {word} mon-fri\n{word} task 1wd calendar {word}\nb task 1d after {word}\n").project
    text = emit_project(project)
    assert f"'{word}':" in text
    loaded = safe_load(text)
    assert loaded == project
    assert list(loaded["objects"]) == [word, "b"] and loaded["project"]["id"] == word
    assert loaded["relations"][0]["from"]["object"] == word and isinstance(loaded["relations"][0]["from"]["object"], str)


@pytest.mark.parametrize("value", YAML_WORDS + [
    "", " ", "a ", " a", "#", "# x", "a: b", "a #b", "- a", "'", "''", '"', "\\", "a'b", "1", "1.5", "0x1f", "1e3", "2027-03-05", "12:30",
    "*a", "&a", "!a", "%a", "@a", "`a`", "{a}", "[a]", "a, b", "café", "仕様", "\U0001f680", "a b", "\u0080", "\u0085",
    " ", " ", "﻿", "￿", "￾", "\u007f", "<<", "=", "|", ">", "timeline/v0.7", "5wd", "-2d", "0d", "1w",
])
def test_every_string_value_round_trips(value):
    emitted = f"title: {_scalar(value)}\n"
    assert safe_load(emitted) == {"title": value}
    assert safe_load(f"{_scalar(value)}: 1\n") == {value: 1}


def test_dates_are_always_quoted_so_they_load_as_strings():
    project = compile_terse("project p\na task 2026-10-01..2026-10-09\n").project
    text = emit_project(project)
    assert "start: '2026-10-01'" in text
    assert safe_load(text)["objects"]["a"]["schedule"]["start"] == "2026-10-01"


def test_plain_scalars_follow_the_design_rule():
    assert _scalar("Preliminary design review") == "Preliminary design review"
    assert _scalar("HALCYON-1") == "HALCYON-1"
    assert _scalar("a_b-c d") == "a_b-c d"
    assert _scalar("trailing ") == "'trailing '"
    assert _scalar("it's") == "'it''s'"
    assert _scalar("1wd") == "1wd" and _scalar("-2d") == "-2d"  # lags and amounts are never YAML numbers


def test_output_is_lf_only_with_the_fixed_header_and_final_newline():
    text = emit_project(compile_terse("project p\na task 1d\n").project)
    assert text.splitlines()[0] == HEADER and text.endswith("\n") and "\r" not in text and not text.endswith("\n\n")


def test_empty_collections_are_never_emitted():
    text = emit_project(compile_terse("project p\n").project)
    assert "objects" not in text and "relations" not in text and "calendars" not in text
    assert safe_load(text) == {"version": "timeline/v0.7", "project": {"id": "p"}}


def test_an_object_named_like_a_structural_key_stays_a_block():
    project = compile_terse("project p\nschedule task 1d\ntype task 1d\nparent group\n  title task 1d\n").project
    assert safe_load(emit_project(project)) == project
