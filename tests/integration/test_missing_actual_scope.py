"""`comparison.missingActualScope: in-progress` marks the span that has started and not finished (#991).

A synthetic Project through the packaged `executive-light` bundle; no test reads `examples/`.
"""
from __future__ import annotations

from datetime import date

import pytest

from tests.support import synthetic_review as sr

AS_OF = date(2026, 3, 2)
ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed", "body": {
    "asOf": AS_OF.isoformat(), "observations": [
        {"id": "run", "sequence": 1, "projectObjectId": "running", "actual": {"start": "2026-02-09", "openUntil": "asOf"}},
        {"id": "s", "sequence": 1, "projectObjectId": "started", "actual": {"start": "2026-02-20", "progress": 0.4}},
        {"id": "z", "sequence": 1, "projectObjectId": "stalled", "actual": {"start": "2026-02-20", "progress": 1}},
        {"id": "n", "sequence": 1, "projectObjectId": "noprogress", "actual": {"start": "2026-02-20"}},
        {"id": "f", "sequence": 1, "projectObjectId": "future", "actual": {"start": "2026-03-20", "progress": 0.1}},
        {"id": "o", "sequence": 1, "projectObjectId": "explicit", "actual": {"start": "2026-02-20", "openUntil": "asOf", "progress": 1}},
        {"id": "done", "sequence": 1, "projectObjectId": "finished", "actual": {"start": "2026-01-12", "finish": "2026-01-23"}},
    ]}}


def _source() -> dict:
    return sr.project({
        "running": sr.span("running", date(2026, 2, 2), 40),
        "started": sr.span("started", date(2026, 2, 16), 40),
        "stalled": sr.span("stalled", date(2026, 2, 16), 40),
        "noprogress": sr.span("noprogress", date(2026, 2, 16), 40),
        "future": sr.span("future", date(2026, 3, 16), 40),
        "explicit": sr.span("explicit", date(2026, 2, 16), 40),
        "finished": sr.span("finished", date(2026, 1, 12), 11),
        "overdue": sr.span("overdue", date(2026, 1, 19), 14),
        "gate": sr.point("gate", date(2026, 2, 13)),
    })


def _render(tmp_path, scope: str | None, *, rows: str = "automatic"):
    """The packaged bundle's own rows are lanes; `automatic` swaps in automatic rows with a title column."""
    parts = sr.bundle("executive-light")
    comparison = parts["view"]["body"]["comparison"]
    comparison["facets"].append("missingActual")
    if scope is not None:
        comparison["missingActualScope"] = scope
    if rows == "automatic":
        parts["view"]["body"]["rows"] = {"mode": "automatic"}
        parts["view"]["body"]["tableColumns"] = [{"id": "Task", "source": "title", "missing": "em-dash", "align": "start",
                                                  "width": "content", "headerOrientation": "horizontal"}]
    return sr.render(tmp_path, _source(), presentation=parts, actual=ACTUAL)


def _marks(rendered, prefix: str) -> dict[str, tuple]:
    return {item.scene_id.split(":", 1)[1].split(":")[-1]: item.bounds for item in rendered.surface.primitives
            if item.scene_id.startswith(prefix + ":")}


def test_by_default_a_due_unobserved_span_and_gate_are_marked_and_the_open_actual_is_drawn(tmp_path):
    rendered = _render(tmp_path, None)
    missing, actual = _marks(rendered, "missing-actual"), _marks(rendered, "actual")
    assert set(missing) == {"overdue", "gate"}
    # Only an Actual that declares `openUntil: asOf` draws an open actual; the others are incomplete observations.
    assert set(actual) == {"running", "finished", "explicit"}


def test_in_progress_marks_only_the_started_span_from_its_actual_start_to_as_of(tmp_path):
    rendered = _render(tmp_path, "in-progress")
    missing, actual = _marks(rendered, "missing-actual"), _marks(rendered, "actual")

    # The owner's rule: started (on or before as-of), unfinished and progress below 1 or absent is in progress,
    # `openUntil: asOf` or not (and `openUntil` alone is enough, even at progress 1); at progress 1 without a
    # finish or `openUntil` it is not, nor is a span that has not started. No mark on the overdue span or the gate.
    assert set(missing) == {"running", "started", "noprogress", "explicit"}
    assert set(actual) == {"finished"}
    assert not {"stalled", "future", "overdue", "gate"} & set(missing)
    left, _, width, _ = missing["running"]
    planned = next(item for item in rendered.surface.primitives if item.scene_id.startswith("planned:") and item.scene_id.endswith(":running"))
    day = planned.bounds[2] / 40  # one calendar day, from the planned 40-day span
    assert left == pytest.approx(planned.bounds[0] + 7 * day, abs=0.05)  # 9 Feb is 7 days after 2 Feb
    assert width == pytest.approx(21 * day, abs=0.05)  # up to as-of, 2 Mar


def test_in_progress_with_lane_rows_draws_the_same_marks_as_automatic_rows(tmp_path):
    lanes = _render(tmp_path, "in-progress", rows="lanes")
    missing, actual = _marks(lanes, "missing-actual"), _marks(lanes, "actual")
    assert set(missing) == {"running", "started", "noprogress", "explicit"}
    assert set(actual) == {"finished"}
    assert not {"stalled", "future", "overdue", "gate"} & set(missing)


def test_the_default_scope_with_lane_rows_is_unchanged_by_the_in_progress_inventory(tmp_path):
    first = _render(tmp_path, None, rows="lanes")
    assert set(_marks(first, "missing-actual")) == {"overdue", "gate"}
