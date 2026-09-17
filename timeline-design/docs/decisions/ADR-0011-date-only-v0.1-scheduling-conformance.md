# ADR-0011: Scope Core v0.1 Scheduling Conformance to Date

**Status:** Accepted for Core v0.1

## Context

The semantic model distinguishes Date and DateTime. Full DateTime scheduling requires
precise timezone, daylight-saving, and calendar-period behavior that is not needed for
the initial line-chart use case.

## Decision

Core v0.1 **model semantics** retain DateTime and ExactDuration, but Core v0.1
**scheduling conformance** is Date-based.

A conforming Core v0.1 scheduler MUST implement:

- Date coordinates;
- CalendarPeriod `d` and `w` for scheduled span amount;
- WorkPeriod `wd`;
- Date-based dependencies, bounds, and calendars.

DateTime scheduling is an optional capability until a later conformance profile
defines timezone/DST behavior.

## Consequences

The v0.1 scheduler contract becomes small enough to implement independently without
hidden timezone assumptions. Project Format v0.1 canonical scheduling examples remain
Date-based.
