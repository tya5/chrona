"""Count text uses bounded names while preserving existing ordinal semantics."""
from dataclasses import FrozenInstanceError

import pytest

from chrona.presentation.count_text import CountTextError, CountTextFormat, format_count
from chrona.presentation.group_header_text import GroupHeaderTextError, format_ordinal


@pytest.mark.parametrize("value,expected", [
    (0, "zero"), (1, "one"), (19, "nineteen"), (20, "twenty"), (26, "twenty-six"),
    (100, "one hundred"), (101, "one hundred one"), (999, "nine hundred ninety-nine"),
    (1000, "one thousand"), (1001, "one thousand one"),
    (1026, "one thousand twenty-six"), (1000000, "one million"),
    (10**18, "one quintillion"),
    (10**21 - 1, " ".join("nine hundred ninety-nine" + (" " + scale if scale else "")
                           for scale in ("quintillion", "quadrillion", "trillion",
                                         "billion", "million", "thousand", ""))),
])
def test_english_has_closed_names_no_comma_or_and(value, expected):
    assert format_count(value, CountTextFormat("english-words")) == expected


def test_padding_never_truncates_and_capitalization_is_declared():
    assert format_count(3, CountTextFormat(minimum_digits=2)) == "03"
    assert format_count(123, CountTextFormat(minimum_digits=2)) == "123"
    assert format_count(0, CountTextFormat(minimum_digits=80)) == "0" * 80
    assert format_count(26, CountTextFormat("english-words", capitalize=True)) == "Twenty-six"
    with pytest.raises(FrozenInstanceError):
        CountTextFormat().form = "kanji"


@pytest.mark.parametrize("form", ("kanji", "kanji-formal"))
def test_existing_ordinal_names_are_shared_without_expanding_ordinal_range(form):
    assert format_count(0, CountTextFormat(form)) == "〇"
    for value in range(1, 100):
        assert format_count(value, CountTextFormat(form)) == format_ordinal(value, form, group_count=99)
    with pytest.raises(GroupHeaderTextError, match="E_REVIEW_GROUP_ORDINAL_RANGE"):
        format_ordinal(0, form, group_count=99)


@pytest.mark.parametrize("form,value,high", [
    ("kanji", 100, 99), ("kanji-formal", 100, 99), ("english-words", 10**21, 10**21 - 1),
])
def test_unavailable_names_are_typed_range_errors_never_digits(form, value, high):
    with pytest.raises(CountTextError) as caught:
        format_count(value, CountTextFormat(form))
    assert (caught.value.code, caught.value.value, caught.value.form,
            caught.value.supported_range) == ("E_VIEW_FIGURE_FORMAT_RANGE", value, form, (0, high))


@pytest.mark.parametrize("value", (-1, True, 1.0, "1", None))
def test_count_values_are_neutral_nonnegative_integers(value):
    with pytest.raises(CountTextError, match="E_VIEW_FIGURE_FORMAT_INVALID"):
        format_count(value)


@pytest.mark.parametrize("options", [
    {"form": "roman"}, {"minimum_digits": 0}, {"minimum_digits": 81},
    {"minimum_digits": True}, {"capitalize": "yes"},
    {"form": "kanji", "minimum_digits": 2}, {"form": "digits", "capitalize": True},
])
def test_closed_options_refuse_dead_or_malformed_declarations(options):
    with pytest.raises(CountTextError, match="E_VIEW_FIGURE_FORMAT_INVALID"):
        CountTextFormat(**options)


def test_closed_program_binds_formats_without_eagerly_reading_unused_names():
    from chrona.presentation.figure_text import compile_figure_text
    program = compile_figure_text("{{items}} {figure:items} in {figure:groups} sections")
    assert program.figure_ids == {"items", "groups"}
    values = {"items": 26, "groups": 6, "unused": 100}
    formats = {"items": CountTextFormat("english-words", capitalize=True),
               "groups": CountTextFormat("english-words"), "unused": CountTextFormat("kanji")}
    assert program.bind(values, formats) == "{items} Twenty-six in six sections"
    assert values["unused"] == 100
    with pytest.raises(FrozenInstanceError):
        program.template = None


def test_missing_closed_program_fact_is_not_a_blank_or_zero():
    from chrona.presentation.figure_text import FigureTextError, compile_figure_text
    program = compile_figure_text("{figure:notes}")
    with pytest.raises(FigureTextError, match="E_VIEW_FIGURE_UNKNOWN"):
        program.bind({})


def test_core_late_count_bundle_accepts_only_supplied_facts():
    from dataclasses import replace
    from chrona.core.figures import FigureCounts, FigureSpec, resolve_figures
    counts = FigureCounts(3, 0, 0, 0, 3, None, 0, 0, 0, groups=2)
    specs = (FigureSpec("groups", "count", source="groups", path="/groups"),
             FigureSpec("notes", "count", source="placedNotes", path="/notes"))
    kwargs = dict(as_of=None, placements={}, periods=(), calendars={}, default_calendar=None)
    pending = resolve_figures(specs, counts=counts, **kwargs)
    assert pending.values == {"groups": 2}
    assert [(item.id, item.path) for item in pending.diagnostics] == [
        ("E_FIGURE_COUNT_UNAVAILABLE", "/notes/source")]
    completed = resolve_figures(specs, counts=replace(counts, placed_notes=0), **kwargs)
    assert completed.values == {"groups": 2, "notes": 0} and not completed.diagnostics
