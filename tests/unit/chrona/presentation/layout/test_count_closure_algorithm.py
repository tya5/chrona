"""Finite closure policy over typed producer results; real pipeline tests prove producer truth (#1346)."""
from dataclasses import replace

import pytest

from chrona.presentation.count_text import CountTextFormat
from chrona.presentation.heading_text import HeadingTextPrograms, close_heading
from chrona.presentation.layout import surface_count_closure as closure
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.model.info_diagnostics import RoutingCostAdvisory
from chrona.presentation.model.render_progress import RenderAdvisoryEvent, RenderProgress, RenderProgressEvent
from tests.integration.test_slot_heading import _render


@pytest.fixture
def seed(tmp_path, monkeypatch):
    from chrona.presentation import surface_pipeline as pipeline
    complete = pipeline.complete_surface_render_plan
    captured = []
    def observe(value, **kwargs):
        result = complete(value, **kwargs)
        captured.append((value, result))
        return result
    monkeypatch.setattr(pipeline, "complete_surface_render_plan", observe)
    def configure(parts):
        parts["view"]["body"]["figures"] = [{"id": "notes", "kind": "count", "source": "placedNotes"}]
    _render(tmp_path, heading={"template": "{figure:notes}"}, configure=configure)
    return captured[0]


def _stub_planning(monkeypatch, seed):
    initial, completed = seed
    calls = []
    def prepare(value):
        calls.append(dict(value.projection.figures)["notes"])
        if isinstance(value.heading, HeadingTextPrograms):
            value.heading.bind(dict(value.projection.figures), value.view.figure_formats)
        return completed.plan
    monkeypatch.setattr(closure, "prepare_surface_render_plan", prepare)
    return initial, completed, calls


def _facts(completed, count):
    placement = replace(completed.composition.placement,
                        narrative_receipts=completed.composition.placement.narrative_receipts[:count])
    placement.assert_valid()
    return replace(completed.composition, placement=placement)


def test_highest_consistent_candidate_wins_without_trying_lower_solutions(seed, monkeypatch):
    initial, completed, calls = _stub_planning(monkeypatch, seed)
    monkeypatch.setattr(closure, "_compose", lambda value, plan: _facts(completed, dict(value.projection.figures)["notes"]))
    result = closure.complete_surface_render_plan(initial)
    assert calls == [3]
    assert dict(result.projection.figures) == {"notes": 3}
    assert [(t.count, t.outcome) for t in result.trials] == [(3, "accepted")]


def test_no_solution_retains_bounded_mismatch_evidence_and_never_projects(seed, monkeypatch):
    initial, completed, calls = _stub_planning(monkeypatch, seed)
    monkeypatch.setattr(closure, "_compose", lambda value, plan: _facts(
        completed, 0 if dict(value.projection.figures)["notes"] == 3 else 3))
    with pytest.raises(closure.CountClosureError) as caught:
        closure.complete_surface_render_plan(initial)
    assert calls == [3, 2, 1, 0]
    assert caught.value.upper == 3 and len(caught.value.trials) == 4
    assert all(t.outcome == "mismatch" for t in caught.value.trials)
    assert "domain=0..3; trials=4" in caught.value.detail


def test_rejected_trial_reports_attempted_work_early_but_not_candidate_progress(seed, monkeypatch):
    initial, completed, calls = _stub_planning(monkeypatch, seed)
    observed = []
    initial = replace(initial, value=replace(initial.value, progress=RenderProgress(observed.append)))

    def compose(value, plan):
        count = dict(value.projection.figures)["notes"]
        advisory = RoutingCostAdvisory("table-timeline", 2370 + count)
        value.progress.phase("routing")
        value.progress.advisory(advisory)
        # Before this trial's search/completion, the work advisory is visible
        # but its ordinary progress is still buffered.
        assert RenderAdvisoryEvent(advisory) in observed
        assert not any(isinstance(event, RenderProgressEvent) for event in observed)
        return _facts(completed, 2)

    monkeypatch.setattr(closure, "_compose", compose)
    result = closure.complete_surface_render_plan(initial)
    assert calls == [3, 2]
    assert [trial.outcome for trial in result.trials] == ["mismatch", "accepted"]
    assert observed == [RenderAdvisoryEvent(RoutingCostAdvisory("table-timeline", 2373)),
                        RenderAdvisoryEvent(RoutingCostAdvisory("table-timeline", 2372)),
                        RenderProgressEvent("routing")]


