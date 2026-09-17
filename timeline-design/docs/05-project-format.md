# Project Format

**Status:** Proposed  
**Core Specification:** v0.1

## 1. Scope

This document defines the initial human-readable persistent representation of Core
project semantics.

YAML is the normative interchange syntax for Core v0.1 examples.

The semantic models remain authoritative for meaning; this document owns serialization
and normalization.

## 2. Design goals

The format SHOULD be:

- readable without specialized tooling;
- stable under ordinary edits;
- friendly to line-oriented Git diffs;
- explicit where ambiguity would affect semantics;
- concise for common cases;
- extensible through versioned profiles and schemas;
- deterministic to normalize.

## 3. Top-level structure

Initial canonical structure:

```yaml
version: timeline/v0.1

project:
  id: example
  title: Example Project
  calendar: standard

calendars: {}
entities: {}
objects: {}
relations: []
annotations: {}
```

Empty sections MAY be omitted.

## 4. Objects

Objects are keyed by stable identifier.

### 4.1 Fixed span

```yaml
objects:
  fw:
    type: task
    title: Firmware
    schedule:
      mode: fixed
      start: 2026-10-01
      end: 2026-10-30
```

The end is exclusive.

### 4.2 Fixed point

```yaml
objects:
  evt:
    type: milestone
    title: EVT
    schedule:
      mode: fixed
      at: 2026-11-15
```

### 4.3 Scheduled span

```yaml
objects:
  validation:
    type: task
    title: Validation
    schedule:
      mode: scheduled
      amount: 10wd
```

An optional explicit anchor may be supplied:

```yaml
schedule:
  mode: scheduled
  anchor:
    start: 2026-10-01
  amount: 20d
```

or:

```yaml
schedule:
  mode: scheduled
  anchor:
    end: 2026-10-30
  amount: 20d
```

### 4.4 Derived span

```yaml
objects:
  development:
    type: phase
    title: Development
    children: [fw, validation]
    schedule:
      mode: derived
      from: children
```

The exact set of standardized derivation strategies may grow after v0.1.

## 5. Temporal amount syntax

Core shorthand:

```text
72h     ExactDuration
90min   ExactDuration
3d      CalendarPeriod
2w      CalendarPeriod
1mo     CalendarPeriod
1y      CalendarPeriod
5wd     WorkPeriod
```

Compound CalendarPeriod values MAY use a space-separated form such as `1mo 3d`.

For `schedule.amount`, Core v0.1 accepts only amount types permitted as scheduled span
amounts by the Temporal Model. In particular, `mo` and `y` remain valid offset syntax
but are invalid as scheduled task duration.

Ambiguous shorthand such as bare numeric duration values is invalid.

## 6. Calendars

Initial representation:

```yaml
calendars:
  standard:
    working_days: [mon, tue, wed, thu, fri]
    exceptions:
      - date: 2027-01-01
        working: false
```

An object may override the project calendar:

```yaml
objects:
  factory-test:
    type: task
    calendar: factory
```

Calendar inheritance and external holiday feeds are deferred until reproducibility and
versioning rules are specified.

## 7. Relations

Canonical dependency representation uses explicit endpoints.

```yaml
relations:
  - id: fw-to-validation
    type: dependency
    from:
      object: fw
      endpoint: end
    to:
      object: validation
      endpoint: start
    lag: 3wd
```

If `lag` is omitted, it normalizes to `0d`.

For Core v0.1 Date scheduling, dependency lag accepts signed `d`, `w`, or `wd`.
Month/year lag is not part of required scheduler conformance.

A concise form MAY be accepted:

```yaml
relations:
  - type: dependency
    from: fw.end
    to: validation.start
    lag: 3wd
```

Normalization MUST produce the explicit endpoint representation.

FS/SS/FF/SF MAY be supported for import/export but are not required in canonical
project files.

A dependency whose target is `fixed` does not move the target. It is validated against
the fixed endpoint and produces a schedule inconsistency diagnostic if the lower bound
is violated. The same dependency moves/constrains a `scheduled` target.


### 7.1 Explicit lag calendar

```yaml
lag:
  value: 3wd
  calendar: factory
```

Scalar `3wd` uses scheduling calendar resolution rules.

## 8. Constraints

Initial syntax:

