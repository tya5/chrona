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

The CLI adapter only serializes `ScheduleResult.analysis`; it does not repeat
the backward pass, select presentation roles, or expose View/Layout/Scene facts.
The payload is deterministic for equal Project bytes and scheduler version.

## Evidence

Acceptance requires success and rejection CLI tests, exact ordering and
date-free JSON assertions, one HALCYON schedule analysis assertion, the full
suite, conformance, and installed-wheel CLI smoke.
