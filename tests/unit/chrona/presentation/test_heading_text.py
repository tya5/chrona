"""Heading templates share the group-header brace grammar with their own closed placeholders (#991)."""
import pytest

from chrona.presentation.group_header_text import GroupHeaderTextError, parse_template
from chrona.presentation.heading_text import render_heading, validate_heading_template


def test_the_placeholders_are_project_as_of_and_calendar():
    assert validate_heading_template("{project} {asOf} {calendar}") == {"project", "asOf", "calendar"}


def test_a_fact_the_project_lacks_renders_as_empty_text_and_doubled_braces_are_literal():
    assert render_heading("{project} · {calendar} {{x}}", {"project": "H"}) == "H ·  {x}"


@pytest.mark.parametrize("source", ["{ordinal}", "{title}", "{figure:x}", "{nope}", "{project", "a } b"])
def test_any_other_brace_use_is_the_heading_error(source):
    with pytest.raises(GroupHeaderTextError) as caught:
        validate_heading_template(source)
    assert caught.value.code == "E_VIEW_HEADING_TEMPLATE"


def test_the_group_header_grammar_is_unchanged_by_the_shared_parser():
    assert parse_template("{ordinal} {title} {figure:f}").fields == {"ordinal", "title", "figure:f"}
    with pytest.raises(GroupHeaderTextError) as caught:
        parse_template("{project}")
    assert caught.value.code == "E_VIEW_GROUP_HEADER_TEMPLATE"
