"""Observation preserves order, truthful completion, and failure isolation."""
import pytest

from chrona.presentation.model.info_diagnostics import RoutingCostAdvisory
from chrona.presentation.model.render_progress import (
    RenderAdvisoryEvent, RenderProgress, RenderProgressEvent,
    RenderWorkPhaseEvent,
)


def test_declarations_advance_only_after_their_work_and_keep_identity():
    events = []
    declarations = [object(), object()]
    observed = RenderProgress(events.append).routing(declarations, pass_name="final")
    assert next(observed) is declarations[0]
    assert events == [RenderWorkPhaseEvent("routing", "final"),
                      RenderProgressEvent("routing", 0, 2, "final")]
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
    assert RenderWorkPhaseEvent("routing", "rehearsal") not in events
    assert events[-3:] == [RenderWorkPhaseEvent("routing", "final"),
                           RenderProgressEvent("routing", 0, 1, "final"),
                          RenderProgressEvent("routing", 1, 1, "final")]


def test_interrupted_pass_does_not_claim_unfinished_declaration():
    events = []
    observed = RenderProgress(events.append).routing(["a", "b"], pass_name="final")
    assert next(observed) == "a"
    observed.close()
    assert events == [RenderWorkPhaseEvent("routing", "final"),
                      RenderProgressEvent("routing", 0, 2, "final")]


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


def test_nested_rejected_attempt_forwards_start_and_advisory_before_work_but_buffers_counts():
    observed, outer, inner, order = [], [], [], []
    parent = RenderProgress(lambda event: (observed.append(event), order.append(("parent", event))))
    candidate = parent.buffered(lambda event: (outer.append(event), order.append(("outer", event))))
    nested = candidate.buffered(lambda event: (inner.append(event), order.append(("inner", event))))
    advisory = RoutingCostAdvisory("table-timeline", 2370)

    def attempt():
        declarations = nested.routing(["route"], pass_name="annotation-leaders")
        # Opening a nonempty pass is observable before the route search starts.
        start = next(declarations)
        order.append(("work", start))
        nested.advisory(advisory)
        raise RuntimeError("candidate rejected")

    with pytest.raises(RuntimeError, match="candidate rejected"):
        attempt()

    work_start = RenderWorkPhaseEvent("routing", "annotation-leaders")
    assert order.index(("work", "route")) > max(
        i for i, item in enumerate(order) if item[1] == work_start
    )
    assert work_start in observed
    assert RenderAdvisoryEvent(advisory) in observed
    assert RenderProgressEvent("routing", 0, 1, "annotation-leaders") in inner
    assert not any(isinstance(event, RenderProgressEvent) for event in outer)
    assert not any(isinstance(event, RenderProgressEvent) for event in observed)


def test_accepted_nested_attempt_replays_counts_once_without_replaying_starts():
    observed, outer, inner = [], [], []
    parent = RenderProgress(observed.append)
    nested = parent.buffered(outer.append).buffered(inner.append)
    declarations = nested.routing(["route"], pass_name="annotation-leaders")
    assert next(declarations) == "route"
    with pytest.raises(StopIteration):
        next(declarations)

    starts = [event for event in observed if isinstance(event, RenderWorkPhaseEvent)]
    counts = [event for event in inner if isinstance(event, RenderProgressEvent)]
    assert starts == [RenderWorkPhaseEvent("routing", "annotation-leaders")]
    assert counts == [RenderProgressEvent("routing", 0, 1, "annotation-leaders"),
                      RenderProgressEvent("routing", 1, 1, "annotation-leaders")]
    assert not any(isinstance(event, RenderWorkPhaseEvent) for event in inner + outer)
    assert not any(isinstance(event, RenderProgressEvent) for event in observed)

    # The accepting caller replays only buffered progress; the attempted-work
    # start has already been delivered and is never replayed with the counts.
    for event in inner:
        parent.emit(event)
    assert observed == [RenderWorkPhaseEvent("routing", "annotation-leaders"), *counts]


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


def test_failed_work_phase_observer_does_not_interrupt_routing():
    calls = []

    def fail(event):
        calls.append(event)
        raise OSError("sink unavailable")

    progress = RenderProgress(fail)
    assert list(progress.routing(["a", "b"], pass_name="annotation-leaders")) == ["a", "b"]
    assert calls == [RenderWorkPhaseEvent("routing", "annotation-leaders")]
