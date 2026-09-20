# M10 DateTime Scheduler Design Review — 2026-09-19

**Disposition:** Pass — M10-2 is authorized after this checkpoint is published.

## Finding and correction

The prior v0.2 Project contract defined dependency lower bounds but did not state how a
scheduled span resolves a lower bound on its `end`. It also permitted an unknown
one-property `anchor` structurally. Both would require an implementation to choose
semantics, so the runtime work was held.

The Project Format now defines the inverse operation: ExactDuration reverses on the
instant timeline; CalendarPeriod reverses in local date/time with the declared DST
policy. The anchor is closed to exactly `start` or `end`. The schema's negative fixture
also exercises the invalid-anchor rejection.

## M10-2 execution boundary

Create a separate `datetime_scheduler` module. It validates only `timeline/v0.2`,
resolves fixed placements and derived scheduled spans, and enforces dependency lower
bounds for an acyclic subset. It returns DateTime placements separately from the
Date-only `ScheduleResult`; it neither calls nor changes the v0.1 scheduler.

Semantic validation rejects a relation whose source or target is recurrence mode, a
missing object/endpoint, an unsupported amount kind, an anchor lower-bound violation,
and unresolved dependency cycles with declared diagnostics. It does not introduce
WorkPeriod or intraday-calendar behavior.
