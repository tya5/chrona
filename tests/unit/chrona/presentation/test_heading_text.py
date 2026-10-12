"""Heading templates share the group-header brace grammar with their own closed placeholders (#991)."""
import pytest

from chrona.presentation.group_header_text import GroupHeaderTextError, parse_template
from chrona.presentation.heading_text import render_heading, validate_heading_template


def test_the_placeholders_are_project_as_of_and_calendar():
    assert validate_heading_template("{project} {asOf} {calendar}") == {"project", "asOf", "calendar"}


def test_a_fact_the_project_lacks_renders_as_empty_text_and_doubled_braces_are_literal():
    assert render_heading("{project} · {calendar} {{x}}", {"project": "H"}) == "H ·  {x}"


@pytest.mark.parametrize("source", ["{ordinal}", "{title}", "{nope}", "{project", "a } b"])
def test_any_other_brace_use_is_the_heading_error(source):
    with pytest.raises(GroupHeaderTextError) as caught:
        validate_heading_template(source)
    assert caught.value.code == "E_VIEW_HEADING_TEMPLATE"


def test_the_group_header_grammar_is_unchanged_by_the_shared_parser():
    assert parse_template("{ordinal} {title} {figure:f}").fields == {"ordinal", "title", "figure:f"}
    with pytest.raises(GroupHeaderTextError) as caught:
        parse_template("{project}")
    assert caught.value.code == "E_VIEW_GROUP_HEADER_TEMPLATE"


def test_closing_semantic_facts_does_not_reparse_project_text_as_count_syntax():
    from chrona.presentation.heading_text import close_heading
    from chrona.presentation.count_text import CountTextFormat
    facts = {"project": "Project {figure:not-a-reference}"}
    program = close_heading("{project}: {figure:n} {{kept}}", facts)
    facts["project"] = "changed"
    assert program.figure_ids == {"n"}
    assert program.bind({"n": 3}, {"n": CountTextFormat("english-words")}) == "Project {figure:not-a-reference}: three {kept}"


def test_heading_program_binds_typed_range_errors_at_the_exact_text_read():
    from chrona.presentation.heading_text import HeadingTextPrograms, close_heading
    from chrona.presentation.figure_text import FigureTextReadError
    from chrona.presentation.count_text import CountTextError, CountTextFormat
    programs = HeadingTextPrograms(close_heading("Title", {}), subtitle=close_heading("{figure:n}", {}))
    assert programs.figure_ids == {"n"}
    with pytest.raises(FigureTextReadError) as caught:
        programs.bind({"n": 100}, {"n": CountTextFormat("kanji")})
    assert caught.value.path == "/body/heading/subtitle"
    assert isinstance(caught.value.failure, CountTextError)
    assert caught.value.failure.supported_range == (0, 99)
    assert programs.bind({"n": 3}, {"n": CountTextFormat("kanji")}) == ("Title", "三", None)
