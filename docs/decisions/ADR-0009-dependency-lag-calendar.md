# ADR-0009: Resolve WorkPeriod Dependency Lag from Target Calendar

**Status:** Accepted for Core v0.1

## Context

A dependency lag expressed in working days cannot be resolved without a calendar.

Existing project-management systems can combine project, task, and resource calendars,
but Core v0.1 intentionally excludes resource scheduling and working-hour composition.
A deterministic date-level rule is therefore required.

## Decision

For a WorkPeriod dependency lag, resolve the calendar in this order:

```text
explicit relation lag calendar
-> target object's scheduling calendar
-> project default calendar
```

The target calendar is preferred because the lag constrains the earliest placement of
the target object. An explicit relation calendar remains available when the lag itself
belongs to a different operational calendar.

## Consequences

- the rule is deterministic and local;
- source and target calendars do not need to be intersected;
- resource-calendar composition remains outside Core;
- the dependency computes a temporal bound only;
- target placement validity is still applied separately after the bound is computed.

This rule is covered by Core conformance fixtures.
