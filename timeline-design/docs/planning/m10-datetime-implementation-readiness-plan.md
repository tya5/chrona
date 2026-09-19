# M10 DateTime Implementation Readiness Plan

**Status:** Active — M10 implementation blocked by Project Format closure

## Finding

`18-datetime-dst-successor.md` defines DateTime values, local DST resolution, and
recurrence intent, while `temporal-datetime-v0.2.schema.yaml` validates only a single
temporal value. The repository has no `timeline/v0.2` Project schema or canonical
fixture defining where `temporalProfile`, DateTime fixed placements, scheduled amounts,
relation endpoints, recurrence declarations, and migration provenance are serialized.

Implementing a scheduler directly from the value schema would choose persistence and
cross-domain behavior outside the owning Project Format design.

## Required design closure

1. Extend `05-project-format.md` with successor-only v0.2 serialization and explicit
   non-mixing rule; retain v0.1 Date-only syntax unchanged.
2. Add a versioned v0.2 Project schema and positive/negative canonical fixtures for
   instant/zone, fold/gap local input, dependency endpoints, recurrence, and migration.
3. Define v0.2 scheduling endpoint semantics for ExactDuration and CalendarPeriod;
   state that WorkPeriod/intraday calendars reject until separately specified.
4. Update Quality, UC-16 evidence, and M10 review; validate this closure before runtime
   code begins.

## Authorization boundary

M10 may implement `temporal_datetime` and the successor scheduler only after all four
items pass conformance and the replacement readiness review is published.
