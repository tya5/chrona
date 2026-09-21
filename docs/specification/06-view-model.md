# View Model

**Status:** Draft
**Depends on:** `01-concepts.md`, `02-domain-model.md`, `03-temporal-model.md`, `04-scheduling-model.md`, `05-project-format.md`  
**Owns:** selection, comparison context, grouping, ordering, temporal-window selection, visibility, layout intent, and presentation annotations.

## 1. Purpose

A View is a reproducible presentation projection over a semantic Project. It answers **which** information is shown and **where it is arranged**. A View does not change the meaning of a Project object, date, dependency, schedule, Snapshot, or Actual observation.

```text
Project  = What exists and what it means
View     = Which information is shown and where it is arranged
Style    = How selected information is expressed visually
Theme    = Concrete visual tokens
Scene    = Renderer-neutral visual primitives
```

### 1.1 Design drivers from prior research

Chrona is not a generic project-management suite, a Mermaid-only diagram DSL, a slideware clone, or a pixel-authoritative canvas. Existing tools expose complementary but insufficient trade-offs:

- project-management and Gantt tools commonly add workflow, resources, cost, and portfolio machinery that is outside Chrona's purpose;
- Git-friendly diagram DSLs preserve reviewability but do not provide enough timeline annotation and presentation freedom;
- canvas editors such as tldraw are valuable future interaction surfaces, but their scene state would create noisy diffs if it became the Project source of truth; and
- slide tools provide expressive callouts and emphasis but hide schedule semantics inside geometry.

The View Model therefore preserves semantic, Git-reviewable Project data while allowing multiple review-focused projections, named comparisons, and anchored presentation annotations. Its purpose is to make semantic changes visible without turning presentation state into the model.

## 2. Invariants

- A View MUST NOT mutate Project data, scheduling results, Snapshot data, or Actual observations.
- A View MUST NOT make Actual observations scheduling inputs or infer a rescheduling policy from them.
- A View MUST identify Project objects by stable project-local IDs, never by title, visual position, or renderer identity.
- A View MAY select a resolved federated summary object only by its stable derived
  `federation-id:child-object-id`, never by a child title or a live repository lookup.
- A View MUST be reproducible from explicit input references and View parameters.
- A View MUST NOT own colors, fonts, stroke widths, renderer-specific state, or absolute scene coordinates.
- Omitting an item from a View MUST NOT delete or alter the underlying semantic item.

## 3. View Context

A View is evaluated against an explicit View Context.

| Input | Meaning | Required |
|---|---|---|
| Primary Project | Semantic project data and its derived planned schedule | Yes |
| Snapshot | Named immutable comparison state, potentially identified by a Git ref | No |
| Actual observations | Observed start, finish, point occurrence, and progress | No |
| Federation Plan | Pinned, read-only subproject summary inputs declared in a separately versioned parent-side plan | No |
| Render context | Explicit evaluation date, locale, and other environment data | As required by the consumer |

The primary Project is required. Snapshot and Actual inputs MUST be named when present. A View or renderer MUST NOT silently select “latest”, “main”, or a local-clock date as a comparison source.

A federated item is a read-only projection input after the Federation Plan's pinned
reference has been resolved. It may be selected, grouped by federation ID, and styled
by declared origin. It cannot be edited through the parent's View and it must not cause
the parent scheduler to inspect non-published child internals.

Serialization for Views, Snapshots, and Actual observations is outside this document. The View Model defines their presentation semantics only.

## 4. View Definition

A View definition is declarative. Its common resource envelope, reference syntax, and
normalization belong to [Presentation Format](13-presentation-format.md); this document
owns the View-body meaning and v0.1 field language below.

| Concern | View responsibility |
|---|---|
| Selection | Include or exclude objects, relations, entities, and annotations |
| Grouping | Partition selected objects into lanes from semantic fields |
| Ordering | Deterministically order groups and objects |
| Temporal window | Select the presented time interval |
| Comparison | Declare which named comparison inputs and facets the View accepts or requires; the concrete Project, Snapshot, and Actual references come from the Render Context |
| Visibility | Select labels, relations, annotations, and comparison facets |
| Layout intent | Choose lanes, hierarchy expansion, compactness, and annotation anchoring |

Selection expressions MUST be declarative predicates over semantic data and MUST NOT execute arbitrary host-language code.

### 4.1 v0.1 persistent body

The v0.1 View resource uses a deliberately small, closed selector language. It enables
reviewable plan-versus-actual views without embedding code or renderer geometry:

