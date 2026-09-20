# ADR-0001: Use Half-Open Temporal Intervals

**Status:** Accepted for Core v0.1

## Context

Date-based project tools often expose inclusive finish dates to users, while scheduling
and duration arithmetic become simpler when an end boundary is exclusive.

## Decision

Resolved TemporalSpan intervals use:

```text
[start, end)
```

A span with `start == end` is invalid; a zero-duration event is represented by
TemporalPoint.

## Consequences

- adjacent work may satisfy `A.end == B.start`;
- FS + 0 requires no implicit +1 day;
- duration is naturally derived from the boundary difference;
- UI may display an inclusive final date, but this is presentation only.
