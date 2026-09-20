# Scheduling Model

**Status:** Stable
**Core Specification:** v0.1

## 1. Scope

This document defines how temporal objects receive resolved positions and how
dependencies, bounds, calendars, and duration interact.

It defines observable scheduling semantics, not a required solver implementation.

### v0.2 DateTime successor boundary

When a Project declares `temporalProfile: datetime-v0.2`, every endpoint and bound in
one dependency-connected scheduling component MUST use DateTime. The component compares
instants; CalendarPeriod application is performed in the endpoint's declared zone as
defined by `18-datetime-dst-successor.md`. Date-only components retain all v0.1 rules.
Mixed-domain relations reject with `E_TEMPORAL_DOMAIN_MISMATCH`; the scheduler MUST NOT
invent a Date-to-midnight conversion. Recurrence occurrences are derived scheduling
inputs selected by an explicit occurrence policy and are not independently scheduled
objects.

## 2. Placement modes

### 2.1 Fixed

A fixed placement supplies authoritative temporal coordinates.

Point:

```text
at = fixed value
```

Span:

```text
start = fixed value
end   = fixed value
```

Duration is derived from fixed span endpoints.

### 2.2 Derived

A derived placement obtains coordinates deterministically from semantic state.

A summary span may use:

```text
start = min(children.start)
end   = max(children.end)
```

The derivation rule MUST be explicit and deterministic.

### 2.3 Scheduled

A scheduled placement is solved from some combination of:

- an anchor;
- temporal amount;
- dependencies;
- explicit bounds;
- calendar validity;
- project scheduling context.

A scheduled span SHOULD avoid storing mutually redundant authoritative values.

## 3. Schedule authority

A span MUST NOT ambiguously treat `start`, `end`, and amount as three independent
authorities.

Valid scheduled forms include conceptually:

```text
start anchor + amount -> end
end anchor   + amount -> start
dependencies/bounds + amount -> placement
```

Fixed spans use explicit start and end instead.

## 4. Endpoints

Core endpoints are:

```text
TemporalPoint:
  at

TemporalSpan:
  start
  end
```

A dependency connects a source endpoint to a target endpoint.

## 5. Dependency semantics

A dependency imposes a lower bound:

```text
target.endpoint >= advance(source.endpoint, lag)
```

The dependency does not normally impose equality.

This allows multiple dependencies and constraints to contribute bounds to the same
endpoint.

### 5.1 Conventional dependency names

Traditional dependency types are aliases over endpoint pairs:

```text
FS = end   -> start
SS = start -> start
FF = end   -> end
SF = start -> end
```

The endpoint pair is the semantic primitive. FS/SS/FF/SF are compatibility vocabulary.

## 6. Zero lag

Zero lag is identity:

```text
advance(t, 0) = t
```

For a half-open predecessor span:

```text
A.end == B.start
```

is a valid adjacent Finish-to-Start schedule with no implicit extra day.

No “finish date + 1” correction is part of Core semantics.

## 7. Positive and negative lag

Lag MAY be positive, zero, or negative.

Examples:

```text
FS + 3d:
B.start >= A.end + 3 calendar days

FS - 3d:
B.start >= A.end - 3 calendar days
```

Negative lag is valid but SHOULD be surfaced by linting because explicit overlapping
work may communicate intent more clearly.

## 8. WorkPeriod lag

A WorkPeriod lag requires a calendar.

Default calendar resolution for dependency lag is:

```text
explicit relation lag calendar
        ↓
target object's scheduling calendar
        ↓
project default calendar
```

This is a Core v0.1 design choice and SHOULD be covered by conformance examples.

Dependency lag arithmetic and target placement validity are separate operations.

For example, `FS + 0wd` produces the predecessor endpoint unchanged. If the resulting
target start is a non-working date and the target is subject to working-calendar
placement, the scheduler moves to a valid position according to the target's calendar
rule. The dependency itself does not perform that adjustment.

## 9. Bounds

Scheduling constraints normalize to lower or upper endpoint bounds.

```text
lower:
endpoint >= value

upper:
endpoint <= value
```

Examples:

