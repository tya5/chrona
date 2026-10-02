"""#586 I586-3: the `{figure:<id>}` placeholder of the group-header template (pure, no Project)."""
from __future__ import annotations

import pytest

from chrona.presentation.group_header_text import (
    GroupHeaderTextError, compose_group_headers, parse_template, render_header)


def test_a_figure_placeholder_names_a_figure_and_renders_its_signed_integer():
    template = parse_template("LANE {ordinal} · {figure:launch-countdown} DAYS · {figure:since}")
    assert template.fields == {"ordinal", "figure:launch-countdown", "figure:since"}
    assert template.figure_ids == {"launch-countdown", "since"}
    assert render_header(template, ordinal="2", title="", secondary=None,
                         figures={"launch-countdown": 63, "since": -3}) == "LANE 2 · 63 DAYS · -3"


def test_a_template_without_a_figure_placeholder_shows_none():
    assert parse_template("{title}").figure_ids == frozenset()


def test_a_figure_with_zero_days_is_rendered_not_blanked():
    assert render_header(parse_template("{figure:f}"), ordinal="", title="", secondary=None, figures={"f": 0}) == "0"


@pytest.mark.parametrize("source", ["{figure:}", "{figure}", "{figure:x", "{Figure:x}", "{figure :x}"])
def test_a_malformed_figure_placeholder_is_rejected(source):
    with pytest.raises(GroupHeaderTextError) as failure:
        parse_template(source)
    assert failure.value.code == "E_VIEW_GROUP_HEADER_TEMPLATE"


def test_literal_braces_around_a_figure_stay_literal():
    assert render_header(parse_template("{{{figure:f}}}"), ordinal="", title="", secondary=None, figures={"f": 5}) == "{5}"


@pytest.mark.parametrize("figures", [None, {}, {"other": 1}])
def test_a_figure_that_was_not_resolved_is_an_error_never_a_blank(figures):
    with pytest.raises(GroupHeaderTextError) as failure:
        render_header(parse_template("{figure:f}"), ordinal="", title="", secondary=None, figures=figures)
    assert failure.value.code == "E_VIEW_GROUP_HEADER_TEMPLATE" and "'f'" in failure.value.detail


def test_composition_passes_the_figures_to_every_group_and_to_the_first_template():
    result = compose_group_headers(group_ids=("a", "b"), titles={"a": "A", "b": "B"}, secondaries=None,
                                   text="{title} {figure:f}", first="First {figure:g}", ordinal="arabic",
                                   figures={"f": 7, "g": -1})
    assert result == (("a", "First -1"), ("b", "B 7"))
