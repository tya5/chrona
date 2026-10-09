# Project Format

**Status:** Stable
**Core Specification:** v0.1

## 1. Scope

This document defines the initial human-readable persistent representation of Core
project semantics.

YAML is the normative interchange syntax for Core v0.3 examples.

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
# chrona-contract: historical
version: timeline/v0.3

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

A Project may be compiled from the terse plan syntax of Spec 65 (`chrona compile`); the compiled Project
remains the authority and Spec 65 repeats no rule of this document.

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

### 4.2.1 Scheduled point

A point whose date is derived from its dependencies stores no date:

```yaml
objects:
  launch:
    type: gate
    title: Launch
    schedule:
      mode: scheduled-point
      constraints:
        at:
          min: 2027-05-07   # optional: not earlier than
          max: 2027-06-30   # optional: not later than (hard cap)
```

`mode` is the only required property. There is no `amount`, no `anchor` and no date. A relation into
the object targets `at`; the scheduler places the object at the latest of every incoming `source + lag` and the
optional `min` (Spec 04 Section 20.4). `max` rejects a plan whose derived date is later
(`E_CONTRADICTORY_BOUNDS`). An object with no relation into `at` and no `min` is `E_DERIVATION`. The mode works
for any object `type` label. Unlike a fixed point it is never a validation target: a dependency moves it.

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

### 4.4 Hierarchy and rollup span

```yaml
objects:
  development:
    type: phase
    title: Development
    wbsCode: 1
    schedule: {mode: rollup}
  fw:
    type: task
    parent: development
    plannedProgress: 0.5
    schedule: {mode: fixed, start: 2026-10-01, end: 2026-10-30}
```

`parent` is the sole containment edge.  Parents must resolve to another object,
must not self-reference, and form an acyclic forest.  YAML mapping order is the
canonical root and sibling order.  `wbsCode` is an optional, unique author
label; an omitted display code is derived deterministically from that tree
order and does not create a second hierarchy edge.

`schedule: {mode: rollup}` is valid only for an object with descendants.  It
derives the envelope of all completed descendant placements after they are
scheduled.  A parent with a fixed or scheduled span is an ordinary scheduled
object and never constrains or moves its children.  The former `children` and
`derived: {from: children}` syntax is not part of v0.3.

`plannedProgress` is an optional decimal in `[0, 1]` expressing plan intent.
It does not affect schedule, forecast, or Actual selection.

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

For `schedule.amount`, Core v0.3 accepts only amount types permitted as scheduled span
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