```yaml
schedule:
  mode: scheduled
  amount: 10wd
  constraints:
    start:
      min: 2026-10-01
      max: 2026-10-10
    end:
      max: 2026-11-30
```

`min` and `max` serialize lower and upper bounds.

## 9. Deadline

A deadline is serialized separately from constraints.

```yaml
deadline: 2026-11-30
```

A parser MUST NOT normalize a deadline into an upper scheduling bound.

## 10. Entities and typed references

Example:

```yaml
entities:
  fw-team:
    type: team
    title: Firmware Team

  controller:
    type: component
    title: Controller

objects:
  fw:
    type: task
    fields:
      team: fw-team
      component: controller
```

Profile/extension schemas define whether a field is a reference and what targets it
accepts.

## 11. Profiles and extensions

A project MAY declare extension/profile schemas.

Provisional form:

```yaml
extensions:
  - ./schemas/semiconductor.yaml
```

A custom profile may then be used:

```yaml
objects:
  evt:
    type: gate
    fields:
      approval: pending
```

The exact external-schema composition mechanism remains provisional for Core v0.1.

## 12. Annotations

Semantic annotation example:

```yaml
annotations:
  evt-approval:
    kind: callout
    text: Customer approval required
    anchor:
      object: evt
```

Presentation-specific placement offsets are not part of this Core representation.

## 13. Precision and uncertainty

The semantic model distinguishes precision and uncertainty.

Core v0.1 reserves syntax such as:

```yaml
at: 2027-Q1
```

for coarse precision and:

```yaml
at:
  earliest: 2026-11-10
  latest: 2026-11-20
```

for uncertainty.

These forms are **provisional** until parsing, normalization, and scheduling behavior
are fully specified. Implementations claiming only Core v0.1 scheduling conformance
MAY reject unresolved uncertainty.

## 14. Canonicalization

Canonical output SHOULD:

- preserve stable object identifiers;
- use explicit schedule modes;
- use explicit relation endpoints;
- avoid serializing derived renderer coordinates;
- avoid serializing redundant derived schedule values;
- use a deterministic top-level section order;
- preserve user-significant object ordering where supported, otherwise use a documented
  deterministic order;
- normalize accepted shorthand without changing semantic meaning.

## 15. Unknown fields and forward compatibility

Unknown top-level semantic fields MUST NOT be silently interpreted.

A validator SHOULD report unknown fields unless they are declared by an extension
schema.

Consumers MAY preserve unknown extension data when they can do so losslessly, but
MUST NOT pretend to understand its semantics.

## 16. Versioning

The top-level `version` identifies the project-format contract:

```yaml
version: timeline/v0.1
```

A breaking change to parsing or semantic interpretation requires a format-version
change or a defined migration.

Profile/package versions SHOULD be independently versionable.

## 17. Multi-file composition

Large projects are expected eventually to support structures such as:

```text
project.yaml
schemas/
data/
views/
styles/
themes/
```

Core v0.1 defines the logical separation but does not yet standardize all include,
merge, and conflict rules.

A small project MUST be representable in a single file.

## 18. Git-diff requirements

The format MUST avoid storing data that can be deterministically regenerated when
doing so would create noisy diffs.

In particular, Core project files MUST NOT require persistence of:

- canvas x/y positions for temporal placement;
- renderer caches;
- tldraw Store records as semantic source of truth;
- duplicated FS/SS/FF/SF fields when endpoint pairs are canonical;
- duplicated duration when fixed start/end are authoritative.

## 19. Validation layers

Validation SHOULD occur in stages:

```text
YAML syntax
   ↓
structural schema
   ↓
profile/extension schema
   ↓
semantic references and types
   ↓
temporal validation
   ↓
scheduling validation
```

This separation SHOULD allow diagnostics to identify whether a failure is structural
or semantic.

## 20. Core v0.1 required format subset

A Core v0.1 conforming scheduler/parser pair MUST support the Date-based subset used by
the canonical examples and schema.

The following remain reserved/provisional and do not block Core scheduler conformance:

- DateTime scheduling;
- coarse precision serialization;
- uncertainty scheduling;
- multi-file merge/include semantics;
- external extension package acquisition.

A consumer MUST diagnose unsupported reserved features rather than reinterpret them.

