"""#584: the annotation kind header template grammar and composition (pure, no Project or Theme)."""
from __future__ import annotations

import pytest

from chrona.presentation.annotation_kind_text import (
    AnnotationKindTextError, header_lines, kind_header, parse_title,
)


def test_a_title_is_literal_text_and_the_three_closed_placeholders():
    assert parse_title("{label} · {subject}") == (("field", "label"), ("text", " · "), ("field", "subject"))
    assert parse_title("plain") == (("text", "plain"),)
    assert parse_title("{secondary}/{label}") == (("field", "secondary"), ("text", "/"), ("field", "label"))


def test_doubled_braces_are_literal_braces():
    assert parse_title("{{{label}}}") == (("text", "{"), ("field", "label"), ("text", "}"))


@pytest.mark.parametrize("source", ["{unknown}", "{label", "{}", "{label }", "}", "a } b", "{ label}", "{{label}"])
def test_every_other_brace_use_is_the_template_error(source):
    with pytest.raises(AnnotationKindTextError) as failure:
        parse_title(source)
    assert failure.value.code == "E_THEME_ANNOTATION_KIND_TEMPLATE"


def test_the_title_defaults_to_the_label():
    header = kind_header("risk", {"label": "RISK"})
    assert header.title == "{label}"
    assert header_lines(header, subject="Task 1") == ("RISK",)


def test_the_secondary_label_is_a_second_line_unless_the_title_shows_it():
    declared = {"label": "警告", "secondary": "WARNING"}
    assert header_lines(kind_header("risk", declared), subject="x") == ("警告", "WARNING")
    inline = kind_header("risk", {**declared, "title": "{label} {secondary}"})
    assert inline.inline_secondary
    assert header_lines(inline, subject="x") == ("警告 WARNING",)


def test_the_subject_is_the_anchored_object_title():
    header = kind_header("risk", {"label": "RISK", "title": "{label} · {subject}"})
    assert header_lines(header, subject="payload-tvac") == ("RISK · payload-tvac",)


@pytest.mark.parametrize("declaration", [
    {}, {"label": ""}, {"label": "   "}, {"label": 3},
    {"label": "A", "secondary": ""}, {"label": "A", "secondary": 4},
    {"label": "A", "title": ""}, {"label": "A", "title": 7},
    {"label": "A", "title": "{secondary}"},  # uses {secondary} without a secondary label
    {"label": "A", "title": "{nope}"},
])
def test_an_invalid_declaration_is_the_template_error(declaration):
    with pytest.raises(AnnotationKindTextError) as failure:
        kind_header("risk", declaration)
    assert failure.value.code == "E_THEME_ANNOTATION_KIND_TEMPLATE"
    assert failure.value.detail