A calendar MAY declare an optional `title` (non-empty text, #1026), a display name only: it never
affects scheduling, and the View heading placeholder `{calendar}` shows it, or the calendar identifier when
absent ([Spec 06 §7.4](06-view-model.md)). The member is additive in place in `chrona/timeline/v0.7`.

A Project that declares no default calendar (`project.calendar` absent) has no
built-in one: Chrona assumes no Monday-to-Friday week, so working-day arithmetic
without a calendar is `E_CALENDAR_REQUIRED` and a View shades no closed day
(`calendar-closed`; [Spec 50 §3.4](50-constraint-driven-gantt-surface-quality.md#34-groups-and-legend), #893).
Closed days come only from the declared default calendar, so scheduling and
shading read the same fact.

Project schema evolution follows the additive-in-place and incompatible-change
rules in [Spec 56 §3.2](56-schema-authoring-and-diagnostics.md#32-schema-version-evolution-591).
Calendar inheritance and external holiday feeds remain deferred until their
reproducibility rules are specified.

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

For Core v0.3 Date scheduling, dependency lag accepts signed `d`, `w`, or `wd`.
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
is violated. The same dependency moves/constrains a `scheduled` target. A
rollup has `start` and `end` endpoints from its derived envelope and may be a
dependency endpoint; a parent edge itself is never a dependency.


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

### 9.1 Attachment

A fixed point MAY name the span it belongs to for presentation:

```yaml
campaign-readiness:
  type: gate
  attachesTo: campaign
  schedule: {mode: fixed-point, at: 2027-10-01}
```

`attachesTo` is presentation metadata, not a scheduling edge. Like a deadline, it MUST NOT move or constrain either object. It is independent of `parent`. The host MUST exist, MUST NOT be the point itself, and MUST be a span (`E_PROJECT_ATTACH_TARGET_UNKNOWN`, `E_PROJECT_ATTACH_SELF`, `E_PROJECT_ATTACH_TARGET_NOT_SPAN`). Only a point (a fixed point or a scheduled point) may attach (`E_PROJECT_ATTACH_SOURCE_NOT_POINT`); a scheduled point is not a span host. A point dated outside its host's planned span is valid and is reported as `W_PROJECT_ATTACHED_OUTSIDE_HOST`. The field is optional and additive in `timeline/v0.7` (§16).

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

### 12.1 Periods

A Project MAY name date ranges, such as a launch window, in an optional top-level `periods` map (#582):

```yaml
periods:
  launch-window:
    title: Launch window
    start: {object: launch, endpoint: at}
    end: 2027-11-06
```

A period is the half-open range `[start, end)`, the convention of every Project span (§4.1): "22 October to 5
November inclusive" is written `end: 2027-11-06`. Each side is a calendar date or an endpoint reference
`{object, endpoint}` (the form relations use, §7), which names the completed date the schedule gives that
endpoint. `title` is optional and is the period's label text. The object is closed: it has no presentation member
(placement, paint, pattern), which belong to a View and a Theme.

A period is a fact that never schedules. Like a deadline (§9) it MUST NOT move or constrain any object, add a
relation, or be read by the scheduler. Scenario overrides do not change it.

Validation, in `validate`, with the period's pointer under `/periods/<id>`: a side that is not a calendar date is
`E_SCHEMA`; when both sides are dates, `start` MUST be before `end` (`E_PROJECT_PERIOD_ORDER`); a reference MUST
name a Project object (`E_PROJECT_PERIOD_OBJECT_UNKNOWN`) and an endpoint its schedule offers, `at` for a point and
`start` or `end` for a span (`E_PROJECT_PERIOD_ENDPOINT_UNAVAILABLE`). A range with a reference on either side can
be ordered only once dates exist: when the resolved `start` is not before the resolved `end`, `schedule` and render
reject the plan with `E_PROJECT_PERIOD_ORDER` (same code and pointer, naming both resolved dates), whether or not a
View selects the period. `validate` computes no dates and cannot report it, the split that already holds for
`E_FIXED_TARGET_VIOLATION`. The member is optional and additive in `timeline/v0.7` (§16). The terse syntax (Spec 65) does not spell periods; they stay in YAML.

### 12.2 Derived figures

A derived figure is an integer: signed days computed by Core from declared dates (#586), or a selected neutral count supplied by the View projection (#927). A View declares which figures it needs (Spec 06) and consumers show them by name (Specs 46, 50). Core owns date arithmetic and the closed count selector; View owns selection and observation-state interpretation. Nothing is an expression and no arbitrary field is read by name.

A fact is exactly one of: the Actual Set as-of; a named period's `start`, `end` or `last` (§12.1; `end` is the exclusive end and `last` is `end` minus one calendar day); an object's placed `at`, `start` or `end` (the completed date the schedule gives that endpoint, which moves with a re-plan); the caller-gathered first planned start/point of the current selected View group (Spec 06 §7.2). `last` is the final covered calendar day even when it is not a working day; a working-day figure applies its counting convention to that same date, without moving the boundary.

| Kind | Value |
| --- | --- |
| `daysUntil` from `a` to `b` (`a` defaults to the as-of) | Calendar days: `b - a`, negative once `b` has passed, 0 on the same day. Working days: the working days `d` with `a < d <= b`, or the negation of the working days in `(b, a]` when `b` is before `a`. |
| `daysIn` a period | Calendar days: `end - start`. Working days: the working days `d` with `start <= d < end`; a period with none is 0. |
| `count` a declared source | The injected integer count for that source (Spec 06 §7.2). Zero is a value; an absent bundle or unavailable source yields `E_FIGURE_COUNT_UNAVAILABLE` at the declaration's `/source`. Core does not infer state or count projection objects. |

Working days use a Project calendar: the figure's declared calendar, otherwise the Project default (§6), including its exceptions. The `daysUntil` count is the scheduler's working-day convention (§5: an advance counts days strictly after its start), so counting from `d` to `advance(d, k wd)` gives `k`. For example, with a Monday-to-Friday calendar, from Friday 2027-01-01 to Monday 2027-01-04 is 1 working day and from Monday 2027-01-04 to Saturday 2027-01-09 is 4 (a target on a non-working day counts up to the last working day before it), while the working days in the period `[2027-01-04, 2027-01-09)` are 5 (its start day counts, its exclusive end does not). No value is clamped, rounded or made absolute.

A fact that cannot be read is a diagnostic that names the figure, the fact and what is declared, never a blank, a zero or a guess: `E_FIGURE_PERIOD_UNKNOWN` (a period the Project does not declare), `E_FIGURE_OBJECT_UNKNOWN` (an object the schedule does not place), `E_FIGURE_ENDPOINT_UNAVAILABLE` (an endpoint the object's schedule does not offer), `E_FIGURE_ASOF_MISSING` (the as-of, when the Actual Set declares none) and `E_FIGURE_CALENDAR_UNAVAILABLE` (working days with no declared or default calendar). A figure with a diagnostic has no value.

For a group-relative View figure (Spec 06 §7.2), Core additionally accepts the caller-gathered
first planned start/point date of the current selected group. Selection and group membership
remain View-owned; Core imports no projection model and applies the same date arithmetic.
An absent injected date yields `E_FIGURE_GROUP_START_MISSING` at the figure's group fact.

## 13. Precision and uncertainty

The semantic model distinguishes precision and uncertainty.

Core v0.3 reserves syntax such as:

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
are fully specified. Implementations claiming only Core v0.3 scheduling conformance
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
# chrona-contract: historical
version: timeline/v0.3
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

Core v0.3 defines the logical separation but does not yet standardize all include,
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

## 20. Core v0.3 required format subset

A Core v0.3 conforming scheduler/parser pair MUST support the Date-based subset used by
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
is not a `timeline/v0.3` top-level field:

```yaml
# chrona-contract: historical
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

The federation resources are versioned outside Core v0.3. The Git-shaped syntax above
is a v0.1 compatibility form; RA-4 defines the successor provider-neutral form. A future
Render Context minor version will reference the Federation Plan explicitly.
Implementations must not claim federation support until the resolver contract and fixtures in
[16 Federation](16-federation.md) are complete.

## 22. Resource and capacity successor resources

Resource capacity is not embedded implicitly in a v0.3 Project or Calendar. A
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
versioned successor Project format. `timeline/v0.3` rejects it and retains Date-only
syntax. `datetime-v0.2` endpoints use the `temporal-datetime-v0.2` schema and MUST
carry either an instant plus IANA zone or an explicitly disambiguated local input.

Migration from v0.1 is opt-in: the original document remains valid unchanged. A
migration tool MAY create a v0.2 copy only when it supplies one explicit zone policy
with IANA zone, non-midnight local time, and DST disambiguation; it MUST NOT invent any
of those values. The result records source revision/format and the complete policy in
migration provenance. The migratable subset is v0.3 fixed points/spans, scheduled
`d`/`w` CalendarPeriod amounts, their date anchors, and `d`/`w` dependency lags.
WorkPeriod, calendars, extensions, constraints, derived schedules, entities, annotations,
unrecognized top-level fields, and unsupported amount units reject with a migration diagnostic rather
than being dropped. A v0.3 scheduled span without its required v0.2 anchor rejects.
An omitted v0.3 relation lag normalizes to `{kind: calendarPeriod, value: 0d}`; an
explicit v0.1 `d`/`w` lag maps to the same CalendarPeriod form. Downgrade to v0.1 is always rejected for a v0.2 Project, since it
contains DateTime semantics even when its values happen to align to dates.
Before subset conversion the adapter validates the v0.1 source structurally and
semantically; any source diagnostic rejects the entire migration.

## 23. DateTime Project successor (`timeline/v0.2`)

`timeline/v0.2` is a distinct, opt-in document format. It requires
`temporalProfile: datetime-v0.2`; all scheduling endpoints use the DateTime value
contract (instant plus IANA zone, or explicit local disambiguation). It MUST NOT
contain Date-only endpoints, and `timeline/v0.3` neither accepts nor converts it.

The v0.2 structural contract is `project-v0.2.schema.yaml`. Fixed spans use
`start`/`end`, fixed points use `at`, and scheduled spans use one explicit anchor with
either an `exactDuration` (ISO-8601 elapsed duration) or `calendarPeriod`. A dependency
remains `target.endpoint >= advance(source.endpoint, lag)` with an explicit matching
lag type. For a scheduled span, a lower bound on `start` is its candidate start; a lower
bound on `end` is converted to a candidate start by the inverse of its declared amount.
The inverse of `exactDuration` is instant arithmetic; the inverse of `calendarPeriod`
is local-date arithmetic that retains local clock time and applies the schedule's DST
disambiguation. An explicit anchor is exactly one of `start` or `end`; an anchor that
violates a derived lower bound is rejected. Recurrences and their occurrences are not
dependency endpoints. WorkPeriod and intraday calendars reject until separately
specified.

A recurrence has `mode: recurrence` and declares local start, zone, frequency,
interval, exactly one terminal bound (`count` or DateTime `until`), and DST
disambiguation. `until` is an inclusive instant boundary. Its occurrences are derived;
neither it nor an occurrence may be a dependency endpoint. A v0.3→v0.2 copy records
source revision/format and a non-implicit zone policy in migration provenance.

### 23.1 v0.3→v0.2 migration form

`migration.zonePolicy` is an object `{zone, localTime, disambiguation}`. `zone` is an
IANA identifier, `localTime` is `HH:MM[:SS]` and MUST NOT be `00:00` or `00:00:00`,
and `disambiguation` is `earlier`, `later`, or `reject`. Each source Date is converted
to the local DateTime formed from the Date plus this policy, then resolved under the
declared disambiguation. The migration is all-or-nothing: a rejected input produces no
v0.2 document. It preserves project/object IDs, titles and types; it does not mutate the
source document. A successful copy stores `sourceRevision` supplied by the caller and
`sourceFormat: timeline/v0.3`.
