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
  criticalObjectIds: ordered object identifiers on a zero-float driving path to project finish
  totalFloat: object identifier -> {value, unit, calendar}
}
```

Identifiers use the canonical Project object order. `totalFloat` uses the
Scheduler's completed analysis values and includes every non-rollup scheduled
object. No analysis object is emitted for a rejected schedule.

Each `totalFloat` record has a non-negative integer `value`, `unit` equal to
`calendar-days` or `working-days`, and `calendar` equal to `null` for calendar
days or the effective Project calendar identifier for working days. The
effective calendar is the object's declaration, otherwise the Project's;
the amount's `d`/`wd` spelling does not select the float unit. The Scheduler
owns this typed value and its basis. CLI/MCP serialize it; presentation
projection explicitly takes its numeric `value` rather than a transport map.

This replaces the ambiguous integer-only `totalFloat` values. Consumers read
`totalFloat[id].value` and its basis together; there is no legacy integer
alias or misleading global unit for a mixed-calendar Project.

### Backward pass

The project finish is the greatest completed finish (`end` for a span, `at`
for a point) over non-rollup objects. Every terminal uses this **one global
target**, not its dependency component's finish. Rollups remain excluded
from float analysis; no implicit child/parent dependency is synthesized. An
empty eligible set gives empty analysis mappings.

Fixed objects and explicitly anchored spans retain their authoritative
scheduled dates in the latest pass. Other objects start the backward pass at
the project finish, subject to their declared upper bounds. Dependencies then
tighten those latest dates using the dual rule below. Fixed/anchored zero
float means that a date cannot move; it does not alone establish criticality.

Total float is the calendar distance (working days of the object's calendar when it has one) between an object's
scheduled start and its latest start. The latest start comes from the latest endpoint of every object it feeds, and the
rule is the exact dual of the forward rule of Spec 04 section 5: through a relation, the latest source endpoint is the
**greatest date `s` with `advance(s, lag) <= latest target endpoint`**, the lag read on the same calendar the forward
pass uses (Spec 04 section 8). A working-day `advance` counts days strictly after its start, so a source endpoint that is
not a working day of that calendar (the end of a calendar-day span, a point, a source on another calendar) is a valid
latest date, and the latest start of a working-day span is the greatest working date whose forward end does not pass its
latest end. Consequently a latest date is never earlier than the scheduled one and `totalFloat` is never negative; an
implementation that cannot meet this has a defect, not a plan to reject.

### Critical membership

A driving dependency is one whose completed source endpoint advanced by its
declared lag on the forward pass's effective relation calendar equals the
completed target endpoint. Its stable identity is the Scheduler's existing
driving-relation identity; rendering order plays no part.

Consider only dependencies between eligible objects with zero total float
at **both** ends. Starting at zero-float objects that finish at the project
finish, follow these driving dependencies backwards. A critical path ends at
that finish and contains only these zero-float objects and driving edges:
a positive-float intermediate or a non-driving edge breaks the path. Every
object participating in such a path with at least one edge is critical.
A movable, unanchored terminal that sets the project finish may also form a
one-object path. An isolated fixed or anchored object is not critical, even
when it sets the finish. A fixed finish separated from all predecessors by
slack can therefore have no critical dependency path. There is no implicit
per-component or multiple-critical-path compatibility mode.

Critical membership is independent of the float distance and never modifies
placements, latest dates, deadlines or fixed-target validation. In particular,
the #1297 CPM example keeps `build`'s 21 working-day float to the fixed launch;
the earlier campaign/survey component targets the project finish instead,
and is not critical. Presentation of critical relations is separate from
this scheduling contract.

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
