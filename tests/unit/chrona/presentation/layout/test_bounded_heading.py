from dataclasses import replace
from decimal import Decimal as D

import pytest

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.sources import SourceInput, SourceTextRun, measure_sources
from chrona.presentation.layout.surface_heading import place_heading, place_surface_headings
from chrona.presentation.layout.surface_quality import SlotPlacement, SurfaceLayoutRequest
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.layout.test_bounded_table_measurement import Metrics
from tests.unit.chrona.presentation.layout.test_sources import theme as base_theme


def theme():
    resolved = base_theme()
    resolved["body"]["roles"]["kicker"] = dict(resolved["body"]["roles"]["text"])
    resolved["body"]["roles"]["subtitle"] = dict(resolved["body"]["roles"]["text"])
    return resolved


def measure(source, key="title", budget=D(300)):
    return measure_sources({key: source}, theme(), font_metrics=Metrics(), heading_inline={key: budget})


def request():
    return SurfaceLayoutRequest(theme_tokens=ThemeTokenView(theme()), font_metrics=Metrics())


def slot(key="title"):
    return SlotPlacement(key, key, Rect(D(40), D(20), D(300), D(3000)))


def test_native_heading_wraps_before_source_block_measurement_and_projects_full_lines():
    source = SourceInput(("long title " * 100,), typography_role="heading", text_wrap="allow")
    measured = measure(source)
    run = measured.run_measurements["title"][0]
    assert len(run.lines) > 1
    assert run.inline_size <= 300
    assert measured.measurements["title"].preferred_block == run.block_size
    placed, = place_heading(request(), slot(), measured)
    assert placed.lines == run.lines
    assert placed.source_content == source.lines[0]
    assert placed.bounds.inline + placed.bounds.inline_size <= 340
    assert float(placed.bounds.block_size) == pytest.approx(float(run.block_size))
    assert measured.measurements["title"].last_baseline == run.baseline + D(str(run.font_size)) * D(str(run.line_height)) * (len(run.lines) - 1)


def test_whole_heading_stack_closes_kicker_title_subtitle_without_overlap():
    source = SourceInput(runs=(SourceTextRun("Kicker " * 30, "kicker", "kicker"),
                              SourceTextRun("Title " * 100, "heading", "title"),
                              SourceTextRun("Deck " * 40, "subtitle", "subtitle")),
                         run_flow="block", text_wrap="allow")
    measured = measure(source)
    placed = place_heading(request(), slot(), measured)
    assert all(len(item.lines) > 1 for item in placed)
    assert all(left.bounds.block + left.bounds.block_size <= right.bounds.block
               for left, right in zip(placed, placed[1:]))
    assert max(item.bounds.block + item.bounds.block_size for item in placed) <= 20 + measured.block_stacks["title"].block_size
    last = measured.run_measurements["title"][-1]
    assert measured.measurements["title"].last_baseline == measured.block_stacks["title"].baselines[-1] + D(str(last.font_size)) * D(str(last.line_height)) * (len(last.lines) - 1)


def test_native_title_and_deck_last_baseline_matches_completed_last_line():
    source = SourceInput(lines=("Title " * 40, "Deck " * 40),
                         runs=(SourceTextRun("Title " * 40, "heading", "title"),
                               SourceTextRun("Deck " * 40, "subtitle", "subtitle")), text_wrap="allow")
    measured = measure(source)
    title, deck = place_heading(request(), slot(), measured)
    assert title.bounds.block + title.bounds.block_size <= deck.bounds.block
    assert float(measured.measurements["title"].last_baseline) == pytest.approx(deck.baseline[1] - 20 + deck.font_size * deck.line_height * (len(deck.lines) - 1))


@pytest.mark.parametrize("part,role", [("title", "heading"), ("kicker", "kicker"), ("subtitle", "subtitle")])
def test_separately_allocated_heading_part_uses_closed_source_lines(part, role):
    key = f"heading.{part}"
    source = SourceInput(runs=(SourceTextRun("words " * 80, role, part),), run_flow="block", text_wrap="allow")
    measured = measure(source, key)
    placed, = place_surface_headings(request(), {key: slot(key)}, measured).text
    assert placed.lines == measured.run_measurements[key][0].lines
    assert placed.source_content == source.runs[0].content
    assert placed.bounds.inline_size <= 300


@pytest.mark.parametrize("flow", ["stack", "block"])
def test_fitting_heading_and_whitespace_keep_measurements_and_placements_exact(flow):
    source = SourceInput(lines=("  Short\t  ",), runs=(SourceTextRun("  Short\t  ", "heading", "title"),),
                         typography_role="heading", run_flow=flow, text_wrap="allow")
    bounded = measure(source)
    ordinary = measure_sources({"title": source}, theme(), font_metrics=Metrics())
    assert bounded == ordinary
    assert place_heading(request(), slot(), bounded) == place_heading(request(), slot(), ordinary)


def test_overlong_unit_ellipsizes_with_source_and_does_not_choose_table_diagnostic():
    source = SourceInput(("X" * 1000,), typography_role="heading", text_wrap="allow")
    placed, = place_heading(request(), slot(), measure(source))
    assert placed.content.endswith("…")
    assert placed.overflow == "ellipsized"
    assert placed.source_content == "X" * 1000
    with pytest.raises(LayoutError, match="E_LAYOUT_TEXT_OVERFLOW"):
        measure(source, budget=D(1))


def test_inline_reservation_is_removed_before_text_fit_and_kept_in_source_width():
    source = SourceInput(runs=(SourceTextRun("words " * 100, "heading", "title", D(30)),),
                         run_flow="block", text_wrap="allow")
    run = measure(source).run_measurements["title"][0]
    assert run.inline_size <= 300
    assert max(len(line) * 17 for line in run.lines) <= 270
    with pytest.raises(LayoutError, match="E_LAYOUT_TEXT_OVERFLOW"):
        measure(source, budget=D(30))


def test_declared_source_floor_survives_intrinsic_width_shortage():
    source = SourceInput(("words " * 100,), typography_role="heading", text_wrap="allow", min_inline=D(200))
    assert measure(source).measurements["title"].min_inline == 200


def test_forbid_or_absent_budget_does_not_activate_wrapping():
    source = SourceInput(("word " * 100,), typography_role="heading")
    ordinary = measure_sources({"title": source}, theme(), font_metrics=Metrics())
    assert measure(source) == ordinary
    assert measure_sources({"title": replace(source, text_wrap="allow")}, theme(), font_metrics=Metrics()).run_measurements == ordinary.run_measurements


def test_empty_selected_heading_stays_zero_and_does_not_require_fit():
    source = SourceInput(("word " * 100,), text_wrap="allow", content_present=False)
    measured = measure(source, budget=D(0))
    assert measured.measurements["title"].preferred_block == 0
    assert measured.run_measurements["title"] == ()
