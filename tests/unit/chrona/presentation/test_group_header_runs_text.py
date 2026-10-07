"""Role-marked placeholders of a group-header template (#1192): the grammar, the runs and backwards compatibility."""
from __future__ import annotations

import pytest

from chrona.presentation.group_header_text import (
    GroupHeaderTextError, HeaderRun, compose_group_header_runs, compose_group_headers, parse_template, render_header,
    render_header_runs, template_roles,
)
from chrona.presentation.heading_text import validate_heading_template
from chrona.presentation.model.theme_role_consumers import unread_roles

EXISTING = ("{ordinal} {title}", "ACT {ordinal} · {title} / {secondary}", "{{{title}}} {{x}}", "{figure:a-b.c}", "plain",
            "{figure:since}days", "{ordinal}{title}")


@pytest.mark.parametrize("source", EXISTING)
def test_an_existing_template_parses_identically_with_or_without_role_support(source):
    plain = parse_template(source)
    allowing = parse_template(source, allow_roles=True)

    assert allowing == plain
    assert plain.marks == () and plain.roles == frozenset()


def test_a_marked_placeholder_carries_its_role_and_keeps_its_field():
    template = parse_template("{ordinal|group-ordinal} {title} {secondary|gloss_2}", allow_roles=True)

    assert template.fields == {"ordinal", "title", "secondary"}
    assert template.roles == {"group-ordinal", "gloss_2"}
    assert template.marks == ("group-ordinal", None, None, None, "gloss_2")
    assert template.parts == (("field", "ordinal"), ("text", " "), ("field", "title"), ("text", " "),
                              ("field", "secondary"))


def test_a_figure_can_be_marked():
    template = parse_template("{figure:launch-countdown|gloss}", allow_roles=True)

    assert template.figure_ids == {"launch-countdown"} and template.roles == {"gloss"}


@pytest.mark.parametrize("source", ["{ordinal|}", "{ordinal|1x}", "{ordinal|a b}", "{ordinal|a|b}", "{|role}",
                                    "{nope|role}", "{ordinal|role", "{ordinal |role}", "{ordinal| role}"])
def test_a_malformed_mark_is_the_template_error(source):
    with pytest.raises(GroupHeaderTextError) as raised:
        parse_template(source, allow_roles=True)

    assert raised.value.code == "E_VIEW_GROUP_HEADER_TEMPLATE"


def test_a_mark_is_refused_where_roles_are_not_allowed():
    for source in ("{ordinal|role}", "{title|role}"):
        with pytest.raises(GroupHeaderTextError):
            parse_template(source)
    with pytest.raises(GroupHeaderTextError) as raised:
        validate_heading_template("{project|role}")
    assert raised.value.code == "E_VIEW_HEADING_TEMPLATE"


def test_literal_text_is_never_marked_and_the_pipe_stays_literal():
    template = parse_template("a|b {title|role} c", allow_roles=True)

    assert template.parts[0] == ("text", "a|b ") and template.marks == (None, "role", None)


def test_the_runs_merge_adjacent_parts_of_one_role_and_join_to_the_plain_text():
    template = parse_template("{ordinal|n} {title} · {secondary|g}", allow_roles=True)
    facts = dict(ordinal="01", title="Bus", secondary="SPACECRAFT")

    runs = render_header_runs(template, **facts)

    assert runs == (HeaderRun("01", "n"), HeaderRun(" Bus · ", None), HeaderRun("SPACECRAFT", "g"))
    assert "".join(run.text for run in runs) == render_header(template, **facts) == "01 Bus · SPACECRAFT"


def test_two_neighbouring_marks_of_one_role_are_one_run_and_an_empty_value_makes_no_run():
    template = parse_template("{ordinal|n}{title|n}{secondary|g}", allow_roles=True)

    runs = render_header_runs(template, ordinal="1", title="", secondary="x")

    assert runs == (HeaderRun("1", "n"), HeaderRun("x", "g"))


def test_compose_gives_runs_only_for_a_marked_template_and_the_same_text_either_way():
    common = dict(group_ids=("a", "b"), titles={"a": "Alpha", "b": "Beta"}, secondaries=None, ordinal="roman",
                  figures=None)

    marked = compose_group_header_runs(text="{ordinal|n} {title}", first=None, **common)
    plain_text = compose_group_headers(text="{ordinal|n} {title}", first=None, **common)
    unmarked = compose_group_header_runs(text="{ordinal} {title}", first=None, **common)

    assert unmarked == ()
    assert plain_text == (("a", "I Alpha"), ("b", "II Beta"))
    assert marked == (("a", (HeaderRun("I", "n"), HeaderRun(" Alpha", None))),
                      ("b", (HeaderRun("II", "n"), HeaderRun(" Beta", None))))


def test_the_first_group_variant_may_be_marked_while_the_rest_are_not():
    result = compose_group_header_runs(group_ids=("a", "b"), titles={}, secondaries=None, text="{title}",
                                       first="{ordinal|n} {title}", ordinal="arabic")

    assert [group for group, _ in result] == ["a"]


def test_roles_are_found_leniently_for_the_consumer_check():
    assert template_roles("{ordinal|group-ordinal} {title} {figure:f|gloss} {x|1}") == {"group-ordinal", "gloss"}
    assert template_roles("{ordinal} {title}") == frozenset()
    assert template_roles("no braces | here") == frozenset()


def test_a_role_a_header_template_marks_has_a_consumer_for_the_unread_role_check():
    body = {"roles": {"group-ordinal": {"fontSize": "s"}, "group-gloss": {"fontSize": "s"}, "orphan": {"fontSize": "s"}},
            "colorBindings": {}}
    view = {"body": {"grouping": {"header": {"text": "{ordinal|group-ordinal} {title}",
                                             "first": "{figure:f|group-gloss}"}}}}

    assert unread_roles(body, [view]) == {"orphan"}
    assert unread_roles(body, []) == {"group-ordinal", "group-gloss", "orphan"}
