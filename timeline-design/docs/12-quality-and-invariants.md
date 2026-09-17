# Quality Goals and Architectural Invariants

**Status:** Proposed  
**Core Specification:** v0.1

## 1. Purpose

This document defines reviewable system qualities and invariants that cut across the
Core Specification.

## 2. Git quality

### Q-GIT-1 Meaningful diff

A simple semantic schedule edit SHOULD produce a small diff focused on the changed
semantic value.

Moving a milestone must not require updating renderer coordinates, unrelated objects,
or generated caches.

### Q-GIT-2 Stable identity

Renaming an object SHOULD NOT require changing its identifier or references unless the
user explicitly chooses to rename the identifier.

### Q-GIT-3 Derived-state exclusion

Deterministically derived scene and renderer state MUST NOT be required in the
semantic project source.

## 3. Determinism

### Q-DET-1 Scheduling

The same Project, profiles, calendars, and explicit scheduling context MUST produce
the same resolved schedule.

### Q-DET-2 Rendering boundary

The same resolved semantic project plus View, Style, Theme, and explicit RenderContext
SHOULD produce equivalent scene output.

Dynamic values such as `today` must be explicit context when reproducibility is
required.

## 4. Semantic isolation

### Q-SEM-1 Presentation independence

View, Style, Theme, Scene, and renderer state MUST NOT alter project scheduling
semantics.

### Q-SEM-2 Renderer independence

Domain data MUST remain usable without tldraw or any other renderer.

### Q-SEM-3 Serialization independence

YAML shorthand MUST normalize into the semantic model; shorthand syntax MUST NOT
introduce semantics that do not exist in the model.

## 5. Temporal correctness

### Q-TIME-1 Type distinction

Date and DateTime MUST NOT be silently mixed.

ExactDuration, CalendarPeriod, and WorkPeriod MUST remain distinct.

### Q-TIME-2 Interval consistency

Resolved spans MUST use `[start, end)` semantics and MUST be non-empty.

### Q-TIME-3 No hidden day adjustment

Finish-to-Start zero lag MUST allow `predecessor.end == successor.start`.

### Q-TIME-4 Explicit calendar dependency

WorkPeriod arithmetic MUST NOT resolve without a calendar.

### Q-TIME-5 Scheduling-safe amount types

Calendar-month and calendar-year periods MUST NOT be accepted as scheduled span
amounts in Core v0.1. They remain valid temporal offsets.

## 6. Scheduling correctness

### Q-SCHED-1 Endpoint semantics

Dependencies MUST be reducible to endpoint bounds.

### Q-SCHED-2 Deadline distinction

A deadline MUST NOT silently become a scheduling constraint.

### Q-SCHED-3 Conflict diagnostics

Unsatisfiable bounds, cycles, missing calendars, and invalid temporal types MUST
produce diagnostics rather than arbitrary schedule output.

## 7. Extensibility

### Q-EXT-1 Known base semantics

A declarative custom profile MUST inherit from a known semantic primitive.

### Q-EXT-2 Fallback

A consumer that does not understand a custom profile SHOULD be able to fall back
through its inheritance chain where safe.

### Q-EXT-3 Typed fields

Extension fields SHOULD be schema-declared and type-checkable.

### Q-EXT-4 Safe expressions

User-defined predicates and derived expressions MUST NOT permit arbitrary host-language
code execution.

## 8. Agent operability

### Q-AI-1 Semantic mutation

A schedule edit SHOULD be expressible as a semantic command rather than a sequence of
pixel manipulations.

### Q-AI-2 Explainability

Validation, scheduling, and style resolution SHOULD expose enough structured
diagnostics to explain why a value or appearance was produced.

### Q-AI-3 Discoverability

Schemas, profiles, and examples SHOULD provide sufficient structure for an agent to
discover valid operations without relying solely on prose documentation.

## 9. Scope discipline

Core design SHOULD reject features that require turning the system into:

- a resource optimizer;
- a timesheet system;
- a generic workflow engine;
- a generic graph database;
- an arbitrary programmable scheduler.

Such features MAY be reconsidered as extensions when they can preserve Core invariants.

## 10. Core v0.1 review checklist

Core v0.1 is internally coherent when all of the following hold:

- every core primitive has one semantic definition;
- temporal arithmetic is type-distinct and deterministic;
- interval boundaries are unambiguous;
- dependency endpoint semantics are unambiguous;
- zero-lag behavior is demonstrated by examples;
- calendar-day and working-day behavior are distinguishable;
- Project Format can represent all normative Core concepts;
- canonical examples satisfy the intended schema;
- major irreversible choices have ADRs;
- no normative Core rule depends on a renderer.
