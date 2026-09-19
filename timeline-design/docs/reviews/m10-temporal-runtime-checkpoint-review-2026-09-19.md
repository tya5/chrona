# M10 DateTime Temporal Runtime Checkpoint Review — 2026-09-19

**Disposition:** M10-1 complete; M10 remains in progress.

## Scope reviewed

The runtime implements the value-level portion of the `timeline/v0.2` successor only:
instant/zone resolution, explicit local fold selection, nonexistent-local-time rejection,
ExactDuration instant arithmetic, CalendarPeriod local-date advancement, and bounded
daily/weekly/monthly recurrence.

The Project Format contract was corrected before this checkpoint: a recurrence now has
exactly one terminal bound (`count` or inclusive DateTime `until`). The JSON Schema and
negative fixture reject an unbounded recurrence. This closes the structural omission
without changing v0.1 or the DateTime value contract.

## Evidence

| Check | Result |
|---|---|
| Unit tests | Fold, gap, duration, CalendarPeriod, count recurrence, and inclusive `until` pass. |
| Regression | `python -m pytest -q` passes. |
| Design fixtures | `python timeline-design/docs/fixtures/run_conformance.py` passes, including DateTime Project validation. |
| Compatibility | The module is opt-in; it imports the existing Date-only `advance` only to perform declared CalendarPeriod date arithmetic. No v0.1 parser, scheduler, or data structure changed. |

## Remaining M10 authorization

M10-2 must add a separate v0.2 Project scheduler for fixed/scheduled placements and
dependency bounds. M10-3 must add the explicit-policy migration path and downgrade
rejection. Until those phases and M10-4 evidence complete, no release may claim UC-16
or complete M10.
