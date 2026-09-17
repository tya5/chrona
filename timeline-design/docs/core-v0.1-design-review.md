# Core Specification v0.1 Design Review

**Review status:** Completed  
**Result:** Draft retained; specification materially tightened toward Proposed.

## 1. Summary

The Core architecture is coherent: semantic primitives, temporal algebra, scheduling,
and serialization have useful boundaries and do not depend on a renderer.

The review found two correctness issues significant enough to change the draft:

1. calendar-month/year periods should not be authoritative scheduled task durations;
2. dependency cycles cannot be declared invalid merely because they are cycles.

Both are corrected in the current artifact set.

## 2. Accepted corrections

### R1 — Restrict month/year task duration

`CalendarPeriod` remains useful for offsets such as `+1mo`, but `mo` and `y` are not
accepted as `schedule.amount` in Core v0.1.

This avoids direction-dependent task duration caused by month-end clamp arithmetic.

### R2 — Cycles are not automatically semantic errors

The dependency model is a system of endpoint inequalities. A graph cycle may be
satisfiable. Core therefore requires detection of unsatisfiable systems, while an
implementation may explicitly support only an acyclic scheduling subset.

### R3 — Fixed dependency targets removed from canonical examples

A fixed target has authoritative placement. A dependency that would move it cannot
simultaneously be authoritative scheduling input. Canonical examples no longer imply
otherwise.

## 3. Remaining Proposed decisions

### P1 — WorkPeriod dependency-lag calendar

Current proposal:

```text
explicit relation calendar
-> target scheduling calendar
-> project default
```

This is deterministic and simple but remains Proposed pending additional real-world
examples.

## 4. Deferred rather than blocking Core

The following are intentionally deferred and should not block the semantic core:

- uncertainty scheduling;
- complete coarse-precision serialization;
- multi-file include/merge rules;
- external extension package resolution;
- snapshots/baselines;
- actual-progress rescheduling;
- presentation and renderer architecture.

## 5. Readiness assessment

### Coherent enough for Proposed

- semantic primitive set;
- Point/Span distinction;
- half-open span semantics;
- Date vs DateTime distinction;
- temporal amount type separation;
- endpoint-based dependency semantics;
- bound-based constraints;
- deadline/constraint separation;
- Project Format ownership boundary;
- renderer independence.

### Needs conformance fixtures before Stable

- month-end `advance`/`retreat` table;
- WorkPeriod traversal from working and non-working dates;
- target-calendar lag examples;
- contradictory-bound examples;
- cycle examples;
- scheduled span amount validation;
- fixed/derived/scheduled authority conflict cases.

## 6. Recommendation

Move the major Core documents from **Draft** to **Proposed** after the conformance
fixture set is added and validated mechanically.

Do not mark Core v0.1 Stable until those fixtures exist. Stable should mean the
temporal and scheduling semantics are executable as tests, not merely well described.

## 7. Hole-closing pass

A second review pass added normative conformance cases and resolved several ambiguous
edges:

- `0wd` is identity even on a non-working source date;
- working-day traversal counts valid dates strictly after/before the source for
  non-zero amounts;
- holiday exceptions and working-day exceptions are covered;
- zero/negative scheduled span amounts are invalid;
- Date scheduled spans accept `d`, `w`, and `wd`; DateTime elapsed scheduling remains
  conceptually distinct;
- dependencies targeting fixed objects validate rather than move them;
- zero-lag cycles are not automatically invalid;
- positive contradictory cycles are explicitly unsatisfiable;
- ADR-0009 target-calendar lag policy is now Accepted.

### Remaining blockers before Stable

The remaining blockers are now implementation/conformance oriented rather than major
semantic-model questions:

1. mechanically validate every canonical example against the structural schema;
2. turn `conformance-v0.1.yaml` into executable tests in the first implementation;
3. decide whether DateTime scheduling belongs in v0.1 implementation conformance or
   remains a semantic capability with implementation support optional;
4. freeze exact error/diagnostic identifiers.

The Core semantic documents are ready to move to **Proposed**.
