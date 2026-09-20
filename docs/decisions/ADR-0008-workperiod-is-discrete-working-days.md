# ADR-0008: WorkPeriod Uses Discrete Working Dates

**Status:** Accepted for Core v0.1

## Context

Supporting working hours introduces shifts, breaks, resource calendars, and fractional
capacity.

## Decision

Core v0.1 WorkPeriod supports integer `wd` values only and advances across dates marked
working by a Calendar.

## Consequences

Fractional working days and working-hour scheduling are deferred. Calendar structure
can remain date-level.
