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

Selection expressions MUST be declarative predicates over semantic data and MUST NOT execute arbitrary host-language code.

### 4.1 v0.1 persistent body

The v0.1 View resource uses a deliberately small, closed selector language. It enables
reviewable plan-versus-actual views without embedding code or renderer geometry:

```yaml
# chrona-contract: historical
version: chrona/view/v0.1
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

`baselineMarks: ghost` (optional; omitted means none, #991) makes a `baseline: snapshot`
comparison draw the Snapshot's placement of each selected item as a baseline ghost in
automatic and lane rows, also under field grouping: View composition adds one
shared-track `snapshot` member (`snapshot:<object>`) beside the primary item, and omits it
for an object the Snapshot lacks. `baseline: snapshot` alone draws no ghost, and explicit
rows name their snapshot items themselves. `ghost` without `baseline: snapshot` or without a
Snapshot in the Render Context is `E_REVIEW_BASELINE_MARKS_SNAPSHOT`. `baselineMarks:
ghost-when-changed` (#991 item 16) draws the ghost only for an item whose Snapshot placement
differs from its current one (any planned date), so an item whose baseline equals the plan gets
no dashed frame; it needs the same Snapshot baseline and fails the same way without it.

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
values in ascending order and before in descending order. The key `source` (also a
`tieBreak`, #991) is the position of the object among the Project's `objects` as the Project
document declares them, not the scheduler's order; descending reverses it, and a group still
keeps its members together.

A grouping with `presentation: header` may declare `header`, a text template for each
group header (literal text, an ordinal in a declared form, the entity title and an entity
field as a secondary title; a first-group variant). The text is View content; its
grammar, ordinal forms and diagnostics are owned by
[Specification 50](50-constraint-driven-gantt-surface-quality.md) section 3.4.

## 7. Temporal Window

A View selects a temporal window independently from scheduling semantics. v0.1 allows
`{mode: explicit, start: Date, end: Date}`, `{mode: selected-planned, marginDays: N}`,
or `{mode: selected-comparison, marginDays: N}`. Explicit windows are `[start, end)`
with both bounds and `start < end`; derived windows use selected minimum start and
maximum exclusive end. For `selected-planned`, pad each side by
`max(marginDays, ceil(elapsedDays / 10), 1)` Date days, where `elapsedDays` is
the selected maximum exclusive end minus the minimum start (zero for same-date
points). This general rule strictly contains selected marks and preserves larger
authored margins; it does not change Core schedules or depend on fonts, viewport
size or axis units. `selected-comparison` retains its authored non-negative margin.
If padded bounds cannot be represented in the Date domain, diagnose
`E_REVIEW_WINDOW` with the selected dates and object identifiers rather than
wrapping or silently clamping. An empty eligible set is a diagnostic,
never a current-date default.

Date-based Views use the Date temporal domain. DateTime View behavior is deferred until a corresponding Core scheduling profile exists. Human-facing inclusive end-date display is a View or renderer concern and MUST NOT alter Core half-open span semantics.

### 7.1 Named periods (#582)

A `table-timeline` View MAY select named Project periods (Spec 05 §12.1) with `periods: [{id}]`, each drawn as a band across the plot rows over the period's dates. The selection owns only which periods are shown and in what order (the order is the drawing order); the period's dates are a Project fact and its colour, stroke, opacity and pattern are Theme role `period-band` (Spec 07), its geometry Layout's (Spec 50 §3.4). The band is clipped to the View window and never extends it: a period with no extent left draws nothing and is recorded as the Scene diagnostic `I_LAYOUT_PERIOD_OUTSIDE_WINDOW:<id>`. An id the Project does not declare is `E_VIEW_PERIOD_UNKNOWN` (pointer `/body/periods/<i>/id`; the message lists the declared ids) and a repeated id is `E_VIEW_PERIOD_DUPLICATE`; nothing is skipped silently. The member is optional and additive in `chrona/view/v0.28`; a `dependency-network` View, which has no timeline, MUST NOT declare it. A View without `periods` renders as before.

A selected period may carry `label: {placement, overflow?, text?}`. `placement` is `top` (at the plot's top edge), `bottom` (at its bottom edge) or `inside` (centred in the band); the label is the View's `text` override when it declares one (#871; one to eighty characters, shown for this View only), else the period's `title` (its identifier when absent), centred on the band's visible extent. `overflow` is `suppress` (omit the label and record `W_LAYOUT_LABEL_SUPPRESSED`) or `visible-overflow` (the default: place it at the preferred position and record `W_LAYOUT_LABEL_OVERFLOW`) when no collision-free position exists; a label never silently overprints a mark. Absent `label` draws the band alone.

### 7.2 Axis band fills (#490)

A `table-timeline` View MAY give a fixed-unit `axis.tiers[]` band tier `fillScale: {scale, key, containingTier?}`. `key: alternating` selects Theme slots `"0"` and `"1"` by the natural interval ordinal's parity; `key: interval` selects its canonical decimal ordinal. An optional `containingTier` names another declared, coarser fixed-unit band tier and selects by the unique natural interval containing this interval. The View names the Theme scale and the source rule; Layout resolves interval identity, and Scene receives the resolved paint without changing geometry. A tier without `fillScale` renders as before. See Presentation Specification 60 for interval, Theme mapping, and diagnostic rules.

### 7.3 Deadline marks (#822)

A `table-timeline` View MAY declare `deadlines: {show: slipped | all}` to draw each object's Project `deadline` (Spec 05 section 9). A deadline is drawn as a **tick** at its date, centred on the object's planned mark, and, when the planned finish is later than the deadline, a **run** from the tick to that finish (`at` of a point, `end` of a span, the date `W_DEADLINE` compares: Spec 04 section 10). `slipped` draws only the deadlines the plan misses; `all` draws every deadline, the missed ones with their run, so a kept promise reads as slack. Slipped and kept differ by shape (the run), not only by colour. The Core decides which deadlines slipped (`deadline_statuses`); a deadline equal to the finish is kept. The View selects; the Project owns the date; the Theme owns paint and reach (Spec 07, role `deadline-mark`); Layout owns the geometry (Spec 50 section 3.4). No text is drawn.

A deadline outside the View window draws nothing and is recorded as the Scene diagnostic `I_LAYOUT_DEADLINE_OUTSIDE_WINDOW:<object>`; a planned mark folded into a group header is not decorated and is recorded as `I_LAYOUT_DEADLINE_FOLDED:<object>`. A Theme that omits the role while a View shows deadlines fails with `E_THEME_ROLE_REQUIRED` at `/body/roles/deadline-mark`. The member is optional and additive in `chrona/view/v0.28`; a `dependency-network` View, which has no timeline, MUST NOT declare it. A View without `deadlines` renders as before. An author explains the mark with a Detail Profile legend entry whose role is `deadlineMark`.

### 7.4 Heading templates (#991)

A `table-timeline` View MAY declare `heading: {title?, subtitle?, dateForm?}`. Each of `title` and `subtitle` is a template of literal text and the closed placeholders `{project}` (the Project title), `{asOf}` (the Actual Set's as-of date, formatted in `dateForm`, today `localized-date` in the context locale) and `{calendar}` (the Project's default calendar **title** when that calendar declares one, else its **id**; #1026). `{{` and `}}` are literal braces; any other brace use is `E_VIEW_HEADING_TEMPLATE`. The grammar is the group-header template's (section 6, #583) with this placeholder set. A fact the Project lacks (no as-of date, no default calendar) renders as empty text. Without `title` the title is the Project title; without `subtitle` there is no subtitle line, and a View without `heading` renders as before. The content layer composes the text; the title slot measures it as a stack of a `heading` run and a `subtitle` run, so the slot grows by the subtitle line; Layout places the subtitle under the title and Scene emits it as `subtitle-text` in the Theme's `subtitle` typography role (a Theme without that role fails with `E_THEME_ROLE_REQUIRED`). A `dependency-network` View draws its own title and ignores `heading`. The member is optional and additive in `chrona/view/v0.28`.

For independent heading-part sources (Spec 33, #1239), both native surfaces
resolve the View's heading into named parts. A dependency-network profile without
a whole-title host selects this mode; its legacy whole-title mode still ignores
View heading. Only allocated parts require their typography roles, and Layout
reports unallocated nonempty copy without measuring it.

A heading MAY also declare `kicker` (#1189), a template using the same facts,
grammar and `dateForm`, above the title in the Theme's required `kicker`
typography role. Content normalization retains named kicker/title/subtitle
runs. Layout measures and places them as one completed block: the measured
envelope contains every text bound, including actual font-baseline offsets
and the Theme's declared kicker gap. Without `kicker`, existing title/deck
measurement, coordinates and output remain unchanged. This is an optional
addition to `chrona/view/v0.28`, not a new schema version.

### 7.5 Slot caption copy (#1100)

A View MAY declare `slotHeadingText: {<Layout slot node id>: <literal copy>}`. Each target must be a slot
with a heading in the resolved Layout Profile, including an optional slot absent from this render. Copy is
one to eighty characters without control characters, not a template. An unknown, container or headless
target refuses the render with `E_VIEW_SLOT_HEADING_TARGET` at `/body/slotHeadingText/<escaped node id>`;
the message names the target and valid headed IDs. Layout completes the selected text using the existing
heading typography, placement, transform and overflow rules (Spec 33); the caption's inline bounds follow
its selected text, without mutating the profile, slot allocation or non-caption geometry. An absent optional
slot still draws nothing. Without this optional v0.28 member,
or with an empty map, the profile's copy and output remain unchanged.

### 7.2 Derived figures (#586)

A View MAY declare `figures`, an array of derived figures that the Core resolves (Spec 05 §12.2) and a consumer shows by name. Each has a unique `id` (no braces, whitespace or control characters: `E_VIEW_FIGURE_INVALID`; a repeat is `E_VIEW_FIGURE_DUPLICATE`) and one closed `kind`: `daysUntil {from?, to, days?, calendar?}`, `daysIn {period, days?, calendar?}` or `count {source, scope?}`. A fact (`from`, `to`) is exactly one of `asOf`, `{period, side: start | end | last}` or `{object, endpoint: at | start | end}`; `from` defaults to `asOf`. `last` is the period's exclusive end minus one calendar day, not its last working day (Spec 05 §12.2). `days` is `calendar` (the default) or `working`; `calendar` names the Project calendar a working count uses (the Project default when omitted) and is a dead declaration, `E_VIEW_FIGURE_INVALID`, with calendar days. Nothing else is accepted: no expression, no operator, no field name, no other kind or fact.

Every declared figure is resolved after scheduling, whether or not a consumer shows it. A fact that cannot be read refuses the render with all findings (`E_FIGURE_PERIOD_UNKNOWN`, `E_FIGURE_OBJECT_UNKNOWN`, `E_FIGURE_ENDPOINT_UNAVAILABLE`, `E_FIGURE_ASOF_MISSING`, `E_FIGURE_CALENDAR_UNAVAILABLE`; the message names the figure, the fact and what is declared): a figure is never blank, zero or guessed. A Summary Profile metric shows a figure with `source: {figure: <id>}` (Spec 46); a metric naming an id the View does not declare is `E_VIEW_FIGURE_UNKNOWN`. The member is optional and additive in `chrona/view/v0.28`; a View without `figures` renders as before.

A `daysUntil` figure MAY declare `scope: group` (omission or `global` resolves once).
The additional fact `{group: firstPlannedStart}` requires that scope. View projection gathers
the earliest selected Primary planned start or point in each rendered group; Core receives only
that date, not projection objects. Group figures are keyed by group identity and figure identity,
separately from global values. Plain and role-marked group headers resolve `{figure:<id>}` in their
current group. A global consumer such as a Summary Profile cannot select a group-only value
(`E_FIGURE_SCOPE_UNAVAILABLE`). No projected groups is `E_FIGURE_GROUP_UNAVAILABLE`; a group
without a selected Primary start/point is `E_FIGURE_GROUP_START_MISSING`, not zero. Neither
comparison ghosts nor duplicate lane appearances change the selected dates.

`kind: count` selects one closed `source`: `selected`, `recorded`, `dueUnobserved`,
`notYetDue`, `unavailable`, `missingActual`, `knownFinishVariance`, `behind` or `ahead`.
It accepts `scope: global | group` (global when omitted), but no date facts, calendar or day unit.
One projection-owned producer supplies these facts to both figures and existing Summary metrics:
selected Primary items, not row occurrences or comparison ghosts. The four state sources count
the already-projected observation state. `missingActual` counts due-unobserved items but is
unavailable without explicit Actual as-of; that is `E_FIGURE_COUNT_UNAVAILABLE`, not zero.
Known finish variance counts non-absent deltas, including zero; behind/ahead count strictly
positive/negative observed deltas. They are not critical-path membership, forecast or project
slippage. Count figures accept Summary `count` or `text`, never `date` or `signedDays`.

A period label MAY declare `template` instead of its literal `text`: a closed grammar of
`{figure:<id>}` and `{{`/`}}` brace escapes. Both sources together are `E_VIEW_PERIOD_LABEL_SOURCE`.
Literal `text`, including figure-like strings, is unchanged. A malformed template is
`E_VIEW_FIGURE_TEMPLATE`; an undeclared figure is `E_VIEW_FIGURE_UNKNOWN`; a group-scoped
reference is `E_FIGURE_SCOPE_UNAVAILABLE`, all at `/body/periods/<index>/label/template`.
Presentation resolves the global integer before Layout measures and places the caption.

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
| span with planned exclusive `end` on/before Actual `asOf` | no resolved observation | `missingActual` | `true`; Actual/delta facets absent |
| point with planned `at` on/before Actual `asOf` | no resolved observation | `missingActual` | `true`; Actual/delta facets absent |
| planned due endpoint after Actual `asOf` | no resolved observation | `missingActual` | unavailable, not `false` or `true`; no missing-Actual mark |
| any | selected observation exists | `missingActual` | `false`, including an incomplete observation |
| any | no Actual `asOf` available | `missingActual` | unavailable; no due-state inference from the local clock |
| any | multiple observations | any | Greatest `sequence`; duplicate sequence is invalid |

`finishDelta` uses the canonical exclusive endpoint; display inclusivity never changes it.
The View derives one typed observation state (`recorded`, `due-unobserved`,
`not-yet-due`, or `unavailable`) from the selected observation, canonical
planned due endpoint and explicit Actual `asOf`. Equality with `asOf` is due.
All table, summary and Layout missing-Actual consumers use this projected
state; a future unobserved item must not be called “Recorded”. An observed but
incomplete Actual remains recorded, not missing. A start-based obligation or
separate not-yet-due treatment requires a future versioned View policy.

A table column MAY declare `missingBy` (optional, #991): the text of an absent value by the item's observation state, each of `inProgress` (a span with an Actual start and no finish), `dueUnobserved`, `notYetDue` and `unavailable` taking `blank`, `em-dash`, `unknown` or an author-chosen literal `{text}` (#1288: one to eight characters with no control character, drawn exactly as written in the column's text role); a state not named keeps the column's `missing`, which takes the same `{text}` form. `affixes.missing` is unchanged and wraps whatever the absent text is, in every absent state, so it is not the way to mark one state only. A Delta column can thereby leave unobserved items blank and show a dash for in-progress ones. It changes only the text of an absent value (affixes still wrap it); without it every absent value reads `missing` as before. It applies to automatic and explicit rows, not to the fixed lane table.

`comparison.missingActualScope` (optional; omitted or `due-unobserved` is the behaviour above,
#991) selects which work the missing-Actual **mark** covers; the projected state and every table
and summary count stay as above. `in-progress` marks only a span in progress at `asOf` (the
owner's rule: an observed span with a `start` on or before `asOf`, no `finish`, and a `progress`
that is absent or below 1; `openUntil: asOf` stays a sufficient explicit signal, even at progress 1;
a span at progress 1 without a finish or `openUntil`, or one that has not started, is not in
progress), drawn as a span from that start to `asOf` in place of its open Actual, and puts no mark
on a due-unobserved span or on a gate. With lane rows the lane expected-mark inventory lists that
mark (`missing-actual`) in place of the span's `actual` mark when the `missingActual` facet is
selected, and a typed absence (`in-progress-empty-at-cutoff`) when `asOf` is not after the start (#1027).

## 9. Annotations and Layout Intent

Semantic annotations remain Project data and are selected with their anchors. Presentation annotations are View-local callouts, highlights, notes, or explanatory arrows. They MAY anchor to a selected object, relation, group, or temporal coordinate. The View owns the stable anchor and logical placement preference; Layout owns every concrete offset, coordinate, collision decision, and connector route. Scene projects completed Layout geometry and Rendering serializes it. Deleting a presentation annotation MUST NOT alter a Project object, semantic annotation, or dependency.

### 9.1 Presentation annotation intent

A presentation annotation has a stable View-local ID, one typed anchor, a purpose, and
a logical placement preference. It is not a free coordinate blob. This
legacy shorthand normalizes to an ordered candidate:

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

View selection, grouping, hierarchy expansion, visibility, and annotation anchoring are semantic inputs, not renderer geometry. An annotation has one source (`text` or a stable Project annotation reference), a typed anchor, and an ordered candidate list. A Project reference inherits narrative text and object identity; View owns facet, endpoint, purpose and placement. The anchor endpoint is `start`, `end`, `finish`, `at` or `body`; `end` is the canonical spelling of a span's end and `finish` its alias, and the two produce the same Scene. A referenced Project note is not duplicated in the notes slot. Each candidate declares a region, search, obstacle classes and connector; Layout evaluates the list against one completed surface obstacle set, records the selected candidate and bounded search count, and owns box and connector geometry. The rail, adjacent sides and plot search are configurations of this one model; legacy named rungs normalize to candidates without changing their output. No View field contains concrete coordinates. `layoutMetrics` is the revision-bound metrics/algorithm artifact declared by Render Context, never a renderer font default.

The **kind** of a presentation annotation is the `kind` of the Project annotation its `projectAnnotation` reference selects (an open string such as `risk` or `note`); it is distinct from `purpose`, the closed placement intent. An annotation that carries its own `text` has no kind. The kind selects an optional Theme header (a label, a title bar, an accent edge; Specification 07) and nothing else: it never changes placement, purpose or the text. The View gains no property for it.

For a plot `tail` candidate, the same View intent may complete as a direct
integrated balloon tail or a strict routed connection to a short balloon tip.
Layout records the topology; View does not declare path coordinates. See
[the C3 correction](../design/issue-466-c3-routed-tail-correction-2026-09-29.md).

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
