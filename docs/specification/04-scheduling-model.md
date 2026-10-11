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

A **scheduled point** (`scheduled-point`) is the point counterpart: it stores no date and its single
endpoint `at` is solved from dependencies and an optional lower bound (Section 20.4). Like a fixed point it
exposes `at` only; like a scheduled span the scheduler owns its date.

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

A fixed point and a scheduled point are `TemporalPoint`s and expose `at`; fixed spans, scheduled spans and
rollups are `TemporalSpan`s.

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

A deadline violation produces the warning `W_DEADLINE` and nothing else: no placement, verdict, analysis or
diagnostic error changes, and a plan with a missed deadline is still scheduled and drawn.

The finish of an object is `at` for a point and `end` for a span (the stored value that `constraints.end.max` also
compares, Section 9); a rollup's finish is its `end`. The warning is raised when the finish is strictly later than the
deadline; a finish equal to the deadline keeps it. Only planned placements are judged: an Actual never counts
(Section 17), and a scenario is judged only when it is the scheduled Project. The evaluation is a pure function of the
Project and its placements, applied after scheduling; the scheduler itself never reads `deadline`. A `deadline` that is
not a calendar date is `E_SCHEMA` at `/objects/<id>/deadline`.

The warning carries `details` with the stable keys `object`, `endpoint` (`at` or `end`), `finish`, `deadline` (ISO
dates) and `daysLate` (calendar days, at least 1), and the pointer `/objects/<id>/deadline`. Warnings follow Project
object order. `chrona schedule` prints them as the `warnings` array of its result, beside an empty `diagnostics`;
`chrona validate` computes no placements and does not judge a deadline.

A View may draw the finished verdict (Spec 06 section 7.3): a tick at the deadline date and, for a slipped deadline, a run
to the planned finish. The verdict is the same one `W_DEADLINE` names (`core/deadlines.py` `deadline_statuses`), so the
picture and the warning cannot disagree, and drawing it changes no placement, verdict or analysis.

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

For a scheduled point the dependency lower bound participates in placement (Section 20.4); a gate that must
not move is a fixed point, and a gate that follows its predecessors is a scheduled point.

## 16. Cycles and unsatisfiable schedules

A scheduling implementation MUST detect contradictory bounds and unsatisfiable
dependency systems.

A graph cycle is **not by itself defined as an error**. Endpoint inequalities with
zero or negative lag can contain cycles that are satisfiable. An implementation MAY
initially support only an acyclic subset, but it MUST diagnose an unsupported cyclic
system as a capability limitation rather than claim that every cycle is semantically
invalid.

The reference implementation (`chrona validate` and `chrona schedule`, one use case, #780) reports an unsupported
cyclic system with the same diagnostic from both commands, before any date is computed: a set of objects that wait
for each other (a non-fixed object waits for the source of every relation into it, a rollup for its children), and
a loop of non-negative-lag relations through a fixed object. One diagnostic names the objects on the cycle in Project
order and points at `/relations/<index>` of the relation declared last inside it; the code is `E_UNSATISFIABLE_DEPENDENCIES`
when the calendar-day relations of the cycle contain a positive loop, otherwise `E_UNSUPPORTED_CYCLE`. A loop with a
negative lag is left to the date check, because it can be satisfiable.

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

A violated bound on a fixed object produces `E_FIXED_TARGET_VIOLATION`, one diagnostic per violating
relation. The diagnostic names the earliest feasible date of the fixed endpoint, which is the maximum of the
`source endpoint + lag` dates (Section 15.1; a lag with a `wd` part uses the lag's own calendar, else the target object's, else the Project's) of every relation into that
endpoint, and the relation that gives it (the first in declaration order on a tie). For a fixed span the answer is
per endpoint: it does not claim a full re-placement of the span. Substituting the reported date for the fixed
date makes that relation satisfied; the scheduler never proposes or applies the correction itself.

The diagnostic carries an optional `details` object with these stable keys (keys may be added, never renamed):
`object`, `endpoint`, `placed` (the fixed date), `relation` (the relation `id`, or `/relations/N` with `N` the
zero-based index when it has none), `from` (`{object, endpoint, value}` of the source), `lag` (the Project value
verbatim), `required` (this relation's date), `earliest` and `forcedBy` (a relation key as in `relation`). Dates are
ISO strings. The pointer of the diagnostic is `/relations/<id>` or, for a relation without an `id`,
`/relations/N`. The message text is not normative.

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

### 20.4 Scheduled point

A point with `schedule.mode: scheduled-point` has no stored date. Its only optional properties are
`constraints.at.min` (not earlier than) and `constraints.at.max` (not later than, a hard cap). It has no
`amount` and no `anchor`, and it exposes the endpoint `at` only (a relation naming `start` or `end` on it is
`E_ENDPOINT_MODE_MISMATCH`).

```text
bounds(P) = { advance(source value, lag, calendar) : each relation into P.at } + { constraints.at.min }
at(P)     = max(bounds(P))
```

`calendar` is the lag's own `calendar`, else the object's, else the Project's; only a lag with a `wd` part uses
one (Section 8). The date is placed exactly: it is **not** normalized to a working day (Section 21 normalizes
the start of a scheduled span; a point has no amount, and a lag in `d` from a Friday lands on a Sunday). An
author who wants working days writes `wd` in the lag. When the floor equals a dependency bound the floor wins
silently.

Consequences, each a tested property: a scheduled point and the fixed point at its derived date are
interchangeable (the scheduler accepts the substitution with identical placements, and a presentation of
either is identical); a fixed point one day earlier is rejected with `E_FIXED_TARGET_VIOLATION` whose
`details.earliest` is the derived date (unless the floor is binding); a later predecessor never makes the
date earlier; placement does not depend on object or relation order.

If `constraints.at.max` is present and the derived date is later, the schedule fails with
`E_CONTRADICTORY_BOUNDS` at `/objects/<id>/schedule/constraints/at/max`, and the placement is still returned.
`details` is `{object, endpoint, derived, max, forcedBy}`, `forcedBy` naming the relation (id, else
`/relations/N`) that reaches the derived date, or the pointer of the floor when the floor does. A `min` later
than `max` is the same diagnostic. A point with no relation into `at` and no `min` has nothing to derive from:
`E_DERIVATION` at `/objects/<id>/schedule`, reported by validation, so `validate` and `schedule` agree. A
cycle through scheduled points is reported by the scheduler like any other cycle (Section 16).

Analysis treats a scheduled point like any other non-fixed object: it has float
and joins the critical path when it meets the project-finish/zero-float
driving-path rule. Its latest date honours `constraints.at.max`.
Fixed/anchored dates stay fixed in the backward pass but are not critical
merely because they cannot move. The global terminal target, critical
membership, unit-bearing float and backward lag rule are stated in
[Spec 57](57-public-schedule-analysis.md).

A scheduled point is a derived **plan**, not a forecast. Actual values never move a planned date
(Section 17): a late predecessor actual does not move the gate; editing the plan does. A scheduled point is not
a promise either; the hard cap is `constraints.at.max`, and `deadline` remains a target the scheduler
never reads; it is judged afterwards and warns (Section 10).

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
- scheduled Date points (Section 20.4) where the Project format admits `scheduled-point`;
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
