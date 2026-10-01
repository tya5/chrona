# Public Schedule Analysis

**Status:** Accepted
**Depends on:** [04 Scheduling Model](04-scheduling-model.md), [09 Application
Architecture](09-application-architecture.md), and [10 Command Model](10-command-model.md).
**Owns:** the public CLI serialization of already-derived schedule analysis.

## Decision

On a successful `chrona schedule`, the JSON result includes an `analysis` object
alongside `placements` and `diagnostics`:

```text
analysis {
  criticalObjectIds: ordered object identifiers with zero total float
  totalFloat: object identifier -> non-negative integer calendar distance
}
```

Identifiers use the canonical Project object order. `totalFloat` uses the
Scheduler's completed analysis values and includes every non-rollup scheduled
object. No analysis object is emitted for a rejected schedule.

### Backward pass

Total float is the calendar distance (working days of the object's calendar when it has one) between an object's
scheduled start and its latest start. The latest start comes from the latest endpoint of every object it feeds, and the
rule is the exact dual of the forward rule of Spec 04 section 5: through a relation, the latest source endpoint is the
**greatest date `s` with `advance(s, lag) <= latest target endpoint`**, the lag read on the same calendar the forward
pass uses (Spec 04 section 8). A working-day `advance` counts days strictly after its start, so a source endpoint that is
not a working day of that calendar (the end of a calendar-day span, a point, a source on another calendar) is a valid
latest date, and the latest start of a working-day span is the greatest working date whose forward end does not pass its
latest end. Consequently a latest date is never earlier than the scheduled one and `totalFloat` is never negative; an
implementation that cannot meet this has a defect, not a plan to reject.

Every mapping of the analysis is emitted in the canonical Project object order, not in the order a set or a hash
happens to give: `totalFloat` is keyed in Project object order exactly as `criticalObjectIds` is listed, and the same
holds for any other mapping the analysis carries.

The CLI adapter only serializes `ScheduleResult.analysis`; it does not repeat
the backward pass, select presentation roles, or expose View/Layout/Scene facts.
The payload is deterministic for equal Project bytes and scheduler version.

## Evidence

Acceptance requires success and rejection CLI tests, exact ordering and
date-free JSON assertions, one HALCYON schedule analysis assertion, the full
suite, conformance, and installed-wheel CLI smoke.
