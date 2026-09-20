# Temporal Model

**Status:** Stable
**Core Specification:** v0.1

## 1. Scope

This document defines time values and arithmetic independently of tasks, dependencies,
YAML syntax, and rendering.

## 2. Temporal coordinate domains

Core v0.1 defines two coordinate domains.

### 2.1 Date

A `Date` identifies a calendar date without a time-of-day or timezone.

`2027-03-15` MUST NOT be silently interpreted as midnight in a timezone.

### 2.2 DateTime

A `DateTime` identifies a date and time with sufficient zone/offset semantics to
determine temporal arithmetic.

Date and DateTime are distinct. Cross-domain comparison or dependency is invalid
unless an explicit conversion policy is supplied outside Core v0.1.

## 3. Point semantics

A TemporalPoint occupies one coordinate in its temporal domain.

A Date-based point denotes a calendar position, not an implied midnight instant.

## 4. Span semantics

A resolved TemporalSpan is a half-open interval:

```text
[start, end)
```

`start` is included and `end` is excluded.

A resolved span MUST satisfy `start < end`.

Consequences:

- adjacent spans may satisfy `A.end == B.start` without overlap;
- duration calculations avoid an implicit “plus one day” rule;
- a zero-length span is invalid and SHOULD be represented as a point.

Human-facing inclusive end-date display MAY be provided by a View or renderer, but it
MUST NOT alter stored or scheduled semantics.

## 5. Temporal amounts

Temporal amounts serve two different roles:

- **offsets**, which move a temporal coordinate;
- **scheduled span amounts**, which describe schedulable working extent.

Not every offset type is valid as a scheduled span amount.

### 5.1 ExactDuration

An ExactDuration is physical elapsed time.

Core units:

```text
h
min
s
```

Smaller units MAY be added by implementations if serialization remains unambiguous.

Examples:

```text
72h
90min
30s
```

ExactDuration does not depend on a calendar.

### 5.2 CalendarPeriod

A CalendarPeriod is calendar-relative and retains calendar components rather than
normalizing them to elapsed seconds.

Core components:

```text
years
months
weeks
days
```

Examples:

```text
3d
2w
1mo
1y
1mo 3d
```

Normative shorthand:

```text
1w = 7 calendar days
```

Quarter MAY be accepted as convenience syntax and MUST normalize to three months if
introduced. Core v0.1 does not require quarter arithmetic syntax.

CalendarPeriod components are integer-valued in Core v0.1.

### 5.3 WorkPeriod

A WorkPeriod is a discrete count of working dates.

Core v0.1 defines only:

```text
wd = working day
```

Examples:

```text
1wd
5wd
-2wd
```

WorkPeriod requires a Calendar and a starting coordinate to resolve.

`0wd` is the identity operation. It does not mean “next working day.”

Fractional working days and working-hour arithmetic are outside Core v0.1.

## 6. Non-convertibility

The following implicit conversions are invalid:

```text
CalendarPeriod -> ExactDuration
WorkPeriod     -> CalendarPeriod
WorkPeriod     -> ExactDuration
```

For example:

```text
1d != 24h        in the general DateTime case
1mo != 30d
5wd != 5d
```

A conversion MAY be computed only with the explicit anchor/context required to resolve
the amount.

## 7. Arithmetic

Required operations include:

```text
Date + CalendarPeriod -> Date
Date + WorkPeriod     -> Date       [Calendar required]

DateTime + ExactDuration  -> DateTime
DateTime + CalendarPeriod -> DateTime

ExactDuration + ExactDuration   -> ExactDuration
CalendarPeriod + CalendarPeriod -> CalendarPeriod
WorkPeriod + WorkPeriod         -> WorkPeriod
```

Mixed amount addition is not implicitly defined.

### 7.1 Date difference

`Date - Date` SHOULD produce a day-component CalendarPeriod rather than attempting to
infer months or years.

Example:

```text
2026-10-01 -> 2026-11-01 = 31d
```

Calendar-aware month/year difference, if required, MUST be an explicit operation.

## 8. Calendar-period application order

When a CalendarPeriod contains multiple components, application order MUST be
deterministic.

Core v0.1 applies components from largest to smallest:

```text
year -> month -> week -> day
```

The result of each component becomes the input to the next.

## 9. Month-end policy

Month/year arithmetic can target a date that does not exist.

