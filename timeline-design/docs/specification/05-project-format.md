# Project Format

**Status:** Stable
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
- friendly to line-oriented diffs, including Git diffs when Git is used;
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

A project MAY declare immutable extension package references. Each reference is resolved
before profile validation and is part of the Project revision closure. The v0.1 shape
below is Git-adapter-specific; successor formats use the provider-neutral resource
reference defined by [15 Revision Store Adapters](15-revision-store-adapters.md).

```yaml
extensions:
  - packageId: semiconductor-development
    path: packages/semiconductor.yaml
    revision: git:<40-or-64-hex>
    contentIdentity: sha256:<64-hex>
```

A custom profile may then be used:

```yaml
objects:
  evt:
    type: gate
    fields:
      approval: pending
```

Moving branch names, directory scans, and an unpinned "latest" package are invalid.

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

## 21. Federated subproject references (post-v0.1 draft)

A program may need to present timelines owned by independently reviewed subprojects.
This is not multi-file composition of one canonical Project. The child Project remains
authoritative in its own Revision Store and is never included, merged, or mutated by the
parent Project.

The parent-side syntax is a separately versioned Federation Plan containing typed,
immutable references to child **timeline exports**, rather than raw child Projects. It
is not a `timeline/v0.1` top-level field:

```yaml
version: chrona/federation-plan/v0.1
id: program-federation
primaryProject: {id: program, kind: project, path: project.yaml, revision: git:<40-or-64-hex>, contentIdentity: sha256:<64-hex>}
exports:
  - id: firmware
    export: {id: firmware-program, kind: timeline-export, projectId: firmware, repository: git+https://host.example/org/firmware.git, path: exports/program.yaml, revision: git:<40-or-64-hex>, contentIdentity: sha256:<64-hex>}
    presentation: {mode: summary, namespace: firmware}
```

The Federation Plan ID and each federation ID are parent-local and stable. A child object that appears in the parent
projection has the derived identity `federation-id:child-object-id`; it does not become
a member of the parent `objects` map. `revision` must be immutable and
`contentIdentity` must match the exact export bytes. `repository` is a canonical
locator subject to configured trust policy. Moving branch names, abbreviated Git IDs,
source-tree mounts, and recursive Project inclusion are invalid.

Only an explicitly published child interface milestone may be the target of a
parent-owned dependency. That dependency constrains parent-owned work only; it never
schedules, edits, or otherwise reaches into the child Project. Aggregated child
progress is display information with an explicit aggregation rule and is not a
scheduling input.

The federation resources are versioned outside Core v0.1. The Git-shaped syntax above
is a v0.1 compatibility form; RA-4 defines the successor provider-neutral form. A future
Render Context minor version will reference the Federation Plan explicitly.
Implementations must not claim federation support until the resolver contract and fixtures in
[16 Federation](16-federation.md) are complete.

## 22. Resource and capacity successor resources

Resource capacity is not embedded implicitly in a v0.1 Project or Calendar. A
successor evaluation names a separately versioned `chrona/resource-capacity/v0.2`
resource, whose structural form is owned by `resource-capacity-v0.2.schema.yaml`.
It holds stable resource IDs, their dimensioned capacity unit and calendar reference,
and assignments from stable Project object IDs to the same dimensioned unit.

The Project revision, capacity resource revision, requested objective, movement scope,
and resulting proposal fingerprint are explicit evaluation inputs. A generated leveling
proposal is not serialized as a Project edit. Only an accepted
`applyLevelingProposal` Command serializes the selected semantic placement changes in
a new Project revision. Cost, rate, and timesheet observations use separately
identified resources and are not fields inferred into an assignment or schedule.
# v0.2 temporal profile note

The v0.2 DateTime successor adds an optional top-level `temporalProfile` only to a
versioned successor Project format. `timeline/v0.1` rejects it and retains Date-only
syntax. `datetime-v0.2` endpoints use the `temporal-datetime-v0.2` schema and MUST
carry either an instant plus IANA zone or an explicitly disambiguated local input.

Migration from v0.1 is opt-in: the original document remains valid unchanged. A
migration tool MAY create a v0.2 copy only when it supplies a zone policy for each
Date-to-DateTime conversion; it MUST NOT assume midnight. The result records the source
revision and chosen policy in migration provenance. Downgrade to v0.1 is rejected when
a Project contains any DateTime, recurrence, or intraday calendar value.

## 23. DateTime Project successor (`timeline/v0.2`)

`timeline/v0.2` is a distinct, opt-in document format. It requires
`temporalProfile: datetime-v0.2`; all scheduling endpoints use the DateTime value
contract (instant plus IANA zone, or explicit local disambiguation). It MUST NOT
contain Date-only endpoints, and `timeline/v0.1` neither accepts nor converts it.

The v0.2 structural contract is `project-v0.2.schema.yaml`. Fixed spans use
`start`/`end`, fixed points use `at`, and scheduled spans use one explicit anchor with
either an `exactDuration` (ISO-8601 elapsed duration) or `calendarPeriod`. A dependency
remains `target.endpoint >= advance(source.endpoint, lag)` with an explicit matching
lag type. WorkPeriod and intraday calendars reject until separately specified.

A recurrence has `mode: recurrence` and declares local start, zone, frequency,
interval, optional count/until, and DST disambiguation. Its occurrences are derived;
neither it nor an occurrence may be a dependency endpoint. A v0.1→v0.2 copy records
source revision/format and a non-implicit zone policy in migration provenance.