```yaml
version: chrona/presentation/v0.1
kind: view
id: controller-review
body:
  selection:
    include: { types: [span, milestone] }
  grouping: { by: entity, missing: ungrouped }
  ordering: { by: plannedStart, direction: ascending, tieBreak: id }
  window: { mode: selected-planned, marginDays: 7 }
  comparison:
    actual: required
    facets: [planned, actual, startDelta, finishDelta, progress, missingActual, unmatchedActual]
  visibility: { labels: true, relations: semantic, annotations: all }
  layoutIntent: { compactness: balanced }
```

`selection.include` is an intersection of its declared filters. v0.1 permits only
stable IDs, object types, entity IDs, profiles, and declared typed-field equality; an
omitted filter does not constrain selection. There is no arbitrary boolean expression,
regular expression, title match, script, or implicit hierarchy traversal. The exact
typed-field reference form is introduced only with the Extension schema.

`comparison.actual` is `forbidden`, `optional`, or `required`; a Render Context must
provide an Actual set exactly when the selected mode requires it. The `facets` list is
sorted and duplicate-free. `planned` and `actual` remain separate facets, so a Style or
Scene can update only the affected primitive when an observation changes. A View never
changes a planned placement because a delta facet exists.

### 4.2 Closed comparison language

v0.1 comparison bodies use `baseline: primary|snapshot`,
`observationSelection: latest`, and `deltaUnit: calendar-days`. `baseline: primary`
uses the primary Project's derived planned schedule; `baseline: snapshot` requires a
Snapshot whose resolved `project.id` equals the primary Project ID. `latest` chooses the
observation with greatest positive `sequence` for each resolved Project object; equal
sequences for one object are invalid. Unmatched observations are never planned-comparison
candidates, but may appear through `unmatchedActual`.

`startDelta = actual.start − planned.start`, `finishDelta = actual.finish − planned.finish`,
and `atDelta = actual.at − planned.at`, each as a signed integer in calendar days.
Positive means later/behind; negative means earlier; zero means equal. A delta is absent,
not zero, if either endpoint is absent or the point/span kinds differ. Point Actuals
compare only with planned points and intervals only with planned spans. Actual intervals
use Core's half-open `[start, finish)` form; a human-facing inclusive finish label never
changes it. Progress is observed only and has no implied forecast or rescheduling effect.

## 5. Projection Pipeline

The View pipeline is separate from styling and scene construction.

```text
Project + Schedule + View Context
              │
              ▼
          Selection
              │
              ▼
    Grouping / Ordering / Window
              │
              ▼
       View Projection (semantic)
              │
              ▼
       Style / Theme / Scene
```

A View Projection contains stable object IDs, resolved temporal placements, comparison facets, lane membership, order, temporal window, and annotation-placement intent. It does not contain rectangles, pixels, paths, fonts, or colors.

## 6. Selection, Grouping, and Ordering

Selection identifies semantic items eligible for presentation. A View MAY select by stable object ID, type, hierarchy, entity reference, profile, or typed extension field.

Relations MAY be shown only when both endpoints are selected. A View MAY retain an omitted endpoint as a non-rendered explanatory boundary, but MUST NOT invent a relation absent from the Project.

Semantic dependencies and explanatory arrows are distinct. A semantic dependency is owned by the Project and constrains or validates scheduling. An explanatory arrow is a View-local presentation annotation; it MAY explain a risk, decision, or causal narrative but MUST NOT create a scheduling constraint.

Grouping creates presentation lanes; it is not semantic containment. v0.1 uses
`{by: objectType}` or `{by: field, field: <declared semantic field path>, missing:
<lane-id>}`. `by: entity` without a field is invalid. `objectType` means normalized
Core shape (`point` or `span`), not an implementation profile name. Ordering is the
tuple `(ordering key, tieBreak, stable object ID)`; missing values sort after present
values in ascending order and before in descending order.

## 7. Temporal Window

A View selects a temporal window independently from scheduling semantics. v0.1 allows
`{mode: explicit, start: Date, end: Date}`, `{mode: selected-planned, marginDays: N}`,
or `{mode: selected-comparison, marginDays: N}`. Explicit windows are `[start, end)`
with both bounds and `start < end`; derived windows use selected minimum start and
maximum exclusive end plus non-negative margin. An empty eligible set is a diagnostic,
never a current-date default.

Date-based Views use the Date temporal domain. DateTime View behavior is deferred until a corresponding Core scheduling profile exists. Human-facing inclusive end-date display is a View or renderer concern and MUST NOT alter Core half-open span semantics.

## 8. Comparison Views

A comparison is a named relation between independently identified states; it is not a mutable field added to every Project object.

### 8.1 Current versus Snapshot

Current-versus-Snapshot compares the Primary Project with an immutable named Snapshot. A Snapshot MAY ultimately be represented by a Git ref. Alignment uses stable project-local IDs. A missing object is a comparison result, not an instruction to create or delete an object.

### 8.2 Plan versus Actual