def test_unavailable_upper_number_names_do_not_preclude_a_lower_consistent_candidate(seed, monkeypatch):
    initial, completed, calls = _stub_planning(monkeypatch, seed)
    value = replace(initial.value,
        content=replace(initial.value.content, annotations=tuple(
            replace(initial.value.content.annotations[index % 3], annotation_id=f"occurrence-{index}")
            for index in range(102))),
        heading=HeadingTextPrograms(close_heading("{figure:notes}", {})),
        view=replace(initial.value.view, figure_formats={"notes": CountTextFormat("kanji")}))
    initial = closure.inspect_count_reads(value)
    monkeypatch.setattr(closure, "_compose", lambda value, plan: completed.composition)
    result = closure.complete_surface_render_plan(initial)
    assert calls[0] == 102 and calls[-1] == 3
    assert dict(result.projection.figures) == {"notes": 3}
    assert [t.count for t in result.trials if t.outcome == "range"] == [102, 101, 100]
    assert all(t.figure_ids == {"notes"} and t.supported_range == (0, 99)
               for t in result.trials if t.outcome == "range")
    assert len(result.trials) <= 103


def test_real_layout_closes_lower_kanji_count_after_upper_range_rejection(seed):
    from tests.unit.chrona.presentation.layout.test_bounded_table_measurement import Metrics
    initial, _ = seed
    value = replace(initial.value,
        content=replace(initial.value.content, annotations=(), notes=tuple(
            (f"note-{index}", "Narrative" if index < 99 else "") for index in range(100))),
        heading=HeadingTextPrograms(close_heading("{figure:notes}", {})), font_metrics=Metrics(),
        view=replace(initial.value.view, figure_formats={"notes": CountTextFormat("kanji")}))
    result = closure.complete_surface_render_plan(closure.inspect_count_reads(value))
    assert [(t.count, t.outcome, t.actual) for t in result.trials] == [(100, "range", None), (99, "accepted", 99)]
    assert dict(result.projection.figures) == {"notes": 99}
    assert len(result.composition.placement.narrative_receipts) == 99
    assert next(t for t in result.composition.placement.text if t.source_ref == "title").content == "九十九"


def test_real_measured_heading_fit_rejects_upper_count_and_accepts_lower_count(seed):
    from copy import deepcopy
    from chrona.presentation.layout.text import measure_text_width, metric_for_role
    from chrona.presentation.model.theme_tokens import ThemeTokenView
    from tests.support import synthetic_review as sr
    initial, _ = seed
    value = initial.value
    tokens = ThemeTokenView(value.theme)
    treatment = tokens.text_treatment("heading")
    metrics = metric_for_role(tokens, "heading", value.font_metrics)
    def width(text):
        return measure_text_width(text, font_size=float(treatment.font_size), font_metrics=metrics,
            letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
            numeric_spacing=treatment.numeric_spacing)
    assert width("9") < width("…")
    ceiling = (width("9") + width("…")) / 2
    profile = deepcopy(value.profile)
    sr.find_node(profile, "title")["inlineSize"] = {"fixed": ceiling}
    value = replace(value, profile=profile,
        content=replace(value.content, annotations=(), notes=tuple(
            (f"note-{index}", "Narrative" if index < 9 else "") for index in range(10))),
        heading=HeadingTextPrograms(close_heading("{figure:notes}", {}), text_wrap="allow"))
    result = closure.complete_surface_render_plan(closure.inspect_count_reads(value))
    assert [(t.count, t.outcome, t.actual) for t in result.trials] == [(10, "text-fit", None), (9, "accepted", 9)]
    assert result.trials[0].figure_ids == {"notes"}
    assert dict(result.projection.figures) == {"notes": 9}
    assert next(t for t in result.composition.placement.text if t.source_ref == "title").content == "9"


@pytest.mark.parametrize("code", ["E_LAYOUT_TEXT_OVERFLOW", "E_LAYOUT_TABLE_OVERFLOW", "E_LAYOUT_SCHEMA", "E_LAYOUT_MEASUREMENT_REQUIRED"])
def test_unrelated_error_is_not_retried_even_if_it_shares_a_fit_code(seed, monkeypatch, code):
    initial, _, _ = _stub_planning(monkeypatch, seed)
    calls = []
    error = LayoutError(code, "/unrelated", detail="independent failure")
    def fail(value):
        calls.append(None)
        raise error
    monkeypatch.setattr(closure, "prepare_surface_render_plan", fail)
    with pytest.raises(LayoutError) as caught:
        closure.complete_surface_render_plan(initial)
    assert caught.value is error and len(calls) == 1


def test_range_failure_on_an_unrelated_figure_is_not_retried(seed, monkeypatch):
    from chrona.presentation.count_text import CountTextError
    from chrona.presentation.figure_text import FigureTextReadError
    initial, _, _ = _stub_planning(monkeypatch, seed)
    error = FigureTextReadError(CountTextError("E_VIEW_FIGURE_FORMAT_RANGE", "fixed count outside names",
        figure_id="fixed", value=100, form="kanji", supported_range=(0, 99)), "/body/heading/title")
    calls = []
    def fail(value):
        calls.append(None)
        raise error
    monkeypatch.setattr(closure, "prepare_surface_render_plan", fail)
    with pytest.raises(FigureTextReadError) as caught:
        closure.complete_surface_render_plan(initial)
    assert caught.value is error and len(calls) == 1