```text
start not before 2026-10-01
=> start >= 2026-10-01

end not after 2026-11-30
=> end <= 2026-11-30
```

This is preferred over encoding every constraint combination as a distinct core enum.

## 10. Deadlines

A deadline is not a scheduling bound.

A deadline expresses a target against which a resolved schedule can be evaluated.

```text
deadline: 2026-11-30
```

does not imply:

```text
end <= 2026-11-30
```

A deadline violation may produce derived state or a diagnostic.

## 11. Span amount rule

For a start-anchored scheduled span:

```text
end = advance(start, amount)
```

For an end-anchored scheduled span:

```text
start = retreat(end, amount)
```

The amount MUST be a type permitted for scheduled span amounts by the Temporal Model.

In Core v0.1, calendar-month and calendar-year periods are offsets but are not valid
scheduled span amounts. This prevents month-end clamp behavior from making task
duration depend on propagation direction.

Implementations MUST follow the Temporal Model's `advance` and `retreat` semantics.

## 12. Calendar validity

Calendar validity is a property of scheduled placement, not of dependency semantics.

Conceptually:

```text
dependency/bounds
       ↓
candidate endpoint
       ↓
calendar validity
       ↓
resolved endpoint
```

Core v0.1 uses date-level working validity for WorkPeriod and working-day scheduling.

Intraday resource scheduling is outside scope.

## 13. Multiple dependencies

Dependencies produce independent lower bounds.

If:

```text
B.start >= A.end
B.start >= C.end
```

then the earliest feasible B start is bounded by the later of the two resolved values,
subject to other constraints and calendar validity.

## 14. Point dependencies

Point and Span endpoints participate uniformly.

Examples:

```text
milestone.at -> task.start
task.end     -> milestone.at
point.at     -> point.at
```

The same dependency inequality applies.

## 15. Summary/derived objects

Dependencies involving derived summary objects MAY be supported because their
endpoints are resolvable semantic values.

Implementations SHOULD lint such relations when they may obscure the actual causal
dependency between leaf objects.


## 15.1 Dependency bounds on fixed objects

A dependency may be evaluated against a fixed object, but it does not move that
object.

For a fixed target, the dependency acts as a **validation condition**:

```text
fixed target endpoint >= dependency lower bound
```

If the condition is false, the schedule is inconsistent and a diagnostic is produced.

For a scheduled target, the same dependency lower bound participates in placement.

This preserves a single dependency meaning while keeping placement authority explicit.

## 16. Cycles and unsatisfiable schedules

A scheduling implementation MUST detect contradictory bounds and unsatisfiable
dependency systems.

A graph cycle is **not by itself defined as an error**. Endpoint inequalities with
zero or negative lag can contain cycles that are satisfiable. An implementation MAY
initially support only an acyclic subset, but it MUST diagnose an unsupported cyclic
system as a capability limitation rather than claim that every cycle is semantically
invalid.

Core v0.1 does not require a general constraint-programming solver.

A DAG-based propagation implementation is conforming for the acyclic subset if it
produces the normative semantics and diagnostics required by the specification.

## 17. Actual values

Actual start, finish, and progress are observations and are not automatically used as
dependency solver inputs in Core v0.1.

Policies that reschedule remaining work based on actual progress are deferred.

## 18. Diagnostics

The scheduling layer SHOULD distinguish at least:

- invalid temporal types;
- unresolved references;
- unsupported or unsatisfiable dependency cycle/system;
- contradictory bounds;
- missing calendar for WorkPeriod;
- impossible calendar placement;
- invalid or empty span;
- deadline violation;
- negative-lag lint warning.

## 19. Scheduling invariants

- Dependency semantics are endpoint-based.
- Dependencies impose bounds, not implicit equality.
- Zero lag introduces no hidden day adjustment.
- Lag arithmetic is separate from target calendar validity.
- Deadlines do not constrain scheduling.
- View and renderer state do not affect scheduling.
- Actual values do not silently redefine planned scheduling.
- Ready-object evaluation, returned placements, and multi-object diagnostics preserve
  Project object order; process hash order is never observable.
