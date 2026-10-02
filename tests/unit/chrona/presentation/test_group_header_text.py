"""#583 I583-1: the group-header template grammar, ordinal forms and composition (pure, no Project)."""
from __future__ import annotations

import pytest

from chrona.presentation.group_header_text import (
    GroupHeaderTextError, compose_group_headers, format_ordinal, parse_template, render_header)


@pytest.mark.parametrize("form,position,count,expected", [
    ("arabic", 1, 3, "1"), ("arabic", 12, 12, "12"), ("arabic", 1000, 1000, "1000"),
    ("zero-padded", 1, 3, "01"), ("zero-padded", 9, 9, "09"), ("zero-padded", 10, 10, "10"),
    ("zero-padded", 7, 100, "007"), ("zero-padded", 100, 100, "100"),
    ("roman", 1, 3, "I"), ("roman", 4, 6, "IV"), ("roman", 6, 6, "VI"), ("roman", 9, 9, "IX"),
    ("roman", 14, 20, "XIV"), ("roman", 1994, 2000, "MCMXCIV"), ("roman", 3999, 3999, "MMMCMXCIX"),
    ("kanji", 1, 6, "一"), ("kanji", 6, 6, "六"), ("kanji", 10, 10, "十"), ("kanji", 11, 11, "十一"),
    ("kanji", 20, 20, "二十"), ("kanji", 23, 23, "二十三"), ("kanji", 99, 99, "九十九"),
    ("kanji-formal", 1, 6, "壱"), ("kanji-formal", 2, 6, "弐"), ("kanji-formal", 3, 6, "参"),
    ("kanji-formal", 4, 6, "肆"), ("kanji-formal", 5, 6, "伍"), ("kanji-formal", 6, 6, "陸"),
    ("kanji-formal", 10, 10, "拾"), ("kanji-formal", 11, 11, "拾壱"), ("kanji-formal", 20, 20, "弐拾"),
    ("kanji-formal", 99, 99, "玖拾玖"),
])
def test_each_ordinal_form_at_its_values(form, position, count, expected):
    assert format_ordinal(position, form, group_count=count) == expected


@pytest.mark.parametrize("form,position", [("roman", 0), ("roman", 4000), ("kanji", 0), ("kanji", 100),
                                           ("kanji-formal", 100), ("arabic", 0), ("zero-padded", 0)])
def test_a_position_outside_the_range_of_its_form_is_an_error(form, position):
    with pytest.raises(GroupHeaderTextError) as failure:
        format_ordinal(position, form, group_count=max(position, 1))
    assert failure.value.code == "E_REVIEW_GROUP_ORDINAL_RANGE"


def test_an_unknown_form_is_an_error():
    with pytest.raises(GroupHeaderTextError):
        format_ordinal(1, "hex", group_count=1)


def test_the_template_has_literal_text_and_three_closed_placeholders():
    template = parse_template("ACT {ordinal} · {title} / {secondary}")
    assert template.fields == {"ordinal", "title", "secondary"}
    assert render_header(template, ordinal="II", title="Bus", secondary="機体") == "ACT II · Bus / 機体"


def test_doubled_braces_are_literal():
    assert render_header(parse_template("{{{title}}} {{x}}"), ordinal="", title="T", secondary=None) == "{T} {x}"


@pytest.mark.parametrize("source", ["{", "}", "{owner}", "{title", "{ title }", "a } b", "{}", "{{}", "{title}}"])
def test_any_other_brace_use_is_rejected(source):
    with pytest.raises(GroupHeaderTextError) as failure:
        parse_template(source)
    assert failure.value.code == "E_VIEW_GROUP_HEADER_TEMPLATE"


def test_a_secondary_placeholder_without_a_value_is_an_error():
    with pytest.raises(GroupHeaderTextError) as failure:
        render_header(parse_template("{secondary}"), ordinal="", title="", secondary=None)
    assert failure.value.code == "E_REVIEW_GROUP_HEADER_SECONDARY"


def test_composition_numbers_in_order_and_varies_only_the_first_group():
    result = compose_group_headers(
        group_ids=("a", "b", "c"), titles={"a": "Alpha", "b": "Beta", "c": "Gamma"}, secondaries=None,
        text="{ordinal}. Then {title}", first="{ordinal}. First {title}", ordinal="roman")
    assert result == (("a", "I. First Alpha"), ("b", "II. Then Beta"), ("c", "III. Then Gamma"))


def test_the_first_template_alone_may_use_the_secondary():
    result = compose_group_headers(
        group_ids=("a", "b"), titles={"a": "A", "b": "B"}, secondaries={"a": "x", "b": ""},
        text="{title}", first="{title} {secondary}", ordinal="arabic")
    assert result == (("a", "A x"), ("b", "B"))


def test_composition_rejects_an_empty_secondary_and_names_the_group():
    with pytest.raises(GroupHeaderTextError) as failure:
        compose_group_headers(group_ids=("a", "b"), titles={}, secondaries={"a": "x", "b": ""},
                              text="{title} {secondary}", first=None, ordinal="arabic")
    assert failure.value.code == "E_REVIEW_GROUP_HEADER_SECONDARY" and "b" in failure.value.detail


def test_zero_padding_width_follows_the_group_count():
    result = compose_group_headers(group_ids=tuple(f"g{i}" for i in range(1, 101)), titles={}, secondaries=None,
                                   text="{ordinal}", first=None, ordinal="zero-padded")
    assert result[0][1] == "001" and result[99][1] == "100"
