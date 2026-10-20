"""Observation preserves order, truthful completion, and failure isolation."""
import pytest

from chrona.presentation.model.info_diagnostics import RoutingCostAdvisory
from chrona.presentation.model.render_progress import (
    RenderAdvisoryEvent, RenderProgress, RenderProgressEvent,
)


def test_declarations_advance_only_after_their_work_and_keep_identity():
    events = []
    declarations = [object(), object()]
    observed = RenderProgress(events.append).routing(declarations, pass_name="final")
    assert next(observed) is declarations[0]
    assert events == [RenderProgressEvent("routing", 0, 2, "final")]
    assert next(observed) is declarations[1]
    assert events[-1] == RenderProgressEvent("routing", 1, 2, "final")
    with pytest.raises(StopIteration):
        next(observed)
    assert events[-1] == RenderProgressEvent("routing", 2, 2, "final")


def test_empty_pass_and_separate_rehearsals_do_not_invent_work():
    events = []
    progress = RenderProgress(events.append)
    assert list(progress.routing([], pass_name="rehearsal")) == []
    assert events == [RenderProgressEvent("routing", 0, 0, "rehearsal")]
    assert list(progress.routing(["a"], pass_name="final")) == ["a"]
    assert events[-2:] == [RenderProgressEvent("routing", 0, 1, "final"),
                          RenderProgressEvent("routing", 1, 1, "final")]


def test_interrupted_pass_does_not_claim_unfinished_declaration():
    events = []
    observed = RenderProgress(events.append).routing(["a", "b"], pass_name="final")
    assert next(observed) == "a"
    observed.close()
    assert events == [RenderProgressEvent("routing", 0, 2, "final")]


def test_advisory_is_a_distinct_frozen_event():
    events = []
    advisory = RoutingCostAdvisory("table-timeline", 336)
    RenderProgress(events.append).advisory(advisory)

    assert events == [RenderAdvisoryEvent(advisory)]
    assert events[0].advisory is advisory


def test_candidate_progress_is_buffered_but_attempted_work_advisory_is_immediate():
    observed, buffered = [], []
    parent = RenderProgress(observed.append)
    candidate = parent.buffered(buffered.append)
    advisory = RoutingCostAdvisory("table-timeline", 2370)
    candidate.phase("layout")
    candidate.advisory(advisory)
    assert observed == [RenderAdvisoryEvent(advisory)]
    assert buffered == [RenderProgressEvent("layout")]


def test_nested_candidate_buffers_keep_advisories_out_of_replay_and_isolate_sink_failures():
    observed, outer, inner = [], [], []

    def fail(event):
        observed.append(event)
        raise OSError("sink unavailable")

    parent = RenderProgress(fail)
    candidate = parent.buffered(outer.append).buffered(inner.append)
    advisory = RoutingCostAdvisory("table-timeline", 2370)
    candidate.advisory(advisory)
    candidate.advisory(advisory)
    candidate.phase("routing")
    assert observed == [RenderAdvisoryEvent(advisory)]
    assert inner == [RenderProgressEvent("routing")] and outer == []


@pytest.mark.parametrize("failure", [BrokenPipeError, OSError, ValueError])
def test_failed_observer_detaches_without_changing_iteration(failure):
    calls = []

    def fail(event):
        calls.append(event)
        raise failure("sink unavailable")

    progress = RenderProgress(fail)
    advisory = RoutingCostAdvisory("table-timeline", 336)
    progress.advisory(advisory)
    assert list(progress.routing(["a", "b"], pass_name="final")) == ["a", "b"]
    progress.phase("output")
    assert calls == [RenderAdvisoryEvent(advisory)]