Plan-versus-Actual compares planned placements from the Primary Project or named Snapshot with independent Actual observations. An observation has exactly one occurrence shape: a point `at`, or an interval with one or both of `start`/`finish`, optionally progress. It has a positive `sequence`; v0.1 selects the latest sequence. Actuals MUST NOT automatically change planned dependencies, duration, forecast, or schedule.

The View Projection MAY expose planned and actual endpoints, start/finish delta, progress, absent observation, and unmatched observation. Whether an actual delay triggers rescheduling belongs to a future scheduling or application policy.

### 8.3 Comparison Alignment

Comparison alignment MUST use stable IDs. A renamed title, regrouped object, or changed visual placement remains the same comparison subject. An unknown reference MUST produce a comparison diagnostic and MUST NOT be matched by text similarity.

### 8.4 Comparison truth table

| Baseline placement | Selected Actual | Requested facet | Result |
|---|---|---|---|
| span `[S, F)` | interval | `startDelta`, `finishDelta` | Signed calendar-day difference for each present endpoint |
| point `A` | point `at` | `atDelta` | Signed calendar-day difference |
| span | point | start/finish delta | Absent facet and `VIEW-COMPARISON-ENDPOINT-KIND` |
| point | interval | `atDelta` | Absent facet and `VIEW-COMPARISON-ENDPOINT-KIND` |
| any | no resolved observation | `missingActual` | `true`; Actual/delta facets absent |
| any | multiple observations | any | Greatest `sequence`; duplicate sequence is invalid |

`finishDelta` uses the canonical exclusive endpoint; display inclusivity never changes it.

## 9. Annotations and Layout Intent

Semantic annotations remain Project data and are selected with their anchors. Presentation annotations are View-local callouts, highlights, notes, or explanatory arrows. They MAY anchor to a selected object, relation, group, or temporal coordinate. The View owns the stable anchor and logical placement preference; Scene and Rendering own any concrete relative offset or coordinate. Deleting a presentation annotation MUST NOT alter a Project object, semantic annotation, or dependency.

### 9.1 v0.1 presentation annotation intent

A presentation annotation has a stable View-local ID, one typed anchor, a purpose, and
a logical placement preference. It is not a free coordinate blob:

```yaml
annotations:
  - id: supplier-risk
    purpose: callout
    anchor: {kind: object, id: firmware}
    placement: {side: above, alignment: end}
    text: "Supplier confirmation pending"
```

Initial `purpose` values are `callout`, `highlight`, `note`, and `explanatory-arrow`.
An explanatory arrow additionally has `source` and `target` typed anchors. It is
projected with source kind `explanatory-arrow` and can never satisfy, replace, or alter
a semantic dependency. A missing anchor produces a View diagnostic; no title or
geometry-based recovery is allowed.

Layout intent includes lane assignment, collapsed groups, hierarchy expansion, preferred compactness, and annotation anchoring. It is not renderer geometry. For v0.1, `layoutIntent.itemStacking` is always `stable`: items receive the lowest non-overlapping lane-local stack index in deterministic View order; equal positions use stable object ID. Annotation placement tries requested side, then `above`, `below`, `end`, `start`; failure emits a diagnostic. `layoutMetrics` is the revision-bound metrics/algorithm artifact declared by Render Context, never a renderer font default.

## 10. Diagnostics

View evaluation SHOULD report stable diagnostics for unknown Project, Snapshot, Actual, or object references; incompatible temporal domains; duplicate comparison identity; and invalid explicit windows. Exact identifiers and schema are deferred to the View schema and Application Architecture work.

## 11. Out of Scope

This document does not own the YAML resource envelope, reference normalization, colors,
typography, line styles, scene primitives or coordinates, SVG/tldraw adaptation, or
resource leveling. Snapshot capture and annotation mutation are Command Model concerns;
Actual-driven rescheduling and DateTime scheduling remain out of scope.

## 12. Boundary to Subsequent Documents

`07-style-and-theme.md` may assume that a View Projection exposes selected objects, comparisons, lanes, order, temporal window, and annotation intent. It MUST NOT redefine selection or comparison semantics.

`08-scene-and-rendering.md` may transform a styled View Projection into scene primitives. It MUST NOT become the source of object identity, temporal truth, or comparison alignment.

## 13. Review row composition

View v0.2 may compose several Review Items into one visible Review row. This is View
arrangement intent, not Project containment: each item names one Primary, Snapshot, or
Actual source and one stable Project-local object ID. A row supplies its View-local
identity, label, group, member order, and table subject; Layout and Scene retain all
geometry. The complete contract, diagnostics, and Scene boundary are specified by
[Review Row Composition](38-review-row-composition.md). No View field may use titles,
absolute coordinates, colors, fonts, or renderer identifiers to resolve a row member.
