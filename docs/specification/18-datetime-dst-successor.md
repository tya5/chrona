# DateTime and DST Successor Design

**Status:** Proposed  
**Owns:** The successor temporal coordinate and arithmetic contract for DateTime,
timezone, DST, and recurrence. It does not change Core v0.1 Date-only meaning.

## 1. Compatibility

`Date` remains a calendar coordinate with no implied midnight or timezone. A v0.1
Project continues to evaluate under the v0.1 Date-only scheduler. A successor Project
MUST declare `temporalProfile: datetime-v0.2`; mixed Date/DateTime dependencies are
rejected unless an explicit, versioned conversion policy is selected.

## 2. DateTime value

A DateTime is an instant plus its supplied IANA zone identifier. Persistent input is:

```yaml
instant: 2027-03-28T00:30:00Z
zone: Europe/London
```

The instant is authoritative for comparison and ExactDuration arithmetic; zone is
authoritative for local calendar interpretation and display. A numeric offset alone is
not a zone identity.

## 3. Local input and DST

Local wall-clock input is accepted only with an explicit disambiguation policy:

```yaml
local: 2027-10-31T01:30:00
zone: Europe/London
disambiguation: earlier # earlier | later | reject
```

For an ambiguous local time, `earlier` and `later` select the corresponding instant;
`reject` yields `E_TEMPORAL_AMBIGUOUS_LOCAL_TIME`. For a nonexistent local time,
`reject` is the only valid policy and yields `E_TEMPORAL_NONEXISTENT_LOCAL_TIME`.
No implementation may silently shift a wall-clock input across a DST gap.

## 4. Arithmetic

`DateTime + ExactDuration` advances the instant by elapsed time. `DateTime +
CalendarPeriod` applies calendar components in the supplied zone, using the existing
largest-to-smallest order, then resolves the resulting local time with an explicit
disambiguation policy. WorkPeriod and future working-hour arithmetic require an
intraday Calendar successor and are not implied by this document.

## 5. Recurrence

Recurrence is a separate, declarative schedule generator. It names a zone, local start,
frequency, interval, optional count/until, and DST disambiguation. Generated occurrences
are derived values, not independently mutable Project objects. A recurrence never
silently changes an existing fixed Date-only placement.

## 6. Required evidence before implementation

- v0.2 schemas and positive/negative fixtures for cross-zone comparison, DST fold, DST
  gap, CalendarPeriod across DST, recurrence, and Date-only compatibility;
- Scheduling/Project Format/Quality updates defining endpoint and migration rules;
- an ADR accepting the instant-plus-IANA-zone representation; and
- cross-document review with no unresolved Date/DateTime conversion or persistence
  authority issue.