- A dependency endpoint must exist on the referenced placement kind: fixed points
  expose `at`, while fixed and scheduled spans expose `start` and `end`.
- Calendar requirements are derived from parsed temporal-amount components. Any `wd`
  component requires a working calendar, regardless of component position.

## 20. Feasibility and authority rules

Core v0.1 distinguishes **authority** from **constraints**.

### 20.1 Fixed placement

Fixed coordinates are authoritative. Bounds and dependencies do not move a fixed
object. They validate it.

A violated bound on a fixed object produces `E_FIXED_TARGET_VIOLATION`.

### 20.2 Scheduled placement with explicit anchor

An explicit anchor is authoritative for the anchored endpoint.

If another bound requires that anchored endpoint to move, the schedule is inconsistent
rather than silently overriding the anchor.

The opposite endpoint is derived from the amount and may then be checked against its
bounds.

If an opposite-endpoint lower bound is later than that derived endpoint, satisfying it
would require moving the authoritative anchor. The result is
`E_CONTRADICTORY_BOUNDS`; the scheduler does not replace the anchor.

### 20.3 Scheduled placement without explicit anchor

For an acyclic forward-scheduling implementation, the earliest feasible start is the
maximum of all applicable start lower bounds after their values are computed.

An end lower bound contributes the start candidate obtained by retreating from that
bound by the scheduled amount. It never becomes a start date directly. When both start
and end lower bounds exist, choose the maximum of the start lower bound and every
retreated end-bound candidate.

The scheduler then applies target calendar placement validity and derives the end from
the scheduled amount.

Upper bounds are feasibility checks unless a backward-scheduling policy explicitly
uses an end authority. Core v0.1 does not silently switch scheduling direction merely
because an upper bound exists.

## 21. Calendar placement normalization

For Date-based scheduled objects using a working calendar:

- a candidate start produced by bounds MAY fall on a non-working date;
- the earliest feasible forward placement is the first working date `>= candidate`;
- this normalization is part of target placement, not dependency arithmetic;
- a fixed endpoint is never normalized;
- an explicit start anchor on a non-working date is invalid for a WorkPeriod scheduled
  span rather than silently moved.

For CalendarPeriod `d`/`w` scheduled spans, calendar working validity does not change
the calendar-day arithmetic unless the object's scheduling policy explicitly uses a
WorkPeriod.

## 22. Duration and endpoint counting

For Date spans:

```text
start = 2026-10-01
end   = 2026-10-10
```

the span occupies nine calendar dates and has calendar-day difference `9d`.

For a WorkPeriod scheduled span:

```text
start = Monday
amount = 1wd
end = Tuesday
```

The span occupies one working date under half-open semantics.

Thus `Nwd` advances the exclusive end boundary by N working-date transitions.

## 23. Conformance subset

Core v0.1 required scheduling conformance is Date-based.

A conforming scheduler MUST support:

- fixed Date points and spans;
- scheduled Date spans with positive `d`, `w`, or `wd`;
- endpoint dependencies;
- signed Date-based lag using `d`, `w`, or `wd`;
- lower/upper Date bounds;
- date-level working calendars and exceptions;
- fixed-target validation;
- deadline diagnostics.

DateTime scheduling is optional in v0.1.

## 24. Diagnostic identifiers

Normative diagnostic identifiers are defined in `core-v0.1-diagnostics.md`.

Implementations may provide richer messages and structured details while preserving
the identifier meaning.

## 25. Resource-leveling successor evaluation

Ordinary v0.1 scheduling has no resource-capacity input. The successor may perform a
separate leveling evaluation only when the caller explicitly supplies the Project
revision, capacity-set revision, assignment set, objective, movement scope, and
deterministic tie-break rule. Its output is overload diagnostics plus an optional
derived proposal of permitted placement changes.

The evaluator MUST retain fixed placements, explicit anchors, dependency/bound
feasibility, and unit compatibility as hard constraints. An infeasible capacity result
is a diagnostic, not permission to relax any of them. Applying a selected proposal is
outside evaluation and is validated by the Command Model at the then-current Project
revision.
