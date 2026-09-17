# ADR-0007: Use Distinct Temporal Amount Types

**Status:** Accepted for Core v0.1

## Context

`3 days` can mean elapsed time, calendar movement, or working-day movement.

## Decision

Core defines:

```text
ExactDuration
CalendarPeriod
WorkPeriod
```

They are not implicitly interchangeable.

## Consequences

`24h`, `1d`, and `1wd` may produce different results. Type checking can reject
ambiguous or invalid arithmetic.