All accepted ISO Dates use the proleptic Gregorian leap-year rule: a year divisible by
4 is a leap year, except a year divisible by 100 is common unless it is also divisible
by 400. Implementations MUST derive the final valid day of the target month from this
general rule and MUST NOT use year-specific exceptions.

Core v0.1 uses **clamp** semantics:

```text
2026-01-31 + 1mo -> 2026-02-28
```

The result is clamped to the final valid day of the target month.

Because clamp arithmetic is not generally invertible, implementations MUST NOT assume:

```text
retreat(advance(t, p), p) == t
```

for all CalendarPeriods.

The exact `advance`/`retreat` conformance cases SHALL be captured in temporal test
fixtures before Core v0.1 becomes Stable. A representative leap-year case is sufficient
when the implementation uses a general Gregorian calendar operation rather than
year-specific branching.

## 10. WorkPeriod arithmetic

For a calendar defining Monday-Friday as working dates:

```text
Friday + 0wd -> Friday
Friday + 1wd -> Monday
Friday + 2wd -> Tuesday
```

The operation counts transitions to valid working dates.

If the starting date itself is non-working, `0wd` remains the starting date. Calendar
validity of a scheduled task is a separate scheduling rule.

Negative WorkPeriod uses the corresponding backward traversal over working dates.

## 11. Calendar

Core v0.1 Calendar represents date-level working validity.

A calendar contains conceptually:

- a repeating weekly working-day pattern;
- date exceptions overriding that pattern.

Core v0.1 intentionally excludes:

- work shifts;
- intraday breaks;
- resource capacity;
- resource-specific availability;
- fractional working days.

A temporal object MAY select a calendar. Otherwise the Project default calendar is
used when a calendar is required.

## 12. Precision

Temporal precision records the information actually supplied rather than inventing a
false exact date.

Examples of useful precision include:

```text
year
quarter
month
week
day
```

A coarse point such as `2027-Q1` is semantically different from a span covering all of
Q1.

Core v0.1 defines the concept. Exact persistent syntax for every coarse precision form
may remain provisional until Project Format stabilization.

## 13. Uncertainty

Precision and uncertainty are distinct.

Precision means that the value is stated only to a certain granularity.

Uncertainty means that the value is known to lie within a range.

Conceptually:

```text
at:
  earliest: 2026-11-10
  latest:   2026-11-20
```

Core v0.1 reserves this semantic distinction but does not require the scheduler to
solve uncertain dates.

## 14. Explicit evaluation context

Dynamic values such as “today” MUST come from an explicit evaluation/render context
rather than hidden global state when reproducibility matters.

For example, CI MAY evaluate with a fixed context date.

## 15. Scheduling suitability

Core v0.1 classifies amount types by scheduling suitability:

```text
ExactDuration   offset: yes   scheduled span amount: DateTime schedules only
CalendarPeriod  offset: yes   scheduled span amount: Date schedules, d/w only
WorkPeriod      offset: yes   scheduled span amount: Date schedules, wd only
```

A scheduled span amount MUST be strictly positive. Zero and negative values are
invalid as span amounts even though signed amounts are valid for offsets and
dependency lag.

Calendar months and years (`mo`, `y`) are deliberately **not valid scheduled span
amounts in Core v0.1**. They remain valid temporal offsets.

Reason: month-end clamp arithmetic is not generally reversible. Allowing `1mo` as an
authoritative task duration would make start-anchored and end-anchored scheduling
direction-dependent in ways that are difficult to explain and validate.

A future specification MAY introduce a separate calendar-month scheduling policy if a
real use case requires it.

## 16. Temporal invariants

- Date and DateTime are not implicitly mixed.
- Span intervals are half-open.
- ExactDuration, CalendarPeriod, and WorkPeriod remain distinct.
- Month and year periods are not normalized to days.
- WorkPeriod requires a Calendar.
- CalendarPeriod and WorkPeriod use integer components in Core v0.1.
- Temporal arithmetic is deterministic for identical inputs and context.

## 17. Required v0.1 conformance profile

Core v0.1 scheduling conformance is Date-based.

DateTime and ExactDuration remain semantic types so the model does not collapse a
calendar date into an instant, but timezone/DST-aware scheduling is not required by
the v0.1 scheduler profile.

For Date scheduling:

- `d` is one calendar-day step;
- `w` is exactly seven calendar-day steps;
- `wd` traverses working dates using a resolved Calendar;
- `mo` and `y` are valid offset operations but not scheduled span amounts.

This boundary is defined by ADR-0011.
