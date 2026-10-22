"""Candidate failure attribution is detector-owned, not an error-code whitelist (#1346)."""
from dataclasses import replace
from decimal import Decimal as D

import pytest

from chrona.presentation.count_text import CountTextError, CountTextFormat
from chrona.presentation.figure_text import FigureTextReadError, compile_figure_text
from chrona.presentation.heading_text import HeadingTextPrograms, close_heading
from chrona.presentation.layout import engine
from chrona.presentation.layout.model import CountDependentHeadingFitError, LayoutError, Measurement, ResolvedLayoutProfile
from chrona.presentation.layout.sources import SourceInput, SourceTextRun
from chrona.presentation.layout.surface_source_inputs import bind_heading_dependencies
from tests.unit.chrona.presentation.layout.test_bounded_heading import measure


@pytest.mark.parametrize("failed", ["late", "fixed"])
def test_name_range_records_exact_read_identity_not_the_programs_combined_references(failed):
    program = compile_figure_text("{figure:fixed} {figure:late}")
    values = {"fixed": 100 if failed == "fixed" else 3, "late": 100 if failed == "late" else 3}
    with pytest.raises(CountTextError) as caught:
        program.bind(values, {name: CountTextFormat("kanji") for name in values})
    assert caught.value.figure_id == failed
    assert caught.value.supported_range == (0, 99)
    heading = HeadingTextPrograms(program)
    with pytest.raises(FigureTextReadError) as read:
        heading.bind(values, {name: CountTextFormat("kanji") for name in values})
    assert read.value.failure.figure_id == failed
    assert read.value.path == "/body/heading/title"


def test_closed_part_dependencies_do_not_reparse_project_text_or_contaminate_other_parts():
    programs = HeadingTextPrograms(close_heading("{project}", {"project": "{figure:fake}"}),
                                   subtitle=close_heading("{figure:notes} notes", {}))
    original = {
        "title": SourceInput(runs=(SourceTextRun("{figure:fake}", "heading", "title"),
                                   SourceTextRun("three notes", "subtitle", "subtitle")), text_wrap="allow"),
        "heading.subtitle": SourceInput(runs=(SourceTextRun("three notes", "subtitle", "heading.subtitle"),),
                                        text_wrap="allow"),
    }
    bound = bind_heading_dependencies(original, programs)
    assert bound["title"].runs[0].figure_dependencies == frozenset()
    assert bound["title"].runs[1].figure_dependencies == {"notes"}
    assert bound["heading.subtitle"].runs[0].figure_dependencies == {"notes"}
    assert all(not r.figure_dependencies for r in original["title"].runs)


def _copy(*runs, minimum=None):
    return SourceInput(runs=tuple(runs), text_wrap="allow", min_inline=minimum)


@pytest.mark.parametrize("dependent", [True, False])
def test_measured_text_detector_issues_typed_failure_only_for_its_actual_dependent_run(dependent):
    refs = frozenset({"notes"}) if dependent else frozenset()
    value = _copy(SourceTextRun("three notes", "heading", "title", figure_dependencies=refs))
    with pytest.raises(LayoutError) as caught:
        measure(value, budget=D(1))
    assert isinstance(caught.value, CountDependentHeadingFitError) is dependent
    assert caught.value.path == "/sources/title"
    if dependent:
        assert caught.value.figure_ids == {"notes"}


def test_nonpositive_authored_budget_is_not_a_count_fit_rejection():
    value = _copy(SourceTextRun("three notes", "heading", "title", figure_dependencies=frozenset({"notes"})))
    with pytest.raises(LayoutError) as caught:
        measure(value, budget=D(0))
    assert type(caught.value) is LayoutError


def test_only_driving_intrinsic_text_minima_carry_dependencies():
    variable = SourceTextRun("three notes", "heading", "title", figure_dependencies=frozenset({"notes"}))
    assert measure(_copy(variable)).measurements["title"].figure_dependencies == {"notes"}
    # An equally large constant is a fixed floor even if a peer reads a count.
    constant = replace(variable, figure_dependencies=frozenset(), source_ref="kicker")
    assert measure(_copy(variable, constant)).measurements["title"].figure_dependencies == frozenset()
    assert measure(_copy(variable, minimum=D(2))).measurements["title"].figure_dependencies == frozenset()


def _budgeted(spec, *, kind="heading"):
    profile = ResolvedLayoutProfile("p", "hash", {}, {}, ())
    measurement = Measurement(D(8), D(16), D(32), D(4), D(8), D(16), figure_dependencies=frozenset({"notes"}))
    budget = engine.SourceInlineBudget("copy", "/node", D(2), D(2), kind)
    sizing = engine.LayoutSizingContext({"copy": budget})
    return engine._spec_base(spec, axis="inline", measurement=measurement, profile=profile,
                             path="/node/inlineSize", sizing=sizing)


@pytest.mark.parametrize("spec", ["content", "min-content", "max-content", {"fitContent": 20},
                                   {"minmax": {"min": "min-content", "max": {"fr": 1}}}])
def test_intrinsic_floor_detector_carries_typed_dependencies(spec):
    with pytest.raises(CountDependentHeadingFitError) as caught:
        _budgeted(spec)
    assert caught.value.figure_ids == {"notes"}


@pytest.mark.parametrize("spec", [{"fixed": 8}, {"minmax": {"min": {"fixed": 8}, "max": "content"}}])
def test_authored_minimum_remains_fatal_even_when_its_text_reads_a_count(spec):
    with pytest.raises(LayoutError) as caught:
        _budgeted(spec)
    assert type(caught.value) is LayoutError


def test_unrelated_table_floor_keeps_its_detector_and_diagnostic():
    with pytest.raises(LayoutError) as caught:
        _budgeted("content", kind="table")
    assert type(caught.value) is LayoutError
    assert caught.value.diagnostic_id == "E_LAYOUT_TABLE_OVERFLOW"


def test_source_budget_closure_failure_is_not_reclassified_as_count_fit():
    before = engine.SourceInlineBudget("copy", "/node", D(2), D(2), "heading")
    with pytest.raises(LayoutError) as caught:
        engine.validate_source_inline_budgets({"copy": before}, {"copy": replace(before, ceiling=D(3))})
    assert type(caught.value) is LayoutError


def test_heading_budget_may_narrow_below_its_probe_without_a_count_fit_failure():
    before = engine.SourceInlineBudget("copy", "/node", D(2), D(2), "heading")

    engine.validate_source_inline_budgets(
        {"copy": before}, {"copy": replace(before, available_inline=D(1), ceiling=D(1))})
